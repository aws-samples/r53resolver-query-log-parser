import json
import boto3
import os
from boto3 import resource
from tld import get_fld
import urllib.request
import io
import gzip
import re
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
ddb = resource('dynamodb')
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
malicious_domains = os.environ.get('MALICIOUS_DOMAINS_TABLE')
notify_invalid = os.environ.get('NOTIFY_INVALID')

""" Function to validate if Top Level Domain is malicious - ie. does it exist in malicious domains DDB table?""" 
def is_malicious_domain( pk_name, pk_value):
    
    logger.info("funct:: is_malicious_domain >> searching for [{}]".format(pk_value))
    
    table = ddb.Table(malicious_domains)
    response = table.get_item(Key={pk_name: pk_value})
    
    return "Item" in response.keys()
   
""" Function to send notification that malicious domain has been detected - sent to SNS topic """
def send_sns_notification(log_item, type):
    
    logger.info("funct:: send_sns_notification >> received record is: [{}]".format(log_item))
    
    # convert to JSON
    record = json.loads(log_item)
    sourceIP = record.get('srcaddr')
    vpcID = record.get('vpc_id')
    queryName = record.get('query_name')
    
    if type == 'malicious':
        message = {"Malicous domain found": queryName, "Source IP": sourceIP, "Source VPC": vpcID}
    if type == 'invalid':
        message = {"Invalid domain found": queryName, "Source IP": sourceIP, "Source VPC": vpcID}
   
    
    sns = boto3.client('sns')
    
    try:
        response = sns.publish(
            TargetArn=sns_topic_arn,
            Message=json.dumps({'default': json.dumps(message)}),
            MessageStructure='json'
        )
    except Exception as ex:
        logger.info("# Exception occured".format(ex))
        
    
""" Main handler function """
def lambda_handler(event, context):
    
    logger.info("funct:: lambda_handler >> received event is: [{}]".format(event))
    
    logObject = event['Records'][0]['s3']['object']['key']
    logBucket = event['Records'][0]['s3']['bucket']['name']

    # get file from S3, decompress it and load it into memory one line at the time
    s3.download_file(logBucket, logObject, '/tmp/logFile.gzip')
    f = open("/tmp/logFile.gzip", "rb")
    compressed_file = io.BytesIO(f.read())
    decompressed_file = gzip.GzipFile(fileobj=compressed_file)
    logContents = decompressed_file.read().splitlines()
    os.remove("/tmp/logFile.gzip")
    
    #Iterate through log entries and compare first level domain for each query to the malicious domain list
    for record in logContents:
        queryName = json.loads(record)['query_name']
        srcaddr = json.loads(record)['srcaddr']
        
        logger.info("testing for {} and srcaddr {} ".format(queryName, srcaddr))
        try:
            fldQuery = get_fld("http://"+ queryName)
            logger.info("Top Level Domain is {}  ".format(fldQuery))
            
            try:
                # Test if query first level domain is in the list of bad domains
                if is_malicious_domain( 'domainName', fldQuery):
                    logger.info("Malicious Domain detected => {}".format(fldQuery))
                    send_sns_notification(record, 'malicious')
            except Exception as ex:
                logger.info('Exception occured: '.format(ex))
        except Exception as ex:
            if type(ex).__name__ == 'TldDomainNotFound':
                logger.info('Invalid TLD for query [{}]'.format(queryName))
                #send_sns_notification(record, 'invalid')
            else:
                logger.info("# Exception occured".format(ex))
    
    