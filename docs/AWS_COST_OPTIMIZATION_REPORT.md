# AWS Cost-Effective Architecture Report
# Yoto Smart Stream - Microsolution Design

**Generated:** 2026-01-15  
**Current Stack:** Python/FastAPI on Railway.app  
**Purpose:** Minimize AWS costs using serverless and on-demand services

---

## Executive Summary

This report analyzes the most cost-effective AWS architecture for Yoto Smart Stream, a service that:
- Streams audio to Yoto devices (HTTP audio delivery)
- Manages MQTT event processing from Yoto devices
- Provides web UI for audio/card management
- Handles OAuth authentication with Yoto API
- Stores user data and audio files

**Key Recommendation:** Hybrid serverless architecture with Lambda for API endpoints, ECS Fargate Spot for long-running MQTT, and S3 for storage can reduce costs to approximately **$5-15/month** at low-to-medium usage.

---

## Current System Analysis

### Component Inventory

| Component | Current Implementation | Usage Pattern | Cost Driver |
|-----------|----------------------|---------------|-------------|
| **API Server** | FastAPI on Railway | Always-on, HTTP requests | Compute time |
| **MQTT Handler** | Background task in FastAPI | Long-running connection | Always-on compute |
| **Database** | SQLite on persistent volume | Read/write for users, tokens | Storage |
| **Audio Storage** | Local filesystem (Railway volume) | Serve MP3 files, TTS generation | Storage + bandwidth |
| **Static UI** | Served by FastAPI | HTML/CSS/JS files | Compute + bandwidth |
| **OAuth Tokens** | File-based on persistent volume | Periodic refresh | Storage |
| **TTS Generation** | Google TTS (gTTS) | On-demand audio creation | Compute |
| **Background Tasks** | Token refresh every 12 hours | Periodic execution | Compute |

### Traffic & Usage Patterns

