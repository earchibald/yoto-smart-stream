---
name: railway-service-management
description: Specialized knowledge for managing multi-environment Railway deployments, including development branch previews, production services, and full lifecycle management. Use this when setting up Railway infrastructure, configuring multi-environment workflows, or managing Railway deployments.
---

# Railway CPWTR Workflow (Assumed Defaults)

This skill is intentionally minimal. It encodes the default Railway workflow for this repo so you don’t need to restate it elsewhere. Use this CPWTR loop by default; reach for references only when you need deeper detail.

## Assumed Defaults

- Environments: `main` → production. Pull requests → PR Environments (automatic, ephemeral).
- Start: `uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port $PORT`.
- Healthcheck: `GET /api/health` with 100s timeout.
- Restart policy: `ON_FAILURE`, max retries 10.
- Volume mount: `/data` when required by a service.
- Logs/Deploys via Railway MCP tools (preferred), CLI as fallback.

Repo docs to consult when needed: docs/RAILWAY_DEPLOYMENT.md, docs/RAILWAY_QUICK_REF.md, docs/RAILWAY_PR_ENVIRONMENTS_NATIVE.md, docs/VALIDATING_PR_ENVIRONMENTS.md, docs/RAILWAY_CONFIG_SYNC.md, docs/REQUIRED_SECRETS.md.

## CPWTR Loop

0) Update version if relevant (`yoto_smart_stream/config.py` → `app_version`).

1) Commit
```bash
git add -A
git commit -m "<change> - bump to vX.Y.Z"
```

2) Push
```bash
git push origin <branch>
```

3) Wait (prefer MCP; fallback CLI)
- List latest deployments (MCP): list deployments (limit 1)
- Build logs (MCP): get logs type=build, lines=50
- Deploy logs (MCP): get logs type=deploy, lines=200
- Health: hit `/api/health` for the target environment

4) Test
- Production: https://<service>.up.railway.app/api/health
- PR: https://<service>-pr-{number}.up.railway.app/api/health
- Verify response includes current `version`.

5) Repeat
- Fix, commit, push. Re-check build → deploy → health.

## Fast Commands (CLI Fallback)

```bash
# One-time
npm i -g @railway/cli
railway login
railway link

# Observe
railway deployments list --json | head -n 60
railway logs -e production --follow

# Variables
railway variables -e production
railway variables set KEY=value -e production

# Manual redeploy (rare)
railway redeploy -e production
```

## Troubleshooting (Fast Path)

- Build failed → open build logs (MCP/CLI); fix imports/deps; rerun CPWTR.
- Deploy failed but build passed → open deploy logs; verify `uvicorn` target and healthcheck. Common fixes:
  - Use `Session` from `sqlalchemy.orm`, `require_auth` from `.user_auth`, `get_db` from `...database`.
  - Healthcheck path must be `/api/health`.
  - Ensure required env vars (see docs/REQUIRED_SECRETS.md).
- Health passed but container stopped → check restart policy/logs; transient restarts are normal during replacement.

## MCP Quick Actions

- List latest deployment: Railway MCP → list deployments (limit 1)
- Build logs: Railway MCP → get logs type=build, lines=100
- Deploy logs: Railway MCP → get logs type=deploy, lines=200
- Domain URL: Railway MCP → generate domain for service
- Variables: Railway MCP → list variables (env: production)
- Redeploy: Railway MCP → deploy current workspace (or use CLI fallback above)
- [💰 Cost Optimization](./reference/cost_optimization.md) - Resource management and billing optimization
- [🔧 Railway CLI & Scripts](./reference/cli_scripts.md) - Command-line tools, Railway MCP Server, and automation scripts
- [🔐 Secrets Management](./reference/secrets_management.md) - GitHub Secrets, Railway variables, and secure credential handling

## Quick Start

### Prerequisites

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login to Railway
railway login

# Link to existing project (or create new)
railway link
```

### Multi-Environment Setup Pattern

```bash
# Create project structure
railway init

# Set up environments
# - production: Connected to 'main' branch
# - pr-*: Ephemeral environments for pull requests (automatic via Railway)

# Configure environment variables
railway variables set KEY=value -e production

