import operator
from flask import Flask, request, jsonify, render_template
from configparser import ConfigParser
import json
import pickle
import requests
import csv
import boto3
import uuid
import os
import pandas

app = Flask(__name__)
config = ConfigParser()
config.read("config.ini")

bucketName = config.get('AWS', 'bucketName')
validateRecordsBucket = config.get('AWS', 'validateRecordsBucket')
itemsWithoutDuplicateBucket = config.get('AWS', 'itemsWithoutDuplicateBucket')

session = boto3.Session(
    aws_access_key_id=str(os.environ.get('aws_access_key_id')),
    aws_secret_access_key=str(os.environ.get('aws_secret_access_key'))
)

s3Client = session.client('s3')

if os.path.exists('matched.pickle'):
    os.remove('matched.pickle')
else:
    print("The file does not exist")
s3Client.download_file(bucketName, 'matched.pickle', 'matched.pickle')
#
# with open('matched.pickle', 'rb') as f:
#     loaded_obj = pickle.load(f)

loaded_obj = pandas.read_pickle('matched.pickle')


# print(loaded_obj)


# took first 10 records
# dataFrame = loaded_obj[:10]
# dicRecord=loaded_obj.to_dict('records')
# dicRecord= dicRecord[:10]


@app.route('/reload', methods=['GET', 'POST'])
def reload():
    loaded_obj.loc[:, 'isSame'] = 0
    return jsonify(True)


@app.route('/', methods=['GET'])
def home():
    return render_template("dashboard.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/upload")
def upload():
    return render_template("upload.html")


@app.route("/validatedRecords")
def validatedRecords():
    data = loadS3File()
    # To sort the class list with itemgetter in place...
    data.sort(key=operator.itemgetter('time'), reverse=True)
    return render_template("ValidatedRecords.html", data=data)


@app.route("/generateFile", methods=['POST'])
def generateFile():
    try:
        with open('records.csv', 'w', newline='') as csvFile:
            writer = csv.writer(csvFile, quoting=csv.QUOTE_MINIMAL)
            # header
            writer.writerow(['Title_ID', 'Title', 'Similar_Title_ID', 'Similar_Title'])
            # body
            res = json.loads(request.form['data'])
            for val in res:
                writer.writerow([val['titleId'], val['title'], val['similarTitleId'], val['similarTitle']])
            csvFile.close()
            guid = str(uuid.uuid4())
            fileName = guid + ".csv"

            s3Client.upload_file(
                'records.csv', validateRecordsBucket, fileName,
                ExtraArgs={'ACL': 'public-read'}
            )

            key = guid + "_rec.csv"
            s3Client.download_file(bucketName, 'Items_Without_SimilarOnes.csv', 'Items_Without_SimilarOnes.csv')
            s3Client.upload_file(
                'Items_Without_SimilarOnes.csv', itemsWithoutDuplicateBucket, key,
                ExtraArgs={'ACL': 'public-read'}
            )

            os.remove('records.csv')
            os.remove('Items_Without_SimilarOnes.csv')
    except Exception as ex:
        print(ex)
    return jsonify("")


def loadS3File():
    # s3Client = session.client('s3')
    resp = s3Client.list_objects_v2(Bucket=validateRecordsBucket)
    data = []
    contents = resp.get('Contents')
    if contents:
        for obj in contents:
            file = obj['Key']
            modifiedTime = obj['LastModified']
            get_last_modified = modifiedTime.strftime('%B %d, %Y %H:%M:%S')
            value = file.split(".", maxsplit=1)[0]
            extension = file.split(".")[1]
            # take only csv files
            item = {"description": value, "time": get_last_modified,
                    "url": f"https://{validateRecordsBucket}.s3.amazonaws.com/{file}",
                    "download2url": f"https://{itemsWithoutDuplicateBucket}.s3.amazonaws.com/{value}_rec.{extension}"}
            data.append(item)
    return data


