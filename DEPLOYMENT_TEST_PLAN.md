> **⚠️ THIS DOCUMENT IS OBSOLETE**
> 
> The deployment process has been simplified. Please see:
> - [GitHub Secrets Setup](GITHUB_SECRETS_SETUP.md) - Configure deployment
> - [Railway Deployment Guide](docs/RAILWAY_DEPLOYMENT.md) - Current deployment process
> - [Railway PR Environments](docs/RAILWAY_PR_ENVIRONMENTS_NATIVE.md) - PR environment usage
> 
> The content below is kept for historical reference only.
> 
> ---
> 
# Deployment Test Plan for YOTO_SERVER_CLIENT_ID Fix

## Issue Fixed
YOTO_SERVER_CLIENT_ID environment variable was not being passed to Railway deployments correctly. Environment variables were being set AFTER the service started, causing the service to start without the required YOTO_SERVER_CLIENT_ID.

## Changes Made
Updated all Railway deployment workflows to set environment variables (including YOTO_SERVER_CLIENT_ID) BEFORE running `railway up`:

1. `.github/workflows/railway-development-shared.yml`
2. `.github/workflows/auto-deploy-pr-to-dev.yml`
3. `.github/workflows/railway-deploy.yml` (staging and production)
4. `.github/workflows/railway-pr-environments.yml`
5. `.github/workflows/railway-copilot-environments.yml`

## Testing Steps

### Option 1: Deploy to Development via GitHub Actions

1. Go to the GitHub repository: https://github.com/earchibald/yoto-smart-stream
2. Navigate to **Actions** tab
3. Select **"Railway Development (Shared Environment)"** workflow
4. Click **"Run workflow"**
5. Fill in the inputs:
   - **branch**: `copilot/fix-yoto-client-id-deployment`
   - **session_id**: `copilot-test-yoto-client-id`
   - **action**: `acquire-and-deploy`
   - **force**: `false` (unless development is locked)
6. Click **"Run workflow"** to start deployment

### Option 2: Check Auto-Deploy Workflow

If you merge this PR or push to a branch that triggers auto-deploy:
1. Go to **Actions** tab
2. Find the running workflow
3. Monitor the deployment progress

## Verification Steps

Once deployment completes, verify YOTO_SERVER_CLIENT_ID is available:

### 1. Check Deployment Logs in GitHub Actions

In the workflow run:
- Look for the "Deploy to Railway Development" step
- Verify it shows: "Setting YOTO_SERVER_CLIENT_ID..."
- Ensure no warning: "⚠️ Warning: YOTO_SERVER_CLIENT_ID not set in GitHub secrets"

### 2. Check Railway Dashboard

1. Go to Railway dashboard: https://railway.app
2. Select the Yoto Smart Stream project
3. Select "development" environment
4. Click on the service
5. Go to **Variables** tab
6. Verify `YOTO_SERVER_CLIENT_ID` is present and has a value

### 3. Check Application Logs in Railway

1. In Railway dashboard, go to the development service
2. Click on **Deployments** tab
3. Select the latest deployment
4. View the logs
5. Look for startup logs that reference YOTO API initialization

Expected log messages on successful startup:
```
Starting Yoto Smart Stream v0.2.0
Environment: development
✓ Yoto API connected successfully
✓ MQTT connected successfully
```

If YOTO_SERVER_CLIENT_ID is missing, you'll see:
```
⚠ Warning: Could not initialize Yoto API: [error message about client ID]
  Some endpoints may not work until authentication is completed.
```

Expected behavior:
- ✅ Logs show "✓ Yoto API connected successfully"
- ✅ No errors about missing or invalid YOTO_SERVER_CLIENT_ID
- ✅ Service starts successfully
- ✅ uvicorn server is running and accepting connections

### 4. Test Health Endpoint

```bash
curl https://yoto-smart-stream-development.up.railway.app/health
```

Expected response should include:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "environment": "development",
  "yoto_api": "connected",
  "mqtt_enabled": true
}
```

If YOTO_SERVER_CLIENT_ID is not set, you might see:
```json
{
  "status": "healthy",
  "version": "0.2.0", 
  "environment": "development",
  "yoto_api": "not_configured"
}
```

### 5. Check Application Config

Test the config endpoint (if available):
```bash
curl https://yoto-smart-stream-development.up.railway.app/config
```

Or check via logs that the application loaded YOTO_SERVER_CLIENT_ID successfully.

## Success Criteria

✅ YOTO_SERVER_CLIENT_ID is set in Railway environment variables BEFORE deployment starts
✅ Service starts without errors related to missing YOTO_SERVER_CLIENT_ID
✅ Health check endpoint responds correctly
✅ Application logs show successful configuration loading
✅ No race conditions or timing issues with environment variable availability

## Rollback Plan

If issues occur:
1. The changes are in workflow files only, no application code changed
2. Revert the workflow changes by reverting the commit
3. Or manually set YOTO_SERVER_CLIENT_ID in Railway dashboard as a workaround

## Additional Notes

- The fix applies to ALL environments: development, staging, production, PR previews, and Copilot environments
- Environment variables in Railway are persistent - setting them multiple times is safe
- The deployment script `scripts/railway_ephemeral_env.sh` also sets variables before deploying, providing redundancy
