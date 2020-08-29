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
    ddbSearchField = 'domainName'

    recordValue = json.loads(record.get('message'))

    dnsQuery = recordValue['query_name']
    srcaddr = recordValue['srcaddr']
    
    try:
      # get Top Level Domain 
      tldToSearchFor = get_fld("http://"+ dnsQuery)

      #initialize and search the DynamoDB table 
      table = ddb.Table(malicious_domains)
      response = table.get_item(Key={ddbSearchField: tldToSearchFor})
    
      if "Item" in response.keys():
        isMaliciousDomain = "Y"

      # add field isMaliciousDomain to DNS Query record -> this will end up in Firehose > S3
      recordValue["isMaliciousDomain"] = isMaliciousDomain
    
      # format the return value to conforom to Firehose
      returnValue = "{'message': '" + json.dumps(recordValue) + "'}"

    except Exception as ex:
      if type(ex).__name__ == 'TldDomainNotFound':
        logger.info('{} is not using a valid domain. Skipping'.format(dnsQuery))
      else:
        # implement proper exception handling
        logger.info("while processing add_items() excpetion occured: {} ".format(ex))
        raise

    logger.info("funct:: is_malicious_domain completed return Value [{}]".format(returnValue))
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
        #data': base64.b64encode(checkedRecord)
        'data': base64.b64encode(checkedRecord.encode('utf-8') + b'\n').decode('utf-8')
      }
      output.append(output_record)
     
    logger.info('Processing completed.  Number of records affected {} '.format(output))    

    return{'records': output}