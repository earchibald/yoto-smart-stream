# AWS Deployment with Python CDK

This directory contains the AWS CDK (Cloud Development Kit) implementation for deploying Yoto Smart Stream to AWS using Architecture 1 (Lambda + Fargate Spot).

## Architecture Overview

- **API**: AWS Lambda with FastAPI (via Mangum adapter)
- **MQTT Handler**: ECS Fargate Spot (persistent connection)
- **Database**: DynamoDB (serverless, pay-per-request)
- **Storage**: S3 (audio files and static UI)
- **API Gateway**: HTTP API (lower cost than REST API)
- **CDN**: CloudFront (optional, for production)
- **TTS**: Amazon Polly Neural voices (replaces gTTS)

**Estimated Monthly Cost**: $7-10/month

## Prerequisites

### 1. AWS Account Setup

```bash
# Create AWS account at https://aws.amazon.com
# Set up billing alerts at https://console.aws.amazon.com/billing/

# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Configure credentials
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

### 2. Install CDK

```bash
# Install Node.js (required for CDK)
# On Ubuntu/Debian:
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install CDK CLI
npm install -g aws-cdk

# Verify installation
cdk --version
```

### 3. Python Dependencies

```bash
# Install Python dependencies
pip install aws-cdk-lib constructs boto3
```

### 4. Environment Variables

Create a `.env` file (add to `.gitignore`):

```bash
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_REGION="us-east-1"
export YOTO_CLIENT_ID="your_yoto_client_id"
```

Load the environment:

```bash
source .env
```

## Quick Start

### Deploy to Development

```bash
cd infrastructure
./deploy.sh dev
```

### Deploy to Production

```bash
cd infrastructure
./deploy.sh prod
```

### Deploy with Custom Options

```bash
cd infrastructure/cdk

# Deploy with MQTT enabled and CloudFront disabled (default)
cdk deploy \
  -c environment=dev \
  -c yoto_client_id="your_client_id" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false

# Deploy production with CloudFront
cdk deploy \
  -c environment=prod \
  -c yoto_client_id="your_client_id" \
  -c enable_mqtt=true \
  -c enable_cloudfront=true
```

## Project Structure

```
infrastructure/
├── cdk/                    # CDK application
│   ├── app.py             # Main CDK app entry point
│   ├── cdk/
│   │   └── cdk_stack.py   # Main stack definition
│   ├── cdk.json           # CDK configuration
│   └── requirements.txt   # CDK Python dependencies
├── lambda/                 # Lambda function code
│   ├── handler.py         # Lambda handler (Mangum wrapper)
│   └── requirements.txt   # Lambda dependencies
├── mqtt_handler/           # MQTT handler for Fargate
│   ├── mqtt_standalone.py # Standalone MQTT script
│   ├── Dockerfile         # Container image
│   └── requirements.txt   # Container dependencies
├── deploy.sh              # Deployment script
└── README.md              # This file
```

## Deployment Process

### 1. Bootstrap CDK (First Time Only)

```bash
cd infrastructure/cdk
cdk bootstrap
```

This creates an S3 bucket and other resources needed for CDK deployments.

### 2. Package Lambda Function

The Lambda function needs the application code packaged with dependencies:

```bash
cd infrastructure/lambda
pip install -r requirements.txt -t package/
cp -r ../../yoto_smart_stream package/
cp handler.py package/
```

### 3. Deploy Stack

```bash
cd infrastructure/cdk
cdk deploy -c environment=dev -c yoto_client_id="your_client_id"
```

### 4. Upload Static UI

After deployment, upload the UI files to S3:

```bash
UI_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
  --output text)

aws s3 sync ../../yoto_smart_stream/static/ s3://$UI_BUCKET/
```

### 5. Migrate Data

Migrate data from SQLite to DynamoDB:

```python
# See migration script: infrastructure/scripts/migrate_to_dynamodb.py
python infrastructure/scripts/migrate_to_dynamodb.py
```

## CDK Commands

```bash
# List all stacks
cdk ls

# Synthesize CloudFormation template
cdk synth

# Show differences between deployed and local
cdk diff

# Deploy stack
cdk deploy

