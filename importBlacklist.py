import boto3
import os
from boto3 import resource
import re
from tld import get_fld
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
dynamodb_resource = resource('dynamodb')
bad_domains_table = os.environ.get('BAD_DOMAINS_TABLE')


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

    # Parse bad domains list for hostnames
    res = re.findall(r"(\b(?:[a-z0-9]+(?:-[a-z0-9]+)*\.)+[a-z]{2,}\b)", listContents)
    print(res)

    # Add first level domain for each found hostname to the bad domain list
    for item in res:
        try:
            fld = get_fld("http://" + item)
            add_item(bad_domains_table, {'domainName': fld})
            print('Domain {} added to database'.format(fld))
        except Exception as ex:
            # Skip if the Top Level Domain is not valid
            if type(ex).__name__ == 'TldDomainNotFound':
                print('{} is not using a valid domain. Skipping'.format(item))
            else:
                raise





