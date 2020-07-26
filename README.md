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

- DeliveryStream (Firehose) - this will be target for RT53 resolver to output the logs 
- import_blocked_list - Lambda function which imports names of 'bad' top level domains
- stream_processor - Lambda function used by Kinesis Firehose to check if DNS loge entry (domain) is malicious or not
- tests - Work in Progress 
- template.yaml - A Seerverless Application Module (SAM) template that defines the application's AWS resources.

The application uses several AWS resources, including Lambda functions, DynamoDB table and Kinesis Firehose data stream. These resources are defined in the `template.yaml` file in this project. You can update the template to add AWS resources through the same deployment process that updates your application code.

## Pre-requisites 

###  SAM CLI
The Serverless Application Model Command Line Interface (SAM CLI) is an extension of the AWS CLI that adds functionality for building and testing Lambda applications. 

To use the SAM CLI, you need the following tools.

* SAM CLI - [Install the SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-install.html)
* [Python 3 installed](https://www.python.org/downloads/)

### Malicous Domains List
You will need to create S3 bucket and store the file with list of malicious domains. For this sample application we obtained list of malicious domain from [curated list of awesome Threat Intelligence resources](https://github.com/hslatman/awesome-threat-intelligence). For the testing we used https://www.malwaredomainlist.com/mdl.php
      
> Optional: You can also modify `import_blocked_list` Lambda function to download the file from location other than S3. i.e using CURL or similar.
To build and deploy your application for the first time, run the following in your shell:


## Deploy SAM  
Once you have pre-requisites you can deploy the RT53 Resolver logging SAM application by:

```bash
@@route53resolverLogging tmak$ sam build@@ 

Building function 'StreamInlineProcessingFunction'
Running PythonPipBuilder:ResolveDependencies
Running PythonPipBuilder:CopySource
Building function 'ImportBlockedListFunc'
Running PythonPipBuilder:ResolveDependencies
Running PythonPipBuilder:CopySource

+ Build Succeeded

! Built Artifacts  : .aws-sam/build
! Built Template   : .aws-sam/build/template.yaml

! Commands you can use next
! =========================
! [*] Invoke Function: sam local invoke
! [*] Deploy: sam deploy --guided
```

The first command will build the source of the application. The second command will package and deploy application to AWS, with a series of prompts:

| Property                | Description           | Default Value  |
| ----------------------- |---------------------| --------------:|
| **Stack Name**          | The name of the stack to deploy to CloudFormation. | $1600          |
| **AWS Region**| The AWS region you want to deploy your app to.|
| **DDBMaliciousDomainsTable**| Name of DynamoDB Table to store list of malicious domain | [malicious-domains-list] 
| **DDBTableRCU**| Read Capacity Units for Dynamo table |  [500]  
| **DDBTableWCU**| Wite Capacity Units for Dynamo table |   [500]: 
| **S3MaliciousDomainsBucket**| S3 Bucket where malicious domains file is stored (see Pre-requisites section) | no default 
| **S3MaliciousDomainsFilePath**|  Path to file containing maliciuous domains| [config/all-malicious-domains.txt]: 
| **S3LogsOutputBucketName**|  S3 Bucket for Kinesis Firehose to output logs | [dns-logs-output]: 
| **StreamProcessorMemorySize**| Inline Lambda function memory allocation | [256]: 
| **StreamProcessorTimeout**|  Inline Lambda function timeout | [120]: 
| **StreamOutput3Prefix**|  Prefix for Kinesis Firehose Output | [dns-query-logs/!{timestamp:yyyy/MM/dd}]: 
| **StreamOutputErrorPrefix**|  Prefix for Kinesis Firehose Output, for errors |[delivery-failures/!{firehose:error-output-type}/!{timestamp:yyyy/MM/dd}]: 
| **StreamOutputCompressionFormat**|  Kinesis Firehose output formrmat | [GZIP]: 
| **StreamBufferingInterval**|  Kinesis Firehose buffer interval in seconds | [60]: 
| **StreamBufferSize**|  Kinesis Firehose buffer size in MB| [5]: 
| **Confirm changes before deploy**| If set to yes, any change sets will be shown to you before execution for manual review. If set to no, the AWS SAM CLI will automatically deploy application changes.| Yes
| **Allow SAM CLI IAM role creation**| This AWS SAM creates AWS IAM roles required for the AWS Lambda function(s) included to access AWS services. By default, these are scoped down to minimum required permissions. To deploy an AWS CloudFormation stack which creates or modified IAM roles, the `CAPABILITY_IAM` value for `capabilities` must be provided. If permission isn't provided through this prompt, to deploy this example you must explicitly pass `--capabilities CAPABILITY_IAM` to the `sam deploy` command. | Yes
| **Save arguments to samconfig.toml**| If set to yes, your choices will be saved to a configuration file inside the project, so that in the future you can just re-run `sam deploy` without parameters to deploy changes to your application.| Yes


You can find your API Gateway Endpoint URL in the output values displayed after deployment.

## Use the SAM CLI to build and test locally

Build your application with the `sam build --use-container` command.

```bash
route53-resolver-logging-sam$ sam build --use-container
```

The SAM CLI installs dependencies defined in `hello_world/requirements.txt`, creates a deployment package, and saves it in the `.aws-sam/build` folder.

Test a single function by invoking it directly with a test event. An event is a JSON document that represents the input that the function receives from the event source. Test events are included in the `events` folder in this project.

Run functions locally and invoke them with the `sam local invoke` command.

```bash
route53-resolver-logging-sam$ sam local invoke HelloWorldFunction --event events/event.json
```

The SAM CLI can also emulate your application's API. Use the `sam local start-api` to run the API locally on port 3000.

```bash
route53-resolver-logging-sam$ sam local start-api
route53-resolver-logging-sam$ curl http://localhost:3000/
```

The SAM CLI reads the application template to determine the API's routes and the functions that they invoke. The `Events` property on each function's definition includes the route and method for each path.

```yaml
      Events:
        HelloWorld:
          Type: Api
          Properties:
            Path: /hello
            Method: get
```

## Add a resource to your application
The application template uses AWS Serverless Application Model (AWS SAM) to define application resources. AWS SAM is an extension of AWS CloudFormation with a simpler syntax for configuring common serverless application resources such as functions, triggers, and APIs. For resources not included in [the SAM specification](https://github.com/awslabs/serverless-application-model/blob/master/versions/2016-10-31.md), you can use standard [AWS CloudFormation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html) resource types.

## Fetch, tail, and filter Lambda function logs

To simplify troubleshooting, SAM CLI has a command called `sam logs`. `sam logs` lets you fetch logs generated by your deployed Lambda function from the command line. In addition to printing the logs on the terminal, this command has several nifty features to help you quickly find the bug.

`NOTE`: This command works for all AWS Lambda functions; not just the ones you deploy using SAM.

```bash
route53-resolver-logging-sam$ sam logs -n HelloWorldFunction --stack-name route53-resolver-logging-sam --tail
```

You can find more information and examples about filtering Lambda function logs in the [SAM CLI Documentation](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-logging.html).

## Unit tests

Tests are defined in the `tests` folder in this project. Use PIP to install the [pytest](https://docs.pytest.org/en/latest/) and run unit tests.

```bash
route53-resolver-logging-sam$ pip install pytest pytest-mock --user
route53-resolver-logging-sam$ python -m pytest tests/ -v
```

## Cleanup

To delete the sample application that you created, use the AWS CLI. Assuming you used your project name for the stack name, you can run the following:

```bash
aws cloudformation delete-stack --stack-name route53-resolver-logging-sam
```

## Resources

See the [AWS SAM developer guide](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/what-is-sam.html) for an introduction to SAM specification, the SAM CLI, and serverless application concepts.

Next, you can use AWS Serverless Application Repository to deploy ready to use Apps that go beyond hello world samples and learn how authors developed their applications: [AWS Serverless Application Repository main page](https://aws.amazon.com/serverless/serverlessrepo/)
