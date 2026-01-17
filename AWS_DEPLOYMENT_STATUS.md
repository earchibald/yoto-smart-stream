# AWS Deployment Implementation - Status Report

## ✅ Completed Work

### Infrastructure as Code (AWS CDK)

I have successfully implemented a complete AWS deployment infrastructure using the Python CDK, following Architecture 1 (Lambda + Fargate Spot) as specified in the documentation.

#### What's Been Created:

1. **CDK Stack** (`infrastructure/cdk/cdk/cdk_stack.py`)
   - Complete infrastructure definition for all AWS resources
   - Parameterized for multiple environments (dev, staging, prod)
   - Configurable MQTT and CloudFront options
   - Following AWS best practices

2. **AWS Resources Defined:**
   - **Cognito User Pool**: Managed authentication service with password policies and MFA support
   - **DynamoDB Table**: Serverless database with single-table design (PK/SK)
   - **S3 Buckets**: 
     - Audio bucket with CORS for Yoto device streaming
     - UI bucket with static website hosting
   - **Lambda Function**: Python 3.9 with FastAPI (via Mangum)
   - **API Gateway**: HTTP API (lower cost than REST API)
   - **ECS Fargate**: MQTT handler with Spot instances (70% cost savings)
   - **CloudFront** (optional): CDN for UI distribution
   - **IAM Roles**: Least-privilege access for Lambda and ECS

3. **Lambda Handler** (`infrastructure/lambda/handler.py`)
   - Mangum adapter to run FastAPI in Lambda
   - Ready to package with application code
   - Environment variables pre-configured

4. **MQTT Handler** (`infrastructure/mqtt_handler/`)
   - Standalone Python script for persistent MQTT connection
   - Dockerfile for container deployment
   - Token management with DynamoDB
   - Auto-reconnection logic

5. **Deployment Scripts:**
   - `infrastructure/deploy.sh`: One-command deployment
   - `infrastructure/scripts/migrate_to_dynamodb.py`: Data migration tool

6. **Documentation:**
   - `infrastructure/README.md`: Complete deployment guide
   - Step-by-step instructions
   - Testing procedures
   - Troubleshooting guide
   - Cost monitoring

### Testing & Validation

- ✅ CDK synthesis successful
- ✅ CloudFormation template generated
- ✅ All warnings addressed (non-breaking deprecations only)
- ✅ Resource naming conventions correct
- ✅ Environment isolation configured

## 🔄 Next Steps (Requires AWS Credentials)

### Prerequisites

You need to set the following environment variables:

```bash
export AWS_ACCESS_KEY_ID="your_access_key_here"
export AWS_SECRET_ACCESS_KEY="your_secret_key_here"
export AWS_REGION="us-east-1"
export YOTO_CLIENT_ID="your_yoto_client_id"
```

### Step 1: Bootstrap CDK (One-time)

```bash
cd infrastructure/cdk
source .venv/bin/activate
cdk bootstrap
```

This creates the necessary S3 bucket and IAM roles for CDK deployments.

### Step 2: Deploy to Development

```bash
cd infrastructure
./deploy.sh dev
```

This will:
1. Package the Lambda function with dependencies
2. Deploy all AWS resources
3. Output the API Gateway URL
4. Test the health endpoint

### Step 3: Migrate Data

```bash
export DYNAMODB_TABLE="yoto-smart-stream-dev"
python infrastructure/scripts/migrate_to_dynamodb.py
```

### Step 4: Upload Static UI

```bash
UI_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
  --output text)

aws s3 sync yoto_smart_stream/static/ s3://$UI_BUCKET/
```

### Step 5: Test Deployment

```bash
API_URL=$(aws cloudformation describe-stacks \
  --stack-name YotoSmartStream-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
  --output text)

# Test health endpoint
curl $API_URL/api/health

# Test cold start timing
time curl $API_URL/api/health

# Test warm start (within 15 minutes)
sleep 2
time curl $API_URL/api/health
```

### Step 6: Monitor and Validate

```bash
# View Lambda logs
aws logs tail /aws/lambda/yoto-api-dev --follow

# View MQTT logs
aws logs tail /ecs/yoto-mqtt-dev --follow

# Check costs
aws ce get-cost-and-usage \
  --time-period Start=$(date +%Y-%m-01),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --group-by Type=SERVICE
```

