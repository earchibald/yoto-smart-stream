# Yoto App Registration - Required URLs

## Overview

When registering a Yoto application at https://yoto.dev/, you need to provide specific URLs. This document outlines what URLs are needed based on the Yoto API authentication method.

## Yoto Authentication Method

The Yoto API uses **OAuth2 Device Flow** (also called Device Authorization Grant), which is designed for:
- CLI applications
- Server-side applications  
- Devices without browsers
- Applications where traditional OAuth redirect flow isn't practical

**Important:** Device Flow does NOT require callback/redirect URLs!

## Required URLs for Yoto App Registration

Based on the OAuth2 Device Flow authentication used by this project:

### 1. Allowed Callback URLs

**Value:** `Not Required` or `N/A`

**Reason:** OAuth2 Device Flow doesn't use redirect callbacks. Instead:
- User visits https://login.yotoplay.com/activate
- User enters a code shown in the application
- Application polls for authorization completion
- No redirect back to your application

**If the field is required**, you can use a placeholder:
```
http://localhost/oauth/callback
```
(This will never be called since we use Device Flow)

### 2. Allowed Logout URLs

**Value:** `Not Required` or `N/A`

**Reason:** This application doesn't implement a logout flow. Token management is handled via:
- Access tokens (expire automatically)
- Refresh tokens (stored locally, can be deleted)
- No server-side session that requires logout callback

**If the field is required**, you can use a placeholder:
```
http://localhost/logout
```
(This will never be called)

### 3. Application Type

**Value:** `Server-side / CLI Application`

**Note:** Some registration forms may ask for application type. Select:
- Server-side application
- CLI application
- Native application
- **NOT** Single Page Application (SPA) or Web Application

## Railway Deployment URLs

While not needed for OAuth, your Railway deployments will have these URLs for **audio streaming**:

### Production
```
https://yoto-smart-stream-production.up.railway.app
```

### Staging
```
https://yoto-smart-stream-staging.up.railway.app
```

### Development
```
https://yoto-smart-stream-development.up.railway.app
```

These URLs are used for:
- Audio streaming endpoints (`/audio/{filename}`)
- Health checks (`/health`)
- API endpoints (not for OAuth)

## Complete Registration Form Example

When filling out the Yoto App registration form:

```
Application Name: Yoto Smart Stream
Description: Audio streaming service for Yoto players
Application Type: Server-side Application

OAuth Configuration:
├── Grant Type: Device Code (Device Authorization Grant)
├── Allowed Callback URLs: N/A (Device Flow - not required)
└── Allowed Logout URLs: N/A (Device Flow - not required)

Deployment URLs (for reference):
├── Production: https://yoto-smart-stream-production.up.railway.app
├── Staging: https://yoto-smart-stream-staging.up.railway.app
└── Development: https://yoto-smart-stream-development.up.railway.app
```

## If Callback URLs Are Required

Some forms may require callback URLs even for Device Flow. If so:

### Option 1: Use Localhost (Recommended)
```
Allowed Callback URLs:
- http://localhost/oauth/callback
- http://localhost:8080/oauth/callback

Allowed Logout URLs:
- http://localhost/logout
- http://localhost:8080/logout
```

### Option 2: Use Railway URLs (if required)
```
Allowed Callback URLs:
- https://yoto-smart-stream-production.up.railway.app/oauth/callback
- https://yoto-smart-stream-staging.up.railway.app/oauth/callback
- https://yoto-smart-stream-development.up.railway.app/oauth/callback

Allowed Logout URLs:
- https://yoto-smart-stream-production.up.railway.app/logout
- https://yoto-smart-stream-staging.up.railway.app/logout
- https://yoto-smart-stream-development.up.railway.app/logout
```

**Note:** Even if these URLs are registered, they won't be used by the Device Flow authentication. They're just to satisfy form requirements.

## Authentication Flow Details

### How Device Flow Works (No Callbacks)

