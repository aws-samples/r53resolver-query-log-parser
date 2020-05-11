import json
import boto3
import os
from boto3 import resource
from tld import get_fld

s3 = boto3.client('s3')
dynamodb_resource = resource('dynamodb')
sns_topic_arn = os.environ.get('SNS_TOPIC_ARN')
bad_domains_table = os.environ.get('BAD_DOMAINS_TABLE')


def read_table_item(table_name, pk_name, pk_value):
    # Return item read by primary key

    table = dynamodb_resource.Table(table_name)
    response = table.get_item(Key={pk_name: pk_value})

    return response


def send_sns_notification(log_item, type):
    # Send SNS notification for malicious or invalid query

    sourceIP = log_item['source-ip']
    vpcID = log_item['vpc-id']
    queryName = log_item['query-name']

    if type == 'malicious':
        message = {"Malicous domain found": queryName, "Source IP": sourceIP, "Source VPC": vpcID}
    if type == 'invalid':
        message = {"Invalid domain found": queryName, "Source IP": sourceIP, "Source VPC": vpcID}

    sns = boto3.client('sns')
    response = sns.publish(
        TargetArn=sns_topic_arn,
        Message=json.dumps({'default': json.dumps(message)}),
        MessageStructure='json'
    )
    return response


def lambda_handler(event, context):
    # Download the log file and pull all log entries
    logObject = event['Records'][0]['s3']['object']['key']
    logBucket = event['Records'][0]['s3']['bucket']['name']
    s3.download_file(logBucket, logObject, '/tmp/logFile.txt')
    logFile = open('/tmp/logFile.txt', 'r')
    logContents = logFile.read()
    os.remove("/tmp/logFile.txt")
    print("Log file {} downloaded".format(logObject))

    """
    Iterate through log entries and compare first level domain for each query to the malicious domain list
    """
    for record in json.loads(logContents)['Records']:
        queryName = record['query-name']
        print("*********************************")
        print("TESTING FOR {} ".format(queryName))
        try:
            # Pull first level domain frome each query
            fldQuery = get_fld("http://" + queryName)
            print("Query: {}, First Level Domain: {}".format(queryName, fldQuery))

            try:
                # Test if query first level domain is in the list of bad domains
                read_table_item(bad_domains_table, 'domainName', fldQuery)['Item']
                print("First level domain {} found in the list".format(fldQuery))

                send_sns_notification(record, 'malicious')

            except:
                print('FLD for {} not found in bad domains'.format(queryName))


        except Exception as ex:
            # Send notification if query TLD is invalid
            if type(ex).__name__ == 'TldDomainNotFound':
                print('Invalid TLD for query {}'.format(queryName))
                send_sns_notification(record, 'invalid')
            else:
                raise



