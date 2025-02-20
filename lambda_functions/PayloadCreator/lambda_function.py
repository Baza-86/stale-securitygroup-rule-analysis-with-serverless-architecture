from datetime import datetime, timedelta, date

def lambda_handler(event, context):
    print(event.keys())
    if 'generatedDate' in event.keys(): 
        outputFileArray = event['outputFileArray']
        outputCsv = event['outputCsv']
        outputFileArray.append(outputCsv)
        outputRows = event['outputRows']
        
        queryParams = event['queryParams']
        
        queryParams['queryOffset'] += queryParams['queryLimit']
        
        payload_dict = {
        'queryParams': queryParams,
        'outputFileArray': outputFileArray,
        'outputRows': outputRows
    }
    else:
        print("date to be added to output")
        date_yst = str(date.today() - timedelta(1))
        payload_dict = {
        'date': date_yst,
        'day': date_yst.split("-")[2],
        'month': date_yst.split("-")[1],
        'year': date_yst.split("-")[0]
    }
    
    return payload_dict