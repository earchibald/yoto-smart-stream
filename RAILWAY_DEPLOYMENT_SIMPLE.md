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
# Railway Deployment - Development Only Workflow

## Current Simplified Workflow

**Focus**: PR work deploys **only to the `development` Railway environment**

Staging and production deployments are not needed yet because:
- There's no `develop` branch for staging to use
- Production deployment can wait until after staging is set up

## How to Deploy This PR to Development

### Step 1: Configure GitHub Secret

The `RAILWAY_TOKEN_DEV` secret must be configured for GitHub Actions to deploy.

**Add the secret**:
1. Go to: https://github.com/earchibald/yoto-smart-stream/settings/secrets/actions
2. Click "New repository secret"
3. Name: `RAILWAY_TOKEN_DEV`
4. Value: Your Railway API token from https://railway.app/account/tokens
5. Click "Add secret"

### Step 2: Trigger Deployment

Once the secret is configured, deploy using GitHub Actions:

**Via GitHub UI**:
1. Go to the **Actions** tab
2. Select "Railway Development (Shared Environment)" workflow
3. Click "Run workflow" button
4. Fill in:
   - Branch: `copilot/build-server-and-setup-railway`
   - session_id: `copilot-build-server-railway`
   - action: `acquire-and-deploy`
5. Click "Run workflow"
6. Monitor the deployment in the Actions tab

**Via GitHub CLI** (if you have `gh` installed):
```bash
gh workflow run "Railway Development (Shared Environment)" \
  --ref copilot/build-server-and-setup-railway \
  --field session_id="copilot-build-server-railway" \
  --field action="acquire-and-deploy"
```

### Step 3: Verify Deployment

After deployment completes:

```bash
# Check health endpoint
curl https://yoto-smart-stream-development.up.railway.app/health

# View API documentation
open https://yoto-smart-stream-development.up.railway.app/docs
```

## Environment Details

- **Railway Environment**: `development`
- **URL**: https://yoto-smart-stream-development.up.railway.app
- **GitHub Secret**: `RAILWAY_TOKEN_DEV`
- **Entry Point**: `uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port $PORT`

## Optional Configuration

### YOTO_SERVER_CLIENT_ID

To enable full Yoto API functionality:
1. Get Client ID from https://yoto.dev/
2. Add as GitHub Secret: `YOTO_SERVER_CLIENT_ID`
3. Re-run deployment (it will automatically inject into Railway)

## What About Staging and Production?

These are configured but **not used yet**:

- **Staging**: Would deploy from `develop` branch (doesn't exist yet)
  - Secret needed: `RAILWAY_TOKEN_STAGING`
  - Environment: `staging`
  
- **Production**: Would deploy from `main` branch (manual approval required)
  - Secret needed: `RAILWAY_TOKEN_PROD`
  - Environment: `production`

**For now, focus only on `development` deployment.**

## Quick Reference

| What | Where | Value |
|------|-------|-------|
| Secret Name | GitHub Secrets | `RAILWAY_TOKEN_DEV` |
| Secret Location | Repo Settings → Secrets → Actions | https://github.com/earchibald/yoto-smart-stream/settings/secrets/actions |
| Workflow | GitHub Actions | "Railway Development (Shared Environment)" |
| Environment | Railway | `development` |
| Deployment URL | Railway | https://yoto-smart-stream-development.up.railway.app |

## Troubleshooting

**"Secret not found" error**:
- Verify secret name is exactly `RAILWAY_TOKEN_DEV` (all caps)
- Check it's added as a **repository secret**, not a Codespace secret

**Workflow not visible**:
- Check the Actions tab is enabled in repository settings
- Verify you have workflow run permissions

**Deployment fails**:
- Check Railway logs: `railway logs -e development` (if you have CLI access)
- Check GitHub Actions logs for error details
- Verify Railway project has a `development` environment

## Summary

To deploy this PR to development:
1. ✅ Add `RAILWAY_TOKEN_DEV` secret
2. ✅ Run "Railway Development (Shared Environment)" workflow
3. ✅ Monitor deployment in Actions tab
4. ✅ Verify at https://yoto-smart-stream-development.up.railway.app/health

No staging or production setup needed yet!
