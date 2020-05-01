import json
import boto3
import os
from boto3 import resource
from tld import get_fld

s3 = boto3.client('s3')
sns = boto3.client('sns')
dynamodb_resource = resource('dynamodb')

sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
bad_domains_table = os.environ.get('BAD_DOMAINS_TABLE')


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

    for record in json.loads(logContents)['Records']:
        # Get the qery and its first level domain
        queryName = record['query-name']
        try:
            fldQuery = get_fld("http://" + queryName)
            print("Full query: {}, First Level Domain: {}".format(queryName, fldQuery))

            try:
                # Test if query is in the list of bad domains
                read_table_item(bad_domains_table, 'domainName', fldQuery)['Item']
                print("First level domain {} found in the list".format(fldQuery))

                # Create and send an SNS notification
                sourceIP = record['source-ip']
                vpcID = record['vpc-id']

                message = {"Malicous domain": queryName, "Source IP": sourceIP, "Source VPC": vpcID}

                sns.publish(
                    TargetArn=sns_topic_arn,
                    Message=json.dumps({'default': json.dumps(message)}),
                    MessageStructure='json'
                )
                print("SNS notification sent")

            except:
                print('Record {} not found in bad domains'.format(queryName))


        except Exception as ex:
            # Skip if the Top Level Domain is not valid
            if type(ex).__name__ == 'TldDomainNotFound':
                print('{} is not using a valid top level domain. Skipping'.format(queryName))
            else:
                raise