@app.route('/clearS3Bucket', methods=['POST'])
def clearS3Bucket():
    global loaded_obj
    s3 = session.resource('s3')
    bucket = s3.Bucket(validateRecordsBucket)
    bucket.objects.all().delete()
    bucket2 = s3.Bucket(itemsWithoutDuplicateBucket)
    bucket2.objects.all().delete()
    if os.path.exists('matched.pickle'):
        os.remove('matched.pickle')
    else:
        print("The file does not exist")
    s3Client.download_file(bucketName, 'matched.pickle', 'matched.pickle')
    loaded_obj = pandas.read_pickle('matched.pickle')
    return jsonify("")


@app.route('/lang2', methods=['GET'])
def apiTest():
    print(f'{request.url_root}api/v1.0/task')
    res = requests.get(url=f'{request.url_root}api/v1.0/task')
    res = res.json()
    res = res['message']
    return render_template("lang2.html", data=res)


@app.route('/validate/<int:itemNo>', methods=['GET'])
def lang3(itemNo):
    dicRecord = createRowSpan(itemNo)
    return render_template('validate.html', data=dicRecord, id=itemNo, totalRecord=len(loaded_obj))


@app.route('/lang/<int:number_item>', methods=['GET'])
def lang(number_item):
    df2 = loaded_obj.head(number_item)
    dc1 = df2.to_dict('records')
    return jsonify({'data': dc1})


@app.route('/similar', methods=['GET', 'POST'])
def similarityFunc():
    if request.form.get('val') == 'true':
        loaded_obj.loc[loaded_obj['ID_Auto'] == int(request.form.get('id')), 'isSame'] = 1
    elif request.form.get('val') == 'false':
        loaded_obj.loc[loaded_obj['ID_Auto'] == int(request.form.get('id')), 'isSame'] = 2
    return jsonify({'id': request.form.get('val')})


@app.route('/api/v1.0/record', methods=['POST'])
def records():
    res = json.loads(request.form['data'])
    for val in res:
        if val['ID'] != '':
            loaded_obj.drop(loaded_obj.loc[loaded_obj['ID_Auto'] == int(val['ID'])].index, inplace=True)
    return {"message": "inside post method"}, 200


@app.route('/invokeStepfunction', methods=['GET', 'POST'])
def executeStepFunction():
    returnVal = True
    stepFunctionClient = session.client('stepfunctions', region_name=config.get('AWS', 'region_name'))
    data = {'Comment': '', }
    json_data = json.dumps(data)
    try:
        response = stepFunctionClient.start_execution(
            stateMachineArn=config.get('AWS', 'StepFunctionARN'),
            name=str(uuid.uuid4()),
            input=json_data
        )
    except Exception as ex:
        returnVal = False
    return jsonify(returnVal)


@app.route('/invokeS3', methods=['GET', 'POST'])
def executeS3UploadFunction():
    # s3Client = session.client('s3')
    fileName = 'similarityengine.csv'
    obj = request.files.getlist('file')
    similarity_data = pandas.DataFrame()
    for file in obj:
        df = pandas.read_csv(file)
        similarity_data = pandas.concat((df, similarity_data), axis=0)

    similarity_data.to_csv(fileName, encoding='utf-8', index=False)

    try:
        s3Client.upload_file(fileName, bucketName, fileName)
        object_url = "https://{0}.s3.amazonaws.com/{1}".format(bucketName, fileName)
        return jsonify({'url': object_url})
    except Exception as ex:
        print(ex)
        return jsonify(False)


def createRowSpan(idNo):
    dataFrame = loaded_obj[idNo:idNo + 10]
    dicRecord = loaded_obj.to_dict('records')
    dicRecord = dicRecord[idNo:idNo + 10]
    groupByRecords = dataFrame.groupby(['left_side_ID']).size()
    for idx, res in enumerate(dicRecord):
        if groupByRecords[res['left_side_ID']] == 1:
            res['rowSpan'] = 1
        else:
            if idx == 0:
                res['rowSpan'] = groupByRecords[res['left_side_ID']]
            else:
                if res['left_side_ID'] == dicRecord[idx - 1]['left_side_ID']:
                    res['rowSpan'] = 0
                else:
                    res['rowSpan'] = groupByRecords[res['left_side_ID']]
    return dicRecord


if __name__ == '__main__':
    app.run()
