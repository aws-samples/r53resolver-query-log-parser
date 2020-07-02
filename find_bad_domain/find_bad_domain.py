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
import uuid
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
ddb = resource('dynamodb')
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
malicious_domains = os.environ.get('MALICIOUS_DOMAINS_TABLE')
notify_invalid = os.environ.get('NOTIFY_INVALID')
secHubClient =  boto3.client('securityhub')

findingTemplate = {
  "SchemaVersion": "",
  "Id": "",
  "ProductArn": "",
  "GeneratorId": "",
  "AwsAccountId": "",
  "Types": [""],
  "CreatedAt": "",
  "UpdatedAt": "",
  "Severity": {
    "Label": "",
    "Normalized": 0
  },
  "ProductFields":
    {
      "ProviderName": "Route 53 Query Log Bad Domain",
      "ProviderVersion": "1.0"
    },
  "Title": "Route 53 Resolver Query for Blocked Domain Detected",
  "Description": "A VPC resource sent a DNS query for a blocked domain",
  "Network": {
    "Protocol": "",
    "SourceIpV4": "",
    "SourcePort": 0,
    "DestinationPort": 0,
    "DestinationDomain": ""
  },
  "Resources": [
    {
      "Type": "",
      "Id": "",
      "Region": "",
      "Details": {
        "AwsEc2Instance": {
          "VpcId": ""
        }
      }
    }
  ],
  "Note": {
    "Text": "",
    "UpdatedBy": "",
    "UpdatedAt": ""
  }
}

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
    
    logger.info("funct:: send_sns_notification >> completed")

""" Create Security Hub Findings """
def create_security_hub_findings(records, context):
    AWS_REGION = os.environ['AWS_REGION']
    ACCOUNT_ID = context.invoked_function_arn.split(":")[4]
    
    schema_version = "2018-10-08"
    generator_id = "DomainBlacklist"
    findingType = "Unusual Behaviors"
    severityLabel = "HIGH"
    severityNormalized = 70
    providerName = "Route 53 Query Log Bad Domain"
    providerVersion = "1.0"
    title = "Route 53 Resolver Query for Blocked Domain Detected"
    findingDesc = "A VPC resource sent a DNS query for a blocked domain"
    guid = uuid.uuid4()
    productArn = "arn:aws:securityhub:"+ AWS_REGION +":" + ACCOUNT_ID +":product/" + ACCOUNT_ID +"/default"
    
    logger.info("funct:: create_security_hub_findings >> received {} records to process".format(len(records)))
    
    finding_list =	[]

    for item in records.values():
        newFinding = findingTemplate
        aRecord = json.loads(item)
        newFinding["SchemaVersion"] = schema_version
        newFinding["Id"] = context.invoked_function_arn +"/"+ str(guid)
        newFinding["ProductArn"] = productArn
        newFinding["GeneratorId"] = generator_id
        newFinding["AwsAccountId"] = aRecord["account_id"]
        newFinding["Types"] = [findingType]
        newFinding["CreatedAt"] = aRecord["query_timestamp"]
        newFinding["UpdatedAt"] = aRecord["query_timestamp"]
        newFinding["Severity"]["Label"] = severityLabel
        newFinding["Severity"]["Normalized"] = severityNormalized
        newFinding["ProductFields"]["ProviderName"] = providerName
        newFinding["ProductFields"]["ProviderVersion"] = providerVersion
        newFinding["Title"] = title
        newFinding["Description"] = findingDesc
        newFinding["Network"]["Protocol"] = "DNS"
        newFinding["Network"]["SourceIpV4"] = aRecord["srcaddr"]
        newFinding["Network"]["SourcePort"] = int(aRecord["srcport"])
        newFinding["Network"]["DestinationPort"] = 0
        newFinding["Network"]["DestinationDomain"] = aRecord["query_name"]
        newFinding["Resources"][0]["Type"] = "N/A"
        newFinding["Resources"][0]["Id"] = aRecord["srcids"][0]
        newFinding["Resources"][0]["Region"] =aRecord["region"]
        newFinding["Resources"][0]["Details"]["AwsEc2Instance"]["VpcId"] = aRecord["vpc_id"]
        newFinding["Note"]["Text"] = "Finding generated against and blocklist in DynamoDB table ["+ malicious_domains +"]"
        newFinding["Note"]["UpdatedBy"] = context.invoked_function_arn
        newFinding["Note"]["UpdatedAt"] = aRecord["query_timestamp"]
        logger.info( "A RECORD [{}]".format(newFinding))
        finding_list.append(newFinding)
        if(len(finding_list) % 100 == 0):
            response = secHubClient.batch_import_findings(Findings=[convert_list(finding_list)])
            del finding_list[:]
   
    logger.info("finding_list type{} | finding_list[0] {}".format(type(finding_list), type(finding_list[0])))
    
    if (len(finding_list) > 0 ):
        try:
            response = secHubClient.batch_import_findings(Findings=finding_list)
            logger.info("Response {}".format(response))
        except Exception as e:
            logger.error("Error has occured sending to Security Hub: {}".format(e))
        
        
    logger.info("funct:: create_security_hub_findings >> completed")
    
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
    
    malicious_records = {}
    
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
                    recordIndex = len(malicious_records) + 1
                    logger.info("Malicious domains index => {}".format(recordIndex))
                    malicious_records[recordIndex] = (record)
                    #send_sns_notification(record, 'malicious')
                   
            except Exception as ex:
                logger.info('Exception occured: '.format(ex))
        except Exception as ex:
            if type(ex).__name__ == 'TldDomainNotFound':
                logger.info('Invalid TLD for query [{}]'.format(queryName))
                #send_sns_notification(record, 'invalid')
            else:
                logger.info("# Exception occured".format(ex))
    
    # send finding to security hub
    create_security_hub_findings(malicious_records, context)
    
    