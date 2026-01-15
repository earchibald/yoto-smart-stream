# Getting Started with AWS Deployment

This guide walks you through deploying and testing the Yoto Smart Stream service on AWS.

## Prerequisites

Before you begin, ensure you have:

- ✅ AWS credentials (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION)
- ✅ Yoto API client ID (from https://yoto.dev/)
- ✅ Email address for billing alerts
- ✅ Docker installed (for MQTT handler)
- ✅ Python 3.9+ and Node.js 18+ installed

## Quick Start (5 minutes)

### 1. Set Environment Variables

```bash
# AWS Credentials
export AWS_ACCESS_KEY_ID="your_access_key"
export AWS_SECRET_ACCESS_KEY="your_secret_key"
export AWS_REGION="us-east-1"

# Yoto API
export YOTO_CLIENT_ID="your_yoto_client_id"

# Billing Alerts (optional but recommended)
export BILLING_ALERT_EMAIL="your@email.com"
export BILLING_ALERT_THRESHOLD="10.0"  # Alert when charges exceed $10
```

### 2. Deploy to AWS

```bash
cd infrastructure
./deploy.sh dev
```

That's it! The script will:
- Install dependencies
- Package the Lambda function
- Build the MQTT handler container
- Deploy all AWS resources
- Configure billing alerts
- Output the API URL

Expected deployment time: **10-15 minutes**

### 3. Get Your API URL

After deployment, the script outputs your API URL:

```bash
API URL: https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com
```

Save this URL - you'll need it for testing.

## Testing Your Deployment

### Test 1: Health Check

```bash
# Set your API URL
export API_URL="https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com"

# Test the health endpoint
curl $API_URL/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.2.1",
  "environment": "dev"
}
```

### Test 2: Cold Start Timing

Test Lambda cold start performance:

```bash
# Wait 20 minutes for Lambda to go cold
sleep 1200

# Time the cold start
time curl $API_URL/api/health
# Expected: 2-5 seconds

# Test warm start (within 15 minutes)
sleep 2
time curl $API_URL/api/health
# Expected: <100ms
```

### Test 3: Create Admin User in Cognito

Create your first admin user:

```bash
# Get your User Pool ID
POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)

# Create admin user
aws cognito-idp admin-create-user \
  --user-pool-id $POOL_ID \
  --username admin \
  --user-attributes Name=email,Value=admin@example.com Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $POOL_ID \
  --username admin \
  --password "SecurePass123!" \
  --permanent
```

### Test 4: Login

Test authentication:

```bash
curl -X POST $API_URL/api/user/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "SecurePass123!"
  }' \
  -c cookies.txt
```

Expected response:
```json
{
  "success": true,
  "message": "Login successful",
  "username": "admin"
}
```

### Test 5: Check Session

Verify your session is active:

```bash
curl $API_URL/api/user/session -b cookies.txt
```

Expected response:
```json
{
  "authenticated": true,
  "username": "admin",
  "is_admin": true
}
```

### Test 6: Authenticate with Yoto

Connect to your Yoto account:

```bash
curl -X POST $API_URL/api/auth/device-flow/initiate \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

This returns:
```json
{
  "device_code": "xxxx",
  "user_code": "ABCD-EFGH",
  "verification_uri": "https://yoto.io/device",
  "expires_in": 900
}
```

Go to https://yoto.io/device and enter the user code, then poll for completion:

```bash
curl -X POST $API_URL/api/auth/device-flow/poll \
  -H "Content-Type: application/json" \
  -d '{"device_code": "xxxx"}' \
  -b cookies.txt
```

### Test 7: List Yoto Players

Once authenticated with Yoto:

```bash
curl $API_URL/api/players -b cookies.txt
```

Expected response:
```json
{
  "players": [
    {
      "id": "player-id-123",
      "name": "Living Room Player",
      "online": true,
      "battery_level": 85
    }
  ]
}
```

### Test 8: Monitor MQTT Handler

Check if MQTT handler is running:

```bash
# Get cluster name
CLUSTER=$(aws ecs list-clusters --query 'clusterArns[0]' --output text | rev | cut -d'/' -f1 | rev)

# List tasks
aws ecs list-tasks --cluster $CLUSTER

# View logs
aws logs tail /ecs/yoto-mqtt-dev --follow
```

Expected log output:
```
Starting MQTT Handler for environment: dev
Checking and refreshing tokens...
Starting MQTT connection...
MQTT connection established
```

## Monitoring

### View Lambda Logs

```bash
aws logs tail /aws/lambda/yoto-api-dev --follow
```

### View MQTT Logs

```bash
aws logs tail /ecs/yoto-mqtt-dev --follow
```

### Check Costs

```bash
# Current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### Billing Alerts

You'll receive an email when you:
1. First deploy (to confirm SNS subscription)
2. Exceed your billing threshold (default: $10/month)

Click the confirmation link in the first email to activate billing alerts.

## Stack Outputs

View all stack outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs' \
  --output table
```

Key outputs:
- `ApiUrl`: Your API Gateway endpoint
- `UserPoolId`: Cognito User Pool ID
- `UserPoolClientId`: Cognito App Client ID
- `DynamoDBTableName`: DynamoDB table name
- `AudioBucketName`: S3 bucket for audio files
- `UIBucketName`: S3 bucket for static UI
- `BillingAlertTopicArn`: SNS topic for billing alerts
- `CognitoLoginUrl`: Hosted UI login URL

## Common Issues

### Issue: Lambda Cold Start Too Slow

**Solution**: Cold starts (2-5s) are normal for Lambda. They only occur once per session (first request after 15+ minutes of inactivity).

### Issue: Billing Alert Email Not Received

**Solution**: Check your spam folder. The SNS subscription confirmation email might be filtered. Look for emails from "AWS Notifications".

### Issue: Authentication Fails

**Solutions**:
1. Verify Cognito user was created: `aws cognito-idp admin-get-user --user-pool-id $POOL_ID --username admin`
2. Check Lambda logs: `aws logs tail /aws/lambda/yoto-api-dev --follow`
3. Ensure password meets requirements (8+ chars, uppercase, lowercase, digits)

### Issue: MQTT Handler Not Running

**Solutions**:
1. Check ECS service: `aws ecs describe-services --cluster yoto-mqtt-dev --services yoto-mqtt-dev`
2. View task logs: `aws logs tail /ecs/yoto-mqtt-dev --follow`
3. Verify Yoto tokens are in DynamoDB

### Issue: No Audio Playback

**Solutions**:
1. Check S3 bucket has audio files: `aws s3 ls s3://yoto-audio-dev-{account}/audio/`
2. Verify CORS is configured on audio bucket
3. Check Yoto device can reach API endpoint

## Next Steps

### 1. Upload Audio Files

```bash
# Get audio bucket name
AUDIO_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AudioBucketName`].OutputValue' \
  --output text)

