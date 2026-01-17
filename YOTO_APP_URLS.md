# QUICK ANSWER: Yoto App Registration URLs

## TL;DR - What to Provide

When registering your Yoto App at https://yoto.dev/:

### Allowed Callback URLs
```
NOT REQUIRED - OAuth2 Device Flow doesn't use callbacks

If form requires input (use placeholders):
- http://localhost/oauth/callback
- http://localhost:8080/oauth/callback

OR (if Railway URLs preferred):
- https://yoto-smart-stream-production.up.railway.app/oauth/callback
- https://yoto-smart-stream-staging.up.railway.app/oauth/callback  
- https://yoto-smart-stream-development.up.railway.app/oauth/callback
```

### Allowed Logout URLs
```
NOT REQUIRED - Device Flow doesn't use logout URLs

If form requires input (use placeholders):
- http://localhost/logout
- http://localhost:8080/logout

OR (if Railway URLs preferred):
- https://yoto-smart-stream-production.up.railway.app/logout
- https://yoto-smart-stream-staging.up.railway.app/logout
- https://yoto-smart-stream-development.up.railway.app/logout
```

## Why These URLs Don't Matter

This project uses **OAuth2 Device Flow** (RFC 8628):

1. User visits: `https://login.yotoplay.com/activate`
2. User enters code shown by application
3. Application polls Yoto server for token
4. **No redirect back to your application**
5. **No logout callback**

The URLs above are only if the registration form requires something. They'll never be called.

## What URLs Actually Matter

### Railway Deployment URLs (for audio streaming)

**Production:**
```
https://yoto-smart-stream-production.up.railway.app
```

**Staging:**
```
https://yoto-smart-stream-staging.up.railway.app
```

**Development:**
```
https://yoto-smart-stream-development.up.railway.app
```

**Used for:**
- `/audio/{filename}` - Streaming audio to Yoto players
- `/health` - Health checks
- `/api/*` - API endpoints
- **NOT** for OAuth (that uses Device Flow)

## Registration Form Example

```
Application Name: Yoto Smart Stream
Application Type: Server-side / CLI Application
Grant Type: Device Code (OAuth 2.0 Device Authorization Grant)

Allowed Callback URLs: 
  http://localhost/oauth/callback (not used, placeholder only)

Allowed Logout URLs:
  http://localhost/logout (not used, placeholder only)

Deployment URLs (reference only):
  Production: https://yoto-smart-stream-production.up.railway.app
  Staging: https://yoto-smart-stream-staging.up.railway.app
  Development: https://yoto-smart-stream-development.up.railway.app
```

## After Registration

You'll receive:
- **Client ID** - Store as `YOTO_CLIENT_ID` environment variable
- Verification URI: `https://login.yotoplay.com/activate` (already known)

**No Client Secret** typically (Device Flow doesn't need it)

## Test Authentication

```bash
export YOTO_CLIENT_ID="your_client_id_here"
python examples/simple_client.py

# Follow prompts to complete Device Flow
```

---

**See full details:** `docs/YOTO_APP_REGISTRATION.md`