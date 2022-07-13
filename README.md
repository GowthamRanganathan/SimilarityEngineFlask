
# Similarity Engine

The Jupyter notebook Data_Pre-Process_Vectorization.ipynb loads the following company name data set 
https://drive.google.com/open?id=1pI7dTzPZ0dRx-aOu9phnzlr50_oySAiE
(could not upload the data set here since the size is more than 25MB please use the above url to download the dataset)
The dataset contains 663000 company names which have similar and duplicate Company names.
the code used in this project was take from 
https://medium.com/wbaa/https-medium-com-ingwbaa-boosting-selection-of-the-most-similar-entities-in-large-scale-datasets-450b3242e618


# Data_Pre-Process_Vectorization.ipynb
1. Loads data
2. Normalizes and does preprocessing
3. Creates ngrams of each company tile
5. Creates a sparse matrix 
6. Calculates matches/similarity score of each ngram of each title
7. Based on similarity threshhold specified (1 is exact match)stores the top 10000(can be specified) generates matches with other titles within the dataset
8. Saves the result as matched.pickle

[#Data_preprocessing_vectorization_in_AWS.ipynb
is the same file as Data_Pre_Vector.ipynb but I used it on AWS Sagemaker jupyter notebook.
it does the same thing as Data_Pre_Vector.ipynb but uses S3 to load data]

#Post_Precessing_addingID_Deduplication.ipynb 
In  this jupyternotebook I added unique IDs to Company names and added two columns with IDs. The resulting dataframe has been saved as matched_id.pickle 
1. Load matched.pickle
2. Re-name column titles
3. Add unique ID to Company titles
4. Eliminate vice-verca enteries/duplicate entries of the Data_Pre_Vector
5. Save dataframe as matched_id_dedup.pickle


Flask_rest_api.py deploys the web app that uses the  matched_id_dedup.pickle file as source data 

#Steps to run Flask_rest_api.py in VIRTUAL ENV
1. create a folder XXX in your local computer
2. In XXX copy 
     * the folder templates
     * matched_id_dedup.pickle
     * Flask_rest_api.py
3. from command prompt ( I am using windows) locate the folder XXX
4. py -m venv env ( just first time)
5. env\Scripts\activate (to activate virtual env)
6. pip install flask (first time) [you will need to pip install the libraries imported in the Flask_rest_api.py file]
7. set FLASK_APP=Flask_rest_api.py
8. flask run
9. GO TO Webbrowser http://127.0.0.1:5000/
10. Click on "First Similar item" to see the first items that are similar 
11. to see 100 similar items of the list http://127.0.0.1:5000/lang/100  [ you can replace 100 with any N number]
12.To deactivate venv type deactivate in cmd

