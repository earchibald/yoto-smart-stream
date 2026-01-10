# Multi-Environment Architecture for Railway

## Overview

This guide outlines strategies for implementing a robust multi-environment architecture on Railway, with focus on branch-based deployments, environment isolation, and promotion workflows.

## Environment Strategy

### Recommended Setup

```
┌─────────────────────────────────────────────────────┐
│                Railway Project                       │
│              (yoto-smart-stream)                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Production Environment                      │  │
│  │  - Branch: main                              │  │
│  │  - URL: yoto.up.railway.app                 │  │
│  │  - Services: web, postgres, redis            │  │
│  │  - Auto-deploy: ✓                            │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Staging Environment                         │  │
│  │  - Branch: develop                           │  │
│  │  - URL: yoto-staging.up.railway.app         │  │
│  │  - Services: web, postgres, redis            │  │
│  │  - Auto-deploy: ✓                            │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  PR Environment (pr-123)                     │  │
│  │  - Branch: feature/add-mqtt                  │  │
│  │  - URL: yoto-pr-123.up.railway.app          │  │
│  │  - Services: web, postgres                   │  │
│  │  - Auto-deploy: ✓                            │  │
│  │  - Auto-destroy: on merge/close              │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Branch-to-Environment Mapping

### Main Branch → Production

**Configuration:**
```yaml
Environment: production
Branch: main
Auto-deploy: Yes
Deployment: On push to main
```

**Characteristics:**
- Customer-facing
- Stable, tested code only
- Automatic deployments after merge
- Full resource allocation
- Comprehensive monitoring
- Database backups enabled

**Access Control:**
- Protected branch in GitHub
- Require PR reviews
- Require status checks to pass
- Admin-only force push

### Develop Branch → Staging

**Configuration:**
```yaml
Environment: staging
Branch: develop
Auto-deploy: Yes
Deployment: On push to develop
```

**Characteristics:**
- Pre-production testing
- Integration testing
- QA validation
- Performance testing
- Similar to production setup
- Separate database

**Access Control:**
- Protected branch in GitHub
- Require PR reviews (optional)
- Auto-deploy on merge

### Feature Branches → PR Environments

**Configuration:**
```yaml
Environment: pr-{number}
Branch: feature/*, fix/*, chore/*
Auto-deploy: Yes (on PR creation)
Auto-destroy: Yes (on PR close/merge)
```

**Characteristics:**
- Ephemeral (temporary)
- Created automatically on PR
- Isolated testing environment
- Destroyed after PR close/merge
- Reduced resource allocation
- Simplified service stack

## Environment Configuration

### Production Environment

```bash
# Core services
Services:
  - web (FastAPI application, 2 replicas)
  - postgres (2 GB RAM, daily backups)
  - redis (512 MB RAM, persistence enabled)

# Environment variables
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=warning
YOTO_CLIENT_ID=${{ secrets.YOTO_CLIENT_ID }}
YOTO_CLIENT_SECRET=${{ secrets.YOTO_CLIENT_SECRET }}
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
PORT=${{PORT}}
WORKERS=4
SENTRY_DSN=${{ secrets.SENTRY_DSN }}

# Resource allocation
RAM: 1 GB per web replica
CPU: 1 vCPU per web replica
Storage: 10 GB for PostgreSQL
```

### Staging Environment

```bash
# Core services
Services:
  - web (FastAPI application, 1 replica)
  - postgres (1 GB RAM, daily backups)
  - redis (256 MB RAM)

# Environment variables
ENVIRONMENT=staging
DEBUG=true
LOG_LEVEL=info
YOTO_CLIENT_ID=${{ secrets.YOTO_CLIENT_ID }}
YOTO_CLIENT_SECRET=${{ secrets.YOTO_CLIENT_SECRET }}
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
PORT=${{PORT}}
WORKERS=2
SENTRY_DSN=${{ secrets.SENTRY_DSN_STAGING }}

# Resource allocation
RAM: 512 MB for web
CPU: 0.5 vCPU for web
Storage: 5 GB for PostgreSQL
```

### PR Environments

```bash
# Minimal services for testing
Services:
  - web (FastAPI application, 1 replica)
  - postgres (512 MB RAM, ephemeral)

# Environment variables
ENVIRONMENT=preview
DEBUG=true
LOG_LEVEL=debug
YOTO_CLIENT_ID=${{ secrets.YOTO_CLIENT_ID }}
YOTO_CLIENT_SECRET=${{ secrets.YOTO_CLIENT_SECRET }}
DATABASE_URL=${{Postgres.DATABASE_URL}}
PORT=${{PORT}}
WORKERS=1

# Resource allocation
RAM: 512 MB for web
CPU: 0.5 vCPU for web
Storage: 1 GB for PostgreSQL (ephemeral)
```

## Setting Up Environments

### Step 1: Create Railway Project

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login
railway login

# Create project
railway init

# Or link to existing project
railway link
```

### Step 2: Create Production Environment

```bash
# Via Railway Dashboard:
# 1. Go to project settings
# 2. Click "Environments"
# 3. Click "New Environment"
# 4. Name: "production"
# 5. Connect to GitHub branch: "main"

# Via CLI (if supported):
railway environment add production
```

### Step 3: Add Services to Production

```bash
# Add web service (automatically detects from GitHub)
railway add

# Add PostgreSQL
railway add --plugin postgresql -e production

# Add Redis
railway add --plugin redis -e production

# Set environment variables
railway variables set ENVIRONMENT=production -e production
railway variables set DEBUG=false -e production
railway variables set LOG_LEVEL=warning -e production
railway variables set YOTO_CLIENT_ID="${{ secrets.YOTO_CLIENT_ID }}" -e production
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}' -e production
railway variables set REDIS_URL='${{Redis.REDIS_URL}}' -e production
```

### Step 4: Create Staging Environment

```bash
# Create staging environment
railway environment add staging

# Connect to develop branch (via dashboard)
# Settings → GitHub → Branch: develop

# Add services
railway add --plugin postgresql -e staging
railway add --plugin redis -e staging

# Set variables
railway variables set ENVIRONMENT=staging -e staging
railway variables set DEBUG=true -e staging
railway variables set LOG_LEVEL=info -e staging
railway variables set YOTO_CLIENT_ID="${{ secrets.YOTO_CLIENT_ID }}" -e staging
```

### Step 5: Configure PR Environments

```bash
# Via Railway Dashboard:
# 1. Project Settings → GitHub
# 2. Enable "PR Deploys"
# 3. Check "Create ephemeral environment for each PR"
# 4. Check "Auto-destroy on PR close/merge"
# 5. Template: Use staging as base configuration
```

## Deployment Workflows

### Production Deployment Flow

```
Developer → Feature Branch → PR → Develop Branch → Staging → Main Branch → Production
                                     ↓              ↓           ↓            ↓
                                  PR Env     Staging Env   Manual      Production
                                  (auto)      (auto)       Promotion      (auto)
```

**Steps:**
1. Developer creates feature branch
2. Opens PR → PR environment auto-created
3. Tests in PR environment
4. PR merged to `develop` → Staging deploys
5. QA tests in staging
6. Manual promotion: PR from `develop` to `main`
7. Merge to `main` → Production deploys

### Git Branch Strategy

```
main (production)
  └── develop (staging)
        ├── feature/add-mqtt (pr-123)
        ├── feature/icon-management (pr-124)
        └── fix/auth-bug (pr-125)
```

**Branch Rules:**
```bash
main:
  - Protected
  - Require PR review (2 approvers)
  - Require status checks (tests, linting)
  - No force push

develop:
  - Protected
  - Require PR review (1 approver)
  - Require status checks
  - No force push

feature/* / fix/*:
  - Unprotected
  - Auto-create PR environment
  - Auto-delete after merge
```

## Environment Promotion

### Manual Promotion (Recommended)

```bash
# Step 1: Verify staging is healthy
railway status -e staging
railway logs -e staging

# Step 2: Run smoke tests on staging
pytest tests/smoke/ --environment=staging

# Step 3: Create promotion PR
git checkout develop
git pull origin develop
git checkout -b promote/v1.2.0
git push origin promote/v1.2.0

# Step 4: Create PR to main
gh pr create --base main --head promote/v1.2.0 \
  --title "Release v1.2.0" \
  --body "Promoting changes from staging to production"

# Step 5: After approval, merge PR → Production deploys
```

### Automated Promotion (Advanced)

```yaml
# .github/workflows/promote-to-prod.yml
name: Promote to Production

on:
  workflow_dispatch:
    inputs:
      confirm:
        description: 'Type PROMOTE to confirm'
        required: true

jobs:
  promote:
    runs-on: ubuntu-latest
    if: github.event.inputs.confirm == 'PROMOTE'
    
    steps:
      - uses: actions/checkout@v3
        with:
          ref: develop
      
      - name: Create Promotion PR
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          git checkout -b promote/$(date +%Y%m%d-%H%M%S)
          gh pr create --base main --head $(git branch --show-current) \
            --title "Production Promotion $(date +%Y-%m-%d)" \
            --body "Automated promotion from staging to production"
```

## Database Management Across Environments

### Development/PR Environments

```bash
# Use shared dev database or ephemeral per-PR
Strategy: Ephemeral database per PR

# Seed with test data
railway run -e pr-123 python manage.py seed_data --test

# Run migrations
railway run -e pr-123 python manage.py migrate
```

### Staging Environment

```bash
# Persistent database, separate from production
Strategy: Separate database with sanitized production data

# Refresh from production (sanitized)
pg_dump production_db | sanitize_data | psql staging_db

# Or use synthetic test data
railway run -e staging python manage.py seed_data --staging
```

### Production Environment

```bash
# Production database - never shared
Strategy: Dedicated, backed up, high availability

# Automatic daily backups (Railway)
# Manual backup before migrations
railway connect postgres -e production
pg_dump > backup_$(date +%Y%m%d).sql

# Run migrations
railway run -e production python manage.py migrate
```

## Environment Isolation

### Network Isolation

```bash
# Production environment
Network: Isolated from other environments
Access: Public URL + private internal network
Firewall: Railway handles security

# Inter-service communication (same env)
web → postgres (internal, private)
web → redis (internal, private)

# Cross-environment communication
NOT RECOMMENDED: Use separate environments completely
```

### Data Isolation

```bash
# Each environment has separate:
- Database instance
- Redis instance
- File storage (if using volumes)
- Environment variables
- Secrets
```

### Resource Isolation

```bash
# Each environment has independent:
- CPU allocation
- RAM allocation
- Network bandwidth
- Storage limits
```

## Configuration Management

### Shared Configuration

```bash
# railway.toml (committed to repo)
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
```

### Environment-Specific Configuration

```python
# config.py
import os

class Config:
    ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
    
    # Environment-specific settings
    if ENVIRONMENT == "production":
        WORKERS = 4
        TIMEOUT = 60
        LOG_LEVEL = "warning"
    elif ENVIRONMENT == "staging":
        WORKERS = 2
        TIMEOUT = 120
        LOG_LEVEL = "info"
    else:  # PR/development
        WORKERS = 1
        TIMEOUT = 300
        LOG_LEVEL = "debug"
```

## Monitoring Per Environment

### Production Monitoring

```bash
# Enable comprehensive monitoring
- Railway metrics (CPU, RAM, network)
- Application logs (structured JSON)
- Error tracking (Sentry)
- Uptime monitoring (UptimeRobot, Pingdom)
- Performance monitoring (New Relic, Datadog)

# Alerts
- High error rate
- High response time
- Service down
- Resource exhaustion
```

### Staging Monitoring

```bash
# Basic monitoring
- Railway metrics
- Application logs
- Error tracking (Sentry staging project)

# No uptime monitoring (not customer-facing)
```

### PR Environment Monitoring

```bash
# Minimal monitoring
- Railway logs only
- Manual testing and verification
```

## Cost Optimization

### Resource Right-Sizing

```bash
# Production: Full resources
web: 1 GB RAM, 1 vCPU, 2 replicas = ~$30/month

# Staging: 50% of production
web: 512 MB RAM, 0.5 vCPU, 1 replica = ~$10/month

# PR environments: Minimal
web: 512 MB RAM, 0.5 vCPU, 1 replica = ~$5/month each
Auto-destroy after merge = Cost minimized
```

### Sleep/Destroy Unused Environments

```bash
# Manually stop staging when not in use
railway down -e staging

# Auto-destroy PR environments
# Configured in Railway dashboard: PR Deploys → Auto-destroy

# Restart when needed
railway up -e staging
```

## Testing Strategy Per Environment

### PR Environment Testing

```bash
# Automated tests in CI
pytest tests/unit
pytest tests/integration
pytest tests/functional -m "smoke"

# Manual testing
- Feature verification
- Basic smoke tests
- Visual inspection
```

### Staging Environment Testing

```bash
# Comprehensive testing
pytest tests/  # All tests
pytest tests/e2e  # End-to-end tests

# Manual QA
- Full feature testing
- Regression testing
- Performance testing
- Security testing
```

### Production Environment Testing

```bash
# Post-deployment verification
pytest tests/smoke --environment=production

# Monitoring
- Real user monitoring
- Error tracking
- Performance metrics
```

## Rollback Strategy

### Instant Rollback

```bash
# Via Railway Dashboard
1. Go to Deployments
2. Find previous successful deployment
3. Click "Rollback"

# Via CLI
railway redeploy [DEPLOYMENT_ID] -e production
```

### Git-Based Rollback

```bash
# Revert last commit on main
git revert HEAD
git push origin main
# → Triggers automatic deployment

# Or revert to specific commit
git revert <commit-sha>
git push origin main
```

## Best Practices

### ✅ DO:

1. Use separate environments for dev/staging/prod
2. Auto-deploy staging and PR environments
3. Manually promote staging → production
4. Use branch protection on main and develop
5. Run comprehensive tests in staging
6. Monitor all environments appropriately
7. Destroy PR environments after merge
8. Use Railway's reference variables for service URLs
9. Right-size resources per environment
10. Document environment setup

### ❌ DON'T:

1. Share databases between environments
2. Use production credentials in dev/staging
3. Deploy directly to production without staging
4. Skip PR environments for feature testing
5. Leave PR environments running after merge
6. Over-provision resources for non-prod
7. Ignore failed deployments
8. Auto-promote to production
9. Use same secrets across all environments
10. Skip health checks

---

**Next Steps:**
- Set up [Deployment Workflows](./deployment_workflows.md)
- Configure [Secrets Management](./secrets_management.md)
- Review [Cost Optimization](./cost_optimization.md)
