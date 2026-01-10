# Railway CLI & Automation Scripts

## Overview

This guide covers the Railway CLI, common commands, and automation scripts for managing Railway deployments efficiently.

## Railway CLI Installation

### Installation Methods

```bash
# npm (recommended)
npm i -g @railway/cli

# Homebrew (macOS)
brew install railway

# Scoop (Windows)
scoop install railway

# Binary download
# Visit: https://docs.railway.app/reference/cli#installation
```

### Verify Installation

```bash
railway --version

# Should output: railway version X.X.X
```

## Authentication

### Login

```bash
# Interactive browser login
railway login

# Check authentication status
railway whoami
```

### API Token Authentication

```bash
# For CI/CD environments
export RAILWAY_TOKEN=your_token_here

# Verify
railway whoami
```

### Generate API Token

```bash
# Via Railway Dashboard:
# 1. Go to https://railway.app/account/tokens
# 2. Click "Create Token"
# 3. Copy token
# 4. Add to GitHub Secrets as RAILWAY_TOKEN
```

## Essential Commands

### Project Management

```bash
# Initialize new project
railway init

# Link to existing project
railway link

# List all projects
railway list

# Show current project info
railway status
```

### Environment Management

```bash
# List environments
railway environment

# Switch environment
railway environment staging

# Create new environment
# (Usually done via Railway Dashboard)
```

### Deployment

```bash
# Deploy current directory
railway up

# Deploy to specific environment
railway up -e production
railway up -e staging

# Deploy specific service
railway up -s web -e production

# Redeploy last successful build
railway redeploy -e production

# Redeploy specific deployment
railway redeploy [DEPLOYMENT_ID] -e production
```

### Variables

```bash
# List all variables
railway variables

# List for specific environment
railway variables -e production

# Set variable
railway variables set KEY=value
railway variables set KEY=value -e production

# Set multiple variables
railway variables set \
    DEBUG=false \
    LOG_LEVEL=warning \
    WORKERS=4 \
    -e production

# Set from file
railway variables set -f .env.production -e production

# Delete variable
railway variables delete KEY -e production

# Get specific variable
railway variables get KEY -e production
```

### Service Management

```bash
# List services
railway status

# Add new service
railway add

# Add database plugin
railway add --plugin postgresql
railway add --plugin redis
railway add --plugin mysql
railway add --plugin mongodb

# Remove service
railway remove [SERVICE_NAME]

# Restart service
railway restart -s web -e production

# Stop environment
railway down -e staging

# Start environment
railway up -e staging
```

### Logs

```bash
# Stream logs
railway logs

# Logs for specific environment
railway logs -e production

# Logs for specific service
railway logs -s web -e production

# Follow logs (continuous)
railway logs -e production --follow

# Filter logs
railway logs -e production --filter "ERROR"
railway logs -e production --filter "request_id"

# Tail last N lines
railway logs -e production --tail 100

# Logs for specific deployment
railway logs --deployment [DEPLOYMENT_ID]
```

### Database Access

```bash
# Connect to PostgreSQL
railway connect postgres -e production

# Connect to Redis
railway connect redis -e production

# Connect to MySQL
railway connect mysql -e production

# Run command in Railway context
railway run -e production psql
railway run -e production redis-cli
```

### Run Commands

```bash
# Run command in Railway environment
railway run -e production python manage.py migrate

# Run with environment variables loaded
railway run -e production npm run seed

# Interactive shell
railway run -e production bash

# Python REPL with environment loaded
railway run -e production python
```

## Automation Scripts

### Deployment Script

