# Deployment Workflows for Railway

## Overview

This guide covers automated deployment workflows for Railway, including GitHub Actions integration, CI/CD pipelines, Railway's native PR Environments, and deployment automation strategies.

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
├── Production Environment
│   ├── Branch: main
│   └── Auto-deploy: ✓
├── Staging Environment
│   ├── Branch: develop
│   └── Auto-deploy: ✓
└── PR Deployments
    ├── Enabled: ✓
    ├── Create ephemeral environment: ✓
    └── Auto-destroy on close: ✓
```

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
