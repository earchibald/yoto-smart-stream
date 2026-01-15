# Architecture 1: Minimal Cost Implementation Guide
# AWS Lambda + Fargate Spot Deployment ($5-8/month)

**Last Updated:** 2026-01-15  
**Architecture:** Minimal Cost (Lambda + Fargate Spot)  
**Monthly Cost:** $5-8  
**Purpose:** Step-by-step implementation reference for session continuity

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Cold Start Deep Dive](#cold-start-deep-dive)
3. [Prerequisites](#prerequisites)
4. [Phase-by-Phase Implementation](#phase-by-phase-implementation)
5. [Monitoring & Operations](#monitoring--operations)
6. [Troubleshooting](#troubleshooting)

---

## Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Internet / Yoto Devices                       │
│               (Users, Yoto Players, Yoto API)                    │
└────────────┬────────────────────────────────────────────────────┘
             │ HTTPS
             │
┌────────────▼─────────────────────────────────────────────────────┐
│          AWS API Gateway (HTTP API)                              │
│  • Entry point for all API requests                             │
│  • Cost: ~\$0.50/month                                            │
│  • TRIGGERS: Lambda function on each request                    │
└────────────┬─────────────────────────────────────────────────────┘
             │
             │ [COLD START IF IDLE >15 MIN: 2-5 seconds]
             │ [WARM IF <15 MIN: <100ms]
             │
┌────────────▼─────────────────────────────────────────────────────┐
│          AWS Lambda (FastAPI via Mangum)                         │
│  • Runtime: Python 3.9, 1GB RAM, 30s timeout                    │
│  • Deployment: ~50MB package (FastAPI + dependencies)           │
│  • Scales: 0 to 1000+ concurrent executions                     │
│  • Cost: \$0 (free tier: 1M requests/month)                      │
└─────┬────────────────────────────────┬───────────────────────────┘
      │                                │
      │ Read/Write                     │ Generate pre-signed URLs
      │                                │
┌─────▼─────────────────┐    ┌────────▼────────────────────────────┐
│  DynamoDB On-Demand   │    │  S3 + CloudFront                     │
│  • Users + tokens     │    │  • audio/ - MP3 files                │
│  • Single table       │    │  • static/ - UI files                │
│  • Cost: \$1/month     │    │  • Pre-signed URLs (1 hour expiry)  │
└───────────────────────┘    │  • CloudFront caching                │
                              │  • Cost: \$1.50/month                 │
                              └──────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│         ECS Fargate Spot (MQTT Handler)                          │
│  • Container: Python MQTT client (separate process)             │
│  • Size: 0.25 vCPU, 0.5GB RAM                                   │
│  • ALWAYS RUNNING (persistent MQTT connection)                  │
│  • No cold starts                                                │
│  • Auto-reconnects on Spot interruption                         │
│  • Includes: Token refresh every 12 hours                       │
│  • Cost: \$3/month (70% Spot discount)                           │
└────────────┬─────────────────────────────────────────────────────┘
             │
             │ Writes events
             │
             └───────────► [DynamoDB]

TOTAL COST: \$6/month (can vary \$5-8 based on usage)
```

---

## Cold Start Deep Dive

### What is a Cold Start?

A **cold start** is the initialization time required when AWS Lambda creates a new execution environment. This happens when your Lambda function hasn't been invoked recently.

### Cold Start Timeline

```
REQUEST ARRIVES
    │
    ├─ [0-1s] AWS Provisions Infrastructure
    │         • Allocate compute capacity
    │         • Setup network interfaces
    │         • Initialize security context
    │
    ├─ [1-2s] Download Code
    │         • Pull deployment package from S3 (~50MB)
    │         • Unzip and stage files
    │         • Verify integrity
    │
    ├─ [2-4s] Initialize Runtime
    │         • Start Python 3.9 interpreter
    │         • Import modules:
    │           - fastapi (~500ms)
    │           - mangum (~200ms)
    │           - boto3 (AWS SDK) (~300ms)
    │           - yoto_api (~200ms)
    │           - pydantic, paho-mqtt, etc. (~300ms)
    │         • Execute module-level code
    │         • Initialize Mangum ASGI adapter
    │         • Create FastAPI application instance
    │
    ├─ [4-5s] Execute Handler
    │         • Process actual HTTP request
    │         • Query DynamoDB / Call S3
    │         • Generate response
    │
    └─ RESPONSE (Total: 2-5 seconds)
```

### Warm Start (Container Reuse)

```
REQUEST ARRIVES
    │
    ├─ Lambda reuses EXISTING container
    │  • Python already running
    │  • Modules already imported
    │  • FastAPI app already initialized
    │
    ├─ [<100ms] Execute Handler Only
    │           • Process HTTP request
    │           • Return response
    │
    └─ RESPONSE (Total: 50-100 milliseconds)
```

### When Cold Starts Happen

#### Timeline Examples

**Scenario 1: Morning First Use (COLD START)**
```
11:00 PM - Last use (bedtime story)
11:15 PM - Lambda container goes idle
11:30 PM - Lambda deallocates container
...
7:00 AM  - Open app on phone
           ⚠️ COLD START (2-5 seconds)
           User sees: "Loading..." for a few seconds
7:01 AM  - Browse library
           ✅ WARM (<100ms) - Fast response
7:05 AM  - Start playing story
           ✅ WARM (<100ms) - Fast response
```

**Scenario 2: Throughout Day (MOSTLY WARM)**
```
8:00 AM  - Morning story
           [Warm if <15 min since last use, otherwise Cold]
8:15 AM  - Adjust volume
           ✅ WARM (<100ms)
...
12:30 PM - Lunch story (4+ hours since last)
           ⚠️ COLD START (2-5 seconds)
12:35 PM - Skip to next chapter
           ✅ WARM (<100ms)
...
7:00 PM  - Bedtime story (6+ hours since last)
           ⚠️ COLD START (2-5 seconds)
7:15 PM  - Pause/resume
           ✅ WARM (<100ms)
```

### Which Endpoints Experience Cold Starts?

**All API endpoints** can have cold starts, but frequency varies:

#### Always Warm (If UI Polling Enabled)
- `/api/health` - Health checks every 1-5 minutes
- `/api/players` - Player status (polled by UI)

#### Sometimes Cold
- `/api/cards/*` - Card management
- `/api/library/*` - Library browse
- **Impact:** Acceptable for these operations

#### Usually Cold
- `/api/admin/*` - Admin functions (rarely used)
- `/api/auth/*` - OAuth (only during setup)
- **Impact:** Acceptable, these are infrequent

### Cold Start vs Warm Performance Data

| Metric | Cold Start | Warm Start |
|--------|-----------|-----------|
| **Lambda Init** | 2,000-4,000ms | 0ms (reused) |
| **Request Processing** | 100-200ms | 100-200ms |
| **Total Response Time** | 2,100-4,200ms | 100-200ms |
| **User Perception** | "Slow to load" | "Instant" |
| **Frequency** | 2-5 times/day | 95-98% of requests |

### Why Cold Starts Are Acceptable

1. **Infrequent:** Only happens 2-5 times per day (once per usage session)
2. **Cost Savings:** Saves \$15-20/month vs always-on Fargate
3. **Home Use:** Not mission-critical, slight delay acceptable
4. **Subsequent Requests:** Fast after first request

### Minimizing Cold Start Impact

#### Strategy 1: Accept Cold Starts (Recommended)
- **Cost:** \$0
- **Implementation:** None
- **Result:** 2-5s delay once per session

#### Strategy 2: Smart Keep-Warm
- **Cost:** +\$0.20/month
- **Implementation:**
  ```yaml
  # EventBridge schedule
  Morning (7-9 AM): Ping every 10 minutes
  Evening (5-8 PM): Ping every 10 minutes
  ```
- **Result:** Warm during expected usage times

#### Strategy 3: UI Polling
- **Cost:** \$0 (uses existing requests)
- **Implementation:** UI polls `/api/players` every 2-5 minutes
- **Result:** Lambda stays warm during active UI sessions

### MQTT Handler: Why Always-On (No Cold Starts)

```
MQTT Requirements:
✓ Persistent TCP connection to mqtt.yoto.io
✓ Must receive events 24/7 (button presses, status updates)
✓ Cannot tolerate disconnections
✓ Interactive cards depend on real-time event processing

Lambda Limitations:
✗ 15-minute maximum execution time
✗ Would disconnect MQTT every 15 minutes
✗ Missing events is unacceptable

Solution: ECS Fargate Spot
✓ Always running (no time limits)
✓ Maintains persistent MQTT connection
✓ Auto-reconnects on rare Spot interruptions
✓ Cost: \$3/month (70% discount with Spot)
```

---

## Prerequisites

### Required Tools

Install these tools on your local machine:

```bash
# 1. AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# 2. AWS SAM CLI (for Lambda deployment)
pip install aws-sam-cli

# 3. Docker (for building containers)
# Install from: https://docs.docker.com/get-docker/

# 4. Verify installations
aws --version        # Should show: aws-cli/2.x.x
sam --version        # Should show: SAM CLI, version 1.x.x
docker --version     # Should show: Docker version 20.x.x
```

### AWS Account Configuration

```bash
# Configure AWS credentials
aws configure
# Enter when prompted:
#   AWS Access Key ID: YOUR_ACCESS_KEY
#   AWS Secret Access Key: YOUR_SECRET_KEY
#   Default region name: us-east-1
#   Default output format: json

# Verify configuration
aws sts get-caller-identity
# Should output your AWS account ID and user ARN
```

### Environment Variables

Create `.env.aws` file (add to `.gitignore`):

```bash
# AWS Configuration
export AWS_ACCOUNT_ID="123456789012"
export AWS_REGION="us-east-1"

# Yoto Configuration
export YOTO_CLIENT_ID="your_yoto_client_id_here"

# AWS Resources
export S3_BUCKET_AUDIO="yoto-smart-stream-audio"
export S3_BUCKET_UI="yoto-smart-stream-ui"
export DYNAMODB_TABLE="yoto-smart-stream"
export LAMBDA_FUNCTION_NAME="yoto-api"
export ECR_REPOSITORY="yoto-mqtt"
export ECS_CLUSTER="yoto-mqtt-cluster"
export ECS_SERVICE="yoto-mqtt-service"

# Load variables
source .env.aws
```

---

## Phase-by-Phase Implementation

### Phase 1: AWS Account Setup (30 minutes)

#### 1.1 Create AWS Account

1. Go to https://aws.amazon.com/
2. Click "Create an AWS Account"
3. Follow signup wizard (requires credit card)
4. Choose "Basic Support (Free)"

#### 1.2 Set Up Billing Alerts

```bash
# Create SNS topic for alerts
aws sns create-topic --name billing-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:${AWS_ACCOUNT_ID}:billing-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Confirm subscription in email

# Create billing alarm (\$10 threshold)
aws cloudwatch put-metric-alarm \
  --alarm-name MonthlyBillingAlert \
  --alarm-description "Alert when monthly charges exceed \$10" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 10.0 \
  --comparison-operator GreaterThanThreshold \
  --alarm-actions arn:aws:sns:us-east-1:${AWS_ACCOUNT_ID}:billing-alerts
```

**Checkpoint:**
- [ ] AWS account created
- [ ] Billing alert configured
- [ ] AWS CLI configured

---

### Phase 2: S3 Storage (4 hours)

#### 2.1 Create S3 Buckets

```bash
# Audio bucket
aws s3api create-bucket \
  --bucket ${S3_BUCKET_AUDIO} \
  --region us-east-1

# UI bucket
aws s3api create-bucket \
  --bucket ${S3_BUCKET_UI} \
  --region us-east-1

# Configure CORS (required for Yoto devices)
aws s3api put-bucket-cors \
  --bucket ${S3_BUCKET_AUDIO} \
  --cors-configuration file://s3-cors-config.json
```

Create `s3-cors-config.json`:
```json
{
  "CORSRules": [{
    "AllowedOrigins": ["*"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 3600
  }]
}
```

#### 2.2 Migrate Audio Files

```bash
# From Railway: Export audio files
railway run tar -czf /tmp/audio.tar.gz /data/audio_files/
railway cp /tmp/audio.tar.gz ./audio.tar.gz

# Upload to S3
tar -xzf audio.tar.gz
aws s3 sync ./audio_files/ s3://${S3_BUCKET_AUDIO}/audio/ \
  --storage-class STANDARD

# Verify
aws s3 ls s3://${S3_BUCKET_AUDIO}/audio/ --recursive --human-readable
```

#### 2.3 Test S3 Streaming

```python
# test_s3_streaming.py
import boto3

s3 = boto3.client('s3')

# Generate pre-signed URL
url = s3.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'yoto-smart-stream-audio', 'Key': 'audio/test.mp3'},
    ExpiresIn=3600
)

print(f"Pre-signed URL: {url}")
# Test by opening URL in browser - should download/play MP3
```

**Checkpoint:**
- [ ] S3 buckets created
- [ ] Audio files uploaded
- [ ] Pre-signed URLs working

---

### Phase 3: DynamoDB (8 hours)

#### 3.1 Create Table

```bash
aws dynamodb create-table \
  --table-name ${DYNAMODB_TABLE} \
  --attribute-definitions \
    AttributeName=PK,AttributeType=S \
    AttributeName=SK,AttributeType=S \
  --key-schema \
    AttributeName=PK,KeyType=HASH \
    AttributeName=SK,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST

# Enable backups
aws dynamodb update-continuous-backups \
  --table-name ${DYNAMODB_TABLE} \
  --point-in-time-recovery-specification PointInTimeRecoveryEnabled=true
```

#### 3.2 Export SQLite Data

```python
# export_sqlite_to_dynamodb.py
import sqlite3
import boto3
import json
from datetime import datetime, timezone

# Connect to SQLite
conn = sqlite3.connect('yoto_smart_stream.db')
cursor = cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

# Connect to DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('yoto-smart-stream')

# Import users
for user in users:
    item = {
        'PK': f'USER#{user[1]}',  # username
        'SK': 'PROFILE',
        'username': user[1],
        'hashed_password': user[2],
        'is_admin': bool(user[5]),
        'is_active': bool(user[4]),
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Add Yoto tokens if present
    if user[6]:  # yoto_refresh_token
        item['yoto_refresh_token'] = user[6]
    
    table.put_item(Item=item)
    print(f"Imported: {user[1]}")

conn.close()
```

**Checkpoint:**
- [ ] DynamoDB table created
- [ ] Data migrated from SQLite
- [ ] Test queries working

---

### Phase 4: MQTT Fargate Spot (8 hours)

#### 4.1 Create ECR Repository

```bash
# Create repository for Docker image
aws ecr create-repository --repository-name ${ECR_REPOSITORY}

# Get login command
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
```

#### 4.2 Create MQTT Handler Container

Create `mqtt_handler/Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY mqtt_standalone.py .

# Run MQTT handler
CMD ["python", "mqtt_standalone.py"]
```

Create `mqtt_handler/mqtt_standalone.py`:
```python
import asyncio
import logging
import os
import boto3
from yoto_api import YotoManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize DynamoDB for token storage
dynamodb = boto3.resource('dynamodb', region_name=os.environ['AWS_REGION'])
table = dynamodb.Table(os.environ['DYNAMODB_TABLE'])

def get_tokens():
    """Get Yoto tokens from DynamoDB."""
    response = table.get_item(Key={'PK': 'USER#admin', 'SK': 'PROFILE'})
    item = response.get('Item', {})
    return item.get('yoto_refresh_token')

def save_tokens(refresh_token, access_token, expires_at):
    """Save Yoto tokens to DynamoDB."""
    table.update_item(
        Key={'PK': 'USER#admin', 'SK': 'PROFILE'},
        UpdateExpression='SET yoto_refresh_token = :rt, yoto_access_token = :at, yoto_token_expires_at = :exp',
        ExpressionAttributeValues={
            ':rt': refresh_token,
            ':at': access_token,
            ':exp': expires_at
        }
    )

async def main():
    client_id = os.environ['YOTO_CLIENT_ID']
    refresh_token = get_tokens()
    
    ym = YotoManager(client_id=client_id)
    ym.set_refresh_token(refresh_token)
    
    # Refresh token
    ym.check_and_refresh_token()
    save_tokens(ym.refresh_token, ym.access_token, ym.token_expiry)
    
    # Start MQTT
    logger.info("Starting MQTT connection...")
    ym.connect_to_mqtt()
    
    # Token refresh loop (every 12 hours)
    async def token_refresh_loop():
        while True:
            await asyncio.sleep(12 * 3600)
            logger.info("Refreshing tokens...")
            ym.check_and_refresh_token()
            save_tokens(ym.refresh_token, ym.access_token, ym.token_expiry)
    
    # Run both
    await asyncio.gather(
        asyncio.to_thread(ym.mqtt_client.loop_forever),
        token_refresh_loop()
    )

if __name__ == '__main__':
    asyncio.run(main())
```

#### 4.3 Build and Push Docker Image

```bash
cd mqtt_handler

# Build image
docker build -t ${ECR_REPOSITORY}:latest .

# Tag for ECR
docker tag ${ECR_REPOSITORY}:latest \
  ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest

# Push to ECR
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}:latest
```

#### 4.4 Create ECS Cluster and Service

```bash
# Create cluster
aws ecs create-cluster --cluster-name ${ECS_CLUSTER}

# Create task definition (see task-definition.json below)
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service with Fargate Spot
aws ecs create-service \
  --cluster ${ECS_CLUSTER} \
  --service-name ${ECS_SERVICE} \
  --task-definition yoto-mqtt-handler:1 \
  --desired-count 1 \
  --launch-type FARGATE \
  --capacity-provider-strategy \
    capacityProvider=FARGATE_SPOT,weight=1 \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxxxx],securityGroups=[sg-xxxxx],assignPublicIp=ENABLED}"
```

Create `task-definition.json`:
```json
{
  "family": "yoto-mqtt-handler",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [{
    "name": "mqtt-handler",
    "image": "<AWS_ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/yoto-mqtt:latest",
    "essential": true,
    "environment": [
      {"name": "YOTO_CLIENT_ID", "value": "your_client_id"},
      {"name": "DYNAMODB_TABLE", "value": "yoto-smart-stream"},
      {"name": "AWS_REGION", "value": "us-east-1"}
    ],
    "logConfiguration": {
      "logDriver": "awslogs",
      "options": {
        "awslogs-group": "/ecs/yoto-mqtt",
        "awslogs-region": "us-east-1",
        "awslogs-stream-prefix": "ecs"
      }
    }
  }]
}
```

**Checkpoint:**
- [ ] MQTT container built and pushed
- [ ] ECS cluster created
- [ ] Fargate Spot service running
- [ ] MQTT connection established

---

### Phase 5: Lambda API (12 hours)

#### 5.1 Create Lambda Deployment Package

Create `lambda/handler.py`:
```python
from mangum import Mangum
from yoto_smart_stream.api.app import create_app

# Create FastAPI app
app = create_app()

# Disable lifespan events in Lambda (no startup/shutdown tasks)
handler = Mangum(app, lifespan="off")
```

Create `lambda/requirements.txt`:
```
fastapi>=0.104.0
mangum>=0.17.0
boto3>=1.28.0
yoto_api>=2.1.0
pydantic>=2.4.0
python-multipart>=0.0.6
pillow>=10.0.0
gtts>=2.5.0
```

#### 5.2 Package Lambda Function

```bash
cd lambda

# Create deployment package
pip install -r requirements.txt -t package/
cp handler.py package/
cp -r ../yoto_smart_stream package/

# Zip package
cd package
zip -r ../lambda-deployment.zip .
cd ..

# Check size (should be <50MB)
ls -lh lambda-deployment.zip
```

#### 5.3 Create Lambda Function

```bash
# Create execution role first
aws iam create-role \
  --role-name lambda-yoto-api-role \
  --assume-role-policy-document file://lambda-trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name lambda-yoto-api-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name lambda-yoto-api-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

aws iam attach-role-policy \
  --role-name lambda-yoto-api-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

# Create Lambda function
aws lambda create-function \
  --function-name ${LAMBDA_FUNCTION_NAME} \
  --runtime python3.9 \
  --role arn:aws:iam::${AWS_ACCOUNT_ID}:role/lambda-yoto-api-role \
  --handler handler.handler \
  --zip-file fileb://lambda-deployment.zip \
  --timeout 30 \
  --memory-size 1024 \
  --environment Variables="{
    YOTO_CLIENT_ID=${YOTO_CLIENT_ID},
    S3_AUDIO_BUCKET=${S3_BUCKET_AUDIO},
    DYNAMODB_TABLE=${DYNAMODB_TABLE},
    AWS_REGION=${AWS_REGION}
  }"
```

#### 5.4 Create API Gateway

```bash
# Create HTTP API
aws apigatewayv2 create-api \
  --name yoto-smart-stream-api \
  --protocol-type HTTP \
  --target arn:aws:lambda:${AWS_REGION}:${AWS_ACCOUNT_ID}:function:${LAMBDA_FUNCTION_NAME}

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name ${LAMBDA_FUNCTION_NAME} \
  --statement-id apigateway-invoke \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com

# Get API endpoint
aws apigatewayv2 get-apis --query "Items[?Name=='yoto-smart-stream-api'].ApiEndpoint" --output text
```

#### 5.5 Test Lambda API

```bash
# Test health endpoint
API_URL=$(aws apigatewayv2 get-apis --query "Items[?Name=='yoto-smart-stream-api'].ApiEndpoint" --output text)

curl ${API_URL}/api/health

# Expected output:
# {
#   "status": "healthy",
#   "version": "0.2.1",
#   ...
# }

# Test cold start timing
time curl ${API_URL}/api/health
# First request: ~2-5 seconds (cold start)

# Wait 1 second, test again
sleep 1
time curl ${API_URL}/api/health
# Second request: ~0.1 seconds (warm)
```

**Checkpoint:**
- [ ] Lambda function deployed
- [ ] API Gateway created
- [ ] Cold start measured (~2-5s)
- [ ] Warm requests measured (<100ms)
- [ ] All endpoints working

---

### Phase 6: CloudFront CDN (4 hours)

#### 6.1 Upload Static UI to S3

```bash
# Upload UI files
aws s3 sync ./yoto_smart_stream/static/ s3://${S3_BUCKET_UI}/ \
  --cache-control "public, max-age=3600"

# Enable static website hosting
aws s3 website s3://${S3_BUCKET_UI}/ \
  --index-document index.html
```

#### 6.2 Create CloudFront Distribution

```bash
# Create distribution (use AWS Console for easier setup)
# Or use CLI:
aws cloudfront create-distribution \
  --origin-domain-name ${S3_BUCKET_UI}.s3.amazonaws.com \
  --default-root-object index.html

# Get distribution domain name
aws cloudfront list-distributions \
  --query "DistributionList.Items[0].DomainName" \
  --output text
```

**Checkpoint:**
- [ ] Static UI uploaded to S3
- [ ] CloudFront distribution created
- [ ] UI accessible via CloudFront URL

---

### Phase 7: Testing & Cutover (12 hours)

#### 7.1 End-to-End Testing

```bash
# Test cold start
curl -w "\nTime: %{time_total}s\n" ${API_URL}/api/health
# Expected: 2-5 seconds

# Test warm start
curl -w "\nTime: %{time_total}s\n" ${API_URL}/api/health
# Expected: <0.1 seconds

# Test player control
curl ${API_URL}/api/players

# Test card creation
curl -X POST ${API_URL}/api/cards \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Card", "text": "Hello world"}'

# Test audio streaming from S3
# (Create card, play on Yoto device, verify audio plays)
```

#### 7.2 Load Testing

```bash
# Install hey (HTTP load generator)
go install github.com/rakyll/hey@latest

# Test cold start frequency
hey -n 100 -c 1 -q 1 ${API_URL}/api/health
# Should show: Mix of 2-5s (cold) and <0.1s (warm) responses

# Test concurrent load
hey -n 1000 -c 10 ${API_URL}/api/health
# Lambda should auto-scale, all requests succeed
```

#### 7.3 Monitor CloudWatch

```bash
# View Lambda logs
aws logs tail /aws/lambda/${LAMBDA_FUNCTION_NAME} --follow

# View MQTT logs
aws logs tail /ecs/yoto-mqtt --follow

# Check cold start percentage
aws logs filter-log-events \
  --log-group-name /aws/lambda/${LAMBDA_FUNCTION_NAME} \
  --filter-pattern "INIT_START" \
  --start-time $(date -d '1 day ago' +%s)000
```

#### 7.4 Cutover Plan

```
1. Keep Railway running as backup (1-2 weeks)
2. Update DNS to point to API Gateway URL
3. Monitor for 24 hours
4. If issues, revert DNS to Railway
5. After 1-2 weeks stable, decommission Railway
```

**Final Checkpoint:**
- [ ] All tests passing
- [ ] Cold starts measured and acceptable
- [ ] MQTT events flowing correctly
- [ ] Audio streaming working
- [ ] Monitoring in place
- [ ] Costs tracking as expected (~\$6/month)

---

## Monitoring & Operations

### CloudWatch Dashboards

Create custom dashboard to monitor:
- Lambda invocations
- Lambda cold starts (INIT_START count)
- Lambda errors
- DynamoDB read/write capacity
- S3 GET requests
- ECS Fargate task status

### Cost Monitoring

```bash
# Check current month costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Expected output:
# Lambda: \$0.00 (free tier)
# API Gateway: \$0.50
# DynamoDB: \$1.00
# S3: \$0.50
# CloudFront: \$0.50
# ECS: \$3.00
# Total: ~\$6.00/month
```

### Troubleshooting

#### High Cold Start Rate

```bash
# Check cold start percentage
aws logs filter-log-events \
  --log-group-name /aws/lambda/${LAMBDA_FUNCTION_NAME} \
  --filter-pattern "INIT_START" \
  --start-time $(date -d '1 day ago' +%s)000 | \
  jq '.events | length'

# If >10% cold starts, consider:
# 1. Implementing keep-warm pings during expected usage hours
# 2. Enabling UI polling to keep Lambda warm
```

#### MQTT Disconnections

```bash
# Check Fargate task status
aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${ECS_SERVICE}

# Check logs for reconnection attempts
aws logs tail /ecs/yoto-mqtt --follow | grep "reconnect"

# Fargate Spot interruptions are rare (~1-2/month)
# Task will auto-restart and reconnect
```

#### High Costs

```bash
# Identify cost drivers
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity DAILY \
  --metrics BlendedCost \
  --group-by Type=SERVICE

# Common issues:
# - High Lambda invocations (check for polling loops)
# - High S3 bandwidth (check audio file sizes)
# - DynamoDB throttling (should not happen with on-demand)
```

---

## Rollback Procedures

### Emergency Rollback (Revert to Railway)

```bash
# 1. Update DNS to point back to Railway
# 2. Railway should still be running (kept as backup)

# 3. If Railway was stopped:
railway up

# 4. Verify Railway is working
curl https://your-railway-app.up.railway.app/api/health

# 5. Monitor until AWS issues resolved
```

### Partial Rollback Options

#### Rollback Lambda Only (Keep S3/DynamoDB)
```bash
# Deploy old Lambda code
aws lambda update-function-code \
  --function-name ${LAMBDA_FUNCTION_NAME} \
  --zip-file fileb://lambda-deployment-old.zip
```

#### Rollback S3 (Revert to Local Storage)
```bash
# On Railway:
unset S3_AUDIO_BUCKET
railway restart
# Falls back to local storage
```

#### Rollback DynamoDB (Revert to SQLite)
```bash
# On Railway:
unset DYNAMODB_TABLE
railway restart
# Falls back to SQLite
```

---

## Summary

### Architecture 1 Characteristics

| Aspect | Value |
|--------|-------|
| **Monthly Cost** | \$5-8 |
| **Cold Start Time** | 2-5 seconds |
| **Cold Start Frequency** | 2-5 times/day (once per session) |
| **Warm Response Time** | <100ms |
| **MQTT Availability** | 99.9% (Fargate Spot) |
| **Scalability** | Unlimited (Lambda auto-scales) |
| **Maintenance** | Low (serverless) |

### Key Success Factors

1. **Accept Cold Starts:** 2-5s delay once per session is acceptable for home use
2. **Monitor Costs:** Set billing alerts, review monthly
3. **MQTT Always-On:** Fargate Spot ensures MQTT never disconnects
4. **Free Tier:** Lambda within free tier at low-medium traffic

### Cost Breakdown (Monthly)

```
API Gateway:    \$0.50
Lambda:         \$0.00 (free tier)
DynamoDB:       \$1.00
S3 + CloudFront:\$1.50
Fargate Spot:   \$3.00
CloudWatch:     \$0.50
───────────────────
TOTAL:          \$6.50
```

### When to Upgrade

Consider Architecture 2 (No Cold Starts) if:
- Cold starts become problematic
- Usage exceeds Lambda free tier
- Need instant response times
- Can afford \$33/month

---

**Document Status:** Complete and ready for implementation  
**Last Updated:** 2026-01-15  
**For Questions:** Refer to [AWS_COST_OPTIMIZATION_REPORT.md](AWS_COST_OPTIMIZATION_REPORT.md)