```
1. Application                2. User's Browser               3. Yoto Auth Server
   │                              │                               │
   │──── Request device code ────────────────────────────────────>│
   │<─── Returns: user_code ─────────────────────────────────────│
   │     & verification_uri                                       │
   │                              │                               │
   │── Display code to user ──>│                                  │
   │                              │                               │
   │                              │──── Visit activation URL ────>│
   │                              │<─── Show code entry form ────│
   │                              │──── Enter user_code ─────────>│
   │                              │──── Authorize application ───>│
   │                              │<─── Confirmation ─────────────│
   │                              │                               │
   │──── Poll for token ─────────────────────────────────────────>│
   │<─── Return access_token ────────────────────────────────────│
   │     & refresh_token                                          │
   
   ✓ No redirect/callback to application
   ✓ No logout URL needed
```

### Comparison: Traditional OAuth vs Device Flow

**Traditional OAuth (Web Apps):**
```
✓ Requires callback URLs
✓ Redirects user back to your app
✓ May require logout URLs
✗ Not used by Yoto API
```

**Device Flow (CLI/Server Apps):**
```
✗ No callback URLs needed
✗ No redirects to your app
✗ No logout URLs needed
✓ Used by Yoto API
```

## Verification After Registration

After registering your Yoto app, verify you receive:

1. **Client ID** - Your unique application identifier
   ```
   Example: abc123xyz456
   ```

2. **Client Secret** (may not be provided for Device Flow)
   - Some APIs don't issue secrets for Device Flow
   - Yoto API uses client_id only

3. **Verification URI**
   ```
   Expected: https://login.yotoplay.com/activate
   ```

Store your Client ID securely:
```bash
# In .env file (don't commit!)
YOTO_SERVER_CLIENT_ID=your_client_id_here

# In GitHub Secrets
YOTO_SERVER_CLIENT_ID (value: your_client_id_here)

# In Railway Variables
YOTO_SERVER_CLIENT_ID (value: your_client_id_here)
```

## Testing Authentication

After registration, test the Device Flow:

```bash
# From your Railway deployment or local environment
python examples/simple_client.py

# Expected output:
# AUTHENTICATION REQUIRED
# 1. Go to: https://login.yotoplay.com/activate
# 2. Enter code: XXXX-XXXX
# Waiting for authorization...
```

## Troubleshooting

### Issue: Registration form requires callback URLs

**Solution:** Use localhost or Railway URLs as placeholders. They won't be used, but may satisfy form validation.

### Issue: "Invalid redirect_uri" error

**Solution:** This error typically occurs with traditional OAuth, not Device Flow. If you see this:
1. Verify you're using Device Flow endpoints
2. Check that your app is registered for Device Flow
3. Ensure you're not accidentally using traditional OAuth code

### Issue: Authentication works locally but fails on Railway

**Solution:** Device Flow authentication doesn't depend on deployment URLs. Check:
1. YOTO_SERVER_CLIENT_ID environment variable is set in Railway
2. Railway environment has network access to login.yotoplay.com
3. Refresh token is stored correctly

## Reference Documentation

- **Yoto Developer Portal:** https://yoto.dev/
- **Device Flow Spec:** RFC 8628 (OAuth 2.0 Device Authorization Grant)
- **Yoto API Docs:** https://yoto.dev/api/
- **This Project's Auth Guide:** See `examples/simple_client.py`

## Summary

✅ **What You Need:**
- Client ID from Yoto developer portal
- No callback URLs needed (Device Flow)
- No logout URLs needed

✅ **What You Can Ignore:**
- Callback URL requirements (use placeholder if forced)
- Logout URL requirements (use placeholder if forced)
- Redirect URI configuration

✅ **What Matters:**
- Railway URLs for **audio streaming** (not OAuth)
- Client ID stored in environment variables
- Refresh token persistence

---

**Last Updated:** 2026-01-10  
**Auth Method:** OAuth2 Device Flow (RFC 8628)  
**No Callbacks Required:** ✓
