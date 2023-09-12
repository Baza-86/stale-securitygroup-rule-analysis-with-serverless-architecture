import os
from modules.aws_network.securitygroup import SecurityGroup
from modules.aws_network.export import ExportNetwork
from modules.aws_network.interface import NetworkInterface
from collections import namedtuple


export_client = ExportNetwork()

def lambda_handler(event, context):

    sg_ip_scope = namedtuple('sg_ip_scope',['id','ip_addresses'])
    
    accountNo = event.get('AccountNo')
    CrossAccountRoleName = os.environ.get('CROSS_ACCOUNT_ROLE_NAME')
    if accountNo:
        ArnRole = f"arn:aws:iam::{accountNo}:role/{CrossAccountRoleName}"
        print("Using role: " + ArnRole)
        sg_client = SecurityGroup(role_arn=ArnRole, role_session_name="AssumedRoleSessionName")
        nic = NetworkInterface(role_arn=ArnRole, role_session_name="AssumedRoleSessionName")
    else:
        sg_client = SecurityGroup()
        nic = NetworkInterface()
        
    sg_client.list_security_groups()
    
    # List Security Group Rules
    sg_client.list_security_group_rules()
    security_groups_with_sgrs_mapped = []

    security_group_rules_with_reference = [sgr for sgr in sg_client.security_group_rules if 'ReferencedGroupInfo' in sgr.properties]

    for sgr in security_group_rules_with_reference:
        sg_dict = {
            'id':sgr.properties['ReferencedGroupInfo']['GroupId'],
            'ip_addresses':[]
        }
        nic.get_interfaces_by_sg_id(sg_id=[sgr.properties['ReferencedGroupInfo']['GroupId']])
        for ni in nic.iface_ids:
            sg_dict['ip_addresses'].append(nic.get_interface(nic_id=[ni]).private_ip_address)
        sg_ip = sg_ip_scope(**sg_dict)
        security_groups_with_sgrs_mapped.append(sg_ip)
    
    try:
        response = export_client.write_ddb(ddb_table=os.environ['DB_TABLE'],input_list=security_groups_with_sgrs_mapped)
        return response
    except Exception as e:
        print(e)
        error_msg = {
            "message": e.response
        }
        print(error_msg.error)
        return {
            "message": e.response
        }
    
    
    
    
