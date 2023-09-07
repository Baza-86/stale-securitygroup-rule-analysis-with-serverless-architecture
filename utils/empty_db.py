import os
import boto3
from modules.aws_network.utilities import list_dbb_items, delete_ddb_item

def deleteDBB():
    if os.environ.get('DB_TABLE'):
        session = boto3.session.Session()
        client = session.client('dynamodb')
        ddb_table = os.environ.get('DB_TABLE')
        delete_items(client=client, ddb_table=ddb_table)
           
    else:
        print("Please set the DB_TABLE Enviroment Varible!")

def delete_items(client, ddb_table):
    lastevalutedkey = "start"
    while lastevalutedkey != None:
        items = list_dbb_items(client, ddb_table=ddb_table, IndexName="protocol")
        for item in items['Items']:
            delete_ddb_item(client=client, item=item, ddb_table=ddb_table)
        if items['LastEvaluatedKey']:
            lastevalutedkey = items['LastEvaluatedKey']
        else:
            print("Setting lastevalutedkey is too none..")
            lastevalutedkey = None
            print("lastevalutedkey is now none..")


        print(items['Count'])
        print(items['LastEvaluatedKey'])
    
if __name__ == "__main__":
    deleteDBB()