# Required Secrets for Development and Testing

## Overview

This project requires **two types of secrets** for full functionality:

1. **RAILWAY_TOKEN** - For Railway deployments (optional for local development)
2. **YOTO_SERVER_CLIENT_ID** - For Yoto API access (**REQUIRED for any testing**)

## Quick Answer: Do I Need YOTO_SERVER_CLIENT_ID in Codespaces?

**YES - ABSOLUTELY REQUIRED** if you want to:
- ✅ Run any examples (`simple_client.py`, `basic_server.py`, etc.)
- ✅ Test Yoto API functionality
- ✅ Authenticate with Yoto
- ✅ List or control your Yoto players
- ✅ Create MYO cards
- ✅ Test MQTT event handling

**Without YOTO_SERVER_CLIENT_ID:**
- ❌ All examples will fail with: `Error: YOTO_SERVER_CLIENT_ID environment variable not set`
- ❌ Cannot authenticate with Yoto API
- ❌ Cannot test any Yoto functionality
- ❌ Can only work on documentation or non-Yoto code

## Secret Requirements by Use Case

### Local Development (Testing Yoto API)

**Required:**
```bash
export YOTO_SERVER_CLIENT_ID="your_client_id_from_yoto_dev"
```

**Optional:**
```bash
export RAILWAY_TOKEN="your_railway_token"  # Only if deploying
```

### GitHub Codespaces (Development & Testing)

**Required Codespaces Secrets:**

1. **YOTO_SERVER_CLIENT_ID** (REQUIRED)
   - Location: https://github.com/settings/codespaces
   - Why: Needed for ALL Yoto API interactions
   - Get from: https://yoto.dev/

2. **RAILWAY_TOKEN** (Optional)
   - Location: https://github.com/settings/codespaces
   - Why: Only needed if you want to deploy from Codespace
   - Get from: https://railway.app/account/tokens

### GitHub Actions (CI/CD)

**Required Repository Secrets:**

1. **RAILWAY_TOKEN_PROD** - Production deployments
2. **RAILWAY_TOKEN_STAGING** - Staging deployments
3. **RAILWAY_TOKEN_DEV** - Development deployments
4. **YOTO_SERVER_CLIENT_ID** - Used to set Railway environment variables

## How YOTO_SERVER_CLIENT_ID is Used

### In Examples

Every example requires it to initialize the Yoto API client:

```python
# examples/simple_client.py
client_id = os.getenv("YOTO_SERVER_CLIENT_ID")
if not client_id:
    logger.error("YOTO_SERVER_CLIENT_ID environment variable not set")
    logger.info("Get your client ID from: https://yoto.dev/")
    sys.exit(1)

ym = YotoManager(client_id=client_id)
```

### In Basic Server

The FastAPI server requires it to function:

```python
# examples/basic_server.py
client_id = os.getenv("YOTO_SERVER_CLIENT_ID")
if not client_id:
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="YOTO_SERVER_CLIENT_ID not configured",
    )
```

### Authentication Flow

1. Application uses YOTO_SERVER_CLIENT_ID to request device code
2. User visits https://login.yotoplay.com/activate
3. User enters code
4. Application polls Yoto server
5. Receives access token and refresh token
6. Refresh token stored in `.yoto_refresh_token` file

**Without YOTO_SERVER_CLIENT_ID:** Cannot even start this flow!

## Setup Instructions

### Step 1: Get Your Yoto Client ID

1. Go to https://yoto.dev/get-started/start-here/
2. Register your application:
   - Application Type: Server-side / CLI Application
   - Grant Type: Device Code (OAuth 2.0 Device Authorization Grant)
   - Callback URLs: `http://localhost/oauth/callback` (placeholder)
   - Logout URLs: `http://localhost/logout` (placeholder)
3. Save your Client ID (looks like: `abc123xyz456`)

### Step 2: Add to Codespaces Secrets

**For Yoto API Access (REQUIRED):**

1. Go to https://github.com/settings/codespaces
2. Click "New secret"
3. Fill in:
   - Name: `YOTO_SERVER_CLIENT_ID`
   - Value: Your client ID from step 1
   - Repository access: `earchibald/yoto-smart-stream`
4. Click "Add secret"

**For Railway Deployments (Optional):**

Repeat for `RAILWAY_TOKEN` if you need deployment capability.

