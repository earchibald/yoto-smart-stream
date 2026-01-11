# Railway Configuration Synchronization

## Overview

This document explains how railway.toml configuration changes are applied to Railway services and how to ensure volumes and other configurations are properly synced.

## Problem

Railway uses `railway.toml` to configure services (volumes, health checks, restart policies, etc.). However, changes to `railway.toml` are only applied when:

1. A new deployment occurs (via `railway up` or automatic GitHub deployment)
2. The service is manually redeployed in Railway Dashboard

If you update `railway.toml` but don't trigger a deployment, Railway continues using the old configuration.

## Solution

We've implemented automated detection and reconfiguration for `railway.toml` changes:

### 1. Automatic Sync via GitHub Actions

**Workflow: `.github/workflows/railway-config-sync.yml`**

This workflow automatically triggers when `railway.toml` is changed:

- **Triggers:**
  - Push to `main` branch with `railway.toml` changes → Syncs production
  - Push to `develop` branch with `railway.toml` changes → Syncs staging
  - Manual trigger via workflow_dispatch → Sync any environment

- **Actions:**
  - Validates `railway.toml` syntax
  - Detects volume configuration
  - Triggers redeployment to apply changes
  - Verifies configuration was applied
  - Provides verification steps in summary

### 2. Enhanced Deployment Workflow

**Workflow: `.github/workflows/railway-deploy.yml`**

Updated to check for railway.toml configuration on every deployment:

- Detects presence of `railway.toml`
- Checks for volume configuration
- Adds verification steps after deployment
- Provides Railway Dashboard links to confirm volumes

### 3. Manual Reconfiguration (if needed)

If automated workflows don't run or you need immediate reconfiguration:

#### Option A: Via GitHub Actions (Recommended)

1. Go to **Actions** tab in GitHub
2. Select **"Railway Configuration Sync"** workflow
3. Click **"Run workflow"**
4. Select environment (production/staging/development)
5. Click **"Run workflow"**

#### Option B: Via Railway CLI (Local/Manual)

```bash
# Install Railway CLI (if not already installed)
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project (if not already linked)
railway link

# Trigger redeployment to apply railway.toml changes
railway up -e production --detach

# Wait 30-60 seconds, then verify
railway status -e production
```

#### Option C: Via Railway Dashboard

1. Go to https://railway.app/dashboard
2. Select your project
3. Select the service
4. Click **"Deployments"** tab
5. Click **"Redeploy"** on the latest deployment
6. Railway will rebuild using current `railway.toml`

## Verifying Volume Configuration

After applying configuration, verify volumes were created:

### Via Railway Dashboard

1. Go to https://railway.app/dashboard
2. Select your project and service
3. Navigate to **Settings → Volumes**
4. Confirm volumes are listed:
   - **Name**: `data`
   - **Mount Path**: `/data`

### Via Railway CLI

```bash
# Check service configuration (volumes shown in output)
railway status -e production

# View service details
railway service -e production
```

### Via Application Logs

The application should log volume mount information on startup:

```bash
railway logs -e production --tail 50 | grep -i volume
railway logs -e production --tail 50 | grep "/data"
```

## Current Railway.toml Configuration

```toml
# railway.toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

# Persistent volumes - survive deployments and restarts
[[deploy.volumes]]
name = "data"
mountPath = "/data"

# Watch patterns
watchPatterns = [
    "yoto_smart_stream/**/*.py",
    "requirements.txt",
    "pyproject.toml"
]
```

### Volume Purpose

The `/data` volume is used for:
- **Yoto OAuth tokens** - Refresh tokens that persist across deployments
- **Application state** - Any persistent data needed between restarts
- **File storage** - User-uploaded files or generated content

## Troubleshooting

### Volumes Not Appearing

**Symptom:** Railway Dashboard doesn't show volumes in Settings → Volumes

**Solutions:**

1. **Check railway.toml syntax:**
   ```bash
   python -c "import toml; print(toml.load('railway.toml'))"
   ```

2. **Trigger manual redeployment:**
   - Use Railway Dashboard to redeploy
   - Or run: `railway up -e production`

3. **Check Railway logs for errors:**
   ```bash
   railway logs -e production --tail 100
   ```

4. **Verify environment:**
   - Volumes are per-environment
   - Production, staging, and PR environments each have separate volumes
   - Check you're looking at the correct environment

### Configuration Not Updating

**Symptom:** Changes to railway.toml don't take effect

**Cause:** Railway only reads railway.toml during build/deploy

**Solution:**

1. Commit and push railway.toml changes
2. Ensure workflow runs (check Actions tab)
3. Or manually trigger redeployment

### Volume Data Loss

**Symptom:** Data in /data volume disappears

**Causes:**
- Service was deleted and recreated (volumes are tied to service instance)
- Environment was deleted
- Volume was manually deleted in Railway Dashboard

**Prevention:**
- Don't delete services, use redeploy instead
- Implement application-level backups for critical data
- Use external storage (S3) for permanent data

## Best Practices

1. **Always commit railway.toml changes** before deploying
2. **Test in PR environments first** before deploying to production
3. **Verify volumes after configuration changes** using Dashboard or CLI
4. **Document volume usage** in your application code
5. **Implement health checks** that verify volume accessibility
6. **Back up critical data** from volumes periodically

## Related Documentation

- [Railway Platform Fundamentals](../.github/skills/railway-service-management/reference/platform_fundamentals.md) - Volume configuration details
- [Deployment Workflows](../.github/skills/railway-service-management/reference/deployment_workflows.md) - CI/CD patterns
- [Configuration Management](../.github/skills/railway-service-management/reference/configuration_management.md) - Environment variables and config

## Support

- **Railway Documentation**: https://docs.railway.app/reference/config-as-code
- **Railway Discord**: https://discord.gg/railway
- **GitHub Issues**: Report problems with workflows in this repository
