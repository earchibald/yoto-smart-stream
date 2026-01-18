# OAuth Flow Implementation Reference

This document provides detailed technical reference for the Yoto Smart Stream OAuth implementation.

## Architecture Overview

### Device Code Grant (RFC 8628)

The service uses the Device Code Grant flow, ideal for applications where:
- User has a separate browser for authentication
- No redirect URI available on the streaming device
- Simple, secure single-tenant OAuth model

**Flow State Machine:**
```
START
  ↓
/auth/start (POST)
  → Generate device_code, user_code
  → Return to frontend
  ↓
Frontend displays user_code + verification URL
  ↓
User opens browser, enters code at login.yotoplay.com
  ↓
Frontend polls /auth/status (3s-8s interval)
  → status="pending" (waiting)
  → status="slow_down" (rate limited, increase interval)
  → status="expired" (code expired, restart)
  → status="authorized" (tokens received!)
  ↓
Backend receives tokens from Yoto API
  ↓
Tokens saved to Secrets Manager / local file
  ↓
Frontend detects success
  → Shows "Successfully connected!"
  → Reloads page after 5 seconds
  ↓
Page reloads with authenticated session
  ↓
Players endpoint accessible
  → MQTT connects with tokens
  → Device status flows in real-time
  ↓
SUCCESS - Ready to control devices
```

## Component Breakdown

### Frontend: OAuth Flow (`static/js/dashboard.js`)

**Key Variables:**
```javascript
let authPollDelay = 3000;           // Start at 3 seconds
let authPollMaxDelay = 8000;        // Cap at 8 seconds
const AUTH_POLL_BACKOFF_FACTOR = 1.5;  // Exponential multiplier
let pollCount = 0;                  // Track polling iterations
```

**Functions:**

1. **startAuthFlow()**
   - Calls `POST /auth/start`
   - Receives `user_code` and `device_code`
   - Displays verification URL with user code
   - Starts polling with `startAuthPolling()`

2. **startAuthPolling()**
   - Polls `GET /auth/status` every `authPollDelay` ms
   - Handles response statuses:
     - `pending`: Continue polling, increment `pollCount`
     - `slow_down`: Increase delay: `authPollDelay = Math.min(authPollDelay * 1.5, 8000)`
     - `expired`: Show error, stop polling
     - `authorized`: Show success, reload page
   - Clears interval and restarts with new delay on backoff

3. **handleAuthSuccess()**
   - Shows "Successfully connected!" message
   - Logs completion time
   - Reloads page after 5 seconds

**Rate Limiting Logic:**
```javascript
// Detect rate limiting from backend error message
if (response.error && response.error.includes("slow_down")) {
    // Increase polling delay exponentially
    authPollDelay = Math.min(authPollDelay * AUTH_POLL_BACKOFF_FACTOR, authPollMaxDelay);
    // Clear existing interval
    clearInterval(authPollInterval);
    // Start new interval with increased delay
    authPollInterval = setInterval(authPollingFunction, authPollDelay);
}
```

### Backend: OAuth Routes (`api/routes/auth.py`)

**POST /auth/start**
```python
@router.post("/auth/start")
async def start_oauth():
    """
    Initiates OAuth device code flow with Yoto.
    
    Returns:
        {
            "user_code": "XXXX-XXXX",           # Display to user
            "device_code": "...",               # Store for polling
            "expires_in": 600                   # 10 minutes
        }
    """
    auth_manager = OAuthManager()
    auth_result = auth_manager.start_device_flow()
    
    # Store in session for polling
    session["auth_result"] = auth_result
    
    return {
        "user_code": auth_result.user_code,
        "device_code": auth_result.device_code
    }
```

**GET /auth/status**
```python
@router.get("/auth/status")
async def poll_auth_status():
    """
    Polls for OAuth authorization completion.
    
    Returns:
        {
            "status": "pending|slow_down|expired|authorized",
            "message": "Human-readable status message"
        }
    """
    auth_result = session.get("auth_result")
    
    try:
        # Poll Yoto API for token
        token = yoto_api.poll_for_token(auth_result)
        
        # SUCCESS - Save tokens
        save_yoto_tokens(token)
        
        return {"status": "authorized", "message": "Tokens received"}
        
    except errors.SlowDownError:
        # Rate limited - tell frontend to back off
        return {"status": "slow_down", "message": "Polling too fast, increase interval"}
        
    except errors.ExpiredCodeError:
        # Device code expired (>10 minutes)
        return {"status": "expired", "message": "Device code expired, start over"}
        
    except errors.PendingAuthorizationError:
        # User hasn't authorized yet
        return {"status": "pending", "message": "Waiting for authorization"}
```

