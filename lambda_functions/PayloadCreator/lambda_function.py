import json

def lambda_handler(event, context):
    outputFileArray = event['outputFileArray']
    outputCsv = event['outputCsv']
    outputFileArray.append(outputCsv)
    outputRows = event['outputRows']
    
    queryParams = event['queryParams']
    
    queryParams['queryOffset'] += 10
    
    payload_dict = {
        'queryParams': queryParams,
        'outputFileArray': outputFileArray,
        'outputRows': outputRows
    }
    
    return payload_dict