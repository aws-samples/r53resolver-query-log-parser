# Route53 Resolver DNS Query Log Processor

## About
This project is intended to detect DNS queries to malicious domains using [Amazon Route 53](https://aws.amazon.com/route53/) Resolver DNS query logs. Project is packaged as [Serverless Application Module (SAM)](https://aws.amazon.com/serverless/sam/) . Route 53 Resolver logs contains information about the queries, such as the following:
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
This project will 
1. ingest Route53 DNS logs into Kinesis Firehose data stream 
2. perform inline processing using AWS Lambda to check if DNS query was to malicious domain or not 
3. output the modified DNS query reecords, indicating if queried DNS is malicious, to S3 bucket for further processing (i.e Athena)

Architecture-Diagram:
---
![alt text](https://github.com/spanningt/route53resolverLogging/raw/master/dnslogs-architecture.png "Architecture Diagram")




## Project components
Project contains source code and supporting files for a serverless application that you can deploy with the SAM CLI. It includes the following files and folders.

- deliverey stream (Firehose) - this will be target for RT53 resolver to output the logs 
- import_malicious_list - Lambda function which imports names of 'bad' top level domains
- stream_processor - Lambda function used by Kinesis Firehose to check if DNS loge entry (domain) is malicious or not
- template.yaml - A Seerverless Application Module (SAM) template that defines the application's AWS resources.
- tests - Work in Progress 

The application uses several AWS resources, including Lambda functions, DynamoDB table and Kinesis Firehose data stream. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

## Pre-requisites 

####  SAM CLI
The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. 

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)

#### Malicous Domains List
This SAM will create S3 bucket (bucket will be named based on parameter `S3DNSLogsBucketName`). You will node to store the file with list of malicious domains in that bucket. For this sample application we obtained list of malicious domain from [curated list of awesome Threat Intelligence resources](https://github.com/hslatman/awesome-threat-intelligence). For the testing we used https://www.malwaredomainlist.com/mdl.php
      
> Optional: You can also modify `import_malicious_list` Lambda function to download the file from location other than S3. i.e using CURL or similar.

To build and deploy your application for the first time, run the following in your shell:


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
# Building function 'ImportMaliciousListFunc'
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
| **DDBMaliciousDomainsTable**| Name of DynamoDB Table to store list of malicious domain | `malicious-domains-table` |
| **DDBTableRCU**| Read Capacity Units for Dynamo table *[need to lower this one]* |  `50` | 
| **DDBTableWCU**| Wite Capacity Units for Dynamo table *[need to lower this one]* |   `50` | 
| **S3MaliciousDomainsBucket**| S3 Bucket where malicious domains file is stored (see Pre-requisites section) | no default |
| **S3MaliciousDomainsFilePath**|  Path to file containing maliciuous domains| `malicious_list_config/all_malicious_domains.txt` | 
| **S3LogsOutputBucketName**|  S3 Bucket for Kinesis Firehose to output logs | `dns_logs_output` |
| **StreamProcessorMemorySize**| Inline Lambda function memory allocation | `256` |
| **StreamProcessorTimeout**|  Inline Lambda function timeout | `120` |
| **StreamOutput3Prefix**|  Prefix for Kinesis Firehose Output | `dns-query-logs/!{timestamp:yyyy/MM/dd}` |
| **StreamOutputErrorPrefix**|  Prefix for Kinesis Firehose Output, for errors | `delivery-failures/!{firehose:error-output-type}/!{timestamp:yyyy/MM/dd}` | 
| **StreamOutputCompressionFormat**|  Kinesis Firehose output formrmat | `GZIP` | 
| **StreamBufferingInterval**|  Kinesis Firehose buffer interval in seconds | `60`| 
| **StreamBufferSize**|  Kinesis Firehose buffer size in MB *[need to lower this one]* | `1` | 
| **Confirm changes before deploy**| If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.| `Y` |
| **Allow SAM CLI IAM role creation**| This AWS SAM creates AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modified IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command. | `Y` |
| **Save arguments to samconfig.toml**| If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.| `Y` |



You can find output values displayed after deployment in AWS Console under Cloudformation Stacks.


![alt text](https://github.com/spanningt/route53resolverLogging/raw/master/sam-output.png "SAM Output Values")

 
## Populate `malicious-domains` DynamoDB Table

Navigate to AWS Console and go to Lamba. Find *ImportMaliciousListFunctionOutput* Lambda function it will be named `cfnStackName-ImportMaliciousListFunc-XXXXXXXXX`

> Note: before you run Lambda function you MUST complete pre-requisite section as described under *Malicous Domains List* section

Once *ImportMaliciousListFunctionOutput* has completed, navigate to DynamoDB console. Find `malicious-domains-table` table and make sure that in fact it has been populated with data.

## Create DNS Resolver Logs and send them to Kinesis Firehose
To send Route 53 Resolver DNS quesry logs to Kinesis Firehose requires two steps. creation of resolver log configuration and

#### Create Resolver Log Config

Resolver query logging configuration, which defines where you want Resolver to save DNS query logs that originate in your VPCs. Resolver can log queries only for VPCs that are in the same Region as the query logging configuration. Start by creating a config file i.e. `logging-kinesis-config.json` that looks like one below. Replace `DestinationArn` with value of your own Kinesis Firehose stream. You can get the value from Cloudformation output section or from Kinesis Firehose console.

```json
{
      "CreatorRequestId": "2020-07-11-17:30",
      "DestinationArn": "arn:aws:firehose:us-east-1:999999999999:deliverystream/cfnStackName-DeliveryStream-XXXXXXXXXXXX",
      "Name": "logging-beta-kinesis"
}
```

Next you will use AWS CLI to create Route53 Resolver log config. Open your terminal/command prompt and run

```bash 
aws route53resolver create-resolver-query-log-config --cli-input-json  file://logging-kinesis-config.json --region us-east-1
```

Output after successufull Route53 Resolver log config will looks something like below 
```json
{
    "ResolverQueryLogConfig": {
        "Id": "rqlc-XXXXXXXXXXXX",
        "OwnerId": "999999999999",
        "Status": "CREATING",
        "ShareStatus": "NOT_SHARED",
        "AssociationCount": 0,
        "Arn": "arn:aws:route53resolver:us-east-1:999999999999:resolver-query-log-config/rqlc-XXXXXXXXXXXX",
        "Name": "logging-beta-kinesis",
        "DestinationArn": "arn:aws:firehose:us-east-1:999999999999:deliverystream/cfnStackName-DeliveryStream-XXXXXXXXXXXX",
        "CreatorRequestId": "2020-07-11-17:30",
        "CreationTime": "2020-07-26T16:19:14.215Z"
    }
}
```


#### Associate Resolver Config with VPC
Next step is to associates an Amazon VPC with previously createdquery logging configuration. Route 53 Resolver logs DNS queries that originate in all of the Amazon VPCs that are associated with a specified query logging configuration. To associate more than one VPC with a configuration, submit one
*AssociateResolverQueryLogConfig*  request for each VPC.

Here is sample `associate-config.json` file, replace *ResolverQueryLogConfigId* with value of resolver config you created in previous step and *ResourceId* with your own VPC id:
```json
{
   "ResolverQueryLogConfigId": "rqlc-XXXXXXXXXXXX", 
   "ResourceId": "vpc-XXXXXXXXXXX"
}
```

Next you will use AWS CLI to associate Route53 Resolver log config with VPC. Open your terminal/command prompt and run
```bash
aws route53resolver associate-resolver-query-log-config --cli-input-json  file://associate-config.json --region us-east-1
```


Output after successufull association of resolver config and VPC will look something like below 
```json
{
    "ResolverQueryLogConfigAssociation": {
        "Id": "rqlca-ZZZZZZZZZZZ",
        "ResolverQueryLogConfigId": "rqlc-XXXXXXXXXXX",
        "ResourceId": "vpc-XXXXXXXXXXX",
        "Status": "CREATING",
        "Error": "NONE",
        "ErrorMessage": "",
        "CreationTime": "2020-07-26T16:39:29.418Z"
    }
}
```

## Validate Output
The application template uses AWS Serv

## Analyze using Athena or other prefered service (not part of SAM template)

## Add a resource to your application
The application template uses AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs. For resources not included in [the SAM specification](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md), you can use standard [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) resource types.


## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name route53-resolver-logging-sam
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
