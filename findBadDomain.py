import json
import boto3
import os
from boto3 import resource
from tld import get_fld

s3 = boto3.client('s3')
sns = boto3.client('sns')
dynamodb_resource = resource('dynamodb')

sns_topic_arn=os.environ.get('SNS_TOPIC_ARN')
bad_domains_table=os.environ.get('BAD_DOMAINS_TABLE')


def read_table_item(table_name, pk_name, pk_value):
    """
    Return item read by primary key.
    """
    table = dynamodb_resource.Table(table_name)
    response = table.get_item(Key={pk_name: pk_value})

    return response


def lambda_handler(event, context):

    # Download the log file
    logObject = event['Records'][0]['s3']['object']['key']
    logBucket = event['Records'][0]['s3']['bucket']['name']
    s3.download_file(logBucket, logObject, '/tmp/logFile.txt')
    logFile = open('/tmp/logFile.txt', 'r')
    logContents = logFile.read()
    os.remove("/tmp/logFile.txt")
    print("Log file {} downloaded".format(logObject))

    # Get the first level domain from the log query field using the TLD libary
    queryName = get_fld("http://"+json.loads(logContents)['query-name'])
    print("Doing a lookup for {}".format(queryName))

    try:
        #Test if query is in the list of bad domains
        read_table_item(bad_domains_table, 'domainName', queryName)['Item']
        print("Malicious domain found: {}".format(queryName))

        #Create and send an SNS notification
        sourceIP = json.loads(logContents)['source-ip']
        vpcID = json.loads(logContents)['vpc-id']

        message = {"Malicous domain": queryName, "Source IP": sourceIP, "Source VPC": vpcID}

        sns.publish(
            TargetArn=sns_topic_arn,
            Message=json.dumps({'default': json.dumps(message)}),
            MessageStructure='json'
        )
        print("SNS notification sent")

    except:
        print('Record {} not found in malicious domains'.format(queryName))

