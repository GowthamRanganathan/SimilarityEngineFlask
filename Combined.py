import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from scipy.sparse import csr_matrix
import sparse_dot_topn.sparse_dot_topn as ct
from ftfy import fix_text
import re
from collections import defaultdict
import pickle
import boto3
import time

s3_client = boto3.client('s3')
bucket = 'similarityenginepilot'
key = 'similarityengine.csv'
localFilename = 'similarityengine.csv'
s3_client.download_file(bucket, key, localFilename)


def normalize(string):
    string = fix_text(string)  # fix text
    string = string.encode("ascii", errors="ignore").decode()  # remove non ascii chars
    string = string.lower()
    string = string.title()  # normalise case - capital at start of each word
    chars_to_remove = [")", "(", ".", "|", "[", "]", "{", "}", "'", "#"]
    # rx = '[' + re.escape(''.join(chars_to_remove)) + ']'
    # string = re.sub(rx, '', string)
    string = string.replace('&', 'and')
    string = string.replace('Inch', 'In')
    string = string.replace('.5', '1/2')
    string = string.replace(',', ' ')
    string = string.replace('-', ' ')
    string = string.replace('-', ' ')

    string = re.sub(' +', ' ', string).strip()  # get rid of multiple spaces and replace with a single
    string = ' ' + string + ' '  # pad names for ngrams...
    # string = re.sub(r'[,-./]|\sbd', r'', string)
    # string = re.sub(r'[,-./]|\sbd', r'', string)
    return string


def ngrams(string, n=3):
    ngrams = zip(*[string[i:] for i in range(n)])
    return [''.join(ngram) for ngram in ngrams]


def top(A, B, ntop, lower_bound=0):
    # force A and B as a CSR matrix.
    # If they have already been CSR, there is no overhead
    A = A.tocsr()
    B = B.tocsr()
    M, _ = A.shape
    _, N = B.shape

    idx_dtype = np.int32

    nnz_max = M * ntop

    indptr = np.zeros(M + 1, dtype=idx_dtype)
    indices = np.zeros(nnz_max, dtype=idx_dtype)
    data = np.zeros(nnz_max, dtype=A.dtype)

    ct.sparse_dot_topn(
        M, N, np.asarray(A.indptr, dtype=idx_dtype),
        np.asarray(A.indices, dtype=idx_dtype),
        A.data,
        np.asarray(B.indptr, dtype=idx_dtype),
        np.asarray(B.indices, dtype=idx_dtype),
        B.data,
        ntop,
        lower_bound,
        indptr, indices, data)

    return csr_matrix((data, indices, indptr), shape=(M, N))


def get_matches_df(sparse_matrix, name_vector, name_ID, top=100):
    non_zeros = sparse_matrix.nonzero()

    sparserows = non_zeros[0]
    sparsecols = non_zeros[1]

    if top:
        nr_matches = top
    else:
        nr_matches = sparsecols.size

    left_side = np.empty([nr_matches], dtype=object)
    right_side = np.empty([nr_matches], dtype=object)
    left_side_ID = np.empty([nr_matches], dtype=object)
    right_side_ID = np.empty([nr_matches], dtype=object)
    similairity = np.zeros(nr_matches)

    for index in range(0, nr_matches):
        left_side[index] = name_vector[sparserows[index]]
        left_side_ID[index] = name_ID[sparserows[index]]
        right_side[index] = name_vector[sparsecols[index]]
        right_side_ID[index] = name_ID[sparsecols[index]]
        similairity[index] = round(sparse_matrix.data[index], 2)

    return pd.DataFrame({'left_side': left_side,
                         'left_side_ID': left_side_ID,
                         'right_side': right_side,
                         'right_side_ID': right_side_ID,
                         'similairity': similairity})


def main():
    print('start')
    start_time = time.time()
    names = pd.read_csv('similarityengine.csv')
    # names = pd.read_csv("similarityengine.csv")

    Item = pd.DataFrame()
    Item['Title'] = names['Item Title']

    # Normalize Data
    data1 = []
    for row in Item.itertuples():
        data2 = normalize(row.Title)
        data1.append(data2)
    # add a column that stores the normalized version of the title
    Item['Title_Normalized'] = data1
    temp = defaultdict(lambda: len(temp))
    ID = [temp[ele] for ele in Item['Title_Normalized']]
    # Assing Unique ID to Unique Normalized Title
    Item['Item_ID'] = ID
    # Drop Duplicate items
    Item = Item.drop_duplicates(subset='Item_ID', keep="first")

    # Vectorize Normalized Title Column
    vectorizer = TfidfVectorizer(min_df=1, analyzer=ngrams)
    tf_idf_matrix = vectorizer.fit_transform(Item.Title_Normalized)

    matches = top(tf_idf_matrix, tf_idf_matrix.transpose(), 10, 0.7)
    matches_df = get_matches_df(matches, Item.Title_Normalized, Item.Item_ID,
                                30)  # calling the function get_matches_df()
    matches_df = matches_df[matches_df['similairity'] < 0.99999]  # Remove all exact matches

    # Eleminate Vice Versa
    matches_df["trans"] = matches_df.apply(
        lambda row: (min(row['left_side_ID'], row['right_side_ID']), max(row['left_side_ID'], row['right_side_ID'])),
        axis=1)
    Similar_Item_List = matches_df.drop_duplicates("trans")
    # Save Similar_Item_list as pickle file for validation by user
    Similar_Item_List.insert(6, 'Match_nonMatch', 0)
    Similar_Item_List.insert(7, 'isSame', 0)
    Similar_Item_List.insert(8, 'ID_Auto', np.arange(1, Similar_Item_List.shape[0] + 1))
    # Similar_Item_List.to_csv('SimilarItem_list.csv', index=False)
    with open('matched.pickle', 'wb') as f:
        pickle.dump(Similar_Item_List, f)
    # Creating a dataset without items that will be validated by user
    Similar_Item_ID = []
    for row in Similar_Item_List.itertuples():
        ID_L = row.left_side_ID
        ID_R = row.right_side_ID
        Similar_Item_ID.append(ID_L)
        Similar_Item_ID.append(ID_R)
    Similar_Item_ID = list(dict.fromkeys(Similar_Item_ID))
    Item2 = Item.loc[~Item.index.isin(Similar_Item_ID)]
    Item2.to_csv('Items_Without_SimilarOnes.csv', index=False)
    s3_client.upload_file("Items_Without_SimilarOnes.csv", bucket, 'Items_Without_SimilarOnes.csv')
    print("--- %s seconds ---" % (time.time() - start_time))
    print('End')


if __name__ == '__main__':
    main()