**Error Detection (lines 282-310):**
```python
except HTTPException as e:
    error_msg = str(e).lower()
    
    # Log what error we detected
    logger.warning(f"🔍 [OAuth Poll] Checking error: "
        f"error_msg={repr(error_msg)}, "
        f"has slow_down={('slow_down' in error_msg)}, "
        f"has 429={('429' in error_msg)}")
    
    # Categorize error for frontend
    if "slow_down" in error_msg or "429" in error_msg:
        return AuthPollResponse(status="slow_down")
    elif "expired" in error_msg:
        return AuthPollResponse(status="expired")
    elif "pending" in error_msg:
        return AuthPollResponse(status="pending")
    else:
        # Unknown error - return as-is
        raise
```

### Token Storage & Retrieval

#### AWS Lambda with Secrets Manager Extension

**Load Tokens** (`storage/secrets_manager.py`):
```python
def load_yoto_tokens():
    """
    Load OAuth tokens from Secrets Manager with extension caching.
    
    Priority:
    1. Lambda Extension (fast, cached)
    2. boto3 Secrets Manager (fallback)
    3. None (not found - requires re-auth)
    """
    
    if is_lambda_environment():
        # Try extension first (1000ms cache)
        token = _get_secret_from_extension()
        if token:
            logger.info("Loaded secret from Lambda Extension")
            return token
    
    # Fallback to boto3
    token = _get_secret_from_boto3()
    if token:
        logger.info("Loaded secret from boto3")
        return token
    
    # Not found
    logger.warning("Refresh token not found in Secrets Manager or file")
    return None
```

**Save Tokens**:
```python
def save_yoto_tokens(token):
    """
    Save OAuth tokens to Secrets Manager.
    
    Format:
        {
            "access_token": "...",
            "refresh_token": "...",
            "expires_at": "2026-01-18T14:30:00Z"
        }
    """
    
    if is_lambda_environment():
        secret_value = {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at.isoformat()
        }
        
        try:
            sm_client.put_secret_value(
                SecretId=f"{ENVIRONMENT}/oauth-tokens",
                SecretString=json.dumps(secret_value)
            )
            logger.info("✓ Yoto OAuth tokens saved to Secrets Manager")
        except ClientError as e:
            logger.error(f"Failed to save tokens: {e}")
            raise
```

#### Local Development File Storage

**File-based Storage** (`/tmp/.yoto_refresh_token`):
```python
def load_yoto_tokens_local():
    """Load refresh token from local file for development."""
    try:
        with open("/tmp/.yoto_refresh_token", "r") as f:
            token_data = json.load(f)
            return Token(**token_data)
    except FileNotFoundError:
        return None

def save_yoto_tokens_local(token):
    """Save refresh token to local file for development."""
    with open("/tmp/.yoto_refresh_token", "w") as f:
        json.dump({
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "expires_at": token.expires_at.isoformat()
        }, f)
```

### Token Refresh Logic

**Automatic Refresh** (`core/yoto_client.py`):
```python
async def ensure_authenticated(self):
    """
    Check if access token is still valid.
    Refresh if expired or expiring soon.
    """
    token = load_yoto_tokens()
    
    if not token:
        raise NotAuthenticatedError("No tokens found")
    
    # Check if token expired or expiring in next 60 seconds
    if token.expires_at <= datetime.now() + timedelta(seconds=60):
        logger.info("Token expired/expiring, refreshing...")
        
        try:
            new_token = self.yoto_api.refresh_token(token.refresh_token)
            save_yoto_tokens(new_token)
            logger.info("Token refreshed successfully")
        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            # User must re-authorize
            raise NotAuthenticatedError(f"Token refresh failed: {e}")
```

**Called Before Each API Operation:**
```python
@app.get("/api/players")
async def list_players():
    # Always ensure authenticated before accessing API
    yoto_client.ensure_authenticated()
    
    # Now safe to use tokens
    return yoto_client.get_players()
```

## Rate Limiting Behavior

### Yoto API Rate Limits

- **Polling Interval**: Minimum 5 seconds between device code polls
- **Error Code**: Returns HTTP 429 with JSON: `{"error": "slow_down", "error_description": "..."}`
- **Backoff Required**: Client must increase polling delay when error received

### Implementation Strategy

**Frontend Exponential Backoff:**
```
Initial: 3000ms
After slow_down: 3000 * 1.5 = 4500ms
Next: 4500 * 1.5 = 6750ms
Next: 6750 * 1.5 = 10125ms → capped at 8000ms

If another slow_down arrives: reset to 3000ms (Yoto authorization completed)
```

**Backend Detection:**
```python
# When Yoto API returns 429 or error message contains "slow_down"
if "slow_down" in error_response or response.status_code == 429:
    # Return special status to frontend
    return {"status": "slow_down"}
    # Frontend increases polling interval
```

## Error Scenarios & Recovery

### Scenario 1: User Doesn't Complete OAuth in Time

**Trigger**: Device code expires (10 minute limit)  
**Error**: `{"error": "Invalid or expired device code"}`  
**Frontend Response**:
```javascript
if (response.status === "expired") {
    showMessage("Authorization expired. Please click 'Connect Yoto Account' to try again");
    // User clicks button again, new device code generated
}
```
**Recovery**: User restarts by clicking button