# Configure shared variables (for PR environments to inherit)
# Note: Shared variable type must be set via Railway Dashboard
```

## Architecture Patterns

### Branch-to-Environment Mapping

**Current Architecture:**
- `main` branch → `production` environment (stable, customer-facing)
- Pull requests → **Railway PR Environments** (automatic, ephemeral)

**Previously Used (Now Deprecated):**
- ~~`develop` branch → `staging` environment~~
- ~~`feature/*` branches → custom ephemeral environments~~

### Railway PR Environments

Railway's native PR Environments feature automatically creates ephemeral environments for pull requests:

**Key Features:**
- ✓ **Automatic creation** when PR is opened
- ✓ **Automatic deployment** on PR updates
- ✓ **Automatic destruction** when PR is closed/merged
- ✓ **Zero configuration** after initial setup
- ✓ **GitHub integration** with status checks
- ✓ **Shared Variables** - Can reference production's shared variables
- ✓ **Cost-effective** - only pay while PR is open

**Setup:**
```bash
# Enable in Railway Dashboard:
# Settings → GitHub → PR Environments → Enable
# - Base Environment: staging
# - Auto-Deploy: ✓
# - Auto-Destroy: ✓
# - Target Branches: main, develop
```

**Access PR Environment:**
```bash
# Automatic URL pattern
https://yoto-smart-stream-pr-{number}.up.railway.app

# Via CLI
railway status -e pr-123
railway logs -e pr-123
```

**See [PR Environments Reference](./reference/pr_environments.md) for complete documentation.**

### Service Architecture

```yaml
# Example: Web application with database
services:
  web:
    # Your FastAPI/Flask/Express application
    start_command: uvicorn main:app --host 0.0.0.0 --port $PORT
    healthcheck: /health
    
  postgres:
    # PostgreSQL database
    plugin: postgresql
    
  redis:
    # Redis for caching/sessions
    plugin: redis
```

## Secret Management Strategy

### GitHub Secrets (for CI/CD)

Store secrets in GitHub that are needed during CI/CD workflows:

```bash
# Add secrets via GitHub UI:
# Settings → Secrets and variables → Actions → New repository secret

# Required secrets for this project:
RAILWAY_TOKEN_PROD     # Railway API token for production deployments
RAILWAY_TOKEN_STAGING  # Railway API token for staging deployments
RAILWAY_TOKEN_DEV      # Railway API token for development deployments
YOTO_CLIENT_ID         # Yoto API client ID (from https://yoto.dev/)
```

**Obtaining Yoto Client ID:**
1. Go to https://yoto.dev/get-started/start-here/
2. Register application:
   - Type: Server-side / CLI Application
   - Grant Type: Device Code (OAuth 2.0 Device Authorization Grant)
   - Callback URLs: `http://localhost/oauth/callback` (placeholder - not used with Device Flow)
   - Logout URLs: `http://localhost/logout` (placeholder - not used)
3. Save your Client ID

**Note:** Yoto uses OAuth2 Device Flow which doesn't require callback/logout URLs. The registration form may ask for them, but use localhost placeholders - they won't be called. Device Flow authentication doesn't redirect to your application.
```

## Development Workflow: CPWTR

**CPWTR** stands for: **Commit, Push, Wait, Test, Repeat**

This is the standard development cycle when working with Railway deployments:

```bash
# 0. UPDATE VERSION - Bump the version in config.py
# Edit yoto_smart_stream/config.py and update app_version
# Example: app_version: str = "0.2.1"

# 1. COMMIT - Stage and commit your changes (including version bump)
git add .
git commit -m "Add feature X - bump to v0.2.1"

# 2. PUSH - Push to GitHub
git push origin feature-branch

# 3. WAIT - Wait for Railway to build and deploy
# Railway automatically deploys when:
# - PR is opened (PR Environments)
# - Commits are pushed to main (Production)
# - Commits are pushed to tracked branches
# in a sleep/check loop:
# Check deployment status
# - PREFER the railway MCP server tools
# - FALL BACK to using the railway CLI
# - FALL BACK to using the server health/ API
# Verify using the /api/health version
# If it's taking forever consider a failed deployment and check that with the available tools (MCP and railway cli to examine logs, deployment status)

# 4. TEST - Test the deployed changes
# if in develop we use
https://yoto-smart-stream-develop.up.railway.app/api/health
# in PR Environments we use
curl https://yoto-smart-stream-pr-{number}.up.railway.app/health
# Verify version in response: "version": "0.2.1"
# Or access via browser, test API endpoints, etc.

# 5. REPEAT - Make adjustments and start again
# If tests fail, fix code locally and repeat: version → commit → push → wait → test
# When our last objective is fulfilled and anything we introduced is clean, we are done.

# ENCOUNTERING ISSUES
# Unless otherwise instructed always return to CPWRT workflow with the next user query.
```

**Tips for efficient CPWTR:**
- Monitor deployments in real-time: `railway logs --follow`
- Check deployment status: `railway deployments list --json`
- Test locally before pushing when possible
- Use Railway's healthcheck endpoint to verify deployment success
- Keep PR commits focused to reduce test cycles

### Railway Environment Variables

Set environment-specific variables in Railway:

```bash
# Production environment (via Railway CLI or GitHub Actions)
railway variables set YOTO_CLIENT_ID="your_client_id" -e production
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}' -e production

# In GitHub Actions: use secrets syntax
# railway variables set YOTO_CLIENT_ID="${{ secrets.YOTO_CLIENT_ID }}" -e production

# Staging environment
railway variables set YOTO_CLIENT_ID="your_client_id" -e staging
railway variables set DEBUG=true -e staging
```

### Variable Hierarchy

1. **GitHub Secrets** - For CI/CD automation (RAILWAY_TOKEN, YOTO_CLIENT_ID)
2. **Railway Shared Variables** - Common across environments (LOG_LEVEL, REGION)
3. **Railway Environment Variables** - Per environment (DATABASE_URL, DEBUG)
4. **Railway Service Variables** - Per service in environment (PORT, WORKERS)

## Environment Configuration Strategy

### Development Workflow

```bash
# Local development - use .env file (never commit)
YOTO_CLIENT_ID=dev_client_id
YOTO_CLIENT_SECRET=dev_secret

# GitHub Actions - access GitHub Secrets
${{ secrets.YOTO_CLIENT_ID }}

# Railway deployment - use Railway variables
railway variables get YOTO_CLIENT_ID -e production
```

### Accessing Secrets in Code

```python
# main.py - FastAPI application
import os

# Railway automatically loads environment variables
YOTO_CLIENT_ID = os.getenv("YOTO_CLIENT_ID")
YOTO_CLIENT_SECRET = os.getenv("YOTO_CLIENT_SECRET")
DATABASE_URL = os.getenv("DATABASE_URL")

if not YOTO_CLIENT_ID:
    raise ValueError("YOTO_CLIENT_ID environment variable is required")
```

## Deployment Workflow

### Automated Deployments

1. **Commit to branch** → Railway detects change
2. **Build starts** → Docker build or Nixpacks detection
3. **Deploy** → New deployment goes live
4. **Health check** → Railway verifies service is healthy
5. **Rollback available** → Previous deployment kept for quick rollback

### Manual Deployments

```bash
# Deploy current directory to specific environment
railway up -e production

# Deploy with specific service
railway up -s web -e staging

# Redeploy last successful build
railway redeploy -e production
```

## Tracking Deployment Status via GitHub (Authoritative)

Railway automatically posts **GitHub commit status checks** for every deployment. This is the preferred way for agents to track deployment status:

```bash
# Query deployment status
gh api repos/OWNER/REPO/commits/COMMIT_SHA/status --jq '.statuses[] | select(.context | contains("railway"))'
```

**Status States:**
- `pending` → Deployment in progress
- `success` → Deployment succeeded and healthy
- `failure` → Build or deploy failed
- `error` → Health check failed

**In GitHub MCP workflows:**
1. Get commit SHA from PR via `mcp_github_pull_request_read`
2. Query GitHub API for status (not directly in MCP)
3. Check state to decide next action

**Complete documentation:** See [GitHub Deployment Status Checks](./reference/deployment_workflows.md#github-deployment-status-checks-authoritative-process) for agent patterns, timeouts, and integration examples.

## Database Management

### PostgreSQL Setup

```bash
# Add PostgreSQL to project
railway add --plugin postgresql

# Access database credentials
railway variables -e production | grep DATABASE_URL

# Connect to database
railway connect postgres -e production

# Run migrations
railway run -e production python manage.py migrate
```

### Backup Strategy

- Railway provides automatic daily backups for databases
- For critical production data, implement application-level backups
- Use `pg_dump` for manual backups before major migrations

## Monitoring & Observability

### Built-in Features

- **Logs**: Real-time log streaming via dashboard or CLI
- **Metrics**: CPU, memory, network usage per service
- **Deployments**: History of all deployments with rollback capability

### Log Access

```bash
# Stream logs from production
railway logs -e production

# Follow logs with filter
railway logs -e production --filter "ERROR"

# View logs for specific service
railway logs -s web -e production
```

## Best Practices

### ✅ DO:

- Store sensitive credentials in GitHub Secrets
- Use environment-specific configurations in Railway
- Implement health check endpoints
- Set up automatic deployments for main branches
- Use Railway's reference variables (`${{Postgres.DATABASE_URL}}`)
- Monitor deployment logs after each deploy
- Set resource limits appropriately
- Use Railway CLI for automation scripts
- Document environment setup in repository
- Rotate secrets regularly

### ❌ DON'T:

- Commit secrets to version control (use .env.example as template)
- Use production credentials in development
- Skip health check endpoints
- Deploy directly to production without staging
- Ignore deployment failures
- Over-provision resources unnecessarily
- Hardcode URLs or credentials
- Share production database between environments
- Store secrets in code comments or documentation

## Cost Optimization

### Resource Management

1. **Right-size your services** - Start small, scale based on metrics
2. **Use development environments wisely** - Sleep/destroy unused environments
3. **Leverage free tier** - Railway provides $5/month free credits
4. **Monitor usage** - Set up billing alerts
5. **Clean up old deployments** - Remove unused services and environments

### Scaling Strategy

```bash
# Horizontal scaling (multiple replicas)
railway scale replicas=3 -s web -e production

# Vertical scaling (increase resources)
# Adjust via Railway dashboard or railway.json
```

## Python/FastAPI Specific Configuration

### Recommended Setup

```python
# main.py - FastAPI application
from fastapi import FastAPI
import os

app = FastAPI()

# Railway provides PORT environment variable
PORT = int(os.getenv("PORT", 8000))

@app.get("/api/health")
async def health_check():
    """Health check endpoint for Railway"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
```

### Deployment Configuration

```toml
# railway.toml (optional, but recommended)
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/api/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

# Watch for changes to trigger rebuilds
watchPatterns = [
    "**/*.py",
    "requirements.txt",
    "pyproject.toml"
]

