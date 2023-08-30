import os
from modules.aws_network.securitygroup import SecurityGroup
from modules.aws_network.export import ExportNetwork
from modules.aws_network.interface import NetworkInterface


export_client = ExportNetwork()

def lambda_handler(event, context):
    
    accountNo = None
    CrossAccountRoleName = os.environ.get('CROSS_ACCOUNT_ROLE_NAME')
    if accountNo:
        ArnRole = f"arn:aws:iam::{accountNo}:role/{CrossAccountRoleName}"
        print("Using role: " + ArnRole)
        sg_client = SecurityGroup(role_arn=ArnRole, role_session_name="AssumedRoleSessionName")
        nic = NetworkInterface(role_arn=ArnRole, role_session_name="AssumedRoleSessionName")
    else:
        sg_client = SecurityGroup(aws_profile="LambdaEc2Access-XXXXXXXXXX")
        nic = NetworkInterface(aws_profile="LambdaEc2Access-XXXXXXXXXX")
        
    sg_client.list_security_groups()
    
    # List Security Group Rules
    security_group_rules = sg_client.list_security_group_rules()
    security_groups_with_sgrs_mapped = {}

    nic.list_interfaces()

    interface_details_list = []

    for n in nic.iface_ids:
            interface_details_list.append(nic.get_interface(nic_id=[n]))

    for sgr in security_group_rules:
        if sgr.group_id in security_groups_with_sgrs_mapped:
            pass
        else:
            security_groups_with_sgrs_mapped[sgr.group_id] = {"sgr_ids": [sgr.id], "nic_details": {}}

    security_group_id_list = list(security_groups_with_sgrs_mapped.keys())

    sgAndNICs = nic.get_interfaces_by_sg_id(sg_id=security_group_id_list)
    
    for interface in sgAndNICs:
         thisNIC = nic.get_interface(nic_id=[interface.id])
         for security_group_id in thisNIC.security_group_ids:
             print(thisNIC)
             security_groups_with_sgrs_mapped[security_group_id]['nic_details'].update({"private_ip_address": thisNIC.private_ip_address})

    print(security_groups_with_sgrs_mapped)

if __name__ == "__main__":
    event = []
    context = []
    lambda_handler(event, context)