### Step 3: Restart Codespace

If you have a Codespace running:
1. Stop it
2. Wait a few seconds
3. Start it again
4. Secrets will now be available as environment variables

### Step 4: Verify

In your Codespace terminal:

```bash
# Check if both secrets are set
echo $YOTO_SERVER_CLIENT_ID  # Should show your client ID
echo $RAILWAY_TOKEN   # Should show your token (if set)

# Test Yoto authentication
python examples/simple_client.py
# Should start device flow authentication
```

## What Happens Without YOTO_SERVER_CLIENT_ID

### Error Messages You'll See

```
Error: YOTO_SERVER_CLIENT_ID environment variable not set
Get your client ID from: https://yoto.dev/get-started/start-here/
```

Or:

```
HTTPException: YOTO_SERVER_CLIENT_ID not configured
```

### What Won't Work

- ❌ `python examples/simple_client.py` - Fails immediately
- ❌ `python examples/basic_server.py` - Server starts but API calls fail
- ❌ `python examples/streaming_myo_card.py` - Cannot create cards
- ❌ `python examples/mqtt_listener.py` - Cannot connect
- ❌ Any Yoto API integration tests

### What Will Still Work

- ✅ Documentation editing
- ✅ Non-Yoto Python code
- ✅ Railway infrastructure code (if you have RAILWAY_TOKEN)
- ✅ Running linters, formatters

## Comparison: RAILWAY_TOKEN vs YOTO_SERVER_CLIENT_ID

| Feature | RAILWAY_TOKEN | YOTO_SERVER_CLIENT_ID |
|---------|---------------|----------------|
| **Purpose** | Deploy to Railway | Access Yoto API |
| **Required For** | Deployments only | ALL Yoto testing |
| **Can Skip?** | Yes (if not deploying) | NO |
| **Where to Get** | railway.app/account/tokens | yoto.dev |
| **Secret Type** | User token (can be rotated) | App client ID (stable) |
| **Used In** | Deployment scripts | Every Yoto example |

## Troubleshooting

### "YOTO_SERVER_CLIENT_ID not set" Error

**Problem:** Examples fail with missing YOTO_SERVER_CLIENT_ID

**Solution:**
1. Verify secret is added at https://github.com/settings/codespaces
2. Check repository access is granted
3. Restart Codespace
4. Test: `echo $YOTO_SERVER_CLIENT_ID`

### Secret Not Available in Codespace

**Problem:** `echo $YOTO_SERVER_CLIENT_ID` shows nothing

**Solution:**
1. Verify secret name is exactly `YOTO_SERVER_CLIENT_ID` (case-sensitive)
2. Verify repository access includes this repo
3. Restart Codespace (secrets only load on start)
4. Check `.devcontainer/devcontainer.json` has remoteEnv config

### Authentication Fails Even With Client ID

**Problem:** Have YOTO_SERVER_CLIENT_ID but authentication fails

**Solution:**
1. Verify the Client ID is correct (copy from yoto.dev)
2. Check network access to login.yotoplay.com
3. Try device flow manually
4. Check for any typos in the Client ID

## Best Practices

### ✅ DO:

- Add YOTO_SERVER_CLIENT_ID to Codespaces secrets immediately
- Document your Client ID (not a secret, but keep private)
- Use separate Client IDs for dev/staging/prod if available
- Store refresh token securely (`.yoto_refresh_token`)
- Add `.yoto_refresh_token` to `.gitignore`

### ❌ DON'T:

- Commit YOTO_SERVER_CLIENT_ID to git (even though it's not a secret)
- Share your Client ID publicly
- Use production credentials for development testing
- Skip adding YOTO_SERVER_CLIENT_ID and expect testing to work

## Summary

**YOTO_SERVER_CLIENT_ID is MANDATORY for any Yoto API testing.**

Without it, you can only work on:
- Documentation
- Infrastructure code
- Non-Yoto features

With it, you can:
- Test full Yoto integration
- Run all examples
- Develop new features
- Control your Yoto players

**Setup:** Add to Codespaces secrets → Restart Codespace → Start testing!

---

**See also:**
- `docs/CODESPACES_RAILWAY_SETUP.md` - Detailed setup guide
- `docs/YOTO_APP_REGISTRATION.md` - How to get Client ID
- `.devcontainer/setup.sh` - Verification script