# Persistent volumes survive deployments and restarts
# Use for storing tokens, cache, or other stateful data
[[deploy.volumes]]
name = "data"
mountPath = "/data"
```

## Integration with CI/CD

### GitHub Actions Integration

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
        
      - name: Deploy to Railway
        run: railway up -e ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
          
      - name: Set Railway Variables
        run: |
          railway variables set YOTO_CLIENT_ID="${{ secrets.YOTO_CLIENT_ID }}" -e production
          railway variables set YOTO_CLIENT_SECRET="${{ secrets.YOTO_CLIENT_SECRET }}" -e production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Troubleshooting

### Common Issues

**Deployment Fails**
- Check build logs: `railway logs -e production`
- Verify Python version compatibility
- Ensure all dependencies in requirements.txt

**Database Connection Issues**
- Verify DATABASE_URL variable is set
- Check database service is running
- Confirm network connectivity between services

**Environment Variables Not Loading**
- Verify variables are set in correct environment
- Check for typos in variable names
- Ensure service is redeployed after variable changes

**Secrets Not Accessible**
- Verify GitHub Secrets are created in repository settings
- Check workflow has correct permissions
- Ensure Railway variables are synced from GitHub

**High Costs**
- Review resource usage in dashboard
- Scale down or remove unused environments
- Check for runaway processes or memory leaks

## Security Considerations

1. **Never commit credentials** - Use GitHub Secrets and Railway variables
2. **Rotate secrets regularly** - Especially API keys and tokens (YOTO_CLIENT_ID)
3. **Use least privilege** - Limit access to production environments
4. **Enable 2FA** - For Railway and GitHub account access
5. **Audit access** - Review team member permissions periodically
6. **Network security** - Use private networking for service-to-service communication
7. **Backup regularly** - Especially before major changes
8. **Separate secrets** - Use different credentials for dev/staging/production when possible

## Team Workflow

### Development Process

1. **Create feature branch** → Automatic PR environment spins up
2. **Develop & test** → Use PR environment for testing (with dev credentials)
3. **Merge to develop** → Deploys to staging environment
4. **QA & validation** → Test on staging (with staging credentials)
5. **Merge to main** → Deploys to production (with production credentials)
6. **Monitor** → Watch logs and metrics

### Environment Lifecycle

```bash
# Development branches
feature/add-auth → pr-123 environment (auto-created)
feature/new-ui → pr-124 environment (auto-created)