```bash
#!/bin/bash
# scripts/deploy.sh - Complete deployment workflow

set -e

ENVIRONMENT=${1:-staging}

echo "🚀 Deploying to $ENVIRONMENT..."

# 1. Verify Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "Installing Railway CLI..."
    npm i -g @railway/cli
fi

# 2. Verify authentication
railway whoami || railway login

# 3. Run tests locally first
echo "Running tests..."
pytest tests/ -v

# 4. Backup database (production only)
if [[ "$ENVIRONMENT" == "production" ]]; then
    echo "Creating database backup..."
    ./scripts/backup-database.sh production
fi

# 5. Deploy
echo "Deploying to $ENVIRONMENT..."
railway up -e "$ENVIRONMENT"

# 6. Wait for deployment
echo "Waiting for deployment to complete..."
sleep 30

# 7. Run smoke tests
echo "Running smoke tests..."
pytest tests/smoke/ -v --base-url="https://yoto-${ENVIRONMENT}.up.railway.app"

# 8. Verify health check
echo "Verifying health check..."
HEALTH_URL="https://yoto-${ENVIRONMENT}.up.railway.app/health"
if curl -f "$HEALTH_URL"; then
    echo "✅ Deployment successful"
else
    echo "❌ Health check failed"
    exit 1
fi

echo "✅ Deployment complete"
```

### Environment Setup Script

```bash
#!/bin/bash
# scripts/setup-environment.sh - Set up new Railway environment

set -e

ENVIRONMENT=$1

if [[ -z "$ENVIRONMENT" ]]; then
    echo "Usage: ./setup-environment.sh <environment>"
    exit 1
fi

echo "Setting up $ENVIRONMENT environment..."

# 1. Add services
echo "Adding PostgreSQL..."
railway add --plugin postgresql -e "$ENVIRONMENT"

echo "Adding Redis..."
railway add --plugin redis -e "$ENVIRONMENT"

# 2. Set environment variables
echo "Setting environment variables..."
railway variables set ENVIRONMENT="$ENVIRONMENT" -e "$ENVIRONMENT"

# Load from file based on environment
if [[ -f ".env.$ENVIRONMENT" ]]; then
    railway variables set -f ".env.$ENVIRONMENT" -e "$ENVIRONMENT"
fi

# 3. Set secrets from GitHub
if [[ -n "$YOTO_CLIENT_ID" ]]; then
    railway variables set YOTO_CLIENT_ID="$YOTO_CLIENT_ID" -e "$ENVIRONMENT"
fi

if [[ -n "$YOTO_CLIENT_SECRET" ]]; then
    railway variables set YOTO_CLIENT_SECRET="$YOTO_CLIENT_SECRET" -e "$ENVIRONMENT"
fi

# 4. Set reference variables
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}' -e "$ENVIRONMENT"
railway variables set REDIS_URL='${{Redis.REDIS_URL}}' -e "$ENVIRONMENT"

echo "✅ Environment setup complete"
```

### Database Backup Script

```bash
#!/bin/bash
# scripts/backup-database.sh - Backup Railway database

set -e

ENVIRONMENT=${1:-production}
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${ENVIRONMENT}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "📦 Creating backup for $ENVIRONMENT..."

# Create compressed backup
railway run -e "$ENVIRONMENT" pg_dump | gzip > "$BACKUP_FILE"

# Get file size
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

echo "✅ Backup created: $BACKUP_FILE ($SIZE)"

# Optional: Upload to S3
if [[ -n "$AWS_S3_BUCKET" ]]; then
    echo "Uploading to S3..."
    aws s3 cp "$BACKUP_FILE" "s3://$AWS_S3_BUCKET/database-backups/"
    echo "✅ Uploaded to S3"
fi

# Cleanup old backups (keep last 30 days)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "✅ Backup complete"
```

### Migration Script

