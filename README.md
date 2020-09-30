# Route53 Resolver DNS Query Log Processor
This project is part of blog: https://aws.amazon.com/blogs/networking-and-content-delivery/how-to-automatically-parse-route-53-resolver-query-logs

## About
Project is intended to detect DNS queries to interesting domains using [Amazon Route 53](https://aws.amazon.com/route53/) Resolver DNS query logs. Project is packaged as [Serverless Application Module (SAM)](https://aws.amazon.com/serverless/sam/) . Route 53 Resolver logs contains information about the queries, such as the following:
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

### Python
This template uses Python 3.8. If you dont have Python 3.8 you can modify `template.yaml` and change the `Runtime` parameter for the 2 Lambda functions. 


## Deploy SAM  
Detailed steps for this project are outlined in blog: https://aws.amazon.com/blogs/networking-and-content-delivery/how-to-automatically-parse-route-53-resolver-query-logs 

Once you have pre-requisites you can deploy the RT53 Resolver logging SAM application. The first command will build the source of the application.

```diff
sam build 
```

 The second command will package and deploy application to AWS, with a series of prompts:
 ```diff
sam deploy --guided
```

| Property                | Description           | Default Value  |
| ----------------------- |---------------------| :--------------:|
| **Stack Name**          | The name of the stack to deploy to CloudFormation. | give it unique name          |
| **AWS Region**| The AWS region you want to deploy your app to.| us-east-1 |
| **DDBinterestingDomainsTable**| This is DynamoDB table that will hold list of interesting domain. Table will be populated by the `ImportInterestingDomainsListFunc` Lambda function. `StreamInlineProcessingFunction` Lambda function will check DNS log entries against entries in this table | `interesting-domains-table` |
| **S3interestingDomainsBucket**| S3 Bucket where interesting domains file is stored | `interesting-domains-bucket` |
| **S3DNSLogsBucketName**|  S3 Bucket for Kinesis Firehose to output logs | `dns-logs-output` |
| **StreamProcessorMemorySize**| Inline Lambda function memory allocation | `256` |
| **StreamProcessorTimeout**|  Inline Lambda function timeout in seconds | `120` |
| **StreamOutput3Prefix**|  Prefix for Kinesis Firehose Output | `dns-query-logs/!{timestamp:yyyy/MM/dd}` |
| **StreamOutputErrorPrefix**|  Prefix for Kinesis Firehose Output, for errors | `delivery-failures/!{firehose:error-output-type}/!{timestamp:yyyy/MM/dd}` | 
| **StreamOutputCompressionFormat**|  Kinesis Firehose output format - https://docs.aws.amazon.com/firehose/latest/dev/create-configure.html| `GZIP` | 
| **StreamBufferingInterval**|  Kinesis Firehose buffer interval in seconds (how long Firehose waits before delivering data to S3), select interval of 60–900 seconds - https://docs.aws.amazon.com/firehose/latest/dev/create-configure.html | `60`| 
| **StreamBufferSize**|  Kinesis Firehose buffer size in MB, choose a buffer in size of 1–128 MiBs - https://docs.aws.amazon.com/firehose/latest/dev/create-configure.html | `1` | 
| **SNStopicName**| SNS Topic to send notification on matches | `dns-logs-match-topic` |
| **SNSinUse**| Turn on/off SNS Notifications | `Y` |


You can find output values displayed after deployment in AWS Console under Cloudformation Stacks.


![alt text](https://github.com/spanningt/route53resolverLogging/raw/master/sam-output.png "SAM Output Values")


## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name route53-resolver-logging-sam
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