### Step 7: Deploy to Production

Once development is validated:

```bash
cd infrastructure
./deploy.sh prod
```

## 📊 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS Account                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  API Gateway (HTTP API)                                   │  │
│  │  • Entry point for all API requests                       │  │
│  │  • Cost: ~$0.50/month                                     │  │
│  └────────────┬─────────────────────────────────────────────┘  │
│               │                                                   │
│               ▼                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Lambda Function (Python 3.9)                             │  │
│  │  • FastAPI with Mangum adapter                            │  │
│  │  • 1GB RAM, 30s timeout                                   │  │
│  │  • Cold start: 2-5s, Warm: <100ms                         │  │
│  │  • Cost: $0 (free tier)                                   │  │
│  └────┬─────────────────────────────────┬──────────────────┘  │
│       │                                  │                      │
│       ▼                                  ▼                      │
│  ┌──────────────┐              ┌──────────────────────┐        │
│  │  DynamoDB    │              │  S3 Buckets           │        │
│  │  • Pay-per-  │              │  • Audio files        │        │
│  │    request   │              │  • Static UI          │        │
│  │  • $1/month  │              │  • $1.50/month        │        │
│  └──────────────┘              └──────────────────────┘        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ECS Fargate Spot (MQTT Handler)                          │  │
│  │  • Always-on persistent MQTT connection                   │  │
│  │  • 0.25 vCPU, 0.5GB RAM                                   │  │
│  │  • Auto-reconnects on interruption                        │  │
│  │  • Token refresh every 12 hours                           │  │
│  │  • Cost: $3/month                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

TOTAL COST: $6-8/month
```

## 💰 Cost Breakdown

| Service | Cost/Month | Notes |
|---------|-----------|-------|
| API Gateway | $0.50 | HTTP API |
| Lambda | $0.00 | Free tier (1M requests/month) |
| DynamoDB | $1.00 | Pay-per-request |
| S3 + CloudFront | $1.50 | Storage and bandwidth |
| ECS Fargate Spot | $3.00 | 0.25 vCPU, 0.5GB RAM, Spot |
| Amazon Polly | $2.00 | Neural TTS (optional usage) |
| CloudWatch Logs | $0.50 | Log storage |
| **Total** | **$8.50/month** | Can be as low as $6 with lower usage |

## 🎯 What's Different from Railway

### Database: SQLite → DynamoDB
- **Before**: SQLite file on disk
- **After**: DynamoDB with single-table design
- **Migration**: Required (script provided)
- **Benefits**: Serverless, auto-scaling, no maintenance

### Storage: Local Filesystem → S3
- **Before**: Audio files on local disk
- **After**: S3 with pre-signed URLs
- **Migration**: Upload files to S3
- **Benefits**: Unlimited storage, automatic backups, CDN-ready

### TTS: gTTS → Amazon Polly
- **Before**: Google Text-to-Speech (free, basic quality)
- **After**: Amazon Polly Neural voices (professional quality)
- **Cost**: $16 per 1M characters (very low for home use)
- **Benefits**: Better voice quality, SSML support, faster

### API: Always-On Uvicorn → Lambda
- **Before**: Uvicorn server running 24/7
- **After**: Lambda with cold starts
- **Cold Start**: 2-5 seconds (once per session)
- **Warm**: <100ms (subsequent requests)
- **Benefits**: Lower cost, auto-scaling, no maintenance

### MQTT: Same but on Fargate
- **Before**: Running alongside API
- **After**: Separate ECS Fargate container
- **Benefits**: Independent scaling, Spot instances (70% savings)

## 🔧 Code Changes Required

### 1. Database Access Layer
The application currently uses SQLAlchemy with SQLite. You'll need to create a DynamoDB adapter:

**Option A**: Create a new `database_dynamodb.py` module
**Option B**: Modify existing database layer to use boto3

Example:
```python
# yoto_smart_stream/database_dynamodb.py
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.getenv('DYNAMODB_TABLE'))

def get_user(username):
    response = table.get_item(
        Key={'PK': f'USER#{username}', 'SK': 'PROFILE'}
    )
    return response.get('Item')

