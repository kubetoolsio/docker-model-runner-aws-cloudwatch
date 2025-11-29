## Overview

 This document defines the Identity and Access Management (IAM) configuration required for the Conversational CloudWatch Log Analysis service when extended to real AWS environments

The FastAPI microservice currently supports both **deterministic local mode** and **LLM-powered mode** using TinyLlama via Ollama.  
When extended to live AWS CloudWatch data, IAM permissions will enable the application to:

- Retrieve log events from CloudWatch groups
- Filter logs by time range or log group name
- Maintain least-privilege access to resources
- Optionally write insights or summaries to an S3 bucket
- (Future) Trigger SNS/Lambda notifications for incident automation

##  1. IAM Role Structure
```
Role Name	                                   Purpose	                                                               Attached Policy
--------------------------------------------------------------------------------------------------------------------------------------------------------
ConversationalCloudWatchAppRole      |       Main execution role for FastAPI container	                   |          ConversationalCloudWatchAppPolicy
ConversationalCloudWatchReadOnly     |     Optional user-assigned role for local testing                   |          AWSCloudWatchReadOnlyAccess
```

## 2. Custom IAM Policy — Read Access Only

- Below is the minimal custom policy the app would need to retrieve CloudWatch logs safely.
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "CloudWatchReadAccess",
      "Effect": "Allow",
      "Action": [
        "logs:GetLogEvents",
        "logs:FilterLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/*"
    },
    {
      "Sid": "S3WriteForSummaries",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Resource": "arn:aws:s3:::convo-cloudwatch-summaries/*"
    }
  ]
}
```

**Purpose:**

- Grants read-only access to CloudWatch logs
- Allows writing generated summaries to an S3 bucket (optional)
- Follows least privilege principles - no Delete or Write Logs actions are granted.

## 3. Environment Variable Setup

- Credentials are only needed for real AWS integration (deterministic/local runs do not require them).

```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<your-access-key-id>
AWS_SECRET_ACCESS_KEY=<your-secret-access-key>
AWS_SESSION_TOKEN=<temporary-session-token>   # Optional for roles
MOCK=false
USE_LLM=true
```

For secure environments, credentials should be injected via:
- ECS Task Roles 
- Cloud Run secrets
- AWS Secrets Manager

## 4. Security and Least Privilege Principles
```
|  Principle                 |  Description                                                                       |
| -------------------------- | ---------------------------------------------------------------------------------- |
| Least Privilege            | Grant only the exact actions required ( GetLogEvents, FilterLogEvents, etc.).      |
| No Write to CloudWatch     | The app only reads logs; it does not alter, delete, or publish logs.               |
| Scoped Resources           | Limit to /aws/lambda/ or specific project log groups.                              |
| Credential Rotation        | Use short-lived STS tokens or IAM roles, not permanent keys.                       |
| Secret Management          | Store secrets in AWS Secrets Manager or Parameter Store, not .env in production.   |

```


## 5. Optional Extended Policy (Future Integration)

For a more complete future deployment, this optional policy could enable:

  - S3 Logging of Summaries
  - SNS Notifications on anomaly detection
  - Lambda Function Invocation for automated remediation
```
{
  "Sid": "ExtendedIntegration",
  "Effect": "Allow",
  "Action": [
    "sns:Publish",
    "lambda:InvokeFunction"
  ],
  "Resource": [
    "arn:aws:sns:us-east-1:123456789012:convo-alerts",
    "arn:aws:lambda:us-east-1:123456789012:function:convo-remediate"
  ]
}
```

## 6. Role Attachment Example

- Below is an example of how to create and attach the IAM role via AWS CLI:
```
aws iam create-role \
  --role-name ConversationalCloudWatchAppRole \
  --assume-role-policy-document file://trust-policy.json

aws iam put-role-policy \
  --role-name ConversationalCloudWatchAppRole \
  --policy-name ConversationalCloudWatchAppPolicy \
  --policy-document file://cw-read-policy.json
```

trust-policy.json example:
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ecs-tasks.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

## 7. Summary
```
Category	                                                    Description
---------------------------------------------------------------------------------------------------------------
Access Type	                   |                              /aws/lambda/* log groups
Key Actions	                   |                              logs:GetLogEvents, logs:FilterLogEvents
Security                       |                            	Follows least-privilege & rotation best practices
Integration Ready	           |                              Compatible with ECS, Lambda, or Cloud Run setups
```
## Final Notes

This IAM configuration ensures the Conversational CloudWatch application can:

- Safely retrieve AWS CloudWatch logs
- Summarize and export structured insights
- Remain secure and auditable under AWS IAM best practices

Currently, these configurations remain documented but inactive, as your deployment runs in deterministic local mode or LLM mode during development.
They can be activated seamlessly during future AWS integrations (e.g., Boto3 or Cloud Run).