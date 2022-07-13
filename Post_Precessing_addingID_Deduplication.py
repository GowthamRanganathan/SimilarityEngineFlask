
from collections import defaultdict
import numpy as np
import pickle
import pandas as pd

with open('matched.pickle','rb') as f:
    loaded_obj = pickle.load(f)

loaded_obj.rename(columns={"left_side": "CompanyName1", "right_side": "CompanyName2"},inplace = True)
loaded_obj.reset_index(drop=True,inplace=True)
unique_company_list=loaded_obj.CompanyName1.unique()
### Generating Unique IDs for Unique Company Names

test_list = loaded_obj.CompanyName1


# using list comprehension + defaultdict + lambda
# assigning ids to values 
temp = defaultdict(lambda: len(temp)) 
res = [temp[ele] for ele in test_list]


# print result 
#print("The ids of assigned values is : " + str(res))



loaded_obj['CompanyName1_ID']=res

test_list2 = loaded_obj.CompanyName2

res2 = [temp[ele] for ele in test_list2]

#print result
#print("The ids of assigned values is : " + str(res2))

loaded_obj['CompanyName2_ID']=res2
# ### Eliminating vice-verca enteries e.g index 4 and 5 above...keeping first entry
duplicate_data=pd.DataFrame()
duplicate_data['dup_sim']=loaded_obj.similairity.duplicated(keep='first')
#duplicate_data.head(10)
loaded_obj.loc[loaded_obj.similairity.duplicated(),:]
drop_df=loaded_obj.drop_duplicates(subset=['similairity'])

#### Create a column that will be used to take user input of Match Not Match


drop_df['Match_nonMatch']=0
drop_df['isSame']=0
drop_df['ID_Auto1']=np.arange(1,drop_df.shape[0]+1)
drop_df.reset_index(drop=True)

with open('matched_id_dedup.pickle', 'wb') as f:
    pickle.dump(drop_df, f)

