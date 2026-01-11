# GitHub Copilot Workspace Network Configuration

## Overview

This document explains the network access configuration for GitHub Copilot Workspace to enable testing and validation of Railway deployments.

## Problem

GitHub Copilot Workspace has restricted network access by default for security reasons. This prevents the AI agent from directly testing Railway deployment URLs like:

- `https://yoto-smart-stream-production.up.railway.app`
- `https://yoto-smart-stream-staging.up.railway.app`
- `https://yoto-smart-stream-development.up.railway.app`
- `https://yoto-smart-stream-pr-{number}.up.railway.app`

## Solution

The network access configuration is defined in `.github/copilot-workspace.yml`, which allows Copilot Workspace to access specific domains.

### Configuration File

**Location:** `.github/copilot-workspace.yml`

This file contains:

```yaml
network:
  allowed_domains:
    # Railway.app platform URLs
    - "*.up.railway.app"         # All Railway deployment URLs
    - "railway.app"              # Railway dashboard and API
    - "backboard.railway.app"    # Railway GraphQL API
    
    # Yoto API URLs (for testing and development)
    - "api.yoto.io"              # Yoto REST API
    - "mqtt.yoto.io"             # Yoto MQTT broker
    - "yoto.dev"                 # Yoto developer portal
```

### Allowed Domains

The configuration allows access to:

1. **Railway Deployment URLs** (`*.up.railway.app`)
   - All environment deployments (production, staging, development)
   - PR-specific environments
   - Ephemeral environments

2. **Railway Platform APIs**
   - `railway.app` - Main platform and API endpoints
   - `backboard.railway.app` - GraphQL API for advanced operations

3. **Yoto APIs** (for development and testing)
   - `api.yoto.io` - REST API for player control and card management
   - `mqtt.yoto.io` - MQTT broker for real-time events
   - `yoto.dev` - Developer portal for app registration

## Railway URL Patterns

### Production Environment
- **URL:** `https://yoto-smart-stream-production.up.railway.app`
- **Trigger:** Automatic deployment on merge to `main` branch
- **Purpose:** Live production service

### Staging Environment
- **URL:** `https://yoto-smart-stream-staging.up.railway.app`
- **Trigger:** Automatic deployment on merge to `develop` branch
- **Purpose:** Pre-production testing

### Development Environment (Shared)
- **URL:** `https://yoto-smart-stream-development.up.railway.app`
- **Trigger:** Manual deployment via GitHub Actions
- **Purpose:** Shared testing environment with coordination

### PR Environments
- **URL Pattern:** `https://yoto-smart-stream-pr-{number}.up.railway.app`
- **Trigger:** Automatic deployment when PR is opened
- **Purpose:** Isolated testing for each pull request
- **Example:** PR #42 → `https://yoto-smart-stream-pr-42.up.railway.app`

## How It Works

1. **Configuration Loading**
   - GitHub Copilot Workspace reads `.github/copilot-workspace.yml` on startup
   - Allowed domains are added to the network allowlist
   - The AI agent can now make HTTP requests to these domains

2. **Testing Capabilities**
   - Copilot can curl endpoints to verify deployment health
   - Can check API responses and status codes
   - Can validate that deployments are functioning correctly
   - Can verify Railway platform API access

3. **Security**
   - Only explicitly allowed domains are accessible
   - Wildcard pattern `*.up.railway.app` covers all Railway deployments
   - Other domains remain blocked for security

## Usage Examples

With this configuration, Copilot Workspace can:

### Check Deployment Health

```bash
curl https://yoto-smart-stream-production.up.railway.app/api/health
curl https://yoto-smart-stream-pr-42.up.railway.app/health
```

### Validate API Endpoints

```bash
curl https://yoto-smart-stream-staging.up.railway.app/api/cards
curl https://yoto-smart-stream-development.up.railway.app/api/players
```

### Test Railway CLI Operations

```bash
# These commands can now access Railway's APIs
railway status
railway logs
railway list
```

### Verify Yoto API Access

```bash
curl https://api.yoto.io/v1/me
# (with proper authentication headers)
```

## Maintenance

### Adding New Domains

If you need to allow access to additional domains:

1. Edit `.github/copilot-workspace.yml`
2. Add the domain to the `allowed_domains` list
3. Include a comment explaining why it's needed
4. Commit and push the changes
5. Restart any active Copilot Workspace sessions

### Removing Domains

Only remove domains if:
- They're no longer used by the project
- The service has been shut down
- Security policy requires removal

## Related Documentation

- [Railway Deployment Guide](./RAILWAY_DEPLOYMENT.md)
- [Railway PR Environments](./RAILWAY_PR_ENVIRONMENTS_NATIVE.md)
- [Codespaces Railway Setup](./CODESPACES_RAILWAY_SETUP.md)
- [Railway Token Setup](./RAILWAY_TOKEN_SETUP.md)

## Troubleshooting

### Copilot Cannot Access Railway URLs

**Symptoms:**
- Network errors when curling Railway URLs
- "Domain not allowed" or similar errors
- Timeouts when accessing *.up.railway.app

**Solutions:**

1. **Verify configuration file exists:**
   ```bash
   ls -la .github/copilot-workspace.yml
   ```

2. **Check YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('.github/copilot-workspace.yml'))"
   ```

3. **Restart Copilot Workspace session:**
   - Stop the current session
   - Start a new session to reload configuration

4. **Check wildcard pattern:**
   - Ensure `*.up.railway.app` is in the allowed_domains list
   - Verify no typos in the domain name

### Configuration Not Taking Effect

**Possible causes:**

1. **YAML syntax error** - Validate the file
2. **Session not restarted** - Restart Copilot Workspace
3. **Wrong file location** - Must be in `.github/` directory
4. **Cache issues** - Clear cache and restart

## Best Practices

1. **Use wildcards carefully** - `*.up.railway.app` is safe as it's Railway's official subdomain
2. **Document all domains** - Add comments explaining why each domain is allowed
3. **Review periodically** - Remove unused domains to maintain security
4. **Test after changes** - Verify configuration works after modifications
5. **Keep it minimal** - Only allow domains actually needed for development/testing

## Security Considerations

- **Wildcard domains:** The `*.up.railway.app` wildcard is safe because:
  - It's Railway's official deployment subdomain
  - All deployments go through Railway's security
  - Only applies to Railway infrastructure

- **API domains:** Yoto API domains are allowed because:
  - Required for development and testing
  - All API calls require authentication
  - No sensitive data exposed without auth

- **Railway platform:** Access to `railway.app` and `backboard.railway.app` allows:
  - Deployment status checks
  - Log retrieval
  - Environment management
  - Requires valid RAILWAY_TOKEN for operations

---

**Last Updated:** 2026-01-11  
**Configuration Version:** 1.0.0  
**Maintained By:** GitHub Copilot Workspace
