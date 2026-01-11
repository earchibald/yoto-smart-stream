# Railway Deployment Guide

This guide covers deploying Yoto Smart Stream to Railway.app with automated CI/CD.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Initial Setup](#initial-setup)
- [Deployment Methods](#deployment-methods)
- [Environment Configuration](#environment-configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Overview

Yoto Smart Stream uses Railway.app for hosting with a simplified two-environment architecture:

- **Production Environment**: Auto-deploys from `main` branch
- **PR Environments**: Automatically created by Railway for each pull request

### Current Status

✅ **Active**: Production deployments from `main` branch  
✅ **Active**: Automatic PR environments for pull requests  
🚫 **Removed**: No staging or development environments

### Key Features

- **Automatic deployments** to production on push to `main`
- **Native PR Environments** - Railway automatically creates ephemeral environments for PRs
- **Shared Variables** - PR environments inherit `YOTO_SERVER_CLIENT_ID` from production
- **Zero-config PR lifecycle** - Environments automatically created/destroyed by Railway

## Prerequisites

### Required Tools

1. **Railway CLI** (installed automatically in devcontainer)
   ```bash
   npm i -g @railway/cli
   ```

2. **Railway Account** - Sign up at [railway.app](https://railway.app)

3. **GitHub Secrets** (for CI/CD)
   - `RAILWAY_TOKEN_PROD` - Railway API token for production deployments

### Railway Project Setup

1. Create a new Railway project: https://railway.app/new
2. Connect to GitHub repository: `earchibald/yoto-smart-stream`
3. Create the production environment
4. Enable Railway PR Environments feature in project settings
5. Configure `YOTO_SERVER_CLIENT_ID` as a Shared Variable in production environment

## Initial Setup

### 1. Get Railway Token

Generate a Railway API token for production deployments:

```bash
# Via Railway Dashboard
# 1. Go to https://railway.app/account/tokens
# 2. Click "Create Token"
# 3. Name it "GitHub Actions Production"
# 4. Copy the token
```

### 2. Configure GitHub Secrets

Add the production token to your GitHub repository:

```bash
# Go to: GitHub Repository → Settings → Secrets and variables → Actions

# Add this secret:
RAILWAY_TOKEN_PROD=your_railway_token_here
```

See [GITHUB_SECRETS_SETUP.md](../GITHUB_SECRETS_SETUP.md) for detailed instructions.

### 3. Configure YOTO_SERVER_CLIENT_ID in Railway

**Important**: `YOTO_SERVER_CLIENT_ID` is stored in Railway, not in GitHub Secrets.

1. Go to https://railway.app/dashboard
2. Select your project → production environment
3. Navigate to **Variables** tab
4. Add a new **Shared Variable**:
   - Name: `YOTO_SERVER_CLIENT_ID`
   - Value: Your Yoto Client ID from https://yoto.dev/
   - Type: **Shared Variable** (so PR environments can reference it)

### 4. Enable Railway PR Environments

1. Go to Railway project **Settings**
2. Navigate to **GitHub** section
3. Enable **PR Environments**
4. Configure:
   - Base Environment: `production`
   - Auto-deploy on PR updates: ✓
   - Auto-destroy on PR close: ✓
   - Target branches: `main`

### 5. Authenticate Railway CLI (for local testing)

```bash
# In your devcontainer or local environment
railway login

# Verify authentication
railway whoami
```

### 6. Link to Railway Project

```bash
# Link your local directory to Railway project
railway link

# Or create a new project
railway init
```

## Deployment Methods

### Method 1: Automated Production Deployment (Recommended)

**Via GitHub Actions** - Automatic deployment on push to `main` branch:

```bash
# 1. Create a PR with your changes
git checkout -b feature/my-feature
git add .
git commit -m "Your changes"
git push origin feature/my-feature

# 2. Open PR on GitHub targeting main branch
# Railway automatically creates a PR environment for testing

# 3. After PR approval and merge to main
# GitHub Actions automatically deploys to production
```

The production workflow will:
1. ✅ Run tests
2. ✅ Run linters (ruff, black)
3. ✅ Deploy to Railway production
4. ✅ Configure environment variables
5. ✅ Show deployment logs

### Method 2: PR Environments (Automatic)

**Railway Native Feature** - Automatic ephemeral environments for PRs:

```bash
# 1. Create and push a branch
git checkout -b feature/test-feature
git add .
git commit -m "Test feature"
git push origin feature/test-feature

# 2. Open a PR targeting main
# Railway automatically:
# - Creates pr-{number} environment
# - Deploys your code
# - Inherits YOTO_SERVER_CLIENT_ID from production (via shared variables)
# - Posts deployment status to PR

# 3. Access your PR environment at:
# https://yoto-smart-stream-pr-{number}.up.railway.app

# 4. When PR is closed/merged:
# Railway automatically destroys the environment
```

### Method 3: Railway CLI Direct (Advanced)

**For testing and debugging**:

```bash
# Deploy current directory to production (use with caution!)
railway up -e production

# View logs
railway logs -e production -f

# Check status
railway status -e production
```

## Environment Configuration

### Production Environment Variables

Railway needs these variables set in the production environment:

```bash
# Core Application
YOTO_SERVER_CLIENT_ID=your_client_id_here  # Set as Shared Variable
PORT=8080  # Auto-set by Railway
HOST=0.0.0.0

# Environment Settings
# Note: RAILWAY_ENVIRONMENT_NAME is automatically set by Railway ("production")
DEBUG=false
LOG_LEVEL=warning

# Optional
PUBLIC_URL=https://your-app.up.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}  # If using PostgreSQL
```

### PR Environment Variables

PR environments automatically inherit configuration from production:

- `RAILWAY_ENVIRONMENT_NAME`: Automatically set to `pr-{number}` by Railway
- `YOTO_SERVER_CLIENT_ID`: Set to `${{shared.YOTO_SERVER_CLIENT_ID}}` by GitHub Actions workflow
  - This references the Shared Variable from production
- Other variables can be configured per-PR if needed

### Setting Shared Variables in Railway

**Important**: For `YOTO_SERVER_CLIENT_ID` to work in PR environments, it must be a Shared Variable:

1. Go to Railway Dashboard → Your Project → production environment
2. Click "Variables" tab
3. Add/Edit `YOTO_SERVER_CLIENT_ID`
4. **Select "Shared Variable" type**
5. Save

This allows PR environments to reference it using `${{shared.YOTO_SERVER_CLIENT_ID}}`.

**⚠️ Warning**: If the shared variable is not properly configured:
- PR environments will fail to authenticate with the Yoto API
- You'll see authentication errors in PR environment logs
- The application may start but Yoto features won't work
- Fix by setting `YOTO_SERVER_CLIENT_ID` as a Shared Variable in production environment

### Setting Variables via CLI

```bash
# Set a variable in production
railway variables set DEBUG=false -e production
railway variables set LOG_LEVEL=warning -e production

# Set a shared variable (YOTO_SERVER_CLIENT_ID should be set via dashboard as "Shared Variable")
# Note: CLI doesn't support setting shared variable type, use dashboard

# View all variables
railway variables -e production

# Set variable in a PR environment (if needed for testing)
railway variables set DEBUG=true -e pr-123
```

### Setting Variables via Dashboard

1. Go to Railway Dashboard: https://railway.app/dashboard
2. Select your project
3. Choose environment (production or pr-{number})
4. Click "Variables" tab
5. Add/Edit variables
6. For `YOTO_SERVER_CLIENT_ID` in production: Select "Shared Variable" type

## Monitoring

### View Deployment Logs

```bash
# Stream production logs in real-time
railway logs -e production -f

# View last 100 lines
railway logs -e production --limit 100

# View PR environment logs
railway logs -e pr-123 -f

# Filter by error level
railway logs -e production --filter "ERROR"
```

### Check Deployment Status

```bash
# Get current deployment status
railway status -e production

# Check PR environment status
railway status -e pr-123

# Open Railway dashboard
railway open -e production
```

### Health Check

Your deployment includes a health check endpoint:

```bash
# Check production health
curl https://yoto-smart-stream-production.up.railway.app/api/health

# Check PR environment health
curl https://yoto-smart-stream-pr-123.up.railway.app/api/health

# Expected response:
{
  "status": "healthy",
  "environment": "production",
  ...
}
```

## Troubleshooting

### Deployment Fails

**Issue**: Deployment fails in Railway

**Solutions**:
1. Check build logs: `railway logs -e production`
2. Verify `railway.toml` is correct
3. Ensure all dependencies are in `requirements.txt`
4. Check Python version compatibility (3.9+)

### Tests Fail in GitHub Actions

**Issue**: GitHub Actions workflow fails at test step

**Solutions**:
1. Run tests locally: `pytest tests/ -v`
2. Check for missing dependencies
3. Review GitHub Actions logs in Actions tab
4. Ensure test fixtures are included in repo

### Railway CLI Not Found

**Issue**: `railway: command not found`

**Solutions**:
```bash
# Install Railway CLI
npm i -g @railway/cli

# Or in devcontainer, run setup script
bash .devcontainer/setup.sh

# Verify installation
which railway
railway --version
```

### Authentication Failed

**Issue**: `Not authenticated with Railway`

**Solutions**:
```bash
# For local development
railway login

# For CI/CD, verify RAILWAY_TOKEN_PROD secret
# Go to: GitHub Repository → Settings → Secrets and variables → Actions
# Ensure RAILWAY_TOKEN_PROD is set correctly

# Test token
RAILWAY_TOKEN=your_token railway whoami
```

### Environment Not Found

**Issue**: `Environment 'production' not found`

**Solutions**:
1. Create environment in Railway Dashboard
2. Link it to correct branch (main → production)
3. Verify project is linked: `railway status`

### Variables Not Loading in PR Environments

**Issue**: `YOTO_SERVER_CLIENT_ID` not available in PR environment

**Solutions**:
```bash
# 1. Verify YOTO_SERVER_CLIENT_ID is a Shared Variable in production
railway variables -e production
# It should show as a shared variable

# 2. Check PR environment has the reference set
railway variables -e pr-123
# Should show: YOTO_SERVER_CLIENT_ID=${{shared.YOTO_SERVER_CLIENT_ID}}

# 3. Ensure production environment is named exactly "production"
railway status

# 4. Trigger a redeploy of PR environment
railway redeploy -e pr-123
```

### PR Environment Not Created

**Issue**: Railway doesn't create PR environment automatically

**Solutions**:
1. Verify PR Environments feature is enabled in Railway Dashboard → Settings → GitHub
2. Ensure PR targets `main` branch (or configured target branch)
3. Check that base environment is set to `production`
4. Verify GitHub integration is connected properly

## Configuration Files

### railway.toml

The `railway.toml` file configures Railway deployment:

```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

# Persistent volume for OAuth tokens and other data
[[deploy.volumes]]
name = "data"
mountPath = "/data"
```

**Persistent Storage**: The `/data` volume ensures that Yoto OAuth refresh tokens persist across deployments and instance restarts. Without this volume, you would need to re-authenticate via OAuth after every deployment.

### .github/workflows/railway-deploy.yml

GitHub Actions workflow for automated production deployments:

- **Triggers**: Push to `main` branch, PRs to `main`
- **Jobs**: Test → Deploy to Production
- **Security**: Uses `RAILWAY_TOKEN_PROD` from GitHub Secrets
- **Variables**: Production uses Shared Variable for `YOTO_SERVER_CLIENT_ID`

### .github/workflows/railway-pr-checks.yml

GitHub Actions workflow for PR environment validation:

- **Triggers**: Pull requests to `main`
- **Purpose**: Validates PR environment after Railway creates it
- **Configuration**: Sets `YOTO_SERVER_CLIENT_ID` to reference production's shared variable

## Best Practices

### ✅ DO:

- Run tests locally before pushing: `pytest tests/`
- Use PR environments for testing features
- Monitor logs after deployment: `railway logs -e production -f`
- Keep secrets in Railway (as Shared Variables), not in GitHub Secrets
- Use Railway's native PR Environments feature
- Test in PR environment before merging to main
- Set appropriate LOG_LEVEL for production (warning or error)

### ❌ DON'T:

- Commit `.env` files or secrets to version control
- Deploy directly to production without testing in PR environment
- Skip the test step in deployments
- Store sensitive values in GitHub Secrets if Railway Shared Variables will work
- Ignore deployment failures or warnings
- Deploy with failing tests
- Manually create or manage PR environments (let Railway handle it)

## Next Steps

1. **Test PR Environment**:
   ```bash
   # Create a test branch and PR
   git checkout -b test/deployment-check
   git commit --allow-empty -m "Test PR environment"
   git push origin test/deployment-check
   # Open PR on GitHub - Railway will create environment automatically
   ```

2. **Monitor First Deployment**:
   ```bash
   # Watch production deployment
   railway logs -e production -f
   
   # Or watch PR environment
   railway logs -e pr-123 -f
   ```

3. **Verify Health Check**:
   ```bash
   # Production
   curl https://yoto-smart-stream-production.up.railway.app/api/health
   
   # PR environment
   curl https://yoto-smart-stream-pr-123.up.railway.app/api/health
   ```

4. **Set Up Monitoring**:
   - Configure alerts in Railway Dashboard
   - Monitor deployment notifications in GitHub PRs
   - Set up uptime monitoring (optional)

## Resources

- **Railway Documentation**: https://docs.railway.app/
- **Railway Dashboard**: https://railway.app/dashboard
- **Railway CLI Reference**: https://docs.railway.app/reference/cli
- **Railway PR Environments**: https://docs.railway.app/reference/pr-environments
- **GitHub Actions Documentation**: https://docs.github.com/actions
- **Railway Discord**: https://discord.gg/railway

## Support

- **Repository Issues**: https://github.com/earchibald/yoto-smart-stream/issues
- **Railway Support**: https://railway.app/help
- **GitHub Secrets Setup**: See [GITHUB_SECRETS_SETUP.md](../GITHUB_SECRETS_SETUP.md)

---

**Architecture Summary**: Production only (main branch) + automatic PR environments for all pull requests. No staging or development environments.
