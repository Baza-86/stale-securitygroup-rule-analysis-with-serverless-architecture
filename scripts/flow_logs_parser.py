import boto3
import awswrangler as wr
import pandas as pd
import re
import time
import json
import uuid
from datetime import datetime, timedelta, date
import sys
from awsglue.utils import getResolvedOptions
from boto3.dynamodb.types import TypeDeserializer, TypeSerializer
from ipaddress import IPv4Address, IPv4Network
from hashlib import sha1
from functools import lru_cache
from copy import deepcopy
import functools
import statistics

args = getResolvedOptions(sys.argv, 
    [
        'region', 
        'FlowLogsAthenaResultsBucket', 
        'SGRulesTable', 
        'SGRulesGroupIndex', 
        'NICInterfaceTable', 
        'DynamoTableName', 
        'SGARulesUseIndex', 
        'SGSortTableName',
        'path',
        'outputCsv',
        'accountNo'
    ])

s3 = boto3.resource('s3', args['region'])
dynamodb = boto3.client('dynamodb', args['region'])

flow_logs_athena_results_bucket= args["FlowLogsAthenaResultsBucket"]
sg_rules_tbl_name= args["SGRulesTable"]
sg_rules_group_idx = args["SGRulesGroupIndex"]
nic_interface_tbl= args["NICInterfaceTable"]
dynamodb_tbl_name= args["DynamoTableName"]
sg_analysis_rules_use_idx= args["SGARulesUseIndex"]
sg_sort_table= args["SGSortTableName"]
athena_s3_prefix = args['path']
query_csv = args['outputCsv']
accountNo = args['accountNo']
date_yst = (date.today() - timedelta(1))

my_bucket = s3.Bucket(flow_logs_athena_results_bucket)

sg_rule_id_query_results = []
get_sg_ref_ips_results = []
rule_matcher_results = []
security_group_rule_parser_results = []
get_sg_rule_id_results = []
get_interface_ddb_results = []

def timer(timer_results):
    def timer_decorator(func):
        @functools.wraps(func)
        def wrapper_timer(*args, **kwargs):
            tic = time.perf_counter()
            value = func(*args, **kwargs)
            toc = time.perf_counter()
            elapsed_time = toc - tic
            timer_results.append(elapsed_time)
            print(f"Elapsed time: {elapsed_time:0.4f} seconds")
            return value
        return wrapper_timer
    return timer_decorator

def network_test(rule_block,flow_addr):
    net = IPv4Network(rule_block)
    addr = IPv4Address(flow_addr)
    result = addr in net
    return result

def protocol_test(rule_protocol,flow_protocol):
    if rule_protocol == flow_protocol or rule_protocol == '-1':
        return True
    else:
        return False

def increment_score(sgr_dict,score_value):
    sgr_dict['match_score'] += score_value

def max_score_finder(filtered_list):
    max_score = max([i['match_score'] for i in filtered_list])
    max_score_item = [f for f in filtered_list if f['match_score'] >= max_score]
    return max_score_item

def network_scorer(rule_block):
    network_score = IPv4Network(rule_block).prefixlen
    return network_score

def rule_filter(resp_list):
    ref_rules = [r for r in resp_list if r['properties'].get('ReferencedGroupInfo')]
    cidr_rules = [r for r in resp_list if r['properties'].get('CidrIpv4')]
    return (ref_rules,cidr_rules)

@timer(timer_results=get_sg_ref_ips_results)
@lru_cache(maxsize=1024)
def get_sg_ref_ips(sg_id):
    deserialize = TypeDeserializer()
    response = dynamodb.get_item(
        TableName=sg_sort_table,
        Key={'id':{'S':sg_id}}
    )
    if 'Item' in response:
        ref_ips = {k: deserialize.deserialize(v) for k, v in response['Item'].items()}['ip_addresses']
        return ref_ips
    else:
        print (f'sg id: {sg_id} not found!')

def ref_rule_dict_builder(ref_rule,ip_address):
    rr = deepcopy(ref_rule)
    rr['properties']['CidrIpv4'] = f'{ip_address}/32'
    return rr

def port_test(rule_port_from,rule_port_to,flow_port):
    if rule_port_from == -1 and rule_port_to == -1:
        return True
    elif flow_port in range(int(rule_port_from),int(rule_port_to)+1):
        return True
    else:
        return False

