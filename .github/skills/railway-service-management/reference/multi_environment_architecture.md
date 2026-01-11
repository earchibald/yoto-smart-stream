# Multi-Environment Architecture for Railway

## Overview

This guide outlines the simplified two-environment architecture used in this project: Production and automatic PR Environments. This approach leverages Railway's native features and Shared Variables for efficient deployment management.

## Environment Strategy

### Current Setup (Simplified)

```
┌─────────────────────────────────────────────────────┐
│                Railway Project                       │
│              (yoto-smart-stream)                     │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  Production Environment                      │  │
│  │  - Branch: main                              │  │
│  │  - URL: yoto-smart-stream-production.up.railway.app                 │  │
│  │  - Services: web, postgres (if needed)       │  │
│  │  - Auto-deploy: ✓ (on push to main)         │  │
│  │  - Shared Variables: YOTO_CLIENT_ID          │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐  │
│  │  PR Environment (pr-123)                     │  │
│  │  - Branch: feature/add-feature               │  │
│  │  - URL: yoto-smart-stream-pr-123.up.railway.app          │  │
│  │  - Services: web (inherits from production)  │  │
│  │  - Auto-deploy: ✓ (on PR update)            │  │
│  │  - Auto-destroy: ✓ (on merge/close)         │  │
│  │  - Inherits: ${{shared.YOTO_CLIENT_ID}}      │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

### Previous Setup (Deprecated)

The project previously used a three-environment model with staging and development environments. This has been simplified to:
- Remove maintenance overhead
- Leverage Railway's native PR Environments
- Use Shared Variables for configuration management
- Reduce costs by eliminating unused environments

## Branch-to-Environment Mapping

### Main Branch → Production

**Configuration:**
```yaml
Environment: production
Branch: main
Auto-deploy: Yes
Deployment: On push to main (via GitHub Actions)
```

**Characteristics:**
- Customer-facing
- Stable, tested code only
- Automatic deployments after merge
- Full resource allocation
- Comprehensive monitoring
- Database backups enabled (if applicable)
- Shared Variables defined here (e.g., YOTO_CLIENT_ID)

**Access Control:**
- Protected branch in GitHub
- Require PR reviews
- Require status checks to pass
- Admin-only force push

### Feature Branches → PR Environments (Automatic)

**Configuration:**
```yaml
Environment: pr-{number}
Branch: Any branch with PR to main
Auto-deploy: Yes (automatic via Railway)
Base Environment: production
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
  - web (FastAPI application)
  - postgres (optional, if database needed)

# Environment variables
DEBUG=false
LOG_LEVEL=warning
YOTO_CLIENT_ID=<actual_value>  # Set as Shared Variable in Railway Dashboard
PORT=${{PORT}}  # Auto-set by Railway
PUBLIC_URL=https://yoto-smart-stream-production.up.railway.app

# Optional database
DATABASE_URL=${{Postgres.DATABASE_URL}}  # If using PostgreSQL

# Resource allocation (adjust as needed)
RAM: 512 MB - 1 GB for web
CPU: 0.5 - 1 vCPU for web
Storage: As needed for PostgreSQL (if used)
```

### PR Environments

```bash
# Minimal services for testing (inherited from production)
Services:
  - web (FastAPI application)

# Environment variables
RAILWAY_ENVIRONMENT_NAME=pr-{number}  # Auto-set by Railway
YOTO_CLIENT_ID=${{shared.YOTO_CLIENT_ID}}  # Inherits from production
PORT=${{PORT}}  # Auto-set by Railway
PUBLIC_URL=https://yoto-smart-stream-pr-{number}.up.railway.app

# Debug settings (configured via GitHub Actions)
DEBUG=true
LOG_LEVEL=debug

# Resource allocation (typically smaller than production)
RAM: 256-512 MB for web
CPU: 0.25-0.5 vCPU for web
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

### Step 5: Configure Railway Native PR Environments

**Via Railway Dashboard:**
```bash
# 1. Navigate to Project Settings → GitHub
# 2. Scroll to "PR Environments" section
# 3. Enable "Create ephemeral environments for PRs"
# 4. Configure settings:
#    - Base Environment: staging
#    - Auto-Deploy: ✓ (redeploy on PR updates)
#    - Auto-Destroy: ✓ (cleanup on PR close/merge)
#    - Target Branches: main, develop
# 5. Save settings
```

**Benefits of Native PR Environments:**
- Zero GitHub Actions configuration required
- Automatic lifecycle management (create, update, destroy)
- Native GitHub integration with status checks
- Inherits configuration from base environment
- Cost-effective (only pay while PR is open)

**Alternative: Custom Ephemeral Environments**

For advanced use cases (custom naming, non-PR workflows), see custom ephemeral environment scripts. However, Railway's native PR Environments are recommended for standard PR workflows.

**See [PR Environments Reference](./pr_environments.md) for detailed documentation.**

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
2. Opens PR → Railway automatically creates PR environment (pr-{number})
3. Tests in PR environment (automatic deployments on updates)
4. PR merged to `develop` → Staging deploys automatically
5. QA tests in staging
6. Manual promotion: Create PR from `develop` to `main`
7. Merge to `main` → Production deploys automatically
8. PR environment destroyed automatically on merge

**Key Points:**
- PR environments use Railway's native feature (zero config)
- All deployments triggered by Railway's GitHub integration
- No custom GitHub Actions needed for deployments
- GitHub Actions can be used for testing and validation

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