**Estimated Traffic (Low-Medium Usage Household):**
- API Requests: 100-500/day (player control, card management)
- Audio Streaming: 5-20 streams/day, 5-30 MB each (children's stories)
- MQTT Events: 50-200/day (button presses, status updates)
- Static Assets: 20-50 page loads/day
- TTS Generation: 5-10/day (new cards)
- Database Queries: 200-1000/day

**Key Characteristics:**
- Bursty traffic (concentrated during morning/evening/bedtime)
- Long periods of inactivity (nighttime, school hours)
- Audio files served multiple times (favorite stories)
- MQTT requires persistent connection
- OAuth tokens must persist across restarts

---

## AWS Service Breakdown by Component

### 1. API Endpoints (FastAPI Routes)

**Current Routes:**
- `/api/auth/*` - Yoto OAuth flow
- `/api/user-auth/*` - User login/logout
- `/api/players/*` - Player control (play, pause, volume)
- `/api/cards/*` - Card management, TTS generation
- `/api/library/*` - Browse Yoto library
- `/api/streams/*` - Dynamic playlist management
- `/api/admin/*` - User management
- `/api/health` - Health checks

**AWS Options:**

#### Option A: Lambda + API Gateway (Recommended for Cost)
**Cost:** ~$1-3/month at low-medium usage

- **Service:** AWS Lambda (Python 3.9+) + API Gateway HTTP
- **Architecture:** One Lambda per route group or monolithic FastAPI on Lambda
- **Pricing:**
  - Lambda: Free tier 1M requests/month, then $0.20 per 1M requests
  - API Gateway HTTP: $1.00 per million requests
  - Typical cost: 10K requests/month = $0.02 (within free tier)

**Pros:**
- Zero cost when idle
- Scales automatically
- No infrastructure management
- FastAPI works with Mangum adapter

**Cons:**
- Cold starts (2-5 seconds first request)
- 15-minute execution limit (fine for API calls)
- Requires Lambda-specific adaptations (e.g., file storage)

**Implementation:**
```python
# Lambda handler with Mangum
from mangum import Mangum
from yoto_smart_stream.api import app

handler = Mangum(app, lifespan="off")
```

#### Option B: ECS Fargate with Application Load Balancer
**Cost:** ~$15-25/month (1 task, 0.5 vCPU, 1GB RAM)

- **Service:** ECS Fargate + ALB
- **Architecture:** Container running FastAPI (like Railway)
- **Pricing:**
  - Fargate: $0.04/hour for 0.5 vCPU + $0.004/GB-hour for 1GB = ~$15/month
  - ALB: $0.0225/hour = ~$16/month
  - Total: ~$31/month always-on

**Pros:**
- No cold starts
- Full FastAPI compatibility
- Easy migration from Railway

**Cons:**
- Always-on cost even when idle
- More expensive than Lambda at low usage

#### Option C: Lambda + API Gateway + Fargate (Hybrid)
**Cost:** ~$8-12/month

- **Most API calls:** Lambda (cost-effective)
- **MQTT + Background tasks:** Small Fargate task (0.25 vCPU, 0.5GB)
- **Best of both worlds**

---

### 2. MQTT Event Handler (Long-Running Process)

**Requirements:**
- Maintain persistent connection to `mqtt.yoto.io`
- Process real-time events (button presses, playback status)
- Update database/trigger actions
- Must run 24/7

**AWS Options:**

#### Option A: ECS Fargate Spot (Recommended)
**Cost:** ~$3-6/month for 0.25 vCPU, 0.5GB RAM

- **Service:** ECS Fargate Spot
- **Architecture:** Separate container just for MQTT handler
- **Pricing:**
  - Fargate Spot: 70% discount vs on-demand
  - 0.25 vCPU + 0.5GB = ~$5/month on-demand, ~$2-3/month with Spot
  - Can tolerate interruptions (auto-reconnect)

**Pros:**
- Persistent connection maintained
- 70% cost savings with Spot pricing
- Auto-reconnect on interruption

**Cons:**
- Spot interruptions (rare, but possible)
- Slightly more complex than always-on

**Implementation:**
```python
# Separate MQTT container
# Dockerfile.mqtt
FROM python:3.9-slim
COPY mqtt_handler.py .
CMD ["python", "mqtt_handler.py"]
```

#### Option B: Lambda + EventBridge (Not Recommended)
**Issue:** Lambda cannot maintain persistent MQTT connection (15-min limit)

**Alternative:** Use AWS IoT Core as MQTT proxy, but adds complexity and cost

#### Option C: EC2 t4g.nano Spot Instance
**Cost:** ~$1-2/month

- **Service:** EC2 t4g.nano (ARM) Spot
- **Pricing:** $0.0017/hour = ~$1.25/month
- **Pros:** Very cheap, full control
- **Cons:** More management, less "serverless"

---

### 3. Database (SQLite → AWS Managed)

**Current Schema:**
- `users` - User authentication, Yoto tokens
- `events` - MQTT event log (optional, for debugging)

**Data Volume:** <10MB expected

**AWS Options:**

#### Option A: DynamoDB On-Demand (Recommended)
**Cost:** ~$0.50-2/month

- **Service:** DynamoDB with on-demand billing
- **Pricing:**
  - $1.25 per million write requests
  - $0.25 per million read requests
  - $0.25/GB storage per month
  - Typical usage: 1K writes, 5K reads/day = $0.50/month

**Pros:**
- Serverless, no provisioning
- Pay per request
- Automatic backups
- Perfect for low-traffic apps

**Cons:**
- NoSQL (schema change required)
- Different query patterns

**Schema Migration:**
```python
# User table
{
  "PK": "USER#admin",
  "SK": "PROFILE",
  "username": "admin",
  "hashed_password": "...",
  "yoto_refresh_token": "...",
  "yoto_token_expires_at": 1234567890
}

# Event log
{
  "PK": "EVENT#2026-01-15",
  "SK": "EVENT#123456789",
  "player_id": "...",
  "event_type": "button_press",
  "event_data": {...}
}
```

#### Option B: RDS Aurora Serverless v2 (PostgreSQL/MySQL)
**Cost:** ~$15-30/month minimum

- **Service:** Aurora Serverless v2
- **Pricing:** $0.10/ACU-hour, minimum 0.5 ACU = ~$36/month
- **NOT RECOMMENDED:** Too expensive for this use case

#### Option C: RDS db.t4g.micro (PostgreSQL)
**Cost:** ~$13-15/month

- **Service:** RDS db.t4g.micro (20GB storage)
- **Pricing:** $0.018/hour = ~$13/month + $2.30/month storage
- **Pros:** SQL compatibility (no code changes)
- **Cons:** Always-on cost, overkill for small data

**Recommendation:** DynamoDB On-Demand for minimal cost, or RDS db.t4g.micro if SQL is essential

---

### 4. Audio File Storage (Object Storage)

**Current:** Local filesystem on Railway persistent volume
**Requirements:**
- Store MP3 files (5-30 MB each)
- Serve via HTTP for Yoto device streaming
- TTS-generated files
- Cover images (PNG, small)

**Expected Storage:** 500MB - 5GB

**AWS Options:**

#### Option A: S3 Standard (Recommended)
**Cost:** ~$0.50-2/month for 2GB + bandwidth

- **Service:** S3 Standard
- **Pricing:**
  - Storage: $0.023/GB/month = $0.05 for 2GB
  - GET requests: $0.0004 per 1,000 = $0.02 for 50K requests
  - Data transfer out: First 100GB/month free, then $0.09/GB
  - Typical cost: 2GB storage + 1GB transfer/month = $1-2

**Pros:**
- Highly available (99.99%)
- Direct streaming from S3 (pre-signed URLs)
- Versioning and backup
- CloudFront CDN integration

**Implementation:**
```python
import boto3

s3_client = boto3.client('s3')

# Generate pre-signed URL for Yoto device
url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'yoto-audio', 'Key': 'story.mp3'},
    ExpiresIn=3600  # 1 hour
)

# Return URL to Yoto API
card_data = {
    "chapters": [{
        "tracks": [{"url": url}]
    }]
}
```

#### Option B: S3 Intelligent-Tiering
**Cost:** ~$0.30-1.50/month for 2GB

- **Service:** S3 with automatic tiering
- **Pricing:** $0.023/GB for frequent access, $0.0125/GB for infrequent
- **Pros:** Auto-optimizes for favorite vs. rarely-played stories
- **Cons:** Slight overhead for tiering monitoring

#### Option C: EFS (Elastic File System)
**Cost:** ~$6-10/month for 2GB

- **NOT RECOMMENDED:** Much more expensive than S3 for this use case
- **Use case:** When you need POSIX filesystem (not needed here)

**Recommendation:** S3 Standard with CloudFront CDN for frequently-accessed files

---

### 5. Static Web UI (HTML/CSS/JS)

**Current:** Served by FastAPI from `/static` directory
**Files:** HTML, CSS, JavaScript (~2-5 MB total)

**AWS Options:**

#### Option A: S3 + CloudFront (Recommended)
**Cost:** ~$0.50-1/month

- **Service:** S3 Static Website + CloudFront CDN
- **Pricing:**
  - S3 hosting: $0.023/GB = $0.01 for 5MB
  - CloudFront: 1TB free tier for 12 months, then $0.085/GB
  - Typical cost: 50 page loads/day, 5MB each = 7.5GB/month = $0.60

**Pros:**
- Global CDN (low latency)
- Scales automatically
- Very cheap

**Cons:**
- Separate domain/setup from API

#### Option B: Serve from Lambda via API Gateway
**Cost:** Included in API costs

- **Pros:** Single endpoint for UI + API
- **Cons:** Slower than CloudFront, consumes Lambda invocations

**Recommendation:** S3 + CloudFront for best performance and cost

---

### 6. OAuth Token Persistence

**Current:** File-based (`.yoto_refresh_token` on Railway volume)
**Requirements:**
- Store OAuth refresh token securely
- Survive container restarts
- Enable token refresh every 12 hours

**AWS Options:**

#### Option A: DynamoDB (Recommended if using DynamoDB for users)
**Cost:** Included in DynamoDB database costs

```python
# Store in User record
{
  "PK": "USER#admin",
  "SK": "PROFILE",
  "yoto_refresh_token": "...",
  "yoto_access_token": "...",
  "yoto_token_expires_at": 1234567890
}
```

#### Option B: AWS Secrets Manager
**Cost:** $0.40/month per secret + $0.05 per 10K API calls

- **Service:** Secrets Manager
- **Pros:** Designed for secrets, automatic rotation, encryption
- **Cons:** Overkill for single token, adds $0.40/month base cost

#### Option C: SSM Parameter Store (Secure String)
**Cost:** Free for Standard parameters

- **Service:** Systems Manager Parameter Store
- **Pricing:** Free for up to 10,000 parameters
- **Pros:** Free, secure, encrypted
- **Cons:** Requires IAM permissions

**Recommendation:** DynamoDB (if using) or SSM Parameter Store (free)

---

### 7. Background Jobs (Token Refresh)

**Current:** AsyncIO task in FastAPI (`periodic_token_refresh`)
**Frequency:** Every 12 hours
**Task:** Refresh Yoto OAuth tokens

**AWS Options:**

#### Option A: Lambda + EventBridge Scheduler (Recommended)
**Cost:** ~$0.01/month

- **Service:** Lambda triggered by EventBridge (CloudWatch Events)
- **Pricing:**
  - EventBridge: Free for first 1M events
  - Lambda: 2 invocations/day × 30 days = 60 invocations (free tier)
  - Cost: $0 within free tier

**Implementation:**
```python
# token_refresh_lambda.py
def handler(event, context):
    yoto_client = YotoClient()
    yoto_client.load_token_from_dynamodb()
    yoto_client.refresh_token()
    yoto_client.save_token_to_dynamodb()
    return {"statusCode": 200}

# EventBridge rule: rate(12 hours)
```

#### Option B: Include in MQTT Fargate task
**Cost:** Included in Fargate MQTT handler

**Implementation:**
```python
# Run alongside MQTT handler
import asyncio

async def token_refresh_loop():
    while True:
        await asyncio.sleep(12 * 3600)
        await refresh_tokens()
```

**Recommendation:** Option B (include in Fargate MQTT) - simpler, no extra cost

---

### 8. TTS (Text-to-Speech) Audio Generation

**Current:** Google TTS (gTTS) library, generates MP3 files on-demand
**Usage:** ~5-10 card creations per day

**AWS Options:**

#### Option A: Continue with gTTS in Lambda
**Cost:** ~$0.10/month (compute time)

- **Keep current implementation**
- **Lambda execution:** ~10 seconds per TTS generation
- **Cost:** 10 invocations/day × 10 seconds = 100 seconds/day = 3,000 seconds/month
- **Lambda GB-seconds:** 3,000 seconds × 1GB = 3,000 GB-seconds (free tier: 400,000)
- **Cost:** $0 within free tier

**Pros:**
- No code changes
- Free within Lambda free tier

**Cons:**
- Limited voices (gTTS quality)

#### Option B: AWS Polly (Neural TTS)
**Cost:** ~$1-2/month

- **Service:** Amazon Polly Neural voices
- **Pricing:** $16 per 1M characters (Neural), $4 per 1M characters (Standard)
- **Typical usage:** 10 TTS/day × 500 characters = 150K characters/month = $2.40 (Neural) or $0.60 (Standard)

**Pros:**
- Higher quality voices
- More languages and accents
- SSML support (emotions, pauses)

**Cons:**
- Costs more than gTTS (still very cheap)

**Recommendation:** Start with gTTS in Lambda (free), upgrade to Polly if voice quality is important

---

### 9. Logging & Monitoring

**AWS Options:**

#### Option A: CloudWatch Logs (Included)
**Cost:** ~$0.50-2/month

- **Service:** CloudWatch Logs (Lambda/Fargate auto-configured)
- **Pricing:**
  - Ingestion: $0.50/GB
  - Storage: $0.03/GB
  - Typical usage: 100MB logs/month = $0.05 ingestion + $0.003 storage

#### Option B: CloudWatch + X-Ray for tracing
**Cost:** +$0.50/month

- **Service:** AWS X-Ray for distributed tracing
- **Pricing:** Free tier: 100K traces/month

**Recommendation:** CloudWatch Logs (included), add X-Ray if debugging distributed issues

---

## Complete Architecture Options

### Architecture 1: Minimal Cost (Hybrid Lambda + Fargate Spot)
**Estimated Monthly Cost: $5-10**

```
┌─────────────────────────────────────────────────────────────┐
│                         Users/Yoto Devices                   │
└────────────┬────────────────────────────────────────────────┘
             │
             │ HTTPS
             ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS API Gateway (HTTP API)                                  │
│  • REST endpoints: /api/*                                    │
│  • Cost: $1/million requests (~$0.50/month)                 │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  AWS Lambda (FastAPI via Mangum)                             │
│  • Python 3.9, 1GB RAM                                       │
│  • Cold start: 2-5 seconds                                   │
│  • Routes: players, cards, library, admin, auth             │
│  • Cost: Free tier (1M requests/month)                      │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─────────┐                 ┌─────────────────────┐
             │         │                 │  S3 Bucket          │
             │         └────────────────▶│  • Audio files      │
             │                           │  • Static UI        │
             │                           │  • TTS generated    │
             ▼                           │  Cost: ~$1/month    │
┌─────────────────────────────┐         └─────────────────────┘
│  DynamoDB (On-Demand)       │
│  • Users + Yoto tokens      │         ┌─────────────────────┐
│  • Event log (optional)     │         │  CloudFront CDN     │
│  Cost: ~$0.50/month         │         │  • Cache static UI  │
└─────────────────────────────┘         │  • Cache audio      │
                                         │  Cost: ~$0.50/month │
┌─────────────────────────────┐         └─────────────────────┘
│  ECS Fargate Spot           │
│  • MQTT Handler (0.25 vCPU) │         ┌─────────────────────┐
│  • Persistent connection    │         │  EventBridge        │
│  • Background token refresh │────────▶│  • Token refresh    │
│  • Auto-reconnect on spot   │         │  • every 12 hours   │
│  Cost: ~$2-3/month          │         │  Cost: Free         │
└─────────────────────────────┘         └─────────────────────┘

TOTAL COST: ~$5-8/month
```

**Pros:**
- Lowest cost option
- Scales to zero for API (Lambda)
- MQTT always-on but cheap (Spot)

**Cons:**
- Cold starts on API Gateway
- Spot interruptions (rare, auto-recovers)
- More complex deployment

---

### Architecture 2: Low-Cost with No Cold Starts (ALB + Fargate)
**Estimated Monthly Cost: $15-25**

```
┌─────────────────────────────────────────────────────────────┐
│                         Users/Yoto Devices                   │
└────────────┬────────────────────────────────────────────────┘
             │
             │ HTTPS
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Application Load Balancer (ALB)                             │
│  • Public endpoint                                           │
│  • SSL termination                                           │
│  • Cost: ~$16/month                                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  ECS Fargate (1 task)                                        │
│  • FastAPI + MQTT combined                                   │
│  • 0.5 vCPU, 1GB RAM                                         │
│  • No cold starts                                            │
│  • Cost: ~$15/month                                          │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─────────┐                 ┌─────────────────────┐
             │         │                 │  S3 + CloudFront    │
             │         └────────────────▶│  • Audio storage    │
             │                           │  • Static UI        │
             ▼                           │  Cost: ~$1.50/month │
┌─────────────────────────────┐         └─────────────────────┘
│  RDS db.t4g.micro           │
│  • PostgreSQL (or Aurora)   │
│  • 20GB storage             │
│  • SQL compatibility        │
│  Cost: ~$15/month           │
└─────────────────────────────┘

TOTAL COST: ~$47/month (with RDS)
TOTAL COST: ~$33/month (with DynamoDB instead of RDS)
```

**Pros:**
- No cold starts (instant API responses)
- SQL database (easy migration)
- Simpler deployment (like Railway)

**Cons:**
- Always-on cost even when idle
- More expensive than Lambda at low usage

---

### Architecture 3: Hybrid Best-of-Both (Recommended for Balance)
**Estimated Monthly Cost: $8-15**

```
┌─────────────────────────────────────────────────────────────┐
│                    Users / Yoto Devices                      │
└────────────┬────────────────────────────────────────────────┘
             │
             │ HTTPS
             ▼
┌─────────────────────────────────────────────────────────────┐
│  API Gateway (HTTP API)                                      │
│  • /api/players, /api/cards, /api/library                   │
│  • Lambda backends (cold starts acceptable)                 │
│  • Cost: ~$0.50/month                                        │
└─────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│  Lambda Functions                                            │
│  • Read-only operations (players, library, health)          │
│  • Create cards, TTS generation                             │
│  • Cost: ~$1/month                                           │
└────────────┬────────────────────────────────────────────────┘
             │
             ├─────────┐                 ┌─────────────────────┐
             │         │                 │  S3 + CloudFront    │
             │         └────────────────▶│  • Audio + UI       │
             │                           │  Cost: ~$1.50/month │
             ▼                           └─────────────────────┘
┌─────────────────────────────┐
│  DynamoDB (On-Demand)       │         ┌─────────────────────┐
│  • Users, tokens, events    │         │  ECS Fargate Spot   │
│  Cost: ~$1/month            │◀────────│  • MQTT Handler     │
└─────────────────────────────┘         │  • 0.25 vCPU, 0.5GB │
                                         │  • Token refresh    │
                                         │  Cost: ~$3/month    │
                                         └─────────────────────┘
                                         
┌─────────────────────────────┐
│  CloudWatch                 │
│  • Logs + Metrics           │
│  Cost: ~$0.50/month         │
└─────────────────────────────┘

TOTAL COST: ~$8-12/month
```

**Pros:**
- Balanced cost vs. performance
- API scales to zero (Lambda)
- MQTT always-on (Fargate Spot)
- Cold starts only on infrequent APIs

**Cons:**
- Slightly more complex than single Fargate
- Cold starts on first API call after idle

---

## Cost Comparison Matrix

| Component | Arch 1 (Minimal) | Arch 2 (No Cold Starts) | Arch 3 (Hybrid) | Current (Railway) |
|-----------|------------------|------------------------|-----------------|-------------------|
| **API Endpoints** | Lambda (~$0.50) | Fargate ($15) | Lambda ($1) | Included |
| **MQTT Handler** | Fargate Spot ($3) | Included above | Fargate Spot ($3) | Included |
| **Database** | DynamoDB ($1) | RDS ($15) | DynamoDB ($1) | SQLite (volume) |
| **Audio Storage** | S3 ($1) | S3 ($1.50) | S3 ($1.50) | Volume ($5-10) |
| **Static UI** | CloudFront ($0.50) | ALB (included) | CloudFront ($0.50) | Included |
| **Load Balancer** | None | ALB ($16) | None | Included |
| **Background Jobs** | Included | Included | Included | Included |
| **Monitoring** | CloudWatch ($0.50) | CloudWatch ($0.50) | CloudWatch ($0.50) | Included |
| **TOTAL/MONTH** | **$5-8** | **$47** (RDS) / **$33** (DynamoDB) | **$8-12** | **$5** (Hobby) / **$20** (Pro) |

**Railway Comparison:**
- Railway Hobby: $5/month (500 hours execution, $10 credit)
- Railway Pro: $20/month (unlimited execution)

**Key Insight:** Architecture 1 (Minimal) matches Railway Hobby pricing but with unlimited scalability. Architecture 3 (Hybrid) provides best balance for $8-12/month.

---

## Implementation Considerations

### Migration Path from Railway to AWS

#### Phase 1: Storage Migration
1. **Move audio files to S3**
   - Use AWS CLI: `aws s3 sync ./audio_files s3://yoto-audio/`
   - Update code to generate S3 pre-signed URLs
   - Test audio streaming from S3

2. **Move database to DynamoDB**
   - Export SQLite to JSON: `sqlite3 db.db .dump`
   - Transform schema to DynamoDB single-table design
   - Bulk load with `boto3.batch_write_item()`

#### Phase 2: Deploy MQTT Handler to Fargate
1. Create Docker image for MQTT-only handler
2. Deploy to ECS Fargate Spot
3. Configure environment variables (client ID, tokens)
4. Verify MQTT connection and event processing

#### Phase 3: Deploy API to Lambda
1. Install Mangum adapter: `pip install mangum`
2. Create Lambda handler: `handler = Mangum(app, lifespan="off")`
3. Package dependencies: `pip install -t ./package -r requirements.txt`
4. Deploy via AWS SAM or Terraform
5. Configure API Gateway to trigger Lambda

#### Phase 4: Setup Static UI on S3 + CloudFront
1. Upload static files to S3: `aws s3 sync ./static s3://yoto-ui/`
2. Enable S3 static website hosting
3. Create CloudFront distribution pointing to S3
4. Update DNS records

#### Phase 5: Background Jobs
1. Create EventBridge rule: `rate(12 hours)`
2. Create Lambda for token refresh
3. Test token refresh flow

### Code Changes Required

#### 1. Storage Abstraction (S3 vs. Local)
```python
# yoto_smart_stream/storage.py
from abc import ABC, abstractmethod
import boto3
from pathlib import Path

class StorageBackend(ABC):
    @abstractmethod
    def save_audio(self, file_id: str, data: bytes) -> str:
        pass
    
    @abstractmethod
    def get_audio_url(self, file_id: str, expires_in: int = 3600) -> str:
        pass

class S3StorageBackend(StorageBackend):
    def __init__(self, bucket_name: str):
        self.s3 = boto3.client('s3')
        self.bucket = bucket_name
    
    def save_audio(self, file_id: str, data: bytes) -> str:
        key = f"audio/{file_id}.mp3"
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
        return key
    
    def get_audio_url(self, file_id: str, expires_in: int = 3600) -> str:
        return self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket, 'Key': f"audio/{file_id}.mp3"},
            ExpiresIn=expires_in
        )

class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: Path):
        self.base_path = base_path
    
    def save_audio(self, file_id: str, data: bytes) -> str:
        path = self.base_path / f"{file_id}.mp3"
        path.write_bytes(data)
        return str(path)
    
    def get_audio_url(self, file_id: str, expires_in: int = 3600) -> str:
        # Return local URL (requires FastAPI to serve)
        return f"http://localhost:8080/audio/{file_id}.mp3"

# Configuration
def get_storage_backend() -> StorageBackend:
    if os.getenv('AWS_S3_BUCKET'):
        return S3StorageBackend(os.getenv('AWS_S3_BUCKET'))
    else:
        return LocalStorageBackend(Path('audio_files'))
```

#### 2. Database Abstraction (DynamoDB vs. SQLite)
```python
# yoto_smart_stream/db_adapter.py
from abc import ABC, abstractmethod

class DatabaseAdapter(ABC):
    @abstractmethod
    def get_user(self, username: str) -> dict:
        pass
    
    @abstractmethod
    def save_user(self, user: dict):
        pass

class DynamoDBAdapter(DatabaseAdapter):
    def __init__(self, table_name: str):
        import boto3
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(table_name)
    
    def get_user(self, username: str) -> dict:
        response = self.table.get_item(
            Key={'PK': f'USER#{username}', 'SK': 'PROFILE'}
        )
        return response.get('Item')
    
    def save_user(self, user: dict):
        self.table.put_item(Item={
            'PK': f"USER#{user['username']}",
            'SK': 'PROFILE',
            **user
        })

class SQLiteAdapter(DatabaseAdapter):
    def __init__(self, db_url: str):
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        self.engine = create_engine(db_url)
        self.Session = sessionmaker(bind=self.engine)
    
    def get_user(self, username: str) -> dict:
        session = self.Session()
        user = session.query(User).filter(User.username == username).first()
        return user.__dict__ if user else None
    
    def save_user(self, user: dict):
        session = self.Session()
        user_obj = User(**user)
        session.add(user_obj)
        session.commit()
```

#### 3. Lambda Handler (Mangum)
```python
# lambda_handler.py
from mangum import Mangum
from yoto_smart_stream.api.app import create_app

app = create_app()
handler = Mangum(app, lifespan="off")

# Note: Disable background tasks in Lambda (use EventBridge instead)
```

#### 4. Fargate MQTT Handler (Separate Process)
```python
# mqtt_standalone.py
import asyncio
import logging
from yoto_smart_stream.core import YotoClient
from yoto_smart_stream.db_adapter import get_db_adapter

async def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Initialize clients
    db = get_db_adapter()
    yoto_client = YotoClient()
    
    # Load tokens from database
    admin_user = db.get_user('admin')
    yoto_client.set_refresh_token(admin_user['yoto_refresh_token'])
    await yoto_client.ensure_authenticated()
    
    # Start MQTT connection
    logger.info("Starting MQTT handler...")
    await yoto_client.start_mqtt()
    
    # Background token refresh
    async def token_refresh_loop():
        while True:
            await asyncio.sleep(12 * 3600)  # 12 hours
            logger.info("Refreshing OAuth tokens...")
            await yoto_client.ensure_authenticated()
            # Save updated token to database
            admin_user['yoto_refresh_token'] = yoto_client.get_refresh_token()
            db.save_user(admin_user)
    
    # Run both tasks
    await asyncio.gather(
        yoto_client.run_mqtt_loop(),
        token_refresh_loop()
    )

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Infrastructure as Code (IaC)

### AWS SAM Template (Recommended)
```yaml
# template.yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Parameters:
  YotoClientId:
    Type: String
    Description: Yoto API Client ID

Resources:
  # S3 Bucket for Audio Storage
  AudioBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: yoto-smart-stream-audio
      CorsConfiguration:
        CorsRules:
          - AllowedOrigins: ['*']
            AllowedMethods: [GET]
            AllowedHeaders: ['*']

  # DynamoDB Table
  DataTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: yoto-smart-stream
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE

  # API Lambda Function
  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: yoto-api
      Runtime: python3.9
      Handler: lambda_handler.handler
      MemorySize: 1024
      Timeout: 30
      Environment:
        Variables:
          YOTO_CLIENT_ID: !Ref YotoClientId
          AWS_S3_BUCKET: !Ref AudioBucket
          DYNAMODB_TABLE: !Ref DataTable
      Policies:
        - S3CrudPolicy:
            BucketName: !Ref AudioBucket
        - DynamoDBCrudPolicy:
            TableName: !Ref DataTable
      Events:
        ApiGateway:
          Type: HttpApi
          Properties:
            Path: /{proxy+}
            Method: ANY

  # ECS Fargate for MQTT Handler
  MQTTCluster:
    Type: AWS::ECS::Cluster
    Properties:
      ClusterName: yoto-mqtt-cluster
      CapacityProviders:
        - FARGATE_SPOT
      DefaultCapacityProviderStrategy:
        - CapacityProvider: FARGATE_SPOT
          Weight: 1

  MQTTTaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Properties:
      Family: yoto-mqtt-handler
      RequiresCompatibilities: [FARGATE]
      NetworkMode: awsvpc
      Cpu: 256  # 0.25 vCPU
      Memory: 512  # 0.5 GB
      ContainerDefinitions:
        - Name: mqtt-handler
          Image: !Sub ${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/yoto-mqtt:latest
          Essential: true
          Environment:
            - Name: YOTO_CLIENT_ID
              Value: !Ref YotoClientId
            - Name: DYNAMODB_TABLE
              Value: !Ref DataTable
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: /ecs/yoto-mqtt
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: ecs

  MQTTService:
    Type: AWS::ECS::Service
    Properties:
      ServiceName: yoto-mqtt-service
      Cluster: !Ref MQTTCluster
      TaskDefinition: !Ref MQTTTaskDefinition
      DesiredCount: 1
      LaunchType: FARGATE
      NetworkConfiguration:
        AwsvpcConfiguration:
          Subnets:
            - !Ref PublicSubnet
          SecurityGroups:
            - !Ref MQTTSecurityGroup
          AssignPublicIp: ENABLED

  # EventBridge Rule for Token Refresh
  TokenRefreshRule:
    Type: AWS::Events::Rule
    Properties:
      Description: Refresh Yoto OAuth tokens every 12 hours
      ScheduleExpression: rate(12 hours)
      State: ENABLED
      Targets:
        - Arn: !GetAtt TokenRefreshFunction.Arn
          Id: TokenRefreshTarget

  TokenRefreshFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: yoto-token-refresh
      Runtime: python3.9
      Handler: token_refresh.handler
      MemorySize: 256
      Timeout: 60
      Environment:
        Variables:
          DYNAMODB_TABLE: !Ref DataTable
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref DataTable

Outputs:
  ApiUrl:
    Description: API Gateway endpoint URL
    Value: !Sub https://${ServerlessHttpApi}.execute-api.${AWS::Region}.amazonaws.com/
  
  AudioBucketName:
    Description: S3 bucket for audio files
    Value: !Ref AudioBucket
```

### Deployment Commands
```bash
# Build and deploy with AWS SAM
sam build
sam deploy --guided --parameter-overrides YotoClientId=YOUR_CLIENT_ID

# Or use Terraform (alternative)
terraform init
terraform plan
terraform apply
```

---

## Additional Cost-Saving Ideas

### 1. Audio File Compression
- Use lower bitrate MP3 (128 kbps vs. 256 kbps) for children's stories
- Saves 50% storage and bandwidth
- **Savings:** $0.50-1/month

### 2. CloudFront Caching
- Cache audio files for 24 hours (frequently-played stories)
- Reduces S3 GET requests by 80%
- **Savings:** $0.20-0.50/month

### 3. S3 Lifecycle Policies
- Move old/unused audio to S3 Glacier after 90 days
- Reduces storage cost by 80% for archived files
- **Savings:** $0.10-0.50/month (depending on usage)

### 4. Lambda Reserved Concurrency
- If Lambda usage exceeds free tier, purchase Savings Plan
- 1-year commitment: 17% discount, 3-year: 25% discount
- **Savings:** 17-25% on Lambda costs (if > $10/month)

### 5. Use AWS Free Tier Aggressively
- **Lambda:** 1M requests + 400K GB-seconds/month free (permanent)
- **API Gateway:** 1M requests/month free (12 months)
- **DynamoDB:** 25GB storage + 200M requests/month free (permanent)
- **CloudFront:** 1TB transfer + 10M requests/month free (12 months)
- **S3:** 5GB storage + 20K GET requests/month free (12 months)

**Total Free Tier Value:** ~$20-30/month for 12 months, then ~$10-15/month permanently

### 6. Spot Instance Savings for MQTT
- ECS Fargate Spot: 70% discount vs. on-demand
- **Savings:** $5-7/month on MQTT handler

### 7. Multi-Region Considerations (Optional)
- For global users, consider:
  - CloudFront for audio (automatic global CDN)
  - S3 Cross-Region Replication (only if needed)
- **Trade-off:** Adds complexity, benefits only multi-region users

---

## Performance Considerations

### Cold Starts (Lambda)

**Impact:**
- First request after idle: 2-5 seconds
- Subsequent requests: <100ms

**Mitigation:**
1. **Provisioned Concurrency** (adds cost: $10-20/month for 1 instance)
2. **Warming Lambda** (EventBridge ping every 5 minutes - hacky)
3. **Accept cold starts** (acceptable for non-critical APIs)

**Recommendation:** Accept cold starts for low-traffic home use

### MQTT Latency

**Requirement:** Real-time event processing (<1 second)

**Solution:** ECS Fargate maintains persistent MQTT connection
- No cold starts
- Events processed immediately
- Auto-reconnects on network issues

### Audio Streaming

**Requirement:** Low latency, no buffering issues

**Solution:**
- S3 with CloudFront CDN
- Pre-signed URLs with 1-hour expiry
- Range request support (seeking)

**Performance:**
- First byte latency: 50-200ms (CloudFront edge)
- Throughput: 10-100 Mbps (sufficient for MP3)

---

## Security Considerations

### 1. OAuth Token Storage

**Current:** File-based on persistent volume  
**AWS Options:**
- **DynamoDB:** Encrypted at rest (KMS)
- **Secrets Manager:** Designed for secrets ($0.40/month)
- **SSM Parameter Store:** Free, encrypted (KMS)

**Recommendation:** DynamoDB with encryption at rest (KMS)

### 2. API Authentication

**Current:** Session cookies with JWT

**AWS Integration:**
- Lambda Authorizer for API Gateway
- Validate JWT in Lambda before API execution
- Store sessions in DynamoDB

### 3. S3 Access Control

**Audio Files:**
- Private bucket (no public access)
- Pre-signed URLs with short expiry (1 hour)
- CloudFront signed URLs for UI assets

**Implementation:**
```python
# Generate pre-signed URL
url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': 'yoto-audio', 'Key': 'story.mp3'},
    ExpiresIn=3600  # 1 hour
)
```

### 4. IAM Roles and Policies

**Principle of Least Privilege:**
- Lambda execution role: S3 read/write, DynamoDB CRUD
- ECS task role: DynamoDB CRUD, Secrets Manager read
- No hard-coded credentials in code

---

## Monitoring and Observability

### CloudWatch Metrics

**Key Metrics:**
- Lambda invocations, errors, duration
- API Gateway 4xx/5xx errors
- ECS CPU/memory utilization
- DynamoDB read/write capacity
- S3 GET requests, data transfer

**Alarms:**
- Lambda error rate > 5%
- API Gateway 5xx errors > 1%
- ECS task stopped (MQTT disconnected)
- DynamoDB throttling

### CloudWatch Logs

**Log Groups:**
- `/aws/lambda/yoto-api` - API logs
- `/ecs/yoto-mqtt` - MQTT handler logs
- `/aws/lambda/yoto-token-refresh` - Token refresh logs

**Log Retention:** 7-30 days (cost: $0.03/GB)

### AWS X-Ray (Optional)

**Use Case:** Distributed tracing across Lambda, API Gateway, S3, DynamoDB

**Cost:** Free tier: 100K traces/month

---

## Disaster Recovery and Backup

### Database Backup

**DynamoDB:**
- Point-in-time recovery (PITR): $0.20/GB/month
- On-demand backups: $0.10/GB
- **Recommendation:** Enable PITR for user data

### Audio File Backup

**S3:**
- S3 Versioning: Keep old versions of audio files
- Cross-Region Replication (optional): Copy to second region
- **Cost:** Minimal for small dataset (<5GB)

### OAuth Token Recovery

**Critical:** Yoto refresh token must survive failures

**Strategy:**
- Store in DynamoDB (auto-replicated across AZs)
- Backup to SSM Parameter Store (redundancy)
- Export to encrypted S3 bucket (disaster recovery)

---

## Comparison: Railway vs. AWS

| Aspect | Railway (Current) | AWS Arch 1 (Minimal) | AWS Arch 3 (Hybrid) |
|--------|-------------------|---------------------|-------------------|
| **Monthly Cost** | $5 (Hobby) - $20 (Pro) | $5-8 | $8-12 |
| **Deployment** | Git push (simple) | SAM/Terraform (complex) | SAM/Terraform (complex) |
| **Scaling** | Limited (Hobby: 500 hours) | Unlimited | Unlimited |
| **Cold Starts** | No | Yes (API Gateway) | Yes (API Gateway) |
| **MQTT** | Always-on | Fargate Spot (interruptions) | Fargate Spot (interruptions) |
| **Database** | SQLite (volume) | DynamoDB (NoSQL) | DynamoDB (NoSQL) |
| **Storage** | Persistent volume | S3 (object storage) | S3 (object storage) |
| **Monitoring** | Railway dashboard | CloudWatch | CloudWatch |
| **Free Tier** | 500 hours/month credit | 1M Lambda + 25GB DynamoDB | 1M Lambda + 25GB DynamoDB |

**Recommendation:**
- **Stay on Railway** if:
  - Simplicity is priority
  - Hobby plan (500 hours) is sufficient
  - Don't want to manage AWS complexity

- **Move to AWS** if:
  - Need unlimited scaling
  - Want to optimize costs at higher usage
  - Comfortable with AWS services
  - Need multi-region or advanced features

---

## Conclusion and Recommendations

### Best Architecture for Minimal Cost

**Architecture 1 (Minimal - Lambda + Fargate Spot):** $5-8/month
- Lambda for API endpoints (scales to zero)
- ECS Fargate Spot for MQTT (70% discount)
- DynamoDB on-demand (pay per request)
- S3 + CloudFront for storage and CDN

**When to Use:**
- Low-to-medium traffic (100-1000 requests/day)
- Cost is top priority
- Acceptable to have cold starts on API
- Home/personal use

### Best Architecture for Performance

**Architecture 3 (Hybrid - Lambda + Fargate):** $8-12/month
- Lambda for most APIs (cold starts on infrequent calls)
- ECS Fargate Spot for MQTT (always-on)
- DynamoDB on-demand
- S3 + CloudFront

**When to Use:**
- Balance between cost and performance
- Most APIs can tolerate cold starts
- MQTT must be always-on
- Small-to-medium user base

### Migration Complexity

**Effort:** 40-60 hours (spread over 2-4 weeks)

**Phases:**
1. Storage migration (S3) - 8 hours
2. Database migration (DynamoDB) - 16 hours
3. API Lambda deployment - 12 hours
4. MQTT Fargate deployment - 8 hours
5. UI on S3/CloudFront - 4 hours
6. Testing and debugging - 12 hours

**Skills Required:**
- AWS basics (IAM, S3, Lambda)
- Docker (for Fargate)
- Infrastructure as Code (SAM or Terraform)

### Final Recommendation

**For Home/Personal Use:**
- **Stay on Railway Hobby ($5/month)** if current usage fits within 500 hours
- **Migrate to AWS Arch 1 ($5-8/month)** if need unlimited usage

**For Small Business/Multiple Users:**
- **AWS Arch 3 (Hybrid - $8-12/month)** for best cost/performance balance

**For Growth/Scale:**
- **AWS Arch 2 (No Cold Starts - $33/month with DynamoDB)** when user base grows

---

## Next Steps for Implementation

If proceeding with AWS migration:

1. **Week 1:** Setup AWS account, IAM roles, S3 bucket
2. **Week 2:** Migrate audio files to S3, test streaming
3. **Week 3:** Deploy MQTT handler to Fargate, test events
4. **Week 4:** Deploy API to Lambda, test all endpoints
5. **Week 5:** Setup static UI on S3/CloudFront
6. **Week 6:** Cutover DNS, decommission Railway

**Rollback Plan:** Keep Railway running for 1-2 weeks during migration for easy rollback.

---

## Appendix: AWS Service Cheat Sheet

### S3 (Simple Storage Service)
- **Purpose:** Object storage for audio files, static UI
- **Pricing:** $0.023/GB/month + $0.0004 per 1,000 GET requests
- **Use Case:** Store MP3 files, serve via pre-signed URLs

### Lambda
- **Purpose:** Serverless compute for API endpoints
- **Pricing:** $0.20 per 1M requests + $0.00001667 per GB-second
- **Free Tier:** 1M requests + 400K GB-seconds/month (permanent)
- **Use Case:** FastAPI endpoints (players, cards, library)

### API Gateway (HTTP API)
- **Purpose:** HTTP endpoint for Lambda functions
- **Pricing:** $1.00 per million requests
- **Use Case:** Route /api/* to Lambda functions

### DynamoDB
- **Purpose:** NoSQL database for users, tokens, events
- **Pricing (On-Demand):** $1.25 per million writes, $0.25 per million reads
- **Free Tier:** 25GB storage + 200M requests/month (permanent)
- **Use Case:** Store user data, Yoto OAuth tokens

### ECS Fargate
- **Purpose:** Containerized workloads without managing servers
- **Pricing:** $0.04048/hour per vCPU + $0.004445/hour per GB RAM
- **Fargate Spot:** 70% discount (interruptions possible)
- **Use Case:** Run MQTT handler with persistent connection

### CloudFront
- **Purpose:** CDN for caching static UI and audio files
- **Pricing:** $0.085/GB for first 10TB (US/Europe)
- **Free Tier:** 1TB transfer + 10M requests/month (12 months)
- **Use Case:** Serve static UI, cache popular audio files

### EventBridge (CloudWatch Events)
- **Purpose:** Scheduled tasks (cron jobs)
- **Pricing:** Free for first 1M events/month
- **Use Case:** Token refresh every 12 hours

### CloudWatch
- **Purpose:** Logs, metrics, alarms
- **Pricing:** $0.50/GB ingested, $0.03/GB stored
- **Use Case:** Application logs, Lambda/ECS metrics

---

**Document Version:** 1.0  
**Last Updated:** 2026-01-15  
**Author:** GitHub Copilot Workspace  
**Audience:** Developers, Solution Architects, AI Agents