# Destroy stack
cdk destroy
```

## Stack Outputs

After deployment, the stack outputs key information:

- **ApiUrl**: API Gateway endpoint URL
- **DynamoDBTableName**: DynamoDB table name
- **AudioBucketName**: S3 bucket for audio files
- **UIBucketName**: S3 bucket for UI files
- **LambdaFunctionArn**: Lambda function ARN
- **MQTTServiceArn**: ECS service ARN (if MQTT enabled)
- **CloudFrontDomainName**: CloudFront URL (if enabled)

Get outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs'
```

## Testing

### Test API Endpoint

```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

# Health check
curl $API_URL/api/health

# Test cold start time
time curl $API_URL/api/health

# Test warm start (within 15 minutes)
time curl $API_URL/api/health
```

### Monitor Lambda Logs

```bash
# Tail Lambda logs
aws logs tail /aws/lambda/yoto-api-dev --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/yoto-api-dev \
  --filter-pattern "ERROR"
```

### Monitor MQTT Handler

```bash
# Tail MQTT logs
aws logs tail /ecs/yoto-mqtt-dev --follow

# Check ECS service status
aws ecs describe-services \
  --cluster yoto-mqtt-dev \
  --services yoto-mqtt-dev
```

## Cost Monitoring

### View Current Month Costs

```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### Set Budget Alert

```bash
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

## Troubleshooting

### Lambda Function Errors

```bash
# Check function configuration
aws lambda get-function --function-name yoto-api-dev

# Invoke function directly
aws lambda invoke \
  --function-name yoto-api-dev \
  --payload '{"rawPath": "/api/health"}' \
  response.json
cat response.json
```

### MQTT Handler Not Starting

```bash
# Check task status
aws ecs list-tasks --cluster yoto-mqtt-dev

# Get task details
TASK_ARN=$(aws ecs list-tasks --cluster yoto-mqtt-dev --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster yoto-mqtt-dev --tasks $TASK_ARN

# Check logs
aws logs tail /ecs/yoto-mqtt-dev --follow
```

### DynamoDB Access Issues

```bash
# Test DynamoDB access
aws dynamodb scan --table-name yoto-smart-stream-dev --limit 1

# Check IAM permissions
aws iam get-role --role-name YotoSmartStream-dev-LambdaRole*
```

## Rollback

### Rollback to Previous Version

```bash
# Deploy previous version
git checkout <previous-commit>
cdk deploy -c environment=dev

# Or use CloudFormation rollback
aws cloudformation rollback-stack --stack-name YotoSmartStream-dev
```

### Revert to Railway

If you need to quickly revert to Railway:

1. Update DNS to point back to Railway URL
2. Keep AWS resources running for testing
3. Once stable, you can destroy AWS stack: `cdk destroy`

## Cleanup

### Delete All Resources

```bash
# Empty S3 buckets first (required)
aws s3 rm s3://yoto-audio-dev-<account-id> --recursive
aws s3 rm s3://yoto-ui-dev-<account-id> --recursive

# Destroy stack
cd infrastructure/cdk
cdk destroy -c environment=dev
```

## Multi-Environment Setup

### Development Environment

```bash
cdk deploy \
  -c environment=dev \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```

### Staging Environment

```bash
cdk deploy \
  -c environment=staging \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```

### Production Environment

```bash
cdk deploy \
  -c environment=prod \
  -c enable_mqtt=true \
  -c enable_cloudfront=true
```

## CI/CD Integration

### GitHub Actions Example

Create `.github/workflows/deploy-aws.yml`:

```yaml
name: Deploy to AWS

on:
  push:
    branches: [main, develop]
  workflow_dispatch:

env:
  AWS_REGION: us-east-1

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Install CDK
        run: npm install -g aws-cdk
      
      - name: Deploy
        run: |
          cd infrastructure
          ./deploy.sh dev ${{ secrets.YOTO_CLIENT_ID }}
```

## Support

For issues or questions:
1. Check CloudWatch logs
2. Review AWS documentation: https://docs.aws.amazon.com/cdk/
3. Open an issue on GitHub

## References

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [AWS Lambda Python Runtime](https://docs.aws.amazon.com/lambda/latest/dg/lambda-python.html)
- [Mangum - AWS Lambda adapter for ASGI](https://mangum.io/)
- [Amazon Polly Documentation](https://docs.aws.amazon.com/polly/)
- [AWS Cost Calculator](https://calculator.aws/)
