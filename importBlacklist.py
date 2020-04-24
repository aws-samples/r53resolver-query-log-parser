import boto3
import os
from boto3 import resource
import re
from botocore.exceptions import ClientError, EndpointConnectionError

s3 = boto3.client('s3')
dynamodb_resource = resource('dynamodb')


def add_item(table_name, col_dict):
    """
    Add one item (row) to table. col_dict is a dictionary {col_name: value}.
    """
    table = dynamodb_resource.Table(table_name)
    response = table.put_item(Item=col_dict)

    return response


def lambda_handler(event, context):
    listObject = event['Records'][0]['s3']['object']['key']
    listBucket = event['Records'][0]['s3']['bucket']['name']

    s3.download_file(listBucket, listObject, '/tmp/listFile.txt')

    listFile = open('/tmp/listFile.txt', 'r')
    listContents = listFile.read()
    os.remove("/tmp/listFile.txt")
    print("Bad domain list file {} downloaded".format(listObject))

    res = re.findall(r"(\b(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+[a-z]{2,}\b)", listContents)
    print(res)
    for item in res:
        add_item('malicious-domains', {'domainName': item})
        print('Domain {} added to database'.format(item))




