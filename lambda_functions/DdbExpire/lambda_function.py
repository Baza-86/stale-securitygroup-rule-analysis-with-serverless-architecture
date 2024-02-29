import boto3
from datetime import datetime, timedelta
import os


def lambda_handler(event, context):
    # Initialize the DynamoDB resource
    dynamodb = boto3.resource('dynamodb')
    table_name = os.environ.get('DB_TABLE')
    analysis_table = dynamodb.Table(table_name)
    #print(analysis_table.key_schema)
    # Set the TTL in number of DAYS
    ttl_days = int(os.environ.get('TTL_UPDATE'))
    print(event['data'])
    for e in event['data']:
        print(e)
        try:
            ttl_timestamp = int((datetime.now() + timedelta(days=ttl_days)).timestamp())
            # Update the TTL attribute for each item
            print(e['sgr_flow_hash'])
            print(e['account_no'])
            response = analysis_table.update_item(
                Key={
                    'sgr_flow_hash': str(e['sgr_flow_hash']),
                    'account_no': e['account_no']
                },
                UpdateExpression='SET #ttl_attr = :newttl',
                ExpressionAttributeNames={'#ttl_attr': 'ttl'},
                ExpressionAttributeValues={':newttl': ttl_timestamp},
                ReturnValues="UPDATED_NEW"
            )
            print(f"{response}")
        except Exception as e:
            print(f"Error: {e}")
