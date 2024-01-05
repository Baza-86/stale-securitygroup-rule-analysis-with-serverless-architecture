import json
import os
from modules.src.aws_discovery import awsdiscover
##from modules.aws_network.export import ExportNetwork
from datetime import datetime
import time
import calendar

region = "eu-west-2"

def lambda_handler(event, context):
    if os.environ.get('DB_TABLE'):

        accountNo = "XXXXXXXXXXX"
        CrossAccountRoleName = os.environ.get('CROSS_ACCOUNT_ROLE_NAME')
        if accountNo:
            # ArnRole = f"arn:aws:iam::{accountNo}:role/{CrossAccountRoleName}"
            # print("Using role: " + ArnRole)
            awsconfig = awsdiscover.AwsDiscovery()
            mylist = awsconfig.list_resources(resource_type="AWS::EC2::NetworkInterface")
            resources = []
            for r in mylist:
                resources.append(r.resource_id)
                myresource = awsconfig.get_resource_config_history(resource_type="AWS::EC2::NetworkInterface", resource_id=r.resource_id)
                print(myresource[0].configuration)

            print(resources)
            
            print(mylist)
            
        else:
            pass
        
        # nic.list_interfaces()
        
        # interface_details_list = []
    
        # for n in nic.iface_ids:
        #     interface_details_list.append(nic.get_interface(nic_id=[n]))
        
        # for i in interface_details_list:
        #     try:
        #         i.attachment_properties['AttachTime']=calendar.timegm(i.attachment_properties['AttachTime'].utctimetuple())
        #     except:
        #         pass
    
        # print(interface_details_list)
    
        # try:
        #     response = exp.write_ddb(ddb_table=os.environ['DB_TABLE'],input_list=interface_details_list)
        #     return response
        # except Exception as e:
        #     error_msg = {
        #         "message": e.response
        #     }
        #     print(error_msg)
        #     return {
        #         "message": e.response
        #     }
    else:
        print("Please set the DB_TABLE Enviroment Variable!")
        return {
            "message": "Please set the DB_TABLE Enviroment Variable!"
        }

if __name__ == '__main__':
    lambda_handler(None, None)