### Scenario 2: Rate Limiting Detected

**Trigger**: Frontend polling too fast (< 5 seconds)  
**Error**: `{"error": "slow_down"}`  
**Backend Response**: Returns `{"status": "slow_down"}`  
**Frontend Response**:
```javascript
if (response.status === "slow_down") {
    // Increase polling interval exponentially
    authPollDelay = Math.min(authPollDelay * 1.5, 8000);
    // Restart interval with new delay
}
```
**Recovery**: Automatic - frontend backs off

### Scenario 3: Secrets Manager Version Limit Exceeded

**Trigger**: Too many token save attempts (100+ versions accumulated)  
**Error**: `LimitExceededException`  
**Backend Response**: Returns HTTP 500 with error message  
**Frontend Response**:
```javascript
if (response.error && response.error.includes("LimitExceededException")) {
    showMessage("Authorization failed. Please contact admin");
    // Admin must restore/recreate secret
}
```
**Recovery**: Delete old secret versions or restore from pending deletion:
```bash
aws secretsmanager restore-secret --secret-id yoto-smart-stream-dev/oauth-tokens
```

### Scenario 4: Token Refresh Failure

**Trigger**: Refresh token revoked (user changed Yoto password)  
**Error**: HTTP 401 Unauthorized  
**Backend Response**: Logs error, raises NotAuthenticatedError  
**Frontend Response**:
```javascript
// API returns 401
if (response.status === 401) {
    showMessage("Authentication expired. Please reconnect your Yoto account");
    // User clicks "Connect Yoto Account" again
}
```
**Recovery**: User re-authorizes via OAuth flow

## CloudWatch Logging

### Success Log Messages

```
[INFO] ✓ [OAuth] Device code received: {user_code: XXXX-XXXX, ...}
[INFO] 🔐 [OAuth] OAuth Authentication Success! User authorized the application
[INFO] ✓ Yoto OAuth tokens saved to Secrets Manager
[INFO] Loaded secret from Lambda Extension
```

### Error Log Messages

```
[WARNING] 🔍 [OAuth Poll] Checking error: error_msg='...', has slow_down=True, has 429=True
[ERROR] Failed to save tokens to Secrets Manager: LimitExceededException...
[ERROR] Auth poll exception: Invalid or expired device code
[WARNING] Failed to fetch secret via boto3: InvalidRequestException (marked for deletion)
```

### Monitoring Query

```bash
# Watch OAuth flow in real-time
aws logs tail /aws/lambda/yoto-api-dev --follow --region us-east-1 | grep -E "(OAuth|auth|token|slow_down)"
```

## Testing Considerations

### Test Isolation

Each OAuth test should:
1. Start fresh device code (don't reuse old codes)
2. Wait for 10-minute expiration between tests OR use new codes
3. Clear browser session/cookies between tests
4. Restore Secrets Manager secret if in "pending deletion" state

### Rate Limiting Testing

To verify rate limiting behavior:
```javascript
// In browser console, simulate aggressive polling
const testPoll = async () => {
    const result = await fetch("/auth/status");
    const data = await result.json();
    console.log(data); // Should see "slow_down" after a few calls
}

// Call every 1 second (violates 5s requirement)
setInterval(testPoll, 1000);
```

### Token Expiration Testing

To test automatic token refresh:
1. Complete OAuth flow normally
2. Manually set token expiry to soon: `expires_at = now + 30 seconds`
3. Wait 30 seconds
4. Make any API call
5. Should see "Token refreshed successfully" in logs
6. API call should succeed

## Performance Characteristics

### Lambda Extension Caching

- **First Load**: ~100-200ms (boto3 call to Secrets Manager)
- **Cached Loads**: ~5-10ms (extension HTTP call)
- **Cache TTL**: 1000ms (configurable via `SECRETS_EXTENSION_HTTP_POLL`)
- **Multiple Invocations**: All benefit from same 1000ms cache within that window

### Polling Overhead

- **Initial Interval**: 3 seconds (meets Yoto 5s requirement with margin)
- **Max Interval**: 8 seconds (under rate limit)
- **Per Polling Request**: ~50-100ms network roundtrip

### Token Refresh Overhead

- **Check Expiration**: <1ms (datetime comparison)
- **Refresh (if needed)**: ~200-400ms (network call to Yoto API)
- **Save to Secrets Manager**: ~100-200ms (boto3 call)
- **Typical Case**: Token valid, only expiration check (<1ms)

## Related Components

- **MQTT Connection**: Happens immediately after successful OAuth, uses access token for authentication
- **Player Status Updates**: Flow through MQTT after OAuth establishes connection
- **Token Refresh**: Automatic before each API call to Yoto
- **Session Management**: Separate from OAuth, handled by Cognito/session middleware