@timer(timer_results=rule_matcher_results)
def rule_matcher(resp_list,flow):
    [r.update({'match_score':1}) for r in resp_list]
    ref_rules,cidr_rules = rule_filter(resp_list)
    if len(ref_rules) > 0:
        for ref in ref_rules:
            ip_addresses = get_sg_ref_ips(ref['properties'].get('ReferencedGroupInfo')['GroupId'])
            for ip in ip_addresses:
                cidr_rules.append(ref_rule_dict_builder(ref,ip))
    if len(cidr_rules) > 0:
        filtered_list = [r for r in cidr_rules if network_test(r['properties'].get('CidrIpv4'),flow['addr']) and protocol_test(r['properties']['IpProtocol'],flow['protocol']) and port_test(r['properties'].get('FromPort'),r['properties'].get('ToPort'),flow['port'])]
        [increment_score(r,network_scorer(r['properties'].get('CidrIpv4'))) for r in filtered_list]
        [increment_score(r,1) for r in filtered_list if (r['properties']['FromPort'] == flow['port'] or r['properties']['ToPort'] == flow['port'])]
        [increment_score(r,0.5) for r in filtered_list if flow['port'] in range(int(r['properties']['FromPort']), int(r['properties']['ToPort'])+1)]
        [increment_score(r,1) for r in filtered_list if r['properties']['IpProtocol'] == flow['protocol']]
        [increment_score(r,0.5) for r in filtered_list if r['properties']['IpProtocol'] == '-1']
    
    max_score_list = max_score_finder(filtered_list=filtered_list)
    
    return max_score_list


@timer(timer_results=sg_rule_id_query_results)
@lru_cache(maxsize=2048)
def get_sg_rule_id_dynamo_query(sg_id):
    response=dynamodb.query(
        TableName=sg_rules_tbl_name,
        IndexName=sg_rules_group_idx,
        KeyConditions={
            "group_id":{
                'ComparisonOperator': 'EQ',
                'AttributeValueList': [ {"S": sg_id} ]
            }
        }
    )
    return response

@timer(timer_results=security_group_rule_parser_results)
def security_group_rule_parser(response, flow_dir):
    deserializer = TypeDeserializer()
    if flow_dir == 'egress':
        resp_list = [{k: deserializer.deserialize(v) for k, v in r.items()} for r in response['Items'] if r['properties']['M']['IsEgress']['BOOL'] == True]
    else:
        resp_list = [{k: deserializer.deserialize(v) for k, v in r.items()} for r in response['Items'] if r['properties']['M']['IsEgress']['BOOL'] == False]
    return resp_list

@timer(timer_results=get_sg_rule_id_results)
def get_sg_rule_id(sg_id, flow_count, protocol, flow_dir, addr, dstport, accountNo):
    try:
        response = get_sg_rule_id_dynamo_query(sg_id)

        flow_object = {
            'flow_count': flow_count,
            'addr': addr,
            'port': dstport,
            'protocol': protocol,
        }
    except Exception as e: 
        print("There was an error while trying to perform DynamoDB get operation on Rules table: "+str(e))
       
    resp_list = security_group_rule_parser(response, flow_dir)
        
    try:
        result = rule_matcher(resp_list,flow_object)[0]
        print(f"rule found for flow: sg_rule_id={result['id']},sg_id={result['group_id']},flow_dir={flow_dir},protocol={flow_object['protocol']},addr={flow_object['addr']},dstport={flow_object['port']}")
        insert_usage_data(sg_rule_id=result['id'],sg_id=result['group_id'],flow_dir=flow_dir, accountNo=accountNo, **flow_object)
    except Exception as e:
        print(f'no rule found for flow:{flow_object} - {flow_dir}')
        print(f'error: {e}')
        # raise e

    
