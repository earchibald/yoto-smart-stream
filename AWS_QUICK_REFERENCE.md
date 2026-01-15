# AWS Deployment Quick Reference

## Prerequisites

```bash
# Set AWS credentials
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
export AWS_REGION="us-east-1"
export YOTO_CLIENT_ID="your_yoto_client_id"
```

## One-Command Deployment

```bash
# Deploy to dev
cd infrastructure && ./deploy.sh dev

# Deploy to prod
cd infrastructure && ./deploy.sh prod
```

## Manual Deployment Steps

### 1. Bootstrap CDK (first time only)
```bash
cd infrastructure/cdk
source .venv/bin/activate
cdk bootstrap
```

### 2. Deploy Stack
```bash
cdk deploy \
  -c environment=dev \
  -c yoto_client_id="$YOTO_CLIENT_ID" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```

### 3. Get Stack Outputs
```bash
aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs'
```

### 4. Upload UI Files
```bash
UI_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
  --output text)

aws s3 sync yoto_smart_stream/static/ s3://$UI_BUCKET/
```

### 5. Migrate Data
```bash
export DYNAMODB_TABLE="yoto-smart-stream-dev"
python infrastructure/scripts/migrate_to_dynamodb.py
```

## Testing

```bash
# Get API URL
API_URL=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

# Health check
curl $API_URL/api/health

# Test cold start timing
time curl $API_URL/api/health

# Test warm start
sleep 2 && time curl $API_URL/api/health
```

## Monitoring

```bash
# Lambda logs
aws logs tail /aws/lambda/yoto-api-dev --follow

# MQTT logs
aws logs tail /ecs/yoto-mqtt-dev --follow

# ECS service status
aws ecs describe-services \
  --cluster yoto-mqtt-dev \
  --services yoto-mqtt-dev
```

## Cost Monitoring

```bash
# Current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

## Cleanup

```bash
# Empty S3 buckets (required before deletion)
aws s3 rm s3://yoto-audio-dev-<account> --recursive
aws s3 rm s3://yoto-ui-dev-<account> --recursive

# Delete stack
cd infrastructure/cdk
cdk destroy -c environment=dev
```

## Troubleshooting

### Lambda Function Not Found
```bash
# Check if function exists
aws lambda get-function --function-name yoto-api-dev

# View function logs
aws logs tail /aws/lambda/yoto-api-dev --follow
```

### MQTT Handler Not Starting
```bash
# List ECS tasks
aws ecs list-tasks --cluster yoto-mqtt-dev

# Get task details
TASK_ARN=$(aws ecs list-tasks --cluster yoto-mqtt-dev --query 'taskArns[0]' --output text)
aws ecs describe-tasks --cluster yoto-mqtt-dev --tasks $TASK_ARN

# View logs
aws logs tail /ecs/yoto-mqtt-dev --follow
```

### DynamoDB Access Issues
```bash
# Test table access
aws dynamodb scan --table-name yoto-smart-stream-dev --limit 1

# Check IAM role
aws iam get-role --role-name YotoSmartStream-dev-LambdaRole*
```

## Common Commands

```bash
# List all stacks
cdk ls

# Show stack differences
cdk diff

# Synthesize template
cdk synth

# Deploy specific stack
cdk deploy YotoSmartStream-dev

# View CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name YotoSmartStream-dev \
  --max-items 10
```

## Environment Variables

### Lambda
- `ENVIRONMENT`: dev/staging/prod
- `DYNAMODB_TABLE`: Table name
- `S3_AUDIO_BUCKET`: Audio bucket name
- `S3_UI_BUCKET`: UI bucket name
- `YOTO_CLIENT_ID`: Yoto API client ID
- `AWS_REGION`: Automatic (Lambda runtime)

### ECS (MQTT Handler)
- `ENVIRONMENT`: dev/staging/prod
- `DYNAMODB_TABLE`: Table name
- `AWS_REGION`: us-east-1
- `YOTO_CLIENT_ID`: Yoto API client ID (set via environment variable)

## Cost Estimates

| Environment | Lambda | Fargate | DynamoDB | S3 | Total |
|-------------|--------|---------|----------|-----|-------|
| Development | $0 | $3 | $0.50 | $0.50 | $4/mo |
| Production | $0 | $3 | $1 | $1.50 | $5.50/mo |

Plus:
- API Gateway: $0.50/month
- CloudWatch Logs: $0.50/month
- Amazon Polly: Pay per use (~$2/month for typical usage)

**Total**: $7-10/month depending on usage