```bash
#!/bin/bash
# scripts/migrate.sh - Run database migrations safely

set -e

ENVIRONMENT=${1:-staging}

echo "🗄️  Running migrations on $ENVIRONMENT..."

# 1. Backup database first
echo "Creating pre-migration backup..."
./scripts/backup-database.sh "$ENVIRONMENT"

# 2. Check pending migrations
echo "Checking for pending migrations..."
railway run -e "$ENVIRONMENT" alembic current
railway run -e "$ENVIRONMENT" alembic heads

# 3. Show what will be applied
echo "Migrations to apply:"
railway run -e "$ENVIRONMENT" alembic history --verbose

# 4. Confirm
if [[ "$ENVIRONMENT" == "production" ]]; then
    read -p "⚠️  Apply migrations to PRODUCTION? (yes/no): " CONFIRM
    if [[ "$CONFIRM" != "yes" ]]; then
        echo "Aborted"
        exit 0
    fi
fi

# 5. Run migrations
echo "Applying migrations..."
railway run -e "$ENVIRONMENT" alembic upgrade head

# 6. Verify
echo "Verifying database schema..."
railway run -e "$ENVIRONMENT" python scripts/verify_schema.py

echo "✅ Migrations complete"
```

### Variable Sync Script

```bash
#!/bin/bash
# scripts/sync-variables.sh - Sync variables from GitHub Secrets to Railway

set -e

ENVIRONMENT=${1:-production}

echo "🔄 Syncing variables to Railway $ENVIRONMENT..."

# Verify gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is required"
    exit 1
fi

# Get secrets from GitHub
YOTO_CLIENT_ID=$(gh secret get YOTO_CLIENT_ID)
YOTO_CLIENT_SECRET=$(gh secret get YOTO_CLIENT_SECRET)

# Set in Railway
railway variables set YOTO_CLIENT_ID="$YOTO_CLIENT_ID" -e "$ENVIRONMENT"
railway variables set YOTO_CLIENT_SECRET="$YOTO_CLIENT_SECRET" -e "$ENVIRONMENT"

# Environment-specific settings
if [[ "$ENVIRONMENT" == "production" ]]; then
    railway variables set DEBUG=false -e production
    railway variables set LOG_LEVEL=warning -e production
    railway variables set WORKERS=4 -e production
elif [[ "$ENVIRONMENT" == "staging" ]]; then
    railway variables set DEBUG=true -e staging
    railway variables set LOG_LEVEL=info -e staging
    railway variables set WORKERS=2 -e staging
fi

echo "✅ Variables synced successfully"
```

### Health Check Script

```bash
#!/bin/bash
# scripts/health-check.sh - Check health of all environments

set -e

ENVIRONMENTS=("production" "staging")

echo "🏥 Checking health of all environments..."
echo ""

for ENV in "${ENVIRONMENTS[@]}"; do
    echo "Checking $ENV..."
    
    # Get service URL
    URL="https://yoto-${ENV}.up.railway.app/health"
    
    # Check health
    if curl -f -s "$URL" > /dev/null; then
        echo "  ✅ $ENV is healthy"
    else
        echo "  ❌ $ENV is unhealthy"
    fi
    
    echo ""
done

echo "Health check complete"
```

### Cost Estimation Script

```bash
#!/bin/bash
# scripts/estimate-costs.sh - Estimate Railway costs

set -e

echo "💰 Estimating Railway costs..."
echo ""

# Get resource allocations from Railway
PRODUCTION_STATUS=$(railway status -e production --json)
STAGING_STATUS=$(railway status -e staging --json)

# Calculate costs (simplified)
# Actual costs depend on: RAM, CPU, network, storage

echo "Production Environment:"
echo "  Web service: 1GB RAM × 2 replicas = ~\$0.67/month"
echo "  PostgreSQL: 2GB RAM = ~\$0.33/month"
echo "  Redis: 512MB RAM = ~\$0.08/month"
echo "  Network: ~\$1.00/month"
echo "  Subtotal: ~\$2.08/month"
echo ""

echo "Staging Environment:"
echo "  Web service: 512MB RAM × 1 replica = ~\$0.17/month"
echo "  PostgreSQL: 1GB RAM = ~\$0.17/month"
echo "  Subtotal: ~\$0.34/month"
echo ""

echo "Total Estimated Cost: ~\$2.42/month"
echo "Free tier credit: \$5.00/month"
echo "✅ Covered by free tier"
```

