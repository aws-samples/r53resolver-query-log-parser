# Route53 Resolver DNS Query Log Processor

## About
This project is intended to detect DNS queries to interesting domains using [Amazon Route 53](https://aws.amazon.com/route53/) Resolver DNS query logs. Project is packaged as [Serverless Application Module (SAM)](https://aws.amazon.com/serverless/sam/) . Route 53 Resolver logs contains information about the queries, such as the following:
- Route 53 edge location that responded to the DNS query
- Domain or subdomain that was requested
- DNS record type, such as A or AAAA
- DNS response code, such as NoError or ServFail

Sample DNS log record:
```json
{
      "version":"1.000000",
      "account_id":"99999999999",
      "region":"us-east-1",
      "vpc_id":"vpc-h456k56s57w78e76",
      "query_timestamp":"2020-05-22T03:25:36Z",
      "query_name":"223.0.2.1.in-addr.arpa.",
      "query_type":"PTR",
      "query_class":"IN",
      "rcode":"NOERROR",
      "answers":[{
            "Address":"ip-7-7-7-223.ec2.internal. ",
            "Type":"PTR",
            "Class":"IN"
      }],
      "srcaddr":"9.9.9.70",
      "srcport":"60306",
      "srcids":[
            "i-0f19ert0572c3c54a"
      ]
}
```

## Data flow
This project has 4 main steps of the flow
1. S3 bucket that holds interesting domains file, AWS Lambda `import_interesting_domains/import_interesting_domains.py` which parses that file and then stores it in DynamoDB table  
2. Route53 DNS logs will be ingested into Kinesis Firehose data stream 
3. Using AWS Lambda (inline processing) `stream_processor/stream_processor.py` to check if DNS query was resolving to  interesting domain 
4. Output the modified DNS query reecords, indicating if queried DNS is interesting, to S3 bucket for further processing (i.e Athena)

Architecture-Diagram:
---
TODO > insert link to blog




## Project components
Project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI. It includes the following files and folders.

- DeliveryStream (Firehose) defined in template.yaml - this will be target for RT53 resolver to output the logs 
- import_interesting_domains.py - Lambda function which imports names of 'bad' top level domains
- find_bad_domain.py - Lambda function used by Kinesis Firehose to check if DNS loge entry (domain) is interesting or not
- SNS Topic - to receive notification when matches are found
- template.yaml - A Seerverless Application Module (SAM) template that defines the application's AWS resources.

The application uses several AWS resources, including Lambda functions, DynamoDB table, SNS Topic and Kinesis Firehose data stream. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

## Pre-requisites 

####  SAM CLI
The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. 

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)

## Deploy SAM  
Once you have pre-requisites you can deploy the RT53 Resolver logging SAM application. The first command will build the source of the application.

```diff
sam build 
```

Ouutput from build should look like this
```diff
# Building function 'StreamInlineProcessingFunction'
# Running PythonPipBuilder:ResolveDependencies
# Running PythonPipBuilder:CopySource
# Building function 'ImportinterestingListFunc'
# Running PythonPipBuilder:ResolveDependencies
# Running PythonPipBuilder:CopySource

+ Build Succeeded

! Built Artifacts  : .aws-sam/build
! Built Template   : .aws-sam/build/template.yaml

! Commands you can use next
! =========================
! [*] Invoke Function: sam local invoke
! [*] Deploy: sam deploy --guided
```

 The second command will package and deploy application to AWS, with a series of prompts:
 ```diff
sam deploy --guided
```

| Property                | Description           | Default Value  |
| ----------------------- |---------------------| :--------------:|
| **Stack Name**          | The name of the stack to deploy to CloudFormation. | give it unique name          |
| **AWS Region**| The AWS region you want to deploy your app to.| us-east-1 |
| **DDBinterestingDomainsTable**| Name of DynamoDB Table to store list of interesting domain | `interesting-domains-table` |
| **DDBTableRCU**| Read Capacity Units for Dynamo table *[need to lower this one]* |  `50` | 
| **DDBTableWCU**| Wite Capacity Units for Dynamo table *[need to lower this one]* |   `50` | 
| **S3interestingDomainsBucket**| S3 Bucket where interesting domains file is stored (see Pre-requisites section) | no default |
| **S3interestingDomainsFilePath**|  Path to file containing maliciuous domains| `interesting_list_config/all_interesting_domains.txt` | 
| **S3LogsOutputBucketName**|  S3 Bucket for Kinesis Firehose to output logs | `dns_logs_output` |
| **StreamProcessorMemorySize**| Inline Lambda function memory allocation | `256` |
| **StreamProcessorTimeout**|  Inline Lambda function timeout | `120` |
| **StreamOutput3Prefix**|  Prefix for Kinesis Firehose Output | `dns-query-logs/!{timestamp:yyyy/MM/dd}` |
| **StreamOutputErrorPrefix**|  Prefix for Kinesis Firehose Output, for errors | `delivery-failures/!{firehose:error-output-type}/!{timestamp:yyyy/MM/dd}` | 
| **StreamOutputCompressionFormat**|  Kinesis Firehose output formrmat | `GZIP` | 
| **StreamBufferingInterval**|  Kinesis Firehose buffer interval in seconds | `60`| 
| **StreamBufferSize**|  Kinesis Firehose buffer size in MB *[need to lower this one]* | `1` | 
| **AlertOnMatchSNSTopic**| SNS Topic to send notification on matches | `dns-logs-match-topic` |
| **SNSinUse**| Turn on/off SNS Notifications | `Y` |
| **Confirm changes before deploy**| If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.| `Y` |
| **Allow SAM CLI IAM role creation**| This AWS SAM creates AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modified IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command. | `Y` |
| **Save arguments to samconfig.toml**| If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.| `Y` |



You can find output values displayed after deployment in AWS Console under Cloudformation Stacks.


![alt text](https://github.com/spanningt/route53resolverLogging/raw/master/sam-output.png "SAM Output Values")

## Cost Estimates 
Estimates are performed in US EAST 2 (Ohio) Region. Following assumptions have been made

Kinesis Firehose:
- 10 DNS quesries per second constant load for 24hr/7days. Thats 864,000 a day
- each RT53 Resolver log record is ~2kb

Lambda:
- we assume that Firehose processes record every minute, so that translates to 1440 lambda invocations and we estimated ~10 seconds duration each  

SNS
- we estimated that .5% of all DNS requests will trigger a "match notification" via SNS. We rounded itto 200,000 a month

S3 storage
- we estimated rougly 54GB (864,000 records * 2kb * 30.5 days) of uncompressed files will go to S3 storage monthly

Cost Estimate details for above components is here: https://calculator.aws/#/estimate?id=068f23b44b4dd551c297841a0fdaaf32ba17fed0

DynamoDB
- we estimated 26,352,000 reads (864,000 records a day * 30.5 days) and 1,000,000 writes (weekly 250,000 writes)
IMPORTANT: CloudFormation Template defaults to 50 Write and 50 Read Units. 

DynamoDB isn part of the estimate link above and estimated on-demand pricing cost would be:
Writes: $1.25 per million writes x .1 million writes = $1.25
Reads: $0.25 per million reads x 26.35 million reads = $6.58
You can get more details how to calculate DynamoDB cost here: https://aws.amazon.com/dynamodb/pricing/on-demand/ 

Total monthly cost based on the above assumptions would be $17.02 USD
$9.19 USD for Firehose, Lambda, SNS and S3
$7.83 USD for DynamoDB

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name route53-resolver-logging-sam
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
