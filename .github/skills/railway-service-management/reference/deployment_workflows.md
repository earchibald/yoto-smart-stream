# Deployment Workflows for Railway

## Table of Contents

- [Quick Fixes: Env Linking + Static Cache Busting](#quick-fixes-env-linking--static-cache-busting)
- [Railway Native PR Environments](#railway-native-pr-environments)
- [Automated Deployment via GitHub Integration](#automated-deployment-via-github-integration)
- [GitHub Actions Integration](#github-actions-integration)
- [Manual Deployment Workflows](#manual-deployment-workflows)
- [Checklist](#checklist)
- [Database Migration Workflows](#database-migration-workflows)
- [Rollback Workflows](#rollback-workflows)
- [Environment-Specific Deployment Strategies](#environment-specific-deployment-strategies)
- [Monitoring & Notifications](#monitoring--notifications)
- [Deployment Checklist](#deployment-checklist)
- [Railway.toml Configuration Synchronization](#railwaytoml-configuration-synchronization)
- [GitHub Deployment Status Checks](#github-deployment-status-checks-authoritative-process)
- [Best Practices](#best-practices)

## Overview

This guide covers automated deployment workflows for Railway, including GitHub Actions integration, CI/CD pipelines, Railway's native PR Environments, and deployment automation strategies.

## Quick Fixes: Env Linking + Static Cache Busting

When deploys appear to succeed but the live app serves stale assets or old pages, verify these two areas first:

- Environment link reset: Re-link the workspace and select the correct environment (e.g., `develop`).
  - Commands:
    - `railway link --project <project_id>`
    - `railway environment --environment develop`
    - `railway status --json`
  - Symptom addressed: CLI errors like “Environment is deleted. Run railway environment to connect to an environment.”

- Static asset cache busting: Ensure clients fetch updated CSS/JS after deploys.
  - Pattern: Add a version query param to stylesheet/script URLs, e.g. `/static/css/style.css?v=YYYYMMDD`.
  - Fallback: For critical fixes, add a small inline `<style>` block after the external link to override stale rules with `!important` until cache expires.
  - Symptom addressed: Browser shows old computed styles despite new code being deployed.

These fixes are safe, reversible, and helpful during fast UI iteration.

## Railway Native PR Environments

Railway's PR Environments feature provides automatic ephemeral environments for pull requests with zero configuration.

### Key Features

- **Automatic Lifecycle**: Creates on PR open, updates on push, destroys on close/merge
- **Zero Configuration**: No GitHub Actions workflows required
- **GitHub Integration**: Native status checks and deployment links
- **Cost-Effective**: Only runs while PR is open
- **Inherited Configuration**: Uses base environment (staging) as template

### Setup

**Enable in Railway Dashboard:**
```
Project Settings → GitHub → PR Environments
├── Enable PR Environments: ✓
├── Base Environment: staging
├── Auto-Deploy: ✓
├── Auto-Destroy on close/merge: ✓
└── Target Branches: main, develop
```

### Usage

**Automatic Workflow:**
```
Open PR → Railway creates pr-{number} environment
Push updates → Railway redeploys automatically
Close/Merge PR → Railway destroys environment
```

**Accessing PR Environment:**
```bash
# Automatic URL
https://yoto-smart-stream-pr-{number}.up.railway.app

# Via CLI
railway status -e pr-123
railway logs -e pr-123 --follow

# Health check
curl https://yoto-smart-stream-pr-123.up.railway.app/health
```

**See [PR Environments Reference](./pr_environments.md) for complete documentation.**

## Automated Deployment via GitHub Integration

### Railway's Native GitHub Integration

Railway automatically deploys when code is pushed to connected branches.

**Setup:**
1. Connect Railway project to GitHub repository
2. Configure branch mapping per environment
3. Enable auto-deploy for each environment

**Configuration in Railway Dashboard:**
```
Project Settings → GitHub
├── Repository: earchibald/yoto-smart-stream
├── Production Environment (production branch)
│   ├── Branch: production
│   ├── URL: https://yoto-smart-stream-production.up.railway.app
│   └── Auto-deploy: ✓
├── Staging Environment (staging branch)
│   ├── Branch: staging
│   ├── URL: https://yoto-smart-stream-staging.up.railway.app
│   └── Auto-deploy: ✓
├── Develop Environment (develop branch)
│   ├── Branch: develop
│   ├── URL: https://yoto-smart-stream-develop.up.railway.app
│   └── Auto-deploy: ✓
└── PR Deployments
    ├── Enabled: ✓
    ├── Base Branch: develop
    ├── Create ephemeral environment: ✓
    ├── URL Pattern: https://yoto-smart-stream-yoto-smart-stream-pr-${PR_ID}.up.railway.app
    └── Auto-destroy on close: ✓
```

**Workflow:**
- Feature branches (`copilot/TOPIC` or `copilot-worktree-TIMESTAMP`) merge into `develop`
- `develop` merges into `staging` for integration testing
- `staging` merges into `production` after successful testing
- PR environments automatically created for `copilot/TOPIC` branches

### Deployment Trigger Flow

```
Git Push → GitHub → Railway Webhook → Build → Deploy → Health Check → Live
           ↓
    GitHub Actions (optional)
    - Run tests
    - Lint code
    - Security scans
    - If pass → Continue
    - If fail → Block deploy
```

## GitHub Actions Integration

### Complete CI/CD Pipeline

```yaml
# .github/workflows/ci-cd.yml
name: CI/CD Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

env:
  PYTHON_VERSION: '3.11'

jobs:
  test:
    name: Test
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linter
        run: |
          ruff check .
          black --check .
      
      - name: Run type checker
        run: mypy yoto_smart_stream
      
      - name: Run tests
        env:
          YOTO_CLIENT_ID: ${{ secrets.YOTO_CLIENT_ID }}
          YOTO_CLIENT_SECRET: ${{ secrets.YOTO_CLIENT_SECRET }}
        run: |
          pytest tests/ -v --cov=yoto_smart_stream --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
  
  security:
    name: Security Scan
    runs-on: ubuntu-latest
    needs: test
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Run Bandit security scan
        run: |
          pip install bandit
          bandit -r yoto_smart_stream/ -f json -o bandit-report.json
      
      - name: Run Safety check
        run: |
          pip install safety
          safety check --json
  
  deploy-staging:
    name: Deploy to Staging
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.ref == 'refs/heads/develop' && github.event_name == 'push'
    environment:
      name: staging
      url: https://yoto-smart-stream-staging.up.railway.app
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Deploy to Railway Staging
        run: railway up --environment staging
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Sync secrets to Railway
        run: |
          railway variables set YOTO_CLIENT_ID="${{ secrets.YOTO_CLIENT_ID }}" -e staging
          railway variables set YOTO_CLIENT_SECRET="${{ secrets.YOTO_CLIENT_SECRET }}" -e staging
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Wait for deployment
        run: sleep 30
      
      - name: Run smoke tests
        env:
          TEST_URL: https://yoto-smart-stream-staging.up.railway.app
        run: |
          pytest tests/smoke/ -v --base-url=$TEST_URL
  
  deploy-production:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: [test, security]
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment:
      name: production
      url: https://yoto-smart-stream-production.up.railway.app
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Deploy to Railway Production
        run: railway up --environment production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Sync secrets to Railway
        run: |
          railway variables set YOTO_CLIENT_ID="${{ secrets.YOTO_CLIENT_ID }}" -e production
          railway variables set YOTO_CLIENT_SECRET="${{ secrets.YOTO_CLIENT_SECRET }}" -e production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Wait for deployment
        run: sleep 30
      
      - name: Verify deployment
        run: |
          curl -f https://yoto-smart-stream-production.up.railway.app/health || exit 1
      
      - name: Run smoke tests
        env:
          TEST_URL: https://yoto-smart-stream-production.up.railway.app
        run: |
          pytest tests/smoke/ -v --base-url=$TEST_URL
      
      - name: Notify on success
        if: success()
        run: |
          echo "✅ Production deployment successful"
      
      - name: Notify on failure
        if: failure()
        run: |
          echo "❌ Production deployment failed"
          # Add notification logic (Slack, email, etc.)
```

### Simplified Deploy-Only Workflow

```yaml
# .github/workflows/deploy-railway.yml
name: Deploy to Railway

on:
  push:
    branches: [main, develop]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Determine environment
        id: env
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "environment=production" >> $GITHUB_OUTPUT
          else
            echo "environment=staging" >> $GITHUB_OUTPUT
          fi
      
      - name: Deploy to Railway
        run: railway up --environment ${{ steps.env.outputs.environment }}
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### PR Environment Workflow

```yaml
# .github/workflows/pr-preview.yml
name: PR Preview Environment

on:
  pull_request:
    types: [opened, synchronize, reopened]
    branches: [main, develop]

jobs:
  preview:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Create PR environment
        run: |
          # Railway auto-creates PR environments
          # This workflow can add additional checks
          railway status
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Comment PR with preview URL
        uses: actions/github-script@v6
        with:
          script: |
            const prNumber = context.payload.pull_request.number;
            const previewUrl = `https://yoto-smart-stream-pr-${prNumber}.up.railway.app`;
            
            github.rest.issues.createComment({
              issue_number: prNumber,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: `🚀 Preview environment deployed!\n\n**URL:** ${previewUrl}\n\nTests and checks will run automatically.`
            });
```

## Manual Deployment Workflows

### Manual Deploy via Railway CLI

```bash
#!/bin/bash
# scripts/deploy.sh - Manual deployment script

set -e

ENVIRONMENT=${1:-staging}

echo "🚀 Deploying to $ENVIRONMENT..."

# Ensure Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "Installing Railway CLI..."
    npm i -g @railway/cli
fi

# Login check
railway whoami || railway login

# Deploy
echo "Deploying to $ENVIRONMENT environment..."
railway up --environment "$ENVIRONMENT"

echo "✅ Deployment triggered successfully"

# Wait for deployment
echo "Waiting for deployment to complete..."
sleep 30

# Verify health check
echo "Verifying deployment..."
railway run -e "$ENVIRONMENT" curl -f http://localhost:8000/health

echo "✅ Deployment verified"
```

Usage:
```bash
# Deploy to staging
./scripts/deploy.sh staging

# Deploy to production
./scripts/deploy.sh production
```

### Interactive Promotion Script

```bash
#!/bin/bash
# scripts/promote-to-production.sh - Interactive production promotion

set -e

echo "🚀 Production Promotion Script"
echo "================================"
echo ""

# Verify on develop branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "develop" ]]; then
    echo "❌ Must be on 'develop' branch to promote"
    exit 1
fi

# Pull latest
echo "Pulling latest from develop..."
git pull origin develop

# Check staging deployment status
echo "Checking staging deployment status..."
railway status -e staging

echo ""
echo "⚠️  This will promote current develop to production"
echo "Have you verified staging is healthy? (yes/no)"
read -r CONFIRM

if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted"
    exit 1
fi

# Create promotion branch
PROMOTION_BRANCH="promote/$(date +%Y%m%d-%H%M%S)"
echo "Creating promotion branch: $PROMOTION_BRANCH"
git checkout -b "$PROMOTION_BRANCH"
git push origin "$PROMOTION_BRANCH"

# Create PR
echo "Creating pull request to main..."
gh pr create \
    --base main \
    --head "$PROMOTION_BRANCH" \
    --title "Production Release $(date +%Y-%m-%d)" \
    --body "Promoting changes from staging to production.

## Checklist
- [x] All tests passing
- [x] Staging verified
- [ ] PR reviewed
- [ ] Ready to merge

**Staging URL:** https://yoto-smart-stream-staging.up.railway.app
**Production URL:** https://yoto-smart-stream-production.up.railway.app
"

echo ""
echo "✅ Promotion PR created"
echo "Review and merge the PR to deploy to production"
```

## Database Migration Workflows

### Migration During Deployment

```yaml
# .github/workflows/deploy-with-migrations.yml
name: Deploy with Migrations

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Run database migrations
        run: |
          railway run -e production python manage.py migrate --check
          railway run -e production python manage.py migrate
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Deploy application
        run: railway up --environment production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### Safe Migration Script

```bash
#!/bin/bash
# scripts/migrate.sh - Safe database migration

set -e

ENVIRONMENT=${1:-staging}

echo "🗄️  Running migrations on $ENVIRONMENT..."

# Backup database first
echo "Creating database backup..."
railway run -e "$ENVIRONMENT" pg_dump > "backup_${ENVIRONMENT}_$(date +%Y%m%d_%H%M%S).sql"

# Check migrations
echo "Checking for pending migrations..."
railway run -e "$ENVIRONMENT" python manage.py migrate --check

# Run migrations
echo "Running migrations..."
railway run -e "$ENVIRONMENT" python manage.py migrate

echo "✅ Migrations completed successfully"
```

## Rollback Workflows

### Automatic Rollback on Health Check Failure

```yaml
# .github/workflows/deploy-with-rollback.yml
name: Deploy with Auto Rollback

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Get current deployment ID
        id: current
        run: |
          DEPLOYMENT_ID=$(railway status -e production --json | jq -r '.deploymentId')
          echo "deployment_id=$DEPLOYMENT_ID" >> $GITHUB_OUTPUT
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Deploy to production
        run: railway up --environment production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Wait for deployment
        run: sleep 60
      
      - name: Health check
        id: health
        run: |
          if curl -f https://yoto-smart-stream-production.up.railway.app/health; then
            echo "status=success" >> $GITHUB_OUTPUT
          else
            echo "status=failed" >> $GITHUB_OUTPUT
          fi
      
      - name: Rollback on failure
        if: steps.health.outputs.status == 'failed'
        run: |
          echo "❌ Health check failed, rolling back..."
          railway redeploy ${{ steps.current.outputs.deployment_id }} -e production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Fail workflow if rolled back
        if: steps.health.outputs.status == 'failed'
        run: exit 1
```

### Manual Rollback Script

```bash
#!/bin/bash
# scripts/rollback.sh - Manual rollback script

set -e

ENVIRONMENT=${1:-production}

echo "⚠️  Rolling back $ENVIRONMENT environment"

# List recent deployments
echo "Recent deployments:"
railway deployments -e "$ENVIRONMENT" --limit 5

echo ""
echo "Enter deployment ID to rollback to:"
read -r DEPLOYMENT_ID

echo "Rolling back to deployment $DEPLOYMENT_ID..."
railway redeploy "$DEPLOYMENT_ID" -e "$ENVIRONMENT"

echo "✅ Rollback initiated"
```

## Environment-Specific Deployment Strategies

### Production: Blue-Green Deployment

```yaml
# Manual blue-green via separate environments
# 1. Deploy to "production-blue" environment
# 2. Run tests on "production-blue"
# 3. Switch traffic (DNS/load balancer)
# 4. Keep "production-green" for rollback

# Not natively supported by Railway
# Requires external load balancer or DNS management
```

### Staging: Continuous Deployment

```yaml
# Every push to develop → Auto-deploy to staging
# No manual approval required
# Perfect for rapid iteration
```

### Production: Gated Deployment

```yaml
# .github/workflows/deploy-production-gated.yml
name: Deploy Production (Gated)

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: production
      # Requires manual approval in GitHub
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Deploy to Railway
        run: railway up --environment production
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Monitoring & Notifications

### Slack Notification on Deployment

```yaml
# Add to any deployment workflow
- name: Notify Slack on success
  if: success()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "✅ Deployment to ${{ github.ref }} succeeded",
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Deployment Successful*\n*Environment:* production\n*Commit:* ${{ github.sha }}\n*Author:* ${{ github.actor }}"
            }
          }
        ]
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}

- name: Notify Slack on failure
  if: failure()
  uses: slackapi/slack-github-action@v1
  with:
    payload: |
      {
        "text": "❌ Deployment to ${{ github.ref }} failed"
      }
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

### Email Notification Script

```bash
#!/bin/bash
# scripts/notify-deployment.sh

ENVIRONMENT=$1
STATUS=$2
COMMIT_SHA=$3

if [[ "$STATUS" == "success" ]]; then
    SUBJECT="✅ Deployment to $ENVIRONMENT succeeded"
else
    SUBJECT="❌ Deployment to $ENVIRONMENT failed"
fi

BODY="
Deployment Details:
- Environment: $ENVIRONMENT
- Status: $STATUS
- Commit: $COMMIT_SHA
- Time: $(date)
"

# Send email (requires mail/sendmail configured)
echo "$BODY" | mail -s "$SUBJECT" team@example.com
```

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing
- [ ] Code reviewed and approved
- [ ] Database migrations prepared
- [ ] Environment variables updated (if needed)
- [ ] Secrets rotated (if needed)
- [ ] Staging verified
- [ ] Backup created (production only)
- [ ] Team notified
- [ ] Rollback plan ready

### During Deployment

- [ ] Monitor deployment logs
- [ ] Watch health check status
- [ ] Monitor error rates
- [ ] Check resource usage

### Post-Deployment

- [ ] Verify health check endpoint
- [ ] Run smoke tests
- [ ] Check application logs
- [ ] Monitor error tracking (Sentry)
- [ ] Verify database migrations applied
- [ ] Test critical user flows
- [ ] Notify team of success/failure
- [ ] Document any issues

## Railway.toml Configuration Synchronization

### Overview

Railway uses `railway.toml` to configure build and deployment settings (volumes, health checks, restart policies, etc.). Configuration changes are only applied during deployment, not when the file is simply updated in the repository.

### When railway.toml Changes Are Applied

Railway reads `railway.toml` during:
1. **Automatic deployments** - When code is pushed to a connected branch
2. **Manual deployments** - Via `railway up` or Railway Dashboard
3. **Redeployments** - Triggering a rebuild of existing code

**Important:** Simply committing `railway.toml` changes does NOT update Railway configuration until a deployment occurs.

### Automated Configuration Sync Workflow

Create a workflow that automatically applies railway.toml changes:

```yaml
# .github/workflows/railway-config-sync.yml
name: Railway Configuration Sync

on:
  push:
    branches: [main, develop]
    paths:
      - 'railway.toml'
  workflow_dispatch:
    inputs:
      environment:
        description: 'Environment to reconfigure'
        required: true
        type: choice
        options: [production, staging, development]

jobs:
  validate-config:
    name: Validate railway.toml
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Validate TOML syntax
        run: |
          pip install toml
          python -c "import toml; toml.load('railway.toml')"
      
      - name: Check for volume configuration
        run: |
          if grep -q "volumes" railway.toml; then
            echo "✓ Volume configuration detected"
          fi

  sync-production:
    name: Sync Production Configuration
    runs-on: ubuntu-latest
    needs: validate-config
    if: github.ref == 'refs/heads/main'
    environment:
      name: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Apply railway.toml configuration
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_PROD }}
        run: |
          echo "🔄 Triggering redeployment to apply configuration..."
          railway up --environment production --detach
      
      - name: Verify configuration applied
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_PROD }}
        run: |
          sleep 30
          railway status -e production
```

### Volume Configuration

Volumes defined in `railway.toml` are created when the configuration is first deployed:

```toml
# railway.toml
[deploy]
# Persistent volumes - survive deployments and restarts
[[deploy.volumes]]
name = "data"
mountPath = "/data"

[[deploy.volumes]]
name = "uploads"
mountPath = "/app/uploads"
```

**After deploying volume configuration:**

1. **Verify in Railway Dashboard:**
   - Navigate to: Project → Service → Settings → Volumes
   - Confirm volumes appear with correct names and mount paths

2. **Verify via CLI:**
   ```bash
   railway status -e production
   # Output should show volume mounts
   ```

3. **Verify in application:**
   ```python
   # Check volume accessibility at startup
   import os
   from pathlib import Path
   
   data_path = Path("/data")
   if not data_path.exists():
       data_path.mkdir(parents=True)
       print(f"✓ Created volume directory: {data_path}")
   else:
       print(f"✓ Volume mounted at: {data_path}")
   ```

### Manual Configuration Sync

If automated workflow doesn't run or immediate sync is needed:

**Via Railway CLI:**
```bash
# Install and login
npm i -g @railway/cli
railway login

# Link project
railway link

# Trigger redeployment to apply railway.toml
railway up -e production --detach

# Verify after 30-60 seconds
railway status -e production
```

**Via Railway Dashboard:**
```
1. Go to https://railway.app/dashboard
2. Select project and service
3. Navigate to Deployments tab
4. Click "Redeploy" on latest deployment
5. Verify Settings → Volumes shows new volumes
```

### Common Configuration Changes

**Adding Health Check:**
```toml
[deploy]
healthcheckPath = "/api/health"
healthcheckTimeout = 100
```

**Configuring Restart Policy:**
```toml
[deploy]
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

**Watch Patterns (Trigger rebuilds):**
```toml
[deploy]
watchPatterns = [
    "yoto_smart_stream/**/*.py",
    "requirements.txt",
    "pyproject.toml"
]
```

### Troubleshooting Configuration Sync

**Problem: Volumes not appearing after deployment**

Solution:
1. Check TOML syntax: `python -c "import toml; toml.load('railway.toml')"`
2. Verify deployment completed successfully
3. Check Railway logs for errors: `railway logs -e production`
4. Confirm you're checking the correct environment (volumes are per-environment)
5. Try manual redeploy via Dashboard

**Problem: Configuration changes not taking effect**

Solution:
1. Ensure railway.toml is committed and pushed
2. Trigger new deployment (changes only apply on deploy, not on file update)
3. Check for syntax errors in railway.toml
4. Verify Railway is reading from correct branch

**Problem: Old configuration still in use**

Solution:
1. Force redeploy: `railway up -e production`
2. Check Railway Dashboard for failed deployments
3. Verify railway.toml is in repository root (not subdirectory)

### Best Practices for Configuration Management

1. **Validate syntax before committing:**
   ```bash
   python -c "import toml; toml.load('railway.toml')" || echo "Invalid TOML"
   ```

2. **Test in PR environments first:**
   - PR environments inherit railway.toml from your branch
   - Verify configuration works before merging to main

3. **Document volume usage:**
   - Add comments in railway.toml explaining volume purposes
   - Document in application code what data is stored where

4. **Monitor after config changes:**
   - Check Railway logs after deployment
   - Verify health checks pass
   - Test volume accessibility in application

5. **Use version control:**
   - Always commit railway.toml changes
   - Review changes in PRs
   - Document reasons for configuration changes in commit messages

## GitHub Deployment Status Checks (Authoritative Process)

### Overview

Railway automatically posts **GitHub commit status checks** when deploying your code. This is the authoritative way for GitHub agents and CI/CD workflows to track Railway deployment status without polling or manual checks.

### What Railway Posts

When Railway deploys, it creates a GitHub commit status with:

- **Context**: `{service-name}` or `zippy-encouragement - {service-name}`
- **State**: `pending`, `success`, `failure`, or `error`
- **Description**: Human-readable status (e.g., "Success - yoto-smart-stream-pr-61.up.railway.app")
- **Target URL**: Direct link to Railway deployment logs
- **Timestamps**: `created_at` and `updated_at` in ISO 8601 format

### Status Check States

| State | Meaning | Agent Action |
|-------|---------|--------------|
| `pending` | Build/Deploy in progress | Wait and retry |
| `success` | Deployment successful and healthy | Proceed with tests/merge |
| `failure` | Build or deploy failed | Investigate logs, fix issues |
| `error` | Health check failed | Check application logs |

### Querying Status via GitHub API

**Using GitHub CLI:**
```bash
# Check deployment status for a commit
gh api repos/OWNER/REPO/commits/COMMIT_SHA/status --jq '.statuses'

# Filter for Railway status only
gh api repos/OWNER/REPO/commits/COMMIT_SHA/status --jq '.statuses[] | select(.context | contains("railway") or contains("yoto-smart-stream"))'

# Example output:
{
  "context": "zippy-encouragement - yoto-smart-stream",
  "state": "success",
  "description": "Success - yoto-smart-stream-pr-61.up.railway.app",
  "target_url": "https://railway.com/project/.../deployments/560ed5ff...",
  "created_at": "2026-01-14T06:43:15Z"
}
```

**Using REST API directly:**
```bash
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  "https://api.github.com/repos/OWNER/REPO/commits/COMMIT_SHA/status" | \
  jq '.statuses[] | select(.context | contains("railway"))'
```

### Using with GitHub CLI

**Step 1: Get PR information**
```bash
# Get PR details
gh pr view 61 --json headRefOid,number --jq '.'

# Extract commit SHA
commit_sha=$(gh pr view 61 --json headRefOid --jq -r '.headRefOid')
```

**Step 2: Query deployment status via GitHub API**
```bash
# Get commit status
gh api repos/earchibald/yoto-smart-stream/commits/$commit_sha/status --jq '.statuses'

# Find Railway deployment status
railway_status=$(gh api repos/earchibald/yoto-smart-stream/commits/$commit_sha/status --jq '.statuses[] | select(.context | contains("railway") or contains("yoto-smart-stream"))')
```

**Step 3: Make decisions based on status**
```bash
# Extract state from railway_status
state=$(echo "$railway_status" | jq -r '.state')
description=$(echo "$railway_status" | jq -r '.description')
target_url=$(echo "$railway_status" | jq -r '.target_url')

if [[ -n "$railway_status" ]]; then
    if [[ "$state" == "success" ]]; then
        echo "✅ Deployment succeeded: $description"
        # Proceed with testing or merge
    elif [[ "$state" == "pending" ]]; then
        echo "⏳ Deployment in progress, waiting..."
        # Wait and retry after delay
    elif [[ "$state" == "failure" || "$state" == "error" ]]; then
        echo "❌ Deployment failed"
        echo "Logs: $target_url"
        # Investigate and fix issues
```

### Agent Workflow Pattern

**Wait for deployment before testing:**
```bash
wait_for_railway_deployment() {
    # Wait for Railway deployment to complete before running tests
    local owner=$1
    local repo=$2
    local commit_sha=$3
    local timeout=${4:-600}
    
    local start=$(date +%s)
    
    while true; do
        local now=$(date +%s)
        local elapsed=$((now - start))
        
        if [ $elapsed -gt $timeout ]; then
            echo "❌ Timeout waiting for Railway deployment"
            return 1
        fi
        
        # Query status
        local railway_status=$(gh api repos/$owner/$repo/commits/$commit_sha/status \
            --jq '.statuses[] | select(.context | contains("railway"))')
        
        if [ -z "$railway_status" ]; then
            sleep 10
            continue
        fi
        
        local state=$(echo "$railway_status" | jq -r '.state')
        local description=$(echo "$railway_status" | jq -r '.description')
        
        if [ "$state" = "success" ]; then
            echo "$description"  # Return deployment URL
            return 0
        elif [ "$state" = "failure" ] || [ "$state" = "error" ]; then
            echo "❌ Railway deployment failed: $description" >&2
            return 1
        fi
        
        sleep 10  # Check every 10 seconds
    done
}

# Usage
deployment_url=$(wait_for_railway_deployment "earchibald" "yoto-smart-stream" "$commit_sha")
run_integration_tests "$deployment_url"
```

**Check status before merge:**
```bash
# Function to verify Railway deployment succeeded before allowing merge
can_merge_pr() {
    local owner=$1
    local repo=$2
    local pr_number=$3
    
    # Get PR head commit SHA
    commit_sha=$(gh pr view $pr_number --json headRefOid --jq -r '.headRefOid')
    
    # Get Railway deployment status
    railway_state=$(gh api repos/$owner/$repo/commits/$commit_sha/status --jq -r '.statuses[] | select(.context | contains("railway")) | .state')
    
    [[ "$railway_state" == "success" ]]
}

# Usage
if can_merge_pr "earchibald" "yoto-smart-stream" 61; then
    echo "PR can be merged"
else
    echo "Railway deployment not ready"
fi
```

### Using in GitHub Actions

**Wait for deployment before running tests:**
```yaml
name: Integration Tests

on:
  pull_request:
    branches: [develop, main]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Wait for Railway deployment
        timeout-minutes: 10
        run: |
          COMMIT_SHA=${{ github.event.pull_request.head.sha }}
          MAX_ATTEMPTS=60
          ATTEMPT=0
          
          while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
            STATUS=$(gh api repos/${{ github.repository }}/commits/$COMMIT_SHA/status \
              --jq '.statuses[] | select(.context | contains("railway")) | .state' 2>/dev/null)
            
            if [ "$STATUS" = "success" ]; then
              echo "✅ Railway deployment succeeded"
              break
            elif [ "$STATUS" = "failure" ] || [ "$STATUS" = "error" ]; then
              echo "❌ Railway deployment failed"
              exit 1
            fi
            
            echo "⏳ Waiting for Railway deployment... (attempt $((ATTEMPT+1))/$MAX_ATTEMPTS)"
            sleep 10
            ATTEMPT=$((ATTEMPT+1))
          done
          
          if [ $ATTEMPT -eq $MAX_ATTEMPTS ]; then
            echo "⏱️  Timeout waiting for Railway deployment"
            exit 1
          fi
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Get deployment URL
        id: deployment
        run: |
          COMMIT_SHA=${{ github.event.pull_request.head.sha }}
          URL=$(gh api repos/${{ github.repository }}/commits/$COMMIT_SHA/status \
            --jq '.statuses[] | select(.context | contains("railway")) | .target_url')
          echo "url=$URL" >> $GITHUB_OUTPUT
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Run integration tests
        env:
          TEST_URL: ${{ steps.deployment.outputs.url }}
        run: |
          pytest tests/integration/ -v --base-url=$TEST_URL
```

### Best Practices for Status Checks

1. **Always query for Railway status before deployment decisions**
   - Don't rely on git push timestamps
   - Don't poll Railway API directly
   - Use GitHub's authoritative status checks

2. **Handle all status states gracefully**
   - `pending`: Implement exponential backoff retry
   - `success`: Proceed with confidence
   - `failure`/`error`: Log and investigate

3. **Set appropriate timeouts**
   - Allow 5-10 minutes for builds (depends on image size)
   - Allow 2-5 minutes for deployments (depends on app startup)
   - Use total timeout of 10-15 minutes

4. **Log deployment information**
   - Record commit SHA, PR number, timestamp
   - Store target_url for investigation
   - Include in agent decision logs

5. **Combine with other checks**
   - Use "Wait for CI" feature (GitHub Actions)
   - Only deploy after Railway + your tests pass
   - Document the order of checks

### Troubleshooting Status Checks

**Problem: No Railway status appears**
- Deployment may not have started yet
- Check if Railway integration is properly connected
- Verify service is configured for auto-deploy

**Problem: Status stuck in "pending"**
- Check Railway dashboard for build errors
- Verify healthcheck configuration
- Check service logs via `railway logs`
- May indicate build timeout

**Problem: Status shows "failure" without details**
- Click target_url to see full Railway logs
- Check build logs vs deploy logs
- Verify all environment variables are set

**Problem: Old PR status interfering**
- Status checks accumulate; most recent takes precedence
- Each new push updates the status
- Manual redeploy also updates status

### Example: Real-World Implementation

For PR #61 (`yoto-smart-stream`):

```bash
# Check latest deployment status
gh api repos/earchibald/yoto-smart-stream/commits/53db1fc/status \
  --jq '.statuses[] | select(.context | contains("yoto-smart-stream"))'

# Output:
{
  "context": "zippy-encouragement - yoto-smart-stream",
  "state": "success",
  "description": "Success - yoto-smart-stream-yoto-smart-stream-pr-61.up.railway.app",
  "target_url": "https://railway.com/project/.../deployments/560ed5ff...",
  "created_at": "2026-01-14T06:43:15Z",
  "updated_at": "2026-01-14T06:43:15Z"
}

# Access deployed application
curl https://yoto-smart-stream-yoto-smart-stream-pr-61.up.railway.app/health

# View deployment logs
open https://railway.com/project/.../deployments/560ed5ff...
```

---

## Best Practices

### ✅ DO:

1. Run tests before deployment
2. Use health checks for verification
3. Implement automatic rollback on failure
4. Monitor deployments in real-time
5. Use staging as pre-production gate
6. Document deployment process
7. Keep deployment scripts in version control
8. Use Railway CLI for automation
9. Implement deployment notifications
10. Maintain deployment logs

### ❌ DON'T:

1. Deploy directly to production without staging
2. Skip health checks
3. Ignore deployment failures
4. Deploy during peak hours (production)
5. Skip database backups before migrations
6. Use manual SSH for deployments
7. Deploy without reviewing changes
8. Skip smoke tests after deployment
9. Ignore monitoring during deployment
10. Deploy without rollback plan

---

**Next Steps:**
- Configure [Configuration Management](./configuration_management.md)
- Set up [Monitoring & Logging](./monitoring_logging.md)
- Review [Database & Services](./database_services.md)
