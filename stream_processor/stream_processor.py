import json
import boto3
import os
import urllib.request
import base64
import re
import logging
from boto3 import resource
from tld import get_fld


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
ddb = resource('dynamodb')

interesting_domains = os.environ.get('INTERESTING_DOMAINS_TABLE')
sns_topic = os.environ.get('SNS_TOPIC')
sns_enabled = os.environ.get('SNS_ON')

""" Function to validate if Top Level Domain is interesting - ie. does it exist in interesting domains DDB table?""" 
def is_interesting_domain( record ):
    
  logger.info("funct:: is_interesting_domain started for [{}] type=> {}".format(record, type(record)))

  isMatchedDomain = "N"
  ddbSearchField = 'domainName'

  recordValue = record
  # preset interesting to N
  recordValue["isMatchedDomain"] = isMatchedDomain

  #preset return value 
  returnValue = json.dumps(recordValue) 

  dnsQuery = recordValue['query_name']


  try:
    # get Top Level Domain 
    tldToSearchFor = get_fld("http://"+ dnsQuery)

    #initialize and search the DynamoDB table 
    table = ddb.Table(interesting_domains)
    response = table.get_item(Key={ddbSearchField: tldToSearchFor})

    if "Item" in response.keys():
      isMatchedDomain = "Y"
      #Check if SNS is enabled
      if sns_enabled == 'Y':
        # Create an SNS client
        sns = boto3.client('sns')
        #Send Notification
        logger.info("Sending notification to SNS topic: {} ".format(sns_topic))
        sns.publish(
          TopicArn=sns_topic,
          Subject='Route 53 Query Log Matched',
          Message=json.dumps(recordValue)
        )


    # add field isMatchedDomain to DNS Query record -> this will end up in Firehose > S3
    recordValue["isMatchedDomain"] = isMatchedDomain

    # format the return value
    returnValue = json.dumps(recordValue)

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
        'data': base64.b64encode(checkedRecord.encode('utf-8') + b'\n').decode('utf-8')
      }
      output.append(output_record)
     
    logger.info('Processing completed.  Number of records affected {} '.format(output))    

    return{'records': output}