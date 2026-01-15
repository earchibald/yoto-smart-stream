---
name: yoto-smart-stream-service
description: Development and maintenance of the Yoto Smart Stream service. Covers authentication, service access, OAuth configuration, and general service operations.
---

# Yoto Smart Stream Service Skill

This skill covers development and maintenance of the Yoto Smart Stream service.

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
- **Tokens persist** - OAuth tokens and refresh tokens persist across deployments and service restarts
- **Single-tenant** - Service uses authenticated user's Yoto account for all device operations
- **Non-admin users** - Share the OAuth credentials (single-tenant mode); non-admin users cannot change credentials

**Flow:**
1. Login to Yoto Smart Stream with admin credentials
2. Navigate to Dashboard
3. Click "🔑 Connect Yoto Account" button
4. Complete Yoto OAuth device flow in browser
  a. Agents may not have the Yoto OAuth login credentials to perform this. In this case, the agent should pause, notify the user to perform this one-time step manually, and tell the user that the agent will wait for "continue" from the user to pick up where the agent left off.
5. Authorization complete - tokens stored and used for all subsequent operations

## Service Structure

- **Frontend:** FastAPI with Uvicorn
- **Database:** SQLite with persistent volume at `/data`
- **API:** RESTful endpoints for device control, streaming, user management
- **Real-time:** MQTT for device events and control

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

---

**For detailed deployment management, see** [railway-service-management skill](./../railway-service-management/SKILL.md)

**For Yoto API specifics, see** [yoto-api-development skill](./../yoto-api-development/SKILL.md)
