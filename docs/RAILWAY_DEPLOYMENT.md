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

Yoto Smart Stream uses Railway.app for hosting with the following architecture:

- **Staging Environment**: Auto-deploys from `develop` branch
- **Production Environment**: Currently **DISABLED** - awaiting approval for production deployments
- **Development Environment**: Manual deployments for testing

### Current Status

✅ **Active**: Staging deployments from `develop` branch  
⏸️ **Disabled**: Production deployments from `main` branch  
✅ **Available**: Manual deployments to development environment

## Prerequisites

### Required Tools

1. **Railway CLI** (installed automatically in devcontainer)
   ```bash
   npm i -g @railway/cli
   ```

2. **Railway Account** - Sign up at [railway.app](https://railway.app)

3. **GitHub Secrets** (for CI/CD)
   - `RAILWAY_TOKEN` - Railway API token
   - `YOTO_CLIENT_ID` - Yoto API client ID (optional for staging)

### Railway Project Setup

1. Create a new Railway project: https://railway.app/new
2. Connect to GitHub repository: `earchibald/yoto-smart-stream`
3. Create environments:
   - `staging` - connected to `develop` branch
   - `development` - for manual testing
   - `production` - (not yet active)

## Initial Setup

### 1. Get Railway Token

Generate a Railway API token for deployments:

```bash
# Via Railway Dashboard
# 1. Go to https://railway.app/account/tokens
# 2. Click "Create Token"
# 3. Name it "GitHub Actions" or "CI/CD"
# 4. Copy the token
```

### 2. Configure GitHub Secrets

Add secrets to your GitHub repository:

```bash
# Go to: GitHub Repository → Settings → Secrets and variables → Actions

# Add these secrets:
RAILWAY_TOKEN=your_railway_token_here
YOTO_CLIENT_ID=your_yoto_client_id_here  # Optional
```

### 3. Authenticate Railway CLI (for local deployments)

```bash
# In your devcontainer or local environment
railway login

# Verify authentication
railway whoami
```

### 4. Link to Railway Project

```bash
# Link your local directory to Railway project
railway link

# Or create a new project
railway init
```

## Deployment Methods

### Method 1: Automated Deployment (Recommended)

**Via GitHub Actions** - Automatic deployment on push to `develop` branch:

```bash
# 1. Make your changes
git checkout develop
git add .
git commit -m "Your changes"

# 2. Push to trigger deployment
git push origin develop

# 3. Monitor in GitHub Actions tab
# https://github.com/earchibald/yoto-smart-stream/actions
```

The workflow will:
1. ✅ Run tests
2. ✅ Run linters (ruff, black)
3. ✅ Deploy to Railway staging
4. ✅ Configure environment variables
5. ✅ Show deployment logs

### Method 2: Manual Deployment (Development)

**From Devcontainer** - Use the deployment script:

```bash
# Deploy to staging
./scripts/deploy.sh staging

# Deploy to development
./scripts/deploy.sh development

# Dry run (see what would happen)
./scripts/deploy.sh staging --dry-run

# NOTE: Production deployments are blocked
./scripts/deploy.sh production  # ❌ Will fail
```

### Method 3: Railway CLI Direct

**For Advanced Users**:

```bash
# Deploy current directory to staging
railway up -e staging

# Deploy specific service
railway up -s web -e staging

# Watch deployment logs
railway logs -e staging -f
```

## Environment Configuration

### Required Environment Variables

Railway needs these variables set in each environment:

```bash
# Core Application
YOTO_CLIENT_ID=your_client_id_here
PORT, 8080)  # Auto-set by Railway
HOST=0.0.0.0

# Environment Settings
# Note: RAILWAY_ENVIRONMENT_NAME is automatically set by Railway
# (e.g., "staging", "production", "pr-123")
DEBUG=true  # for non-production
LOG_LEVEL=DEBUG  # or INFO for production

# Optional
PUBLIC_URL=https://your-app.up.railway.app
DATABASE_URL=${{Postgres.DATABASE_URL}}  # If using PostgreSQL
```

### Setting Variables via CLI

```bash
# Set a variable in staging
railway variables set YOTO_CLIENT_ID="your_id" -e staging

# Set multiple variables
railway variables set DEBUG=true LOG_LEVEL=DEBUG -e staging

# View all variables
railway variables -e staging

# Use Railway service references
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}' -e staging
```

### Setting Variables via Dashboard

1. Go to Railway Dashboard: https://railway.app/dashboard
2. Select your project
3. Choose environment (staging/development)
4. Click "Variables" tab
5. Add/Edit variables

## Monitoring

### View Deployment Logs

```bash
# Stream logs in real-time
railway logs -e staging -f

# View last 100 lines
railway logs -e staging --limit 100

# Filter by error level
railway logs -e staging --filter "ERROR"
```

### Check Deployment Status

```bash
# Get current deployment status
railway status -e staging

# List all deployments
railway list -e staging

# Open Railway dashboard
railway open -e staging
```

### Health Check

Your deployment includes a health check endpoint:

```bash
# Check application health
curl https://your-app.up.railway.app/health

# Expected response:
{
  "status": "healthy",
  "yoto_api": "connected",
  "audio_files": 0
}
```

## Troubleshooting

### Deployment Fails

**Issue**: Deployment fails in Railway

**Solutions**:
1. Check build logs: `railway logs -e staging`
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

# For CI/CD, verify RAILWAY_TOKEN secret
# Go to: GitHub Repository → Settings → Secrets and variables → Actions
# Ensure RAILWAY_TOKEN is set correctly

# Test token
RAILWAY_TOKEN=your_token railway whoami
```

### Environment Not Found

**Issue**: `Environment 'staging' not found`

**Solutions**:
1. Create environment in Railway Dashboard
2. Link it to correct branch (develop → staging)
3. Verify project is linked: `railway status`

### Variables Not Loading

**Issue**: Environment variables not available in application

**Solutions**:
```bash
# Verify variables are set
railway variables -e staging

# Re-set variables
railway variables set YOTO_CLIENT_ID="your_id" -e staging

# Trigger a redeploy
railway redeploy -e staging
```

### Production Deployments Blocked

**Issue**: Trying to deploy to production

**Expected Behavior**: This is intentional! Production deployments are currently disabled.

**To Enable** (when ready):
1. Get approval for production deployments
2. Update `.github/workflows/railway-deploy.yml`
3. Add production deployment job
4. Configure production environment in Railway
5. Test thoroughly in staging first

## Configuration Files

### railway.toml

The `railway.toml` file configures Railway deployment:

```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn examples.basic_server:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

### .github/workflows/railway-deploy.yml

GitHub Actions workflow for automated deployments:

- **Triggers**: Push to `develop` branch, PRs to `develop`/`main`
- **Jobs**: Test → Deploy to Staging
- **Security**: Uses GitHub Secrets for sensitive data

## Best Practices

### ✅ DO:

- Run tests locally before pushing: `pytest tests/`
- Use staging environment for testing: `./scripts/deploy.sh staging`
- Monitor logs after deployment: `railway logs -e staging -f`
- Keep secrets in GitHub Secrets, not in code
- Use `--dry-run` to preview deployments
- Document environment-specific configuration
- Set appropriate LOG_LEVEL for each environment

### ❌ DON'T:

- Commit `.env` files or secrets to version control
- Deploy directly to production without testing
- Skip the test step in deployments
- Use production credentials in staging/development
- Ignore deployment failures or warnings
- Deploy with failing tests

## Next Steps

1. **Test Staging Deployment**:
   ```bash
   ./scripts/deploy.sh staging --dry-run
   ./scripts/deploy.sh staging
   ```

2. **Monitor First Deployment**:
   ```bash
   railway logs -e staging -f
   ```

3. **Verify Health Check**:
   ```bash
   curl https://your-app.up.railway.app/health
   ```

4. **Set Up Monitoring**:
   - Configure alerts in Railway Dashboard
   - Set up uptime monitoring (optional)

5. **Plan Production**:
   - Review staging thoroughly
   - Document production requirements
   - Request approval for production deployments
   - Create production runbook

## Resources

- **Railway Documentation**: https://docs.railway.app/
- **Railway Dashboard**: https://railway.app/dashboard
- **Railway CLI Reference**: https://docs.railway.app/reference/cli
- **GitHub Actions Documentation**: https://docs.github.com/actions
- **Railway Discord**: https://discord.gg/railway

## Support

- **Repository Issues**: https://github.com/earchibald/yoto-smart-stream/issues
- **Railway Support**: https://railway.app/help
- **Deployment Script**: `./scripts/deploy.sh --help`

---

**Remember**: Production deployments are currently disabled. Only staging and development environments are active.