def insert_usage_data(sg_rule_id, sg_id, flow_dir, flow_count, addr, port, accountNo, protocol):
    addr_rule_hash = [sg_rule_id,addr,port,protocol]
    hash_digest = sha1(str(addr_rule_hash).encode()).hexdigest()
    try:
        checkRuleIdExists=dynamodb.query(
            TableName=dynamodb_tbl_name,
            KeyConditionExpression="sgr_flow_hash = :sgr_flow_hash",
            ExpressionAttributeValues={':sgr_flow_hash':{'S':hash_digest}}
        )
        if checkRuleIdExists['Count'] == 0:
            insertItemResponse = dynamodb.put_item(
              TableName=dynamodb_tbl_name,
              Item={
                    'sgr_flow_hash': {'S':str(hash_digest)},
                    'rule_id': {'S':sg_rule_id},
                    'sg_id': {'S':str(sg_id)},
                    'flow_direction': {'S':str(flow_dir)},
                    'protocol': {'S':str(protocol)},
                    'addr': {'S':str(addr)},
                    'dstport': {'N':str(port)},
                    'used_times': {'N':str(flow_count)},
                    'sg_rule_last_used': {'S':date_yst.strftime('%Y-%m-%d')},
                    'account_no': {'S': accountNo}
                }
            )
        else:
            updateItemResponse = dynamodb.update_item(
                TableName=dynamodb_tbl_name,
                Key={
                  'sgr_flow_hash': {'S': str(hash_digest)},
                  'account_no': {'S': accountNo}
                },
                UpdateExpression='SET used_times = used_times + :val, sg_rule_last_used = :newlastused',
                ExpressionAttributeValues={
                    ':val': {'N':str(flow_count)},
                    ':newlastused': {'S':date_yst.strftime('%Y-%m-%d')}
                },
                ReturnValues="UPDATED_NEW"
            )
    except Exception as e: 
        print("There was an error while trying to perform DynamoDB insert operation on Usage table: "+str(e))
        # raise e


@timer(timer_results=get_interface_ddb_results)
@lru_cache(maxsize=1024)
def get_interface_ddb(id:str) -> dict:
    deserialize = TypeDeserializer()
    response = dynamodb.get_item(
        TableName=nic_interface_tbl,
        Key={'id':{'S':id}}
    )
    if 'Item' in response:
        nic_dict = {k: deserialize.deserialize(v) for k, v in response['Item'].items()}
        return nic_dict
    else:
        print (f'nic id: {id} not found!')




def main():
    query_csv_path = f's3://{flow_logs_athena_results_bucket}/{athena_s3_prefix}/{date_yst.isoformat().replace("-","/")}/{query_csv}'
    start = time.time()
    print("Writing rules data to DynamoDB table- started at: "+str(datetime.now()))
    dfs = wr.s3.read_csv(path=query_csv_path, chunksize=1000, encoding = 'ISO-8859-1')
    for df in dfs:
        try:
            df_row_count = len(df) - 1
            df['protocol'] = df['protocol'].map({6: 'tcp', 17: 'udp', 1: 'icmp'})
            for index, row in df.iterrows():
                print(f'processing row {index} of {df_row_count}')
                if row is not None and 'dstport' in row:
                    nw_int_info = get_interface_ddb(id=row['interface_id'])
                    
                    for grp in nw_int_info['security_group_ids']:
                        print(grp, row['flow_count'], row['protocol'],row['flow_direction'],row['addr'],row['dstport'])
                        get_sg_rule_id(grp, row['flow_count'], row['protocol'],row['flow_direction'],row['addr'],row['dstport'], accountNo)
        except KeyError:
            pass
        except Exception as e:
            print(f'error: {e}')
            # raise e
    
    #print(f'sg_rule_id_query cache stats')
    #print(get_sg_rule_id_dynamo_query.cache_info())
    try:
        print(f'quantiles for sg_rule_id_query: {statistics.quantiles(sg_rule_id_query_results)}')
    
        #print(f'get_sg_ref_ips cache stats')
        #print(get_sg_ref_ips.cache_info())
        print(f'quantiles for get_sg_ref_ips: {statistics.quantiles(get_sg_ref_ips_results)}')
        
        print(f'quantiles for rule_matcher: {statistics.quantiles(rule_matcher_results)}')
        
        #print(f'security_group_rule_parser cache stats')
        #print(security_group_rule_parser.cache_info())
        print(f'quantiles for security_group_rule_parser: {statistics.quantiles(security_group_rule_parser_results)}')
        
        print(f'quantiles for get_sg_rule_id: {statistics.quantiles(get_sg_rule_id_results)}')
        
        print(f'quantiles for get_interface_ddb: {statistics.quantiles(get_interface_ddb_results)}')
        

        print("Writing rules data to DynamoDB table- completed at: "+str(datetime.now()))
    except statistics.StatisticsError as e:
        print(e)
        print('error printing runtime statistics, could indicate failure in analysis functions, check further up error log')
    except Exception as e:
        print(e)
    finally:
        end = time.time()
        print("Total time taken in minutes: "+str((end - start)/60))


if __name__ == "__main__":
    main()