# Long-lived branches
develop → staging environment (persistent)
main → production environment (persistent)

# Cleanup
# PR environments destroyed after merge/close
# Manual cleanup: railway down -e pr-123
```

## Resources

- **Railway Documentation**: https://docs.railway.app/
- **Railway Templates**: https://railway.app/templates
- **Railway Discord**: https://discord.gg/railway
- **Railway Blog**: https://blog.railway.app/
- **Railway Status**: https://status.railway.app/
- **Railway CLI**: https://docs.railway.app/reference/cli
- **GitHub Secrets**: https://docs.github.com/en/actions/security-guides/encrypted-secrets

## Migration Guides

### From Heroku to Railway

- Railway offers similar workflow with better DX
- Environment variables map 1:1
- Database migration via `pg_dump` and `pg_restore`
- Update deployment scripts to use Railway CLI

### From Docker Compose to Railway

- Convert services to Railway services
- Map environment variables
- Set up service dependencies
- Configure networking

---

**When managing Railway deployments:**
1. Review the relevant reference documentation in the `reference/` folder
2. Set up GitHub Secrets for CI/CD automation (RAILWAY_TOKEN, YOTO_CLIENT_ID)
3. Follow the multi-environment patterns and best practices
4. Use Railway CLI for automation
5. Monitor deployments and costs regularly
6. Document your setup for team members