# Upload audio files
aws s3 cp /path/to/audio.mp3 s3://$AUDIO_BUCKET/audio/
```

### 2. Upload Static UI

```bash
# Get UI bucket name
UI_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
  --output text)

# Upload UI files
aws s3 sync ../yoto_smart_stream/static/ s3://$UI_BUCKET/
```

### 3. Create Additional Users

```bash
curl -X POST $API_URL/api/admin/users \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "username": "family_member",
    "email": "family@example.com",
    "password": "SecurePass456!"
  }'
```

### 4. Deploy to Production

Once dev is working, deploy to production:

```bash
./deploy.sh prod your_yoto_client_id your@email.com
```

## Troubleshooting Commands

```bash
# Check stack status
aws cloudformation describe-stacks --stack-name YotoSmartStream-dev

# View stack events
aws cloudformation describe-stack-events --stack-name YotoSmartStream-dev --max-items 10

# Test Lambda directly
aws lambda invoke \
  --function-name yoto-api-dev \
  --payload '{"rawPath":"/api/health"}' \
  response.json
cat response.json

# List Cognito users
POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UserPoolId`].OutputValue' \
  --output text)
aws cognito-idp list-users --user-pool-id $POOL_ID

# Check DynamoDB table
TABLE=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`DynamoDBTableName`].OutputValue' \
  --output text)
aws dynamodb scan --table-name $TABLE --limit 5
```

## Cost Monitoring

Set up additional budget alerts:

```bash
# Create a budget for $5/month
aws budgets create-budget \
  --account-id $(aws sts get-caller-identity --query Account --output text) \
  --budget file://budget-config.json
```

Create `budget-config.json`:
```json
{
  "BudgetName": "YotoSmartStreamBudget",
  "BudgetLimit": {
    "Amount": "5",
    "Unit": "USD"
  },
  "TimeUnit": "MONTHLY",
  "BudgetType": "COST"
}
```

## Getting Help

- **CloudWatch Logs**: Check `/aws/lambda/yoto-api-dev` and `/ecs/yoto-mqtt-dev`
- **Stack Events**: Use `aws cloudformation describe-stack-events`
- **Documentation**: See `infrastructure/README.md` for detailed information
- **Cognito Guide**: See `docs/AWS_COGNITO_AUTH.md` for authentication details

## Cleanup

To delete all resources:

```bash
# Empty S3 buckets (required before deletion)
AUDIO_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`AudioBucketName`].OutputValue' \
  --output text)
UI_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
  --output text)

aws s3 rm s3://$AUDIO_BUCKET --recursive
aws s3 rm s3://$UI_BUCKET --recursive

# Delete stack
cd infrastructure/cdk
cdk destroy -c environment=dev
```

**Warning**: This permanently deletes all data, users, and configurations.
