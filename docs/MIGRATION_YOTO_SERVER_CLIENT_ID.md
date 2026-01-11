# Migration Guide: YOTO_CLIENT_ID → YOTO_SERVER_CLIENT_ID

## Overview

As of version 0.2.1, we've updated the environment variable name for the Yoto API client ID to better reflect its purpose and align with Yoto's naming conventions.

**What Changed:**
- **Old**: `YOTO_CLIENT_ID`
- **New**: `YOTO_SERVER_CLIENT_ID`

This change clarifies that this client ID is specifically for **server-side/CLI applications** using the OAuth2 device code flow, as documented at https://yoto.dev/api/post-oauth-device-code/.

## Backward Compatibility

**Good news!** This is a **non-breaking change**. The application continues to support `YOTO_CLIENT_ID` for backward compatibility.

**Priority:**
1. `YOTO_SERVER_CLIENT_ID` (preferred)
2. `YOTO_CLIENT_ID` (legacy, still supported)

If both are set, `YOTO_SERVER_CLIENT_ID` takes priority.

## Migration Steps

### For Local Development

#### Option 1: Update Your .env File (Recommended)

```bash
# Old .env
YOTO_CLIENT_ID=your_client_id_here

# New .env  
YOTO_SERVER_CLIENT_ID=your_client_id_here
```

#### Option 2: Keep Using Legacy Variable (Still Supported)

No changes required! Your existing `YOTO_CLIENT_ID` will continue to work.

### For Railway Deployments

#### Update Shared Variables

1. Go to Railway Dashboard → Your Project → Shared Variables
2. Add new variable: `YOTO_SERVER_CLIENT_ID` with your client ID value
3. Optionally remove old `YOTO_CLIENT_ID` variable (or leave it for backward compatibility)

#### Update GitHub Secrets (if applicable)

If you're using GitHub Actions for deployment:

```bash
# Add new secret
gh secret set YOTO_SERVER_CLIENT_ID --body "your_client_id_here"

# Optionally remove old secret
gh secret delete YOTO_CLIENT_ID
```

### For Docker/Container Deployments

Update your docker-compose.yml or Kubernetes manifests:

```yaml
# Old
environment:
  - YOTO_CLIENT_ID=your_client_id_here

# New (preferred)
environment:
  - YOTO_SERVER_CLIENT_ID=your_client_id_here
  
# Or keep both for backward compatibility
environment:
  - YOTO_SERVER_CLIENT_ID=your_client_id_here
  - YOTO_CLIENT_ID=your_client_id_here  # fallback
```

## Why This Change?

1. **Clarity**: The name `YOTO_SERVER_CLIENT_ID` explicitly indicates this is for server-side applications
2. **Consistency**: Aligns with Yoto's OAuth2 device flow documentation terminology
3. **Future-proofing**: Distinguishes from potential browser-based client IDs that might require different OAuth flows

## Getting Your Client ID

If you need to obtain a Yoto API client ID:

1. Visit https://dashboard.yoto.dev/
2. Create a new application
3. Copy your client ID
4. Set `YOTO_SERVER_CLIENT_ID` environment variable

## Testing Your Migration

Verify your configuration is working:

```bash
# Check that the application loads the client ID correctly
python -c "from yoto_smart_stream.config import get_settings; s = get_settings(); print(f'Client ID loaded: {s.yoto_client_id is not None}')"

# Run the authentication example
python examples/simple_client.py
```

The application logs will show which environment variable was used:

```
YOTO_SERVER_CLIENT_ID from env: your_client_id_here
YOTO_CLIENT_ID from env (deprecated): NOT SET
Loaded client_id: your_client_id_here
```

## Troubleshooting

### Both Variables Set, Wrong One Being Used

If you have both `YOTO_SERVER_CLIENT_ID` and `YOTO_CLIENT_ID` set:
- The application will use `YOTO_SERVER_CLIENT_ID` (it has priority)
- Check application startup logs to confirm which value is loaded

### Authentication Failing After Migration

1. Verify the new variable is set correctly:
   ```bash
   echo $YOTO_SERVER_CLIENT_ID
   ```

2. Check for typos in the variable name (it's case-sensitive)

3. Restart your application to pick up the new environment variable

4. Check the logs for the client ID configuration:
   ```
   YOTO_SERVER_CLIENT_ID from env: ...
   ```

### Railway/CI Still Using Old Variable

Make sure to:
1. Update Railway Shared Variables
2. Redeploy your application
3. Check Railway logs to verify the new variable is loaded

## Need Help?

- See [REQUIRED_SECRETS.md](REQUIRED_SECRETS.md) for all required environment variables
- Check [OAUTH_TOKEN_PERSISTENCE.md](OAUTH_TOKEN_PERSISTENCE.md) for authentication details
- Review [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) for common issues

## Summary

| Aspect | Details |
|--------|---------|
| **New Variable** | `YOTO_SERVER_CLIENT_ID` |
| **Old Variable** | `YOTO_CLIENT_ID` (still supported) |
| **Breaking Change?** | No - backward compatible |
| **Action Required** | Optional - update at your convenience |
| **Priority** | New variable takes precedence if both are set |
| **Where to Get ID** | https://dashboard.yoto.dev/ |
