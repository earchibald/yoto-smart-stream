# Service Operations Reference

Complete guide to accessing, configuring, and troubleshooting the Yoto Smart Stream service.

## Table of Contents

- [Service Access](#service-access)
- [Authentication](#authentication)
- [Yoto OAuth Authorization](#yoto-oauth-authorization)
- [Health Checks](#health-checks)
- [Common Operations](#common-operations)
- [Troubleshooting](#troubleshooting)
- [API Quick Reference](#api-quick-reference)
- [Environment Variables](#environment-variables)

---

## Service Access

### Determine Service Hostname

Identify the Yoto Smart Stream service hostname using one of these methods:

#### 1. Railway CLI (Most Reliable)

```bash
# List domains for current environment
railway domains

# Output example:
# yoto-smart-stream-production.up.railway.app
```

#### 2. Railway MCP Server (if available)

```bash
# Generate domain URL
railway generate-domain

# Or query service details
railway service info
```

#### 3. Pattern-Based URL (Consistent)

```
https://yoto-smart-stream-{environment}.up.railway.app
```

**Environment Options:**
- `production` - Main branch deployment (stable)
- `develop` - Develop branch deployment (latest features)
- `yoto-smart-stream-pr-{PR_ID}` - PR preview environments
  - `PR_ID` is the Pull Request number from GitHub

**Examples:**
```
https://yoto-smart-stream-production.up.railway.app
https://yoto-smart-stream-develop.up.railway.app
https://yoto-smart-stream-yoto-smart-stream-pr-61.up.railway.app
```

#### 4. Railway Dashboard

1. Go to https://railway.app
2. Navigate to your project
3. Select the environment
4. Click on the service
5. View "Public Networking" section

### Testing Access

```bash
# Test basic connectivity
curl https://SERVICE_URL/api/health

# Expected response:
# {"status":"healthy","timestamp":"2026-01-17T12:34:56Z"}
```

---

## Authentication

### Default Credentials

**Initial admin access:**
- **Username:** `admin`
- **Password:** `yoto`

**Security Note:** In production, change the default password immediately after first login.

### User Login Flow

#### 1. Web UI Login

1. Navigate to `https://SERVICE_URL/`
2. You'll be redirected to login page if not authenticated
3. Enter credentials (admin/yoto by default)
4. Click "Login"
5. Redirected to Dashboard

#### 2. API Login (Get JWT Token)

```bash
# Login via API
curl -X POST https://SERVICE_URL/api/user/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "yoto"
  }'

# Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}

# Use token in subsequent requests
TOKEN="eyJhbGciOiJIUzI1NiIs..."
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/players
```

### Session Management

**Web UI:**
- Sessions persist via HTTP-only cookies
- Automatic logout on token expiration (24 hours)
- "Remember Me" keeps session for 7 days

**API:**
- JWT tokens valid for 24 hours
- Include in `Authorization: Bearer {token}` header
- No automatic refresh - client must re-authenticate

### User Roles

**Admin:**
- Full access to all endpoints
- User management
- System configuration
- OAuth configuration

**User:**
- Dashboard access
- Audio library
- Player controls
- Cannot create users or modify OAuth

---

## User Interface Features

### Dark Mode

The web interface includes a dark mode toggle for improved viewing comfort in different lighting conditions.

**Features:**
- 🌓 **Toggle Widget**: Floating button in bottom-right corner of all pages
- 🎨 **Auto Detection**: Respects system theme preference (`prefers-color-scheme`)
- 💾 **Persistence**: User choice saved in cookies across sessions
- ⚡ **Smooth Transitions**: 0.3s transition effects between themes
- 📱 **Universal**: Available on all pages (dashboard, library, streams, admin, login)

**How to Use:**

1. **Toggle Dark Mode:**
   - Click the 🌓 button in bottom-right corner
   - Theme switches immediately with smooth transition
   - Preference saved automatically

2. **Automatic Theme:**
   - On first visit, matches your system theme
   - macOS: Follows "Dark Mode" in System Preferences
   - Windows: Follows "Choose your color" in Settings
   - Linux: Follows desktop environment theme

3. **Theme Persistence:**
   - Choice saved in browser cookies
   - Persists across page navigation
   - Survives browser restarts
   - Independent per browser/device

**Implementation:**
- Uses [DarkMode.js](https://darkmodejs.learn.uno/) v1.5.7
- CSS filters for automatic color inversion
- Configures with cyan theme colors (#0891b2, #06b6d4)
- Zero-configuration for users

**Troubleshooting:**

If dark mode toggle doesn't appear:
```bash
# Check if DarkMode.js loaded
# Browser console:
console.log(typeof Darkmode !== 'undefined' ? 'Loaded' : 'Not loaded');

# Clear cookies to reset preference
document.cookie.split(";").forEach(c => {
  document.cookie = c.replace(/^ +/, "").replace(/=.*/, 
    "=;expires=" + new Date().toUTCString() + ";path=/");
});
```

If theme doesn't persist:
- Check browser allows cookies
- Verify cookies not blocked for the domain
- Try incognito/private mode to test

---

## Yoto OAuth Authorization

OAuth authorization connects the Yoto Smart Stream service to your Yoto account, enabling device access and control.

### Overview

- **One-Time Setup**: OAuth only needs to be completed once
- **Token Persistence**: Tokens persist across deployments and restarts
- **Automatic Refresh**: Background task refreshes tokens every 12 hours
- **Single-Tenant**: Service uses one Yoto account for all operations

### Prerequisites

1. **Yoto Client ID**: Must be set in environment variables
   ```bash
   railway variables | grep YOTO_CLIENT_ID
   ```

2. **Admin Access**: Only admin users can initiate OAuth flow

### OAuth Flow Steps

#### 1. Check Current Status

```bash
# Via API
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/auth/status

# Response when not authorized:
{
  "authenticated": false,
  "message": "Not authenticated with Yoto"
}

# Response when authorized:
{
  "authenticated": true,
  "expires_at": "2026-01-18T12:34:56Z",
  "user": {
    "email": "user@example.com",
    "name": "John Doe"
  }
}
```

#### 2. Initiate OAuth (Web UI)

1. Login as admin
2. Navigate to Dashboard (`/`)
3. If not authorized, you'll see: **"🔑 Connect Yoto Account"** button
4. Click the button
5. Follow OAuth device flow:
   - Copy the device code shown
   - Click link to Yoto authorization page
   - Paste code and authorize
   - Return to Dashboard

#### 3. Initiate OAuth (API)

```bash
# Start device flow
curl -X POST https://SERVICE_URL/api/auth/device-code \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "device_code": "abc123...",
  "user_code": "ABCD-EFGH",
  "verification_uri": "https://login.yotoplay.com/device",
  "expires_in": 600
}

# User must visit verification_uri and enter user_code

# Poll for completion (every 5 seconds)
curl -X POST https://SERVICE_URL/api/auth/token \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"device_code": "abc123..."}'

# Response when pending:
{
  "status": "pending"
}

# Response when complete:
{
  "status": "success",
  "authenticated": true
}
```

### Token Lifecycle

**Access Tokens:**
- Valid for 24 hours
- Automatically refreshed by background task
- Used for all Yoto API calls

**Refresh Tokens:**
- Valid until manually revoked
- Stored securely in database
- Used to obtain new access tokens
- Persist across service restarts

**Background Refresh:**
- Runs every 12 hours by default
- Configurable via `TOKEN_REFRESH_INTERVAL_HOURS` (1-23)
- Ensures tokens never expire during idle periods
- No manual intervention required

### Agent Limitations

**Important for AI Agents:**

Agents typically cannot complete the OAuth flow because:
1. They don't have Yoto account credentials
2. They cannot interact with Yoto's login page
3. The device flow requires human verification

**Recommended Agent Workflow:**

1. Agent detects OAuth not configured
2. Agent notifies user: "Yoto OAuth authorization required. Please login to the Dashboard and click 'Connect Yoto Account' to complete one-time setup."
3. Agent pauses and waits for user confirmation
4. User completes OAuth manually
5. User types "continue" to resume agent workflow
6. Agent verifies OAuth status and proceeds

**Checking OAuth Status (Agent):**

```bash
# Check if OAuth is complete
STATUS=$(curl -s -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/auth/status | jq -r '.authenticated')

if [ "$STATUS" = "true" ]; then
  echo "OAuth configured - proceeding"
else
  echo "OAuth not configured - notifying user"
  # Pause and wait for user
fi
```

---

## Health Checks

### Basic Health Check

```bash
# No authentication required
curl https://SERVICE_URL/api/health

# Response:
{
  "status": "healthy",
  "timestamp": "2026-01-17T12:34:56Z"
}
```

### Authentication Health

```bash
# Check if logged in
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/auth/status

# Response includes OAuth status
{
  "authenticated": true,
  "expires_at": "2026-01-18T12:34:56Z"
}
```

### Player Connectivity

```bash
# Check if Yoto devices are accessible
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/players

# Response:
[
  {
    "id": "player-123",
    "name": "Living Room Player",
    "online": true,
    "config": {
      "volume": 50
    }
  }
]

# Empty array means:
# - OAuth not configured, OR
# - No devices in Yoto account, OR
# - Devices offline
```

### Database Health

```bash
# Check if database is accessible
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/admin/users

# Response includes user list (admin only)
[
  {
    "id": 1,
    "username": "admin",
    "role": "admin",
    "created_at": "2026-01-01T00:00:00Z"
  }
]
```

---

## Common Operations

### Create Additional Users

```bash
# Get admin token
TOKEN=$(curl -s -X POST https://SERVICE_URL/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yoto"}' \
  | jq -r '.access_token')

# Create new user
curl -X POST https://SERVICE_URL/api/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user1",
    "password": "secret123",
    "role": "user"
  }'

# Response:
{
  "id": 2,
  "username": "user1",
  "role": "user",
  "created_at": "2026-01-17T12:34:56Z"
}
```

### List Yoto Devices

```bash
# Get list of connected players
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/players | jq

# Response:
[
  {
    "id": "player-abc123",
    "name": "Bedroom Player",
    "online": true,
    "config": {
      "volume": 75,
      "nightlight": {
        "active": true,
        "brightness": 50
      }
    }
  }
]
```

### Audio Library Management

```bash
# List audio files
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/audio/list | jq

# Response:
[
  {
    "filename": "story1.mp3",
    "size": 5242880,
    "created": "2026-01-15T10:00:00Z"
  }
]

# Upload audio file
curl -X POST https://SERVICE_URL/api/audio/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@story.mp3"

# Response:
{
  "filename": "story.mp3",
  "size": 5242880,
  "message": "Upload successful"
}

# Delete audio file
curl -X DELETE https://SERVICE_URL/api/audio/delete/story.mp3 \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "message": "File deleted successfully"
}
```

### Remove MYO Cards

```bash
# List all cards
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/cards | jq

# Delete specific card
curl -X DELETE https://SERVICE_URL/api/cards/{card_id} \
  -H "Authorization: Bearer $TOKEN"

# Response:
{
  "message": "Card deleted successfully"
}
```

---

## Troubleshooting

### Cannot Access Service

**Symptom:** Service URL not responding, connection timeout, or 502/503 errors

**Diagnosis:**

```bash
# 1. Check if service is running
railway status

# 2. Check recent logs
railway logs --tail 50

# 3. Verify domain is configured
railway domains

# 4. Check service health in Railway dashboard
# Look for: deployment status, health checks, resource usage
```

**Common Causes:**

1. **Service Not Deployed:**
   ```bash
   # Trigger new deployment
   railway up
   # Or redeploy from Railway dashboard
   ```

2. **Domain Not Configured:**
   ```bash
   # Generate domain
   railway domain create
   ```

3. **Service Crashed:**
   ```bash
   # Check logs for errors
   railway logs --tail 100

   # Look for:
   # - Python exceptions
   # - Port binding errors
   # - Database connection errors
   ```

4. **Resource Limits:**
   - Check Railway dashboard for memory/CPU usage
   - May need to upgrade plan or optimize code

### Login Failures

**Symptom:** Login form shows "Invalid credentials" or returns 401

**Diagnosis:**

```bash
# 1. Test health endpoint (no auth required)
curl https://SERVICE_URL/api/health

# 2. Verify credentials with verbose output
curl -v -X POST https://SERVICE_URL/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yoto"}'

# 3. Check database logs
railway logs --tail 100 | grep -i "login\|auth"
```

**Common Causes:**

1. **Wrong Credentials:**
   - Default: username=`admin`, password=`yoto`
   - May have been changed in production
   - Check environment variables for custom admin credentials

2. **Database Not Initialized:**
   ```bash
   # Check logs for database errors
   railway logs --tail 100 | grep -i database

   # May need to restart service to trigger initialization
   railway restart
   ```

3. **JWT Secret Changed:**
   - If `JWT_SECRET_KEY` environment variable changed
   - All existing tokens become invalid
   - Users must re-login

### OAuth Authorization Issues

**Symptom:** OAuth flow fails, devices not showing, or "Not authenticated" errors

**Diagnosis:**

```bash
# 1. Check OAuth status
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/auth/status | jq

# 2. Check for OAuth-related logs
railway logs --tail 100 | grep -i oauth

# 3. Verify Yoto Client ID is set
railway variables | grep YOTO_CLIENT_ID
```

**Common Causes:**

1. **Missing YOTO_CLIENT_ID:**
   ```bash
   # Set in Railway environment variables
   railway variables set YOTO_CLIENT_ID=your_client_id
   ```

2. **OAuth Flow Incomplete:**
   - User didn't complete device flow
   - Device code expired (10 minute timeout)
   - Solution: Restart OAuth flow from Dashboard

3. **Token Expired:**
   - Shouldn't happen with background refresh
   - Check logs for refresh task errors
   - Manually trigger refresh by restarting service

4. **Wrong Client ID:**
   - Verify Client ID matches Yoto application registration
   - Check https://yoto.dev/ for correct credentials

### No Devices Showing

**Symptom:** `/api/players` returns empty array

**Diagnosis:**

```bash
# 1. Verify OAuth is configured
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/auth/status

# 2. Check player API directly
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/players | jq

# 3. Check MQTT connection logs
railway logs --tail 100 | grep -i mqtt

# 4. Verify devices exist in Yoto account
# Login to https://my.yotoplay.com/ and check devices
```

**Common Causes:**

1. **OAuth Not Configured:**
   - Complete OAuth flow in Dashboard
   - See [Yoto OAuth Authorization](#yoto-oauth-authorization)

2. **No Devices in Account:**
   - Verify devices exist at https://my.yotoplay.com/
   - Devices must be online and connected to WiFi

3. **MQTT Connection Failed:**
   ```bash
   # Check logs for MQTT errors
   railway logs --tail 100 | grep -i "mqtt\|aws\|iot"

   # Common errors:
   # - "Connection refused" - Wrong MQTT credentials
   # - "Timeout" - Network issues
   # - "Authentication failed" - Token expired (rare)
   ```

4. **API Rate Limiting:**
   - Yoto API may rate limit frequent requests
   - Wait 1 minute and try again
   - Check logs for 429 status codes

### Transcription Not Working

**Symptom:** Uploaded audio files show "transcription: disabled" or empty transcript

**Background:**

Transcription is **disabled by default** to keep container builds fast and small. Whisper models and dependencies are large (~1-2GB).

**User Experience (Settings-Based):**

When a user attempts to transcribe an audio file with transcription disabled:
1. Audio Library displays error: "Transcription is disabled in Settings. Open Admin → System Settings to enable."
2. User can click the link or manually navigate to Admin UI
3. Admin UI loads with deep-link to Settings section (`?focus=settings` query param)
4. Settings section automatically scrolls into view and focuses the transcription toggle
5. User enables transcription via toggle
6. User returns to Audio Library and retries transcription
7. First transcription downloads the Whisper model (~200MB-1GB depending on choice)
8. Subsequent transcriptions use cached model

**To Enable (Admin UI):**

1. Go to Admin UI: **System Settings** section
2. Toggle **Enable Transcription** to **On**
3. (Optional) Choose model from dropdown: tiny, base (default), small, medium, large
4. Settings auto-save to database
5. **Note:** If environment variable `TRANSCRIPTION_ENABLED=false`, it overrides the setting

**To Enable (Environment Override):**

For deployments where transcription must always be enabled (overrides Settings UI):

```bash
# Set environment variable (highest priority)
railway variables set TRANSCRIPTION_ENABLED=true

# 2. (Optional) Choose model
railway variables set TRANSCRIPTION_MODEL=base
# Options: tiny, base (default), small, medium, large

# 3. Redeploy to install dependencies
railway up

# 4. Verify in logs
railway logs --tail 50 | grep -i transcription
```

**Priority Order (Effective Setting):**

1. Environment variable `TRANSCRIPTION_ENABLED` (if set)
2. Database setting (Admin UI toggle)
3. Default: disabled

**Backend Implementation:**

All transcription endpoints compute the effective `transcription_enabled` value:

```python
# Effective setting computation (env override > DB setting)
transcription_enabled = (
    settings.transcription_enabled 
    if settings.transcription_enabled is not None
    else config.transcription_enabled_db
)

if not transcription_enabled:
    raise HTTPException(
        status_code=400,
        detail="Transcription is disabled in Settings. Open Admin → System Settings to enable."
    )
```

The `TranscriptionService` reinitializes whenever the effective setting changes (enabled/disabled state, model choice, or API key), ensuring config changes take effect immediately without restarting the service.

### Slow Performance

**Symptom:** Pages loading slowly, API timeouts, or laggy responses

**Diagnosis:**

```bash
# 1. Check Railway metrics
# Go to Railway dashboard > Service > Metrics
# Look for: CPU usage, Memory usage, Request latency

# 2. Check logs for slow queries
railway logs --tail 100 | grep -i "slow\|timeout"

# 3. Check database size
railway logs --tail 10 | grep -i "database\|storage"
```

**Common Causes:**

1. **Resource Limits:**
   - Free tier has limited CPU/memory
   - Upgrade plan or optimize code
   - Consider adding Redis cache

2. **Large Audio Files:**
   - Keep audio files under 50MB
   - Use MP3 compression (128-256 kbps)
   - Consider external storage (S3, Cloudflare R2)

3. **Database Growth:**
   - SQLite performance degrades with large databases
   - Consider periodic cleanup of old data
   - Archive old cards/audio files

4. **Too Many Concurrent Users:**
   - Service is single-tenant by design
   - For multi-tenant, need architectural changes

### Logs Not Showing

**Symptom:** `railway logs` shows no output or is missing expected entries

**Solutions:**

```bash
# 1. Increase tail count
railway logs --tail 200

# 2. Check specific time range
railway logs --since 1h

# 3. Filter by search term
railway logs | grep -i "error\|warning"

# 4. Check if service is running
railway status

# 5. View logs in Railway dashboard
# Sometimes CLI logs lag behind web UI
```

### Database Corruption

**Symptom:** Database errors in logs, service crashes on startup, or data loss

**Recovery:**

```bash
# 1. Check logs for SQLite errors
railway logs --tail 200 | grep -i "database\|sqlite\|corrupt"

# 2. Access service shell
railway run bash

# 3. Check database integrity
sqlite3 /data/yoto_smart_stream.db "PRAGMA integrity_check;"

# 4. If corrupted, restore from backup
# Note: Railway doesn't auto-backup volumes
# Prevention: Set up regular backups via cron job
```

**Prevention:**

```bash
# Add backup script to service
# File: scripts/backup_db.sh

#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/data/backups"
mkdir -p $BACKUP_DIR

sqlite3 /data/yoto_smart_stream.db ".backup '$BACKUP_DIR/backup_$DATE.db'"

# Keep only last 7 backups
ls -t $BACKUP_DIR/backup_*.db | tail -n +8 | xargs rm -f

# Add to cron (run daily)
# 0 2 * * * /app/scripts/backup_db.sh
```

---

## API Quick Reference

### Public Endpoints (No Auth)

| Method | Endpoint | Purpose | Response |
|--------|----------|---------|----------|
| GET | `/api/health` | Health check | `{"status":"healthy"}` |
| POST | `/api/user/login` | User login | `{"access_token":"..."}` |

### Authenticated Endpoints

| Method | Endpoint | Purpose | Auth | Response |
|--------|----------|---------|------|----------|
| GET | `/` | Dashboard UI | Required | HTML |
| GET | `/api/auth/status` | OAuth status | Required | `{"authenticated":true}` |
| POST | `/api/auth/device-code` | Start OAuth | Required | `{"user_code":"..."}` |
| POST | `/api/auth/token` | Complete OAuth | Required | `{"status":"success"}` |
| GET | `/api/players` | List devices | Required | `[{"id":"..."}]` |
| GET | `/api/players/{id}` | Player details | Required | `{"id":"...","online":true}` |
| POST | `/api/players/{id}/play` | Play content | Required | `{"status":"playing"}` |
| POST | `/api/players/{id}/pause` | Pause playback | Required | `{"status":"paused"}` |
| GET | `/api/cards` | List MYO cards | Required | `[{"id":"..."}]` |
| POST | `/api/cards` | Create MYO card | Required | `{"id":"..."}` |
| DELETE | `/api/cards/{id}` | Delete card | Required | `{"message":"..."}` |
| GET | `/api/audio/list` | List audio files | Required | `[{"filename":"..."}]` |
| POST | `/api/audio/upload` | Upload audio | Required | `{"filename":"..."}` |
| DELETE | `/api/audio/delete/{file}` | Delete audio | Required | `{"message":"..."}` |

### Admin-Only Endpoints

| Method | Endpoint | Purpose | Auth | Response |
|--------|----------|---------|------|----------|
| GET | `/admin` | Admin panel | Admin | HTML |
| GET | `/api/admin/users` | List users | Admin | `[{"id":1}]` |
| POST | `/api/admin/users` | Create user | Admin | `{"id":2}` |
| DELETE | `/api/admin/users/{id}` | Delete user | Admin | `{"message":"..."}` |
| GET | `/api/admin/logs` | View logs | Admin | `[{"timestamp":"..."}]` |

---

## Environment Variables

### Required

| Variable | Purpose | Example | Default |
|----------|---------|---------|---------|
| `YOTO_CLIENT_ID` | Yoto OAuth Client ID | `abc123def456` | None (required) |

### Optional - Database

| Variable | Purpose | Example | Default |
|----------|---------|---------|---------|
| `DATABASE_URL` | SQLite database path | `/data/app.db` | `/data/yoto_smart_stream.db` |

### Optional - Authentication

| Variable | Purpose | Example | Default |
|----------|---------|---------|---------|
| `JWT_SECRET_KEY` | JWT signing secret | `your-secret-key-here` | Auto-generated |
| `TOKEN_REFRESH_INTERVAL_HOURS` | OAuth token refresh interval | `12` | `12` (range: 1-23) |

### Optional - Transcription

| Variable | Purpose | Example | Default |
|----------|---------|---------|---------|
| `TRANSCRIPTION_ENABLED` | Enable audio transcription | `true` | `false` |
| `TRANSCRIPTION_MODEL` | Whisper model size | `base` | `base` (options: tiny/base/small/medium/large) |

### Optional - Logging

| Variable | Purpose | Example | Default |
|----------|---------|---------|---------|
| `LOG_LEVEL` | Logging verbosity | `DEBUG` | `INFO` (options: DEBUG/INFO/WARNING/ERROR) |

### Optional - Server

| Variable | Purpose | Example | Default |
|----------|---------|---------|---------|
| `PORT` | HTTP server port | `8080` | `8080` |
| `HOST` | Server bind address | `0.0.0.0` | `0.0.0.0` |

### Setting Variables in Railway

```bash
# Set single variable
railway variables set YOTO_CLIENT_ID=abc123

# Set multiple variables
railway variables set \
  TRANSCRIPTION_ENABLED=true \
  TRANSCRIPTION_MODEL=base \
  LOG_LEVEL=DEBUG

# List all variables
railway variables

# Delete variable
railway variables delete TRANSCRIPTION_ENABLED
```

---

## Best Practices

### Security

1. **Change Default Password:** Update admin password in production
2. **Use HTTPS:** Always access service via HTTPS (Railway provides this)
3. **Rotate Secrets:** Regularly rotate JWT secret and admin credentials
4. **Limit Access:** Use Railway's access controls to limit who can view logs/variables
5. **Monitor Logs:** Regularly check logs for suspicious activity

### Reliability

1. **Monitor Health:** Set up automated health checks
2. **Backup Database:** Implement regular database backups
3. **Check Logs:** Review logs after deployments
4. **Test OAuth:** Verify OAuth status after deployments
5. **Staged Rollouts:** Test in develop environment before production

### Performance

1. **Optimize Audio:** Use compressed MP3 files (128-256 kbps)
2. **Clean Up:** Regularly delete unused audio files and cards
3. **Monitor Resources:** Check Railway metrics for CPU/memory usage
4. **Cache Responses:** Consider adding Redis for frequently accessed data
5. **Limit Uploads:** Restrict audio file sizes (e.g., 50MB max)

### Maintainability

1. **Document Changes:** Update docs when adding features
2. **Version Control:** Use git tags for releases
3. **Environment Parity:** Keep develop and production configs similar
4. **Test Before Deploy:** Run tests locally before deploying
5. **Review Logs:** Check logs after every deployment

---

## Support Resources

- **Project Documentation:** See `/docs` folder for detailed guides
- **Testing Guide:** See [yoto-smart-stream-testing skill](../../yoto-smart-stream-testing/SKILL.md)
- **Railway Management:** See [railway-service-management skill](../../railway-service-management/SKILL.md)
- **API Development:** See [yoto-smart-stream skill](../SKILL.md)
- **Example Code:** See `/examples` folder for working implementations
- **Test Suite:** See `/tests` folder for test examples