def save_user(username, **kwargs):
    table.put_item(
        Item={'PK': f'USER#{username}', 'SK': 'PROFILE', **kwargs}
    )
```

### 2. File Storage
Update audio file handling to use S3:

```python
# yoto_smart_stream/storage.py
import boto3

s3 = boto3.client('s3')

def save_audio_file(file_content, filename):
    bucket = os.getenv('S3_AUDIO_BUCKET')
    s3.put_object(Bucket=bucket, Key=f'audio/{filename}', Body=file_content)
    return generate_presigned_url(bucket, f'audio/{filename}')

def generate_presigned_url(bucket, key):
    return s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=3600  # 1 hour
    )
```

### 3. Replace gTTS with Polly
```python
# yoto_smart_stream/tts.py
import boto3

polly = boto3.client('polly')

def generate_tts(text, voice_id='Joanna'):
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat='mp3',
        VoiceId=voice_id,
        Engine='neural'
    )
    return response['AudioStream'].read()
```

## 📝 Development Workflow

### Local Development
Continue using Railway or local setup for development:
- SQLite for database
- Local filesystem for storage
- gTTS for TTS

### AWS Deployment
Deploy to AWS for testing and production:
- DynamoDB for database
- S3 for storage
- Amazon Polly for TTS

### Dual Support (Recommended)
Add environment detection:
```python
# yoto_smart_stream/config.py
import os

USE_AWS = os.getenv('USE_AWS', 'false').lower() == 'true'

if USE_AWS:
    from .database_dynamodb import *
    from .storage_s3 import *
    from .tts_polly import *
else:
    from .database_sqlite import *
    from .storage_local import *
    from .tts_gtts import *
```

## 🚀 Quick Deployment Summary

Once AWS credentials are set:

```bash
# 1. Deploy infrastructure
cd infrastructure && ./deploy.sh dev

# 2. Migrate data
export DYNAMODB_TABLE=yoto-smart-stream-dev
python scripts/migrate_to_dynamodb.py

# 3. Upload UI
aws s3 sync ../yoto_smart_stream/static/ s3://yoto-ui-dev-<account>/

# 4. Test
curl <API_URL>/api/health

# 5. Monitor
aws logs tail /aws/lambda/yoto-api-dev --follow
```

## 📚 Documentation

All detailed instructions are in:
- `infrastructure/README.md` - Complete deployment guide
- `docs/AWS_AUTOMATED_DEPLOYMENT_PLAN.md` - Original architecture document
- `docs/AWS_ARCH1_IMPLEMENTATION_GUIDE.md` - Detailed implementation guide

## ✅ What's Ready Now

- ✅ Complete CDK infrastructure code
- ✅ Lambda handler with Mangum
- ✅ MQTT handler for Fargate
- ✅ Deployment automation scripts
- ✅ Data migration script
- ✅ Comprehensive documentation
- ✅ Cost optimization (Spot instances, pay-per-request)
- ✅ Environment isolation (dev/staging/prod)
- ✅ Monitoring setup (CloudWatch logs)

## ⏳ What's Pending (Requires Action)

- ⏳ AWS credentials configuration
- ⏳ CDK bootstrap
- ⏳ First deployment
- ⏳ Code changes for DynamoDB/S3/Polly
- ⏳ Data migration
- ⏳ Testing and validation

## 🔐 Security Notes

- All secrets should be in environment variables
- IAM roles use least-privilege access
- S3 buckets have CORS properly configured
- No hardcoded credentials in code
- Lambda execution role has minimal permissions

## 📞 Support

If you encounter issues during deployment:

1. Check CloudWatch logs: `aws logs tail /aws/lambda/yoto-api-dev --follow`
2. Review CDK documentation: https://docs.aws.amazon.com/cdk/
3. Check AWS costs: `aws ce get-cost-and-usage ...` (see README)
4. Open an issue on GitHub with error details

---

**Status**: Infrastructure complete and ready for deployment ✅  
**Next Step**: Set AWS credentials and run `infrastructure/deploy.sh dev`  
**Estimated Time to Deploy**: 10-15 minutes (after credentials are set)  
**Estimated Monthly Cost**: $7-10/month
