# Private/Confidential Client OAuth Flow Implementation

## Overview

This implementation adds support for OAuth2 **confidential/private client flow** using a client secret, in addition to the existing public client device code flow.

## What Changed

### OAuth Flow Support

The application now supports **two OAuth2 flows**:

1. **Public Client Flow (Device Code)** - Default, no secret needed
   - Set only `YOTO_CLIENT_ID`
   - Uses OAuth2 Device Code Flow
   - Recommended for CLI/server apps
   - No client secret required

2. **Confidential Client Flow (Private)** - Uses client secret
   - Set both `YOTO_CLIENT_ID` and `YOTO_CLIENT_SECRET`
   - Uses OAuth2 with client credentials
   - More secure for server-to-server communication
   - Requires client secret from Yoto dashboard

### Configuration

#### Public Client (Device Code Flow)
```bash
# .env
YOTO_CLIENT_ID=your_client_id_here
# YOTO_CLIENT_SECRET is not set
```

#### Confidential Client (Private Flow)
```bash
# .env
YOTO_CLIENT_ID=your_client_id_here
YOTO_CLIENT_SECRET=your_client_secret_here
```

### New Files

- `yoto_smart_stream/core/oauth_client.py` - OAuth2 confidential client implementation

### Modified Files

- `yoto_smart_stream/config.py` - Added `yoto_client_secret` field
- `yoto_smart_stream/core/yoto_client.py` - Support for both OAuth flows
- `yoto_smart_stream/api/routes/auth.py` - Authentication routes updated
- `.env.example` - Added YOTO_CLIENT_SECRET documentation
- `tests/test_config.py` - Added tests for client secret

## Usage

### Getting Your Client Secret

1. Visit https://dashboard.yoto.dev/
2. Create or select your application
3. Copy both the **Client ID** and **Client Secret**

### Choosing a Flow

**Use Public Client Flow (Device Code) when:**
- Building CLI tools
- Building server-side apps without UI
- You don't have a client secret
- You want users to authenticate via browser

**Use Confidential Client Flow when:**
- You have a client secret from Yoto
- Building server-to-server integrations
- You need more secure authentication
- You have a secure place to store secrets

## Technical Details

### Flow Selection

The application automatically selects the OAuth flow based on configuration:

```python
# In yoto_smart_stream/core/yoto_client.py
if settings.yoto_client_secret:
    # Use confidential client flow
    self.oauth_client = OAuth2ConfidentialClient(...)
else:
    # Use public client device code flow
    self.manager = YotoManager(...)
```

### Token Refresh

**Public Client:**
```python
# Uses yoto_api library's built-in refresh
manager.check_and_refresh_token()
```

**Confidential Client:**
```python
# Uses custom OAuth2ConfidentialClient with client secret
token_data = oauth_client.refresh_token(refresh_token)
```

### Logging

The application logs which OAuth flow is being used:

```
YOTO_CLIENT_SECRET configured: YES/NO
OAuth Flow: Confidential Client (with secret) / Public Client (device code flow)
```

## Limitations

When using **confidential client flow**:
- Player status updates require YotoManager (not available)
- MQTT connections require YotoManager (not available)
- Device code flow still works but includes client secret

For full functionality, use **public client flow** (device code) without client secret.

## Security

- Client secrets are **never logged or exposed**
- Client secrets should be stored in:
  - Environment variables
  - Secret managers (Railway, AWS Secrets Manager, etc.)
  - Never commit to version control

## Testing

Run tests with:
```bash
# Test client secret configuration
pytest tests/test_config.py::TestYotoClientSecret -v

# Test all configuration
pytest tests/test_config.py -v
```

## Migration

No migration needed! Existing deployments continue to work:
- If you only have `YOTO_CLIENT_ID` set → Uses public client flow (existing behavior)
- If you add `YOTO_CLIENT_SECRET` → Automatically switches to confidential client flow

## References

- Yoto Device Code Flow: https://yoto.dev/authentication/headless-cli-auth/
- OAuth2 RFC 6749: https://tools.ietf.org/html/rfc6749
- OAuth2 Confidential Clients: https://oauth.net/2/client-types/
