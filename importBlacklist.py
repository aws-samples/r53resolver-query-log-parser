import boto3
import os
from boto3 import resource
import re

s3 = boto3.client('s3')
dynamodb_resource = resource('dynamodb')
bad_domains_table=os.environ.get('BAD_DOMAINS_TABLE')


def add_item(table_name, col_dict):
    """
    Add one item (row) to table. col_dict is a dictionary {col_name: value}.
    """
    table = dynamodb_resource.Table(table_name)
    response = table.put_item(Item=col_dict)

    return response


def lambda_handler(event, context):

    # Download the bad domains list
    listObject = event['Records'][0]['s3']['object']['key']
    listBucket = event['Records'][0]['s3']['bucket']['name']
    s3.download_file(listBucket, listObject, '/tmp/listFile.txt')
    listFile = open('/tmp/listFile.txt', 'r')
    listContents = listFile.read()
    os.remove("/tmp/listFile.txt")
    print("Bad domain list file {} downloaded".format(listObject))

    # Parse bad domains list for domains
    res = re.findall(r"(\b(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+[a-z]{2,}\b)", listContents)
    print(res)

    # Add each domain to DynamoDB
    for item in res:
        add_item(bad_domains_table, {'domainName': item})
        print('Domain {} added to database'.format(item))




