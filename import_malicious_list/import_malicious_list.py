import boto3
import os
from boto3 import resource
import re
from tld import get_fld
from botocore.exceptions import ClientError
import logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')
dynamodb_resource = resource('dynamodb')
bad_domains_table = os.environ.get('MALICIOUS_DOMAINS_TABLE')
    
"""Add bad domains to DDB Table
    Parameters: malicious_domain_list: list, required
"""
def add_items(malicious_domain_list):
    logger.info("funct:: add_items started... ")
    table = dynamodb_resource.Table(bad_domains_table)
    with table.batch_writer() as batch:
        for domainFld in malicious_domain_list:
            try:
                batch.put_item(Item={'domainName': domainFld})
            except Exception as ex:
                # implement proper exception handling
                logger.info("while processing add_items() excpetion occured: {} ".format(ex))
                raise
    logger.info("funct:: add_items completed ... ")
        
"""Import Domain Blacklist  Lambda function """
def lambda_handler(event, context):
    logger.info("funct:: lambda_handler started... ")
    # get the bad domains list from S3 
    listBucket = os.environ.get('S3_BUCKET_MALICOUS_DOMAINS') 
    listObject = os.environ.get('S3_OBJECT_MALICIOUS_DOMAINS') 
    s3.download_file(listBucket, listObject, '/tmp/listFile.txt')
    logger.info("Bad domain list file {} downloaded".format(listBucket +'/'+ listObject))
    
    # parse the bad domains list
    localFile = open('/tmp/listFile.txt', 'r')
    listContents = localFile.read()
    os.remove("/tmp/listFile.txt")
    
    # Parse bad domains list for any hostnames
    res = re.findall(r"(\b(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+[a-z]{2,}\b)", listContents)

    domainsToAdd = []
   
    # Add valid first level domain for each found hostname to the bad domain list
    for item in res:
        try:
            fld = get_fld("http://" + item)
            domainsToAdd.append(fld)
        except Exception as ex:
            if type(ex).__name__ == 'TldDomainNotFound':
                logger.info('{} is not using a valid domain. Skipping'.format(item))
            else:
                raise
    logger.info("=> Total domains in file [{}], ".format(len(domainsToAdd)))
  
    # quick way to get distinct domain names (list -> set -> list)
    finalBadList = list(set(domainsToAdd)) 
    
    logger.info("=> Unique domains in file [{}], ".format(len(finalBadList)))
    
    add_items(finalBadList)

    logger.info("funct:: lambda_handler completed ... ")

