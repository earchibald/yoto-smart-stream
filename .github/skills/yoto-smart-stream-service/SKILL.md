---
name: yoto-smart-stream-service
description: Development and maintenance of the Yoto Smart Stream service. Covers authentication, service access, OAuth configuration, Yoto API integration, MQTT event handling, and general service operations.
---

# Yoto Smart Stream Service Skill

This skill covers development and maintenance of the Yoto Smart Stream service - an audio streaming application that integrates with Yoto Play API to control Yoto players and stream audio content.

## Overview

Yoto Smart Stream is a FastAPI-based web service that provides:

- **Web UI** for managing audio files, playlists, and Yoto devices
- **REST API** endpoints for device control and audio streaming
- **OAuth2 Integration** with Yoto Play API (single-tenant mode)
- **MQTT Event Handling** for real-time device status and control
- **Audio Library Management** with transcription and metadata
- **Display Icons** for Yoto Mini devices (16x16 pixel custom icons)
- **Playlist Support** for dynamic, chapter-based audio experiences

### Yoto Device Capabilities

**Yoto Player (Original)**:
- No display screen
- No microphone (voice control not possible)
- Physical card slot for content

**Yoto Mini**:
- 16x16 pixel display screen (supports custom icons)
- No microphone (voice control not possible)
- Physical card slot for content

### Technology Stack

