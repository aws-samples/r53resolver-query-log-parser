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

interesting_domains = os.environ.get('interesting_DOMAINS_TABLE')



""" Function to validate if Top Level Domain is interesting - ie. does it exist in interesting domains DDB table?""" 
def is_interesting_domain( record ):
    
  logger.info("funct:: is_interesting_domain started for [{}] type=> {}".format(record, type(record)))

  isinterestingDomain = "N"
  ddbSearchField = 'domainName'

  recordValue = json.loads(record.get('message'))
  # preset interesting to N
  recordValue["isinterestingDomain"] = isinterestingDomain

  #preset return value 
  returnValue = "{'message': '" + json.dumps(recordValue) + "'}"

  dnsQuery = recordValue['query_name']
  srcaddr = recordValue['srcaddr']

  try:
    # get Top Level Domain 
    tldToSearchFor = get_fld("http://"+ dnsQuery)

    #initialize and search the DynamoDB table 
    table = ddb.Table(interesting_domains)
    response = table.get_item(Key={ddbSearchField: tldToSearchFor})

    if "Item" in response.keys():
      isinterestingDomain = "Y"

    # add field isinterestingDomain to DNS Query record -> this will end up in Firehose > S3
    recordValue["isinterestingDomain"] = isinterestingDomain

    # format the return value to conforom to Firehose
    returnValue = "{'message': '" + json.dumps(recordValue) + "'}"

  except Exception as ex:
    # implement proper exception handling
    logger.info("while processing add_items() excpetion occured: {} ".format(ex))

  logger.info("funct:: is_interesting_domain completed return Value [{}]".format(returnValue))
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
      
      checkedRecord = is_interesting_domain(payload)
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