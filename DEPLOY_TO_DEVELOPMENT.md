# Quick Deployment to Railway Development Environment

## Overview

**Current Workflow**: PR work deploys **only to the development Railway environment**. Staging and production deployments are not configured yet (there's no `develop` branch for staging to use).

## Prerequisites Checklist

Before deploying to Railway development, ensure:

- [x] Railway CLI installed (`npm i -g @railway/cli`)
- [x] Production server code is ready (on branch `copilot/build-server-and-setup-railway`)
- [ ] `RAILWAY_TOKEN_DEV` configured as GitHub Secret
- [ ] `YOTO_CLIENT_ID` configured as GitHub Secret (optional for basic deployment)
- [ ] Railway project has a `development` environment configured

## Deployment Options

### Option 1: Deploy via GitHub Actions (Recommended)

This PR branch will automatically deploy when certain conditions are met:

1. **For Copilot branches**: The workflow `.github/workflows/railway-copilot-environments.yml` can deploy copilot branches
2. **For development**: Use the shared development workflow

**To trigger deployment manually:**

```bash
# Via GitHub CLI (if available)
gh workflow run "Railway Development (Shared Environment)" \
  --field session_id="copilot-build-server" \
  --field action="acquire-and-deploy"
```

Or use the GitHub Actions UI:
1. Go to Actions tab
2. Select "Railway Development (Shared Environment)" workflow
3. Click "Run workflow"
4. Enter session ID (e.g., `copilot-build-server`)
5. Select action: `acquire-and-deploy`

### Option 2: Deploy via Railway CLI (From Codespace)

From a GitHub Codespace with `RAILWAY_TOKEN` configured:

```bash
# Install Railway CLI (if not already installed)
npm i -g @railway/cli

# Deploy to development environment
./scripts/railway_ephemeral_env.sh deploy development

# Or deploy directly with Railway CLI
railway up -e development
```

### Option 3: Deploy via Railway CLI (Local with Token)

If you have the Railway token:

```bash
# Export the token
export RAILWAY_TOKEN="your_token_here"

# Deploy to development
railway up -e development

# Set environment variables
railway variables set YOTO_CLIENT_ID="your_client_id" -e development
railway variables set ENVIRONMENT="development" -e development
railway variables set DEBUG="true" -e development
```

## Current Deployment Status

**Branch**: `copilot/build-server-and-setup-railway`  
**Target Environment**: `development` (Railway)
**Status**: Ready for deployment  
**Entry Point**: `uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port $PORT`

**Note**: This PR only deploys to development. Staging/production workflows exist but are not used yet (no `develop` branch for staging trigger).

## Required Environment Variables in Railway

Set these in Railway dashboard or via CLI before first deployment:

```bash
# Required
YOTO_CLIENT_ID="your_yoto_client_id"

# Optional (for production server)
PUBLIC_URL="https://yoto-smart-stream-development.up.railway.app"
ENVIRONMENT="development"
DEBUG="true"
LOG_LEVEL="DEBUG"
```

## Verification After Deployment

Once deployed, verify the deployment:

```bash
# Check health endpoint
curl https://yoto-smart-stream-development.up.railway.app/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "0.2.0",
#   "environment": "development",
#   "yoto_api": "connected",
#   "mqtt_enabled": true,
#   "audio_files": 0
# }

# Check API documentation
open https://yoto-smart-stream-development.up.railway.app/docs
```

## Troubleshooting

### No RAILWAY_TOKEN_DEV Available

**Issue**: Cannot deploy because RAILWAY_TOKEN_DEV is not set.

**Solutions**:
1. Add `RAILWAY_TOKEN_DEV` to GitHub Secrets (for GitHub Actions deployment)
2. Set `RAILWAY_TOKEN` in environment (for Codespace/local deployment)
3. Run `railway login` for interactive authentication (local only)

### Environment Doesn't Exist

**Issue**: Railway environment "development" not found.

**Solution**: Create the environment in Railway dashboard:
1. Go to Railway project
2. Click "New Environment"
3. Name it "development"
4. Configure as persistent environment

### Deployment Fails

**Issue**: Deployment starts but fails.

**Solutions**:
1. Check Railway logs: `railway logs -e development`
2. Verify all required env vars are set
3. Check `railway.toml` configuration
4. Ensure Python dependencies are correct in `requirements.txt`

## Next Steps After Deployment

1. ✅ Verify health endpoint responds
2. ✅ Check `/docs` for API documentation
3. ✅ Test player listing endpoint
4. ✅ Configure PUBLIC_URL for audio streaming
5. ✅ Add sample audio files for testing
6. ✅ Test with real Yoto devices

---

**Note**: This branch (`copilot/build-server-and-setup-railway`) is configured to deploy to the `development` Railway environment only. The workflow is triggered manually via GitHub Actions. Staging and production deployments are not configured yet.
