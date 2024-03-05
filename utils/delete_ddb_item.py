from argparse import ArgumentParser
import csv
import boto3

def delete_record(ddb_client,table_name,pk,sk):
    response = ddb_client.delete_item(
        TableName=table_name,
        Key={
            'sgr_flow_hash': {'S':pk},
            'account_no': {'S': sk}
        },
        ReturnValues='ALL_OLD'
    )
    return response

if __name__ == '__main__':
    parser = ArgumentParser()

    parser.add_argument(
        '--item_csv',
        type=str,
        help='''
            the csv containing a list of records
        '''
    )

    parser.add_argument(
        '--aws_profile',
        type=str,
        help='the name of the aws profile to use'
    )

    parser.add_argument(
        '--aws_region',
        type=str,
        help='the aws region to make the call against'
    )

    parser.add_argument(
        '--ddb_table',
        type=str,
        help='the dynamodb table to delete the records from'
    )

    args = parser.parse_args()

    session = boto3.session.Session(profile_name=args.aws_profile,region_name=args.aws_region)
    client = session.client('dynamodb')

    with open(args.item_csv, 'r') as f:
        reader = csv.DictReader(f)
        for r in reader:
            print(r)
            response = delete_record(
                    ddb_client=client,
                    table_name=args.ddb_table,
                    pk=r['sgr_flow_hash'],
                    sk=r['account_no']
                )
            print(response)