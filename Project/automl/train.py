# train.py
from flaml import AutoML
from flaml.data import get_output_from_log
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
import pymongo
from pymongo import MongoClient
import pandas as pd
import pickle
import json
import matplotlib
matplotlib.use('Agg')  # Use the 'Agg' backend
import matplotlib.pyplot as plt
import numpy as np



#fetch mongo db parameters from the json file
with open("C:/Users/ayesha.amjad/Documents/GitHub/BigDataProject/MLOPS/Project/webpage/mongo_params.json", "r") as json_file:
    mongo_params = json.load(json_file)

# Connect to the MongoDB container
mongo_uri = mongo_params["Client"]
database_name = mongo_params["db"]
collection_name = mongo_params["collection"]

client = MongoClient(mongo_uri)
db = client[database_name]
collection = db[collection_name]
cursor = collection.find()
data = list(cursor)
df = pd.DataFrame(data)

# Connect to the MongoDB container
#client = MongoClient('mongodb://localhost:27017')
#db = client['Customers']
#collection = db['ChurnData']
#cursor = collection.find()
#data = list(cursor)
#df = pd.DataFrame(data)


df[['RowNumber', 'CustomerId', 'CreditScore', 'Age', 'Tenure', 'NumOfProducts', 'HasCrCard', 'IsActiveMember']] = df[['RowNumber', 'CustomerId', 'CreditScore', 'Age', 'Tenure', 'NumOfProducts', 'HasCrCard', 'IsActiveMember']].astype(int)
df[['Balance', 'EstimatedSalary']] = df[['Balance', 'EstimatedSalary']].astype(float)

#identify and drop contant value columns
constant_columns = [col for col in df.columns if df[col].nunique() == 1]
df = df.drop(constant_columns, axis=1)


#identify and drop sequential columns
sequential_columns = []
for col in df.columns:
    if df[col].dtype in [np.int64, np.int32, np.float64]:
        differences = np.diff(df[col])
        if np.all(differences == differences[0]):
            sequential_columns.append(col)

df = df.drop(sequential_columns, axis=1)
df = df.drop('_id', axis=1)

df = df.drop(columns=['CustomerId', 'Surname'], axis=1)


#deal with missing values
df = df.replace(r'^\s*$', pd.NA, regex=True)

#identify numeric and categorical variables
numeric_cols = df.select_dtypes(include=np.number).columns
categorical_cols = df.select_dtypes(include=np.object).columns

# Mean imputation for numeric fields and Mode imputation for categorical fields
df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
df[categorical_cols] = df[categorical_cols].fillna(df[categorical_cols].mode().iloc[0])



#fetch automl parameters from the json file
with open("C:/Users/ayesha.amjad/Documents/GitHub/BigDataProject/MLOPS/Project/webpage/automl_params.json", "r") as json_file:
    automl_params = json.load(json_file)


#X,y
target_col = automl_params["target"]
X=df.drop(columns=[target_col])
y=df[target_col]
y

#Test train split
split_percentage = int(automl_params["test_size"])/100
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=split_percentage, random_state=42)

#encoding and pre-processing
le = LabelEncoder()
for column in X.columns:
    if X[column].dtype == object:
        X[column] = le.fit_transform(X[column])


#set evaluation metrics as per different tasks
task = automl_params["task"].lower()
if task == 'classification':
    metric = 'roc_auc'
else:
    metric = 'r2'


automl = AutoML()   
automl_settings = {
    "time_budget": 60,
    "metric": metric,
    "task": automl_params["task"].lower(),
    "log_file_name": 'automl.log',
    "model_history": True,
}


# Train the model using the data
automl.fit(X_train=X_train, y_train=y_train, dataframe=data, **automl_settings)

# Save the best model for deployment
best_model = automl.model
best_score = automl.best_loss
print(best_model)
print(best_score)


'''retrieve best config and best learner'''
print('Best ML leaner:', automl.best_estimator)
print('Best hyperparmeter config:', automl.best_config)
print('Best accuracy on validation data: {0:.4g}'.format(1-automl.best_loss))
print('Training duration of best run: {0:.4g} s'.format(automl.best_config_train_time))


from flaml.data import get_output_from_log
time_history, best_valid_loss_history, valid_loss_history, config_history, metric_history = \
    get_output_from_log(filename=automl_settings['log_file_name'], time_budget=240)
for config in config_history:
    print(config)


#Save best performing model graph
plt.title('Learning Curve')
plt.xlabel('Wall Clock Time (s)')
plt.ylabel('Validation Accuracy')
plt.scatter(time_history, 1 - np.array(valid_loss_history))
plt.step(time_history, 1 - np.array(best_valid_loss_history), where='post')
plt.show()
plt.savefig(r'C:\Users\ayesha.amjad\Documents\GitHub\BigDataProject\MLOPS\Project\model\roc_auc_curve.jpg')  


# Save the best model to a file or cloud storage for later use
model_path =r'C:\Users\ayesha.amjad\Documents\GitHub\BigDataProject\MLOPS\Project\model\bestmodel.pkl'

with open(model_path, 'wb') as file:
    pickle.dump(best_model, file)

#best_model.save_model('/app/best_model')
