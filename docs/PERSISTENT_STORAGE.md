# Persistent Storage for Yoto Auth Tokens

## Overview

The Yoto Smart Stream application stores OAuth refresh tokens to maintain authentication with the Yoto API. These tokens need to persist across application restarts and redeployments to avoid requiring re-authentication.

## How It Works

### Railway Deployment (Production/Staging)

On Railway, the application uses a **persistent volume** mounted at `/data` to store the refresh token:

```toml
# railway.toml
[[deploy.volumes]]
name = "data"
mountPath = "/data"
```

**Token location:** `/data/.yoto_refresh_token`

### Local Development

In local development (without `RAILWAY_ENVIRONMENT_NAME` set), tokens are stored in the current directory:

**Token location:** `./.yoto_refresh_token`

## Configuration

The token file path is automatically determined based on your environment:

```python
# In yoto_smart_stream/config.py
@field_validator("yoto_refresh_token_file", mode="before")
@classmethod
def get_token_file_path(cls, v):
    # Check if running on Railway
    railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME")
    
    if railway_env:
        # Use persistent volume on Railway
        return Path("/data/.yoto_refresh_token")
    
    # Use local directory for development
    return Path(".yoto_refresh_token")
```

## Railway Volume Benefits

1. **Persistence:** Tokens survive deployments and instance restarts
2. **Environment Isolation:** Each Railway environment (production, staging, PR) has its own volume
3. **Automatic Management:** Railway handles volume lifecycle automatically

## Authentication Flow

### First Time Setup (Any Environment)

1. Deploy the application
2. Visit the web UI at `https://your-app.up.railway.app`
3. Click "Login" and follow the OAuth device flow
4. Enter the code at the Yoto login page
5. Token is saved to persistent storage

### Subsequent Restarts

- Application reads token from persistent storage
- Automatically refreshes if needed
- No re-authentication required

## Troubleshooting

### Token Not Persisting on Railway

**Symptom:** You need to re-authenticate after every deployment

**Solution:** Verify `railway.toml` contains the volume configuration:

```toml
[[deploy.volumes]]
name = "data"
mountPath = "/data"
```

### Token Not Found in Development

**Symptom:** "Refresh token file not found" error locally

**Solution:** Authenticate via the web UI or using the example scripts:

```bash
# Start the server
python -m yoto_smart_stream

# Visit http://localhost:8080 and login
```

### Permission Denied on /data

**Symptom:** `PermissionError: [Errno 13] Permission denied: '/data'`

**Why:** The `/data` directory doesn't exist or isn't writable in your environment

**Solution:**
- On Railway: Volume should be automatically created (verify railway.toml)
- In tests: The code handles this gracefully with try/except
- Locally: Should use current directory instead

## Volume Management

### Viewing Volume Contents (Railway CLI)

```bash
# Connect to the deployed service
railway run bash -e production

# Check if directory exists
ls -la /data

# View token (if authenticated)
cat /data/.yoto_refresh_token
```

### Clearing Tokens

To force re-authentication, delete the token file:

**On Railway:**
```bash
railway run rm /data/.yoto_refresh_token -e production
```

**Locally:**
```bash
rm .yoto_refresh_token
```

Then restart the application and log in again.

## Security Considerations

1. **Environment Isolation:** Each Railway environment has its own volume and token
2. **No Git Commit:** Tokens are never committed to version control (listed in `.gitignore`)
3. **File Permissions:** Token files are readable only by the application user
4. **Automatic Refresh:** Tokens are automatically refreshed before expiration

## Related Documentation

- [Railway Platform Fundamentals](../.github/skills/railway-service-management/reference/platform_fundamentals.md) - Volume concepts and best practices
- [Railway Deployment Guide](RAILWAY_DEPLOYMENT.md) - Full deployment setup
- [Yoto API Development](../.github/skills/yoto-smart-stream/SKILL.md) - OAuth and authentication details
