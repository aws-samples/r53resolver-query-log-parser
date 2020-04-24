import json
import boto3
import os
from boto3 import resource

s3 = boto3.client('s3')
sns = boto3.client('sns')
dynamodb_resource = resource('dynamodb')


def read_table_item(table_name, pk_name, pk_value):
    """
    Return item read by primary key.
    """
    table = dynamodb_resource.Table(table_name)
    response = table.get_item(Key={pk_name: pk_value})

    return response


def lambda_handler(event, context):
    logObject = event['Records'][0]['s3']['object']['key']
    logBucket = event['Records'][0]['s3']['bucket']['name']

    s3.download_file(logBucket, logObject, '/tmp/logFile.txt')
    logFile = open('/tmp/logFile.txt', 'r')
    logContents = logFile.read()
    os.remove("/tmp/logFile.txt")
    print("Log file {} downloaded".format(logObject))

    queryParts = json.loads(logContents)['query-name'].split(".")
    queryName = queryParts[-2] + "." + queryParts[-1]
    queryName2 = queryParts[-3] + "."
    queryParts[-2] + "." + queryParts[-1]

    try:
        record = read_table_item('malicious-domains', 'domainName', queryName)['Item']
        print("Malicious domain found: {}".format(queryName))

        sourceIP = json.loads(logContents)['source-ip']
        vpcID = json.loads(logContents)['vpc-id']

        message = {"Malicous domain": queryName, "Source IP": sourceIP, "Source VPC": vpcID}

        response = sns.publish(
            TargetArn='arn:aws:sns:us-east-2:957487646002:dnslogs',
            Message=json.dumps({'default': json.dumps(message)}),
            MessageStructure='json'
        )
        print("SNS notification sent")

    except:
        print('Record {} not found in malicious domains'.format(queryName))