### Rollback Script

```bash
#!/bin/bash
# scripts/rollback.sh - Quick rollback to previous deployment

set -e

ENVIRONMENT=${1:-production}

echo "⚠️  Rolling back $ENVIRONMENT..."

# Get recent deployments
echo "Recent deployments:"
railway deployments -e "$ENVIRONMENT" --limit 5

echo ""
echo "Enter deployment ID to rollback to (or 'cancel'):"
read -r DEPLOYMENT_ID

if [[ "$DEPLOYMENT_ID" == "cancel" ]]; then
    echo "Rollback cancelled"
    exit 0
fi

# Confirm
read -p "Confirm rollback to $DEPLOYMENT_ID in $ENVIRONMENT? (yes/no): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo "Rollback cancelled"
    exit 0
fi

# Perform rollback
echo "Rolling back..."
railway redeploy "$DEPLOYMENT_ID" -e "$ENVIRONMENT"

echo "✅ Rollback initiated"

# Wait and verify
sleep 30
./scripts/health-check.sh
```

### Cleanup Script

```bash
#!/bin/bash
# scripts/cleanup.sh - Clean up old resources

set -e

echo "🧹 Cleaning up Railway resources..."

# 1. Remove old database backups
echo "Removing old database backups (>30 days)..."
find backups/ -name "*.sql.gz" -mtime +30 -delete

# 2. Vacuum database
echo "Vacuuming database..."
railway run -e production psql -c "VACUUM ANALYZE;"

# 3. Clean Redis cache
echo "Flushing old Redis keys..."
railway run -e production redis-cli --scan --pattern "cache:*" | \
    xargs -L 1 railway run -e production redis-cli DEL

# 4. Check for unused environments
echo "Checking for PR environments..."
# (Manual check via Railway dashboard)

echo "✅ Cleanup complete"
```

## Makefile for Common Tasks

```makefile
# Makefile - Common Railway operations

.PHONY: help deploy backup migrate health logs

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

deploy-staging: ## Deploy to staging
	./scripts/deploy.sh staging

deploy-production: ## Deploy to production
	./scripts/deploy.sh production

backup: ## Backup production database
	./scripts/backup-database.sh production

migrate-staging: ## Run migrations on staging
	./scripts/migrate.sh staging

migrate-production: ## Run migrations on production
	./scripts/migrate.sh production

health: ## Check health of all environments
	./scripts/health-check.sh

logs: ## Stream production logs
	railway logs -e production --follow

logs-staging: ## Stream staging logs
	railway logs -e staging --follow

rollback: ## Rollback production deployment
	./scripts/rollback.sh production

sync-vars: ## Sync variables from GitHub to Railway
	./scripts/sync-variables.sh production
	./scripts/sync-variables.sh staging

estimate-costs: ## Estimate monthly costs
	./scripts/estimate-costs.sh

cleanup: ## Clean up old resources
	./scripts/cleanup.sh
```

Usage:
```bash
# Show available commands
make help

# Deploy to staging
make deploy-staging

# Check health
make health

# View logs
make logs
```

## Best Practices

### ✅ DO:

1. Use scripts for repeatable tasks
2. Store scripts in version control
3. Add error handling (set -e)
4. Include helpful output messages
5. Verify prerequisites before running
6. Backup before destructive operations
7. Test scripts in staging first
8. Use meaningful script names
9. Document script usage
10. Make scripts idempotent when possible

### ❌ DON'T:

1. Hardcode credentials in scripts
2. Skip error handling
3. Run production commands without confirmation
4. Forget to test scripts
5. Use scripts without understanding them
6. Skip logging/output
7. Make irreversible changes without backups
8. Commit sensitive data in scripts
9. Use scripts without version control
10. Skip documentation

---

**Next Steps:**
- Review [Deployment Workflows](./deployment_workflows.md)
- Set up [Monitoring & Logging](./monitoring_logging.md)
- Implement [Cost Optimization](./cost_optimization.md)
