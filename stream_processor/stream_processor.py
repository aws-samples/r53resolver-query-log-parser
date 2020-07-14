import json
import boto3
import os
from boto3 import resource
from tld import get_fld
import urllib.request
import gzip
import base64
import re
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
ddb = resource('dynamodb')

malicious_domains = os.environ.get('MALICIOUS_DOMAINS_TABLE')



""" Function to validate if Top Level Domain is malicious - ie. does it exist in malicious domains DDB table?""" 
def is_malicious_domain( record ):
    
    logger.info("funct:: is_malicious_domain started for [{}] type=> {}".format(record, type(record)))
    
    isMaliciousDomain = "N"
    
    recordValue = json.loads(record.get('message'))
    logger.info("value is : {} and type => {}".format(recordValue, type(recordValue)))
  
    pk_name = 'domainName'
    
    queryName = recordValue['query_name']
    srcaddr = recordValue['srcaddr']
    
    logger.info("Domain [{}]  Src [{}]".format(queryName, srcaddr))
    
    pk_value = get_fld("http://"+ queryName)
    
    logger.info("PK [{}]".format(pk_value))
    
    table = ddb.Table(malicious_domains)
    response = table.get_item(Key={pk_name: pk_value})
    
    logger.info("DDB Respones [{}]".format(response))
    if "Item" in response.keys():
      isMaliciousDomain = "Y"
    
    recordValue["isMaliciousDomain"] = isMaliciousDomain
    
    returnValue = "{'message': '" + json.dumps(recordValue) + "'}"
    
    logger.info("Return Value [{}]".format(returnValue))
    
    return returnValue
   

""" Main handler function """
def lambda_handler(event, context):
    
    logger.info("funct:: lambda_handler >> received event is: [{}]".format(event))
    
    output = []
    
    for record in event['records']:
      logger.info("Record {}".format(record))
      #Kinesis Firehose data is base64 encoded so decode here
      payload=json.loads(base64.b64decode(record["data"]))
      logger.info("Record Decoded {}".format(payload))
      logger.info("PayloadType {}".format(type(payload)))
      
      checkedRecord = is_malicious_domain(payload)
      #checkedRecord = json.dumps(payload)
      
      output_record = {
        'recordId': record['recordId'],
        'result': 'Ok',
        'data': base64.b64encode(checkedRecord.encode('utf-8') + b'\n').decode('utf-8')
      }
      output.append(output_record)
     
    logger.info("output to Firehose {}".format(output))    

    return output