- **Backend**: Python 3.9+ with FastAPI (async/await)
- **Yoto API Client**: yoto_api library (https://github.com/cdnninja/yoto_api)
- **MQTT**: Real-time device events via AWS IoT Core (through yoto_api)
- **Database**: DynamoDB in AWS deployments; SQLite for local development only
- **Audio Processing**: pydub with FFmpeg, optional Whisper transcription
- **Deployment**: AWS Lambda + API Gateway (CloudFront optional in prod)

## Service Access & Authentication

### Determine Service Hostname

Identify the Yoto Smart Stream service hostname using one of these methods:

1. **Railway MCP** (requires Railway CLI)
   ```bash
   railway generate-domain
   ```

2. **Railway CLI**
   ```bash
   railway domains
   ```

3. **Pattern-based URL** (most reliable)
   ```
   https://yoto-smart-stream-{environment}.up.railway.app
   ```

   Environment options:
   - `production` - main branch deployment
   - `develop` - develop branch deployment  
   - `yoto-smart-stream-pr-{PR_ID}` - PR preview environments
     - PR_ID Pull Request ID # from github MCP

### Default Credentials

Initial admin access:
- **Username:** `admin`
- **Password:** `yoto`

### Yoto OAuth Authorization

OAuth authorization flow is required for Yoto device access:

- **Only required once** - Authorization can be completed during first login
- **Tokens persist** - OAuth tokens and refresh tokens persist across deployments and service restarts (stored in AWS Secrets Manager in Lambda, local file in development)
- **Single-tenant** - Service uses authenticated user's Yoto account for all device operations
- **Non-admin users** - Share the OAuth credentials (single-tenant mode); non-admin users cannot change credentials
- **Automatic token refresh** - Service automatically refreshes access tokens before expiration

**OAuth Flow (Device Code Grant):**
1. Login to Yoto Smart Stream with admin credentials
2. Navigate to Dashboard
3. Click "🔑 Connect Yoto Account" button
4. Complete Yoto OAuth device flow in browser:
   - Visit verification URL displayed
   - Enter the device code shown
   - Authorize the application
5. Authorization complete - tokens stored and used for all subsequent operations

**For Agents:** If you don't have Yoto OAuth credentials, pause and notify the user to perform this one-time manual step. Wait for "continue" from the user before proceeding.

### Yoto API Configuration

- **Client ID**: `Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO` (registered Yoto application)
- **Base URLs**:
  - REST API: `https://api.yotoplay.com`
  - Auth: `https://login.yotoplay.com`
  - Developer Portal: https://yoto.dev/

## Architecture & Implementation

### Core Components

**YotoClient** (`yoto_smart_stream/core/yoto_client.py`):
- Wraps yoto_api.YotoManager with enhanced features
- Automatic token refresh and persistence
- MQTT event callback integration
- Token storage in AWS Secrets Manager (Lambda) with Lambda Extension caching or local file (development)

**MQTT Event Store** (`yoto_smart_stream/api/mqtt_event_store.py`):
- Tracks real-time device events from MQTT
- Correlates events with stream requests
- Supports event-driven analytics and debugging

**FastAPI Application** (`yoto_smart_stream/api/`):
- Async request handling
- Route modules: cards, players, library, admin, auth
- Dependency injection for YotoClient and database

**Persistence (AWS-first)**:
- DynamoDB table `yoto-smart-stream-{env}` with composite keys (`PK`, `SK`)
- Users stored as `PK=USER#{username}`, `SK=PROFILE`; audio metadata as `PK=AUDIO#{filename}`, `SK=METADATA`
- Set `DYNAMODB_TABLE` (CDK injects) to activate; `AWS_REGION`/`AWS_DEFAULT_REGION` picked up automatically
- SQLite remains for local-only dev; Lambda runs fully on DynamoDB

### Audio Streaming Architecture

1. **Audio files** - Stored in `/tmp/audio_files` (Lambda ephemeral) or `./audio_files` (local)
2. **Stream queues** - Dynamic playlist configuration stored in-memory or local `./streams` directory
3. **MYO cards** created with URLs pointing to THIS service, not Yoto's servers
4. **Dynamic content** - Update audio without recreating cards
5. **No upload limits** - Stream any size file
6. **Byte-range support** - Enable seeking during playback

**Storage Strategy (Environment-Aware):**
- **Lambda/AWS**: In-memory stream queues (ephemeral, recreated on cold start). Audio from S3 buckets.
- **Local Development**: Filesystem-persisted queues at `./streams/` and audio at `./audio_files/`
- **Graceful Degradation**: If storage unavailable, queues work in-memory without persistence

**Stream Queue Architecture:**
- Queue configuration (file list, order) stored per-stream as JSON
- Implementation: `StreamManager` auto-detects environment and uses appropriate storage
- On Lambda: Ephemeral storage at `/tmp/streams` (cold-start safe)
- No persistent storage needed - streams are recreated as needed

**Supported Audio Formats:**
- MP3 (recommended: 128-256 kbps)
- AAC (M4A)
- OGG
- FLAC

### MQTT Event Handling

The service connects to Yoto's MQTT broker (AWS IoT Core) for real-time events:

**Topics:**
- `device/{device_id}/events` - Device status updates
- `device/{device_id}/status` - Player state changes
- `device/{device_id}/command/*` - Control commands

**Event Types Tracked:**
- Playback status (playing, paused, stopped)
- Volume changes
- Card insertion/removal
- Button presses (left/right buttons)
- Sleep timer status
- Streaming status

**Implementation Pattern:**
```python
# Connect with callback in YotoClient
client.manager.connect_to_events(callback=self._mqtt_event_callback)

# Callback stores events for analytics
def _mqtt_event_callback(self):
    mqtt_store = get_mqtt_event_store()
    for player_id, player in self.manager.players.items():
        event = MQTTEvent(
            timestamp=datetime.now(),
            device_id=player_id,
            playback_status=player.playback_status,
            volume=player.volume,
            # ... other fields
        )
        mqtt_store.add_event(event)
```

### Display Icons (Yoto Mini)

Yoto Mini devices support 16x16 pixel custom icons:

**Requirements:**
- Format: PNG
- Dimensions: Exactly 16x16 pixels
- Max size: 10KB
- Displayed during playback

**Icon Sources:**
- Public icon repository: `/media/displayIcons/public` (Yoto API)
- Custom uploads: `/media/displayIcons/user/me` (Yoto API)

**Implementation:**
- Icons selected/uploaded when creating MYO cards
- Validated before upload (dimensions, format, size)
- Associated with card metadata

## Service Structure

- **Frontend:** FastAPI with Uvicorn
- **Database:** SQLite stored at `/tmp/yoto_smart_stream.db` (Lambda) or `./yoto_smart_stream.db` (local)
- **Stream Queues:** In-memory with optional filesystem persistence
  - Lambda: `/tmp/streams` (ephemeral)
  - Local: `./streams` (persistent)
- **API:** RESTful endpoints for device control, streaming, user management
- **Real-time:** MQTT for device events and control via yoto_api library

### Project Structure
```
yoto_smart_stream/
├── core/
│   ├── yoto_client.py           # Enhanced YotoManager wrapper
│   ├── audio_db.py              # Audio file database operations
│   ├── transcription.py         # Whisper transcription (optional)
│   └── polly_tts.py             # AWS Polly text-to-speech
├── api/
│   ├── routes/
│   │   ├── cards.py             # Card creation, audio upload/streaming
│   │   ├── players.py           # Device control (pause, play, volume)
│   │   ├── library.py           # Yoto library management
│   │   ├── auth.py              # OAuth device flow
│   │   ├── admin.py             # User management
│   │   └── user_auth.py         # Session authentication
│   ├── mqtt_event_store.py      # MQTT event tracking
│   ├── dependencies.py          # FastAPI dependencies
│   └── app.py                   # FastAPI application
├── database/
│   ├── models.py                # SQLAlchemy models
│   └── __init__.py              # Database session management
├── config.py                    # Settings and configuration
└── utils/
    └── token_storage.py         # AWS Secrets Manager integration
```

## Key Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET /api/health` | Health check | None |
| `GET /` | Dashboard UI | Required |
| `POST /api/user/login` | Admin/user login | None |
| `GET /api/players` | List connected Yoto devices | Required |
| `GET /api/auth/status` | Check Yoto OAuth status | Required |
| `GET /api/admin/users` | List users | Admin only |
| `POST /api/admin/users` | Create user | Admin only |
| `GET /audio-library` | Audio Library page | Required |
| `GET /admin` | Admin panel | Admin only |

## Transcription (optional)

- Disabled by default to keep container builds small and fast.
- Enable by installing `openai-whisper`, `torch`, and `torchaudio`, then setting `TRANSCRIPTION_ENABLED=true` (optional `TRANSCRIPTION_MODEL=base|small|medium|large`).
- When disabled, uploads mark transcripts as `disabled` and background transcription is skipped.

## Common Tasks

### Testing Yoto Integration

When testing Yoto API functionality:

1. **Always deploy to AWS first** - Never test against local mocks
2. **Use Playwright MCP for web UI** - Automate browser interactions
3. **Check MQTT connectivity** - Verify real-time events are flowing
4. **Monitor logs** - Use AWS CloudWatch or local console output

**Example: Test OAuth Flow**
```python
# See reference/test_oauth_flow.py for complete example
# Uses Playwright to automate browser OAuth
```

### Control Yoto Devices

**Via MQTT (preferred for real-time control):**
```python
# Play a card on a specific player
manager.mqtt_client.publish(
    f"/device/{player_id}/command/card/start",
    json.dumps({
        "uri": f"https://yoto.io/{card_id}",
        "chapterKey": "01"
    })
)

# Pause playback
manager.pause_player(player_id)

# Set volume
manager.set_volume(player_id, 50)
```

**Via REST API Endpoints:**
- `POST /api/players/{player_id}/pause` - Pause player
- `POST /api/players/{player_id}/play` - Resume playback
- `POST /api/players/{player_id}/volume` - Set volume
- `POST /api/players/{player_id}/play-card` - Play specific card

### Create Streaming MYO Card

```python
# 1. Upload audio file via API or place in audio_files directory

# 2. Create card pointing to THIS service
response = requests.post(
    f"{service_url}/api/cards/create-streaming",
    json={
        "title": "My Story",
        "audio_filename": "story.mp3",
        "description": "A wonderful tale",
        "icon_id": "icon-uuid-here"  # Optional Yoto Mini icon
    }
)

# 3. Card is created, audio streams from this service
# No upload to Yoto servers required!
```

### Update Audio Without Recreating Cards

One of the key advantages of streaming from this service:

```bash
# Simply replace the audio file
cp new-version.mp3 /data/audio_files/story.mp3

# Card continues to work, streams new content
# No need to recreate the card!
```

### Access Service in PR Environment

```bash
# Determine PR environment URL
SERVICE_URL="https://yoto-smart-stream-yoto-smart-stream-pr-61.up.railway.app"

# Login with default credentials
# Username: admin
# Password: yoto

# Complete Yoto OAuth if needed
# Click "Connect Yoto Account" on dashboard
```

### Verify Service Health

```bash
# Check health endpoint
curl https://yoto-smart-stream-{environment}.up.railway.app/api/health

# Should return:
# {"status":"healthy","version":"X.Y.Z",...}
```

### Access Service Logs

Use Railway MCP or CLI:
```bash
railway logs -e {environment} --follow
```

### Create Non-Admin User

1. Login as admin
2. Navigate to Admin page (`/admin`)
3. Fill "Create New User" form with username, password, optional email
4. Click "👤 Create User"
5. New user can login with those credentials

## Development Guidelines

### Token Management Best Practices

**DO:**
- Use `client.ensure_authenticated()` before API operations
- Let the service handle automatic token refresh
- Store refresh tokens securely (Secrets Manager on AWS, protected file locally)
- Save tokens after successful auth or refresh

**DON'T:**
- Commit tokens to version control
- Ignore token expiration
- Skip token refresh checks
- Hardcode credentials

### MQTT Best Practices

**DO:**
- Use MQTT for device control (lower latency than HTTP)
- Subscribe to all relevant topics on connect
- Implement event callbacks for real-time updates
- Handle reconnection with exponential backoff
- Process events asynchronously

**DON'T:**
- Ignore MQTT connection failures
- Block on synchronous operations
- Assume connection stays alive indefinitely
- Skip error handling in callbacks

### Audio Streaming Best Practices

**DO:**
- Use MP3 format at 128-256 kbps for compatibility
- Implement byte-range support for seeking
- Validate audio files before upload
- Use descriptive filenames
- Enable transcription when needed

**DON'T:**
- Upload extremely large files without testing
- Skip format validation
- Use unsupported audio codecs
- Block during audio processing

### Security Considerations

1. **Never commit credentials** to version control
2. **Use environment variables** for sensitive configuration
3. **Validate user input** on all endpoints
4. **Secure MQTT credentials** - they provide device access
5. **Use HTTPS** for all audio streaming endpoints
6. **Implement rate limiting** on public endpoints

## Deployment

### AWS Deployment (Production/Development)

The service deploys to AWS Lambda + API Gateway with optional CloudFront:

**Deployment Command:**
```bash
cd infrastructure/cdk
source ../../cdk_venv/bin/activate

# Development (aws-develop branch)
cdk deploy \
  -c environment=dev \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false

# Production (aws-main branch)
cdk deploy \
  -c environment=prod \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=true
```

**Configuration Flags:**
- `enable_mqtt=true` - Required for real-time device events and control
- `enable_cloudfront=false` - Disabled in dev to reduce deployment time
- `enable_cloudfront=true` - Enabled in prod for performance

**After Deployment:**
1. Test deployment with `/api/health` endpoint
2. Complete OAuth flow if first deployment
3. Verify MQTT connectivity
4. Test audio streaming

### Local Development

```bash
# Activate virtual environment
source cdk_venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run locally
python -m yoto_smart_stream

# Or with uvicorn directly
uvicorn yoto_smart_stream.api.app:app --reload --port 8080
```

## Troubleshooting

### OAuth/Authentication Issues

**Problem:** "Refresh token not found"
- **Solution:** Complete OAuth flow through web UI (Dashboard → Connect Yoto Account)

**Problem:** Access token expired
- **Solution:** Service automatically refreshes. If failing, check Secrets Manager permissions (AWS) or file permissions (local)

## OAuth Token Storage & Caching (Lambda)

### AWS Secrets Manager with Lambda Extension

In Lambda environments, OAuth tokens are stored in **AWS Secrets Manager** with automatic in-memory caching via the **AWS Parameters and Secrets Lambda Extension** for high performance across invocations.

**Architecture:**
- **Secret Name**: `{ENVIRONMENT}/{YOTO_SECRET_PREFIX}/oauth-tokens` (e.g., `yoto-smart-stream-dev/oauth-tokens`)
- **Storage**: JSON format with `access_token`, `refresh_token`, `expires_at` fields
- **Extension Layer**: AWS-managed Lambda Extension (ARN: `arn:aws:lambda:{region}:976759262368:layer:AWS-Parameters-and-Secrets-Lambda-Extension:12`)
- **HTTP Endpoint**: `localhost:2773/secretsmanager/get?secretId={secret_name}` (configurable port)
- **Cache TTL**: 1000ms (configurable via `SECRETS_EXTENSION_HTTP_POLL` env var)
- **Fallback**: Direct boto3 access if extension unavailable (local dev, non-Lambda)

**Token Loading Sequence:**
1. Check if running in Lambda environment (`AWS_LAMBDA_FUNCTION_NAME` set)
2. If Lambda: Try extension HTTP endpoint first (cached, fast)
3. If extension unavailable: Fall back to boto3 Secrets Manager client
4. If both fail: Return `None` (triggering OAuth flow)

**Implementation** (`yoto_smart_stream/storage/secrets_manager.py`):
- `_get_secret_from_extension()`: Uses `urllib.request` to call extension endpoint with AWS session token header
- `_get_secret_from_boto3()`: Direct boto3 client for fallback/save operations
- `load_yoto_tokens()`: Prefers extension for reads, uses boto3 for writes
- `save_yoto_tokens()`: Uses boto3 `put_secret_value()` or `create_secret()`
- No manual cache management: Extension handles all caching and TTL

**Benefits:**
- ✅ Automatic caching across Lambda invocations (1000ms TTL)
- ✅ Eliminates token state desynchronization (multiple Lambda instances)
- ✅ Reduced Secrets Manager API calls (cost savings)
- ✅ No manual cache invalidation needed
- ✅ Transparent fallback for local development

**Verification:** Check CloudWatch logs for "Loaded secret from Lambda Extension" (INFO) when using extension, "Loaded secret from boto3" (INFO) when using fallback.

### MQTT Connection Issues

**Problem:** MQTT connection drops
- **Solution:** Service attempts reconnection automatically. Check AWS IoT Core credentials in yoto_api library

**Problem:** Events not flowing
- **Solution:** Verify `enable_mqtt=true` in deployment. Check CloudWatch logs for MQTT errors

### Audio Streaming Issues

**Problem:** Audio not playing on device
- **Solution:** Verify audio format (MP3 recommended), check file exists, test URL directly

**Problem:** Seeking not working
- **Solution:** Ensure byte-range support enabled in streaming endpoint

### Deployment Issues

**Problem:** CDK deployment fails
- **Solution:** Check AWS credentials, verify region, ensure all context parameters provided

**Problem:** Lambda cold starts
- **Solution:** Normal behavior. CloudFront caching helps in production

## Resources

- **Yoto Developer Portal**: https://yoto.dev/
- **API Documentation**: https://yoto.dev/api/
- **MQTT Documentation**: https://yoto.dev/players-mqtt/mqtt-docs/
- **Python Library**: https://github.com/cdnninja/yoto_api
- **AWS CDK Documentation**: https://docs.aws.amazon.com/cdk/

---

### Railway legacy notes (archived)
- `RAILWAY_ENVIRONMENT_NAME` (legacy): Railway populated this env var and it took priority over `ENVIRONMENT`. Examples: `production`, `staging`, `pr-123`. When migrating, map Railway environment names to your AWS environment naming convention.
- Persistent storage: Railway used a persistent volume mounted at `/data`; refresh tokens were stored at `/data/.yoto_refresh_token` and audio files at `/data/audio_files`. On AWS, prefer S3 for audio and AWS Secrets Manager for refresh tokens.
- Startup timing: Railway deployments sometimes required a short startup wait for shared variables; the application exposes `railway_startup_wait_seconds` to delay initialization. Ensure environment variables are available before starting services on any platform.
- PR preview pattern (legacy): `https://yoto-smart-stream-pr-{number}.up.railway.app`.

**For AWS deployment management specifics, see** [aws-service-management skill](../aws-service-management/SKILL.md)

**For Playwright OAuth automation, see** [reference/playwright_oauth_automation.md](./reference/playwright_oauth_automation.md)