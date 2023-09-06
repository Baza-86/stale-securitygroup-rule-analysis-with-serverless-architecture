import os
import boto3
from modules.aws_network.utilities import list_dbb_items, delete_ddb_item

def deleteDBB():
    if os.environ.get('DB_TABLE'):
        session = boto3.session.Session()
        client = session.client('dynamodb')
        ddb_table = os.environ.get('DB_TABLE')
        items = list_dbb_items(client, ddb_table=ddb_table, IndexName="protocol")
        if items['LastEvaluatedKey']:
            lastevalutedkey = items['LastEvaluatedKey']
            for item in items['Items']:
                delete_ddb_item(item)
                
    else:
        print("Please set the DB_TABLE Enviroment Varible!")
    
if __name__ == "__main__":
    deleteDBB()