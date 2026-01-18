# Railway CLI & Automation Scripts

## Table of Contents

- [Railway MCP Server](#railway-mcp-server)
- [Railway CLI Installation](#railway-cli-installation)
- [Authentication](#authentication)
- [Cloud Agent Authentication (Token-Only Mode)](#cloud-agent-authentication-token-only-mode)
- [Essential Commands](#essential-commands)
- [Automation Scripts](#automation-scripts)
- [Makefile for Common Tasks](#makefile-for-common-tasks)
- [Best Practices](#best-practices)

## Overview

This guide covers the Railway CLI, Railway MCP Server, common commands, and automation scripts for managing Railway deployments efficiently.

## Railway MCP Server

### What is Railway MCP Server?

The Railway MCP (Model Context Protocol) Server provides specialized Railway management tools that can be used directly from AI coding agents like GitHub Copilot Workspace. It enables natural language interaction with Railway infrastructure.

**Official Repository**: https://github.com/railwayapp/railway-mcp-server

### Configuration

The Railway MCP Server is configured in `.github/copilot-workspace.yml`:

```yaml
mcp_servers:
  railway-mcp-server:
    command: npx
    args:
      - "-y"
      - "@railway/mcp-server"
```

For other editors:

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "railway-mcp-server": {
      "command": "npx",
      "args": ["-y", "@railway/mcp-server"]
    }
  }
}
```

**VS Code** (`.vscode/mcp.json`):
```json
{
  "servers": {
    "railway-mcp-server": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@railway/mcp-server"]
    }
  }
}
```

### Available MCP Tools

The Railway MCP Server provides these tools:

**Project Management:**
- `list-projects` - List all Railway projects
- `create-project-and-link` - Create and link new projects

**Service Management:**
- `list-services` - List services in a project
- `link-service` - Link a service to current directory
- `deploy` - Deploy a service
- `deploy-template` - Deploy from Railway Template Library

**Environment Management:**
- `create-environment` - Create new environments
- `link-environment` - Link environment to directory

**Configuration & Variables:**
- `list-variables` - List environment variables
- `set-variables` - Set environment variables
- `generate-domain` - Generate railway.app domains

**Monitoring & Logs:**
- `get-logs` - Retrieve build/deployment logs
  - Railway CLI v4.9.0+: Supports line limits and filtering
  - Older versions: Stream logs without filtering

**Status Check:**
- `check-railway-status` - Verify CLI installation and login

### Usage Examples

Use natural language commands with the MCP server:

```
# Deploy from template
"Deploy a Postgres database for my application"

# Create and deploy
"Create a Next.js app in this directory and deploy it to Railway.
Also assign it a domain."

# Environment management
"Create a development environment that duplicates production settings"

# Variable management
"Pull environment variables for my project and save them in .env"

# Logs
"Show me the last 100 lines of deployment logs"
"Show me error logs from the last deployment"
```

### Prerequisites

The Railway MCP Server requires:
- Railway CLI installed and accessible in PATH
- User logged in (`railway login` or `RAILWAY_TOKEN` set)
- npx available (comes with Node.js)

### Security Considerations

- **No Destructive Actions**: By design, the MCP server doesn't include destructive operations (no delete commands)
- **Authentication Required**: All operations require valid Railway authentication
- **Permission Respect**: Railway's existing permission model is enforced
- **Monitoring**: Always review commands before execution

### Documentation References

- **MCP Server GitHub**: https://github.com/railwayapp/railway-mcp-server
- **Copilot Workspace Config**: See `docs/COPILOT_WORKSPACE_NETWORK_CONFIG.md` for full documentation
- **Railway CLI Reference**: https://docs.railway.com/reference/cli

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

## Cloud Agent Authentication (Token-Only Mode)

### Overview

**Cloud Agents** (e.g., GitHub Copilot Workspace) cannot use interactive `railway login` but can use Railway CLI with the `RAILWAY_TOKEN` environment variable. This provides full CLI functionality without browser authentication.

**Key Points:**
- ❌ No `railway login` (interactive browser login unavailable)
- ✅ All commands work with `RAILWAY_TOKEN` environment variable
- ✅ Token is automatically available in Cloud Agent sessions (may be named `RAILWAY_TOKEN_XX` for PR environments)
- ⚠️ Token must have appropriate project/environment permissions

### Token Resolution for Cloud Agents

Railway tokens may be provided with different variable names depending on context:

```bash
# Generic token (most common)
export RAILWAY_TOKEN="${RAILWAY_TOKEN}"

# PR-specific token (e.g., PR #86 uses RAILWAY_TOKEN_86)
# If RAILWAY_TOKEN is not set, check for PR-specific token
if [ -z "$RAILWAY_TOKEN" ]; then
  # Extract PR number from GitHub context
  if [[ "$GITHUB_REF" =~ refs/pull/([0-9]+)/merge ]] || \
     [[ "$GITHUB_REF" =~ refs/heads/copilot.*-([0-9]+) ]]; then
    PR_NUM="${BASH_REMATCH[1]}"
    PR_TOKEN_VAR="RAILWAY_TOKEN_${PR_NUM}"

    # Use PR-specific token if available
    if [ -n "${!PR_TOKEN_VAR}" ]; then
      export RAILWAY_TOKEN="${!PR_TOKEN_VAR}"
      echo "✅ Using ${PR_TOKEN_VAR} for Railway authentication"
    fi
  fi
fi

# Verify token is now set
if [ -z "$RAILWAY_TOKEN" ]; then
  echo "❌ Error: No Railway token found"
  echo "Expected RAILWAY_TOKEN or RAILWAY_TOKEN_XX environment variable"
  exit 1
fi
```

### Quick Start for Cloud Agents

**Step 1: Set up Railway token**

```bash
# Auto-detect and set RAILWAY_TOKEN from available tokens
if [ -z "$RAILWAY_TOKEN" ]; then
  # Check for PR-specific token (RAILWAY_TOKEN_86, etc.)
  for var in $(env | grep '^RAILWAY_TOKEN_' | cut -d= -f1); do
    export RAILWAY_TOKEN="${!var}"
    echo "✅ Using $var as RAILWAY_TOKEN"
    break
  done
fi

# Verify
if [ -z "$RAILWAY_TOKEN" ]; then
  echo "❌ No Railway token available"
  exit 1
fi
```

**Step 2: Verify authentication**

```bash
# Check Railway CLI version
railway --version

# Test authentication
railway whoami
```

**Step 3: Link service and environment**

```bash
# For this project, use these exact values:
railway service link yoto-smart-stream

# For PR environments, link to the PR environment name
# Environment name format: pr-{NUMBER} (e.g., pr-86, pr-123)
railway environment link pr-86

# Verify linking
railway status --json
```

### Complete Setup Script for Cloud Agents

Copy and run this script at the start of your session:

```bash
#!/bin/bash
# Railway CLI setup for Cloud Agent sessions

echo "🔧 Setting up Railway CLI for Cloud Agent..."

# 1. Auto-detect and set RAILWAY_TOKEN
if [ -z "$RAILWAY_TOKEN" ]; then
  echo "🔍 RAILWAY_TOKEN not set, checking for PR-specific tokens..."

  # Look for RAILWAY_TOKEN_XX variables
  for var in $(env | grep '^RAILWAY_TOKEN_' | cut -d= -f1); do
    export RAILWAY_TOKEN="${!var}"
    echo "✅ Using $var as RAILWAY_TOKEN"
    break
  done
fi

# Verify token
if [ -z "$RAILWAY_TOKEN" ]; then
  echo "❌ Error: No Railway token found"
  echo "Expected RAILWAY_TOKEN or RAILWAY_TOKEN_XX environment variable"
  exit 1
fi
echo "✅ RAILWAY_TOKEN is set"

# 2. Determine environment from branch/PR context
if [[ "$GITHUB_REF" =~ refs/pull/([0-9]+)/merge ]]; then
  PR_NUMBER="${BASH_REMATCH[1]}"
  ENV_NAME="pr-${PR_NUMBER}"
  echo "📋 Detected PR #${PR_NUMBER} → Environment: ${ENV_NAME}"
elif [[ "$GITHUB_REF_NAME" =~ pr-([0-9]+) ]]; then
  PR_NUMBER="${BASH_REMATCH[1]}"
  ENV_NAME="pr-${PR_NUMBER}"
  echo "📋 Detected PR #${PR_NUMBER} from branch → Environment: ${ENV_NAME}"
elif [ "$GITHUB_REF" == "refs/heads/main" ]; then
  ENV_NAME="production"
  echo "📋 Detected main branch → Environment: ${ENV_NAME}"
else
  # Try to extract from token variable name
  for var in $(env | grep '^RAILWAY_TOKEN_' | cut -d= -f1); do
    if [[ "$var" =~ RAILWAY_TOKEN_([0-9]+) ]]; then
      PR_NUMBER="${BASH_REMATCH[1]}"
      ENV_NAME="pr-${PR_NUMBER}"
      echo "📋 Detected PR #${PR_NUMBER} from token variable → Environment: ${ENV_NAME}"
      break
    fi
  done

  # Default to production if nothing detected
  if [ -z "$ENV_NAME" ]; then
    ENV_NAME="production"
    echo "📋 Using default → Environment: ${ENV_NAME}"
  fi
fi

# 3. Link service and environment
echo ""
echo "🔗 Linking to Railway service: yoto-smart-stream"
if railway service link yoto-smart-stream; then
  echo "✅ Service linked"
else
  echo "⚠️  Service link failed, but may already be linked"
fi

echo ""
echo "🔗 Linking to environment: ${ENV_NAME}"
if railway environment link "$ENV_NAME"; then
  echo "✅ Environment linked"
else
  echo "⚠️  Environment link failed, but may already be linked"
fi

# 4. Verify setup
echo ""
echo "📊 Verifying Railway CLI setup..."
if railway status --json > /dev/null 2>&1; then
  echo "✅ Railway CLI is ready!"
  echo ""
  echo "Available commands:"
  echo "  railway status --json          # Project/service info"
  echo "  railway logs --lines 50 --json # Recent logs"
  echo "  railway var list --json        # Environment variables"
  echo "  railway deployment list --json # Deployments"
else
  echo "⚠️  Railway CLI setup incomplete"
  echo "Try running: railway whoami"
fi
```

**Save as `setup_railway.sh` and run:**
```bash
chmod +x setup_railway.sh
./setup_railway.sh
```

### Available Commands (Cloud Agent Mode)

Once linked, these commands work without interactive login:

#### Deployment Commands

```bash
# List deployments (JSON format recommended)
railway deployment list --json

# Upload and deploy from current directory
# --json implies CI mode (stream build logs, then exit)
railway up --json

# Redeploy latest deployment
railway deployment redeploy --yes --json

# Restart service (without rebuilding)
railway restart --yes --json

# Remove most recent deployment
railway down --yes
```

#### Log Commands

```bash
# View logs (extensive options available)
railway logs                              # Stream live logs
railway logs --build                      # Show build logs
railway logs --deployment                 # Show deployment logs
railway logs --json                       # JSON format
railway logs --lines 100                  # Last 100 lines (no streaming)
railway logs --filter "@level:error"      # Filter by level
railway logs --filter "@level:warn AND rate limit"  # Complex filters
railway logs --since 1h                   # Time-based
railway logs --latest                     # Latest deployment (even if failed)
```

**Log Filter Syntax:**
- `@level:error` - Error logs only
- `@level:warn` - Warning logs
- `"search term"` - Text search
- `AND`, `OR` - Combine filters
- `-@level:debug` - Exclude debug logs

**Examples:**
```bash
# Last 10 error logs in JSON
railway logs --lines 10 --filter "@level:error" --json

# Stream logs from latest deployment
railway logs --latest --json

# Logs from last hour
railway logs --since 1h --json
```

#### Status & Info Commands

```bash
# Show project/service information
railway status --json

# List environment variables
railway var list --json

# Set environment variable
railway var set KEY="VALUE"

# Delete environment variable
railway var delete KEY
```

#### SSH Access

```bash
# Connect to service instance (for debugging)
railway ssh
```

### Complete Cloud Agent Workflow Example

```bash
# 1. Verify RAILWAY_TOKEN is set
if [ -z "$RAILWAY_TOKEN" ]; then
  echo "Error: RAILWAY_TOKEN not set"
  exit 1
fi

# 2. Link service and environment (once per session)
railway service link yoto-smart-stream
railway environment link yoto-smart-stream-pr-88

# 3. Check status
railway status --json

# 4. Deploy
railway up --json

# 5. View logs
railway logs --lines 50 --filter "@level:error" --json

# 6. Check environment variables
railway var list --json
```

### Best Practices for Cloud Agents

1. **Always use `--json` flag** for machine-readable output
2. **Filter logs aggressively** with `--filter` and `--lines` to reduce output
3. **Use `--yes` flag** to skip confirmations (non-interactive)
4. **Link service/environment at session start** to avoid repeated `-s`/`-e` flags
5. **Prefer `--latest` for logs** when debugging failed deployments
6. **Use time-based log queries** (`--since`, `--until`) for specific windows

### Troubleshooting

**"Not logged in" errors:**
```bash
# Verify RAILWAY_TOKEN is set
echo $RAILWAY_TOKEN

# Should show token UUID
# If empty, token needs to be provisioned
```

**"No service linked" errors:**
```bash
# Re-link service
railway service link yoto-smart-stream

# Verify with status
railway status --json
```

**"No environment linked" errors:**
```bash
# Re-link environment
railway environment link yoto-smart-stream-pr-88

# Verify
railway status --json
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

**ALWAYS prefer filtering logs for efficiency when using Railway CLI.**

```bash
# Stream logs
railway logs

# Logs for specific environment
railway logs -e production

# Logs for specific service
railway logs -s web -e production

# Follow logs (continuous)
railway logs -e production --follow

# Tail last N lines
railway logs -e production --tail 100

# Logs for specific deployment
railway logs --deployment [DEPLOYMENT_ID]

# Show deployment/build logs
railway logs --deployment  # Show deployment logs
railway logs --build       # Show build logs
```

#### Railway Log Filter Syntax

Railway supports powerful filter syntax for querying logs:

**Filter Operators:**
- `"<search term>"` - Filter for partial substring match
- `@attribute:value` - Filter by custom attribute
- `@level:error` - Filter by error level
- `@level:warn` - Filter by warning level
- `@level:info` - Filter by info level
- `@level:debug` - Filter by debug level
- `AND`, `OR` - Combine filters
- `-` - NOT operator (exclude)

**Common Examples:**

```bash
# Find logs with error level
railway logs --filter "@level:error"

# Find error logs containing specific text
railway logs --filter "@level:error AND \"failed to connect\""

# Find logs containing a substring
railway logs --filter "\"POST /api\""
railway logs --filter "\"uvicorn\" OR \"startup\""

# Exclude specific level
railway logs --filter "-@level:debug"

# Stream latest deployment logs (even if failed/building)
railway logs --latest --json
# After timeout, send ^C to exit

# By time
railway logs --since "1h" --json
railway logs --since "30m" --json

# By number of lines
railway logs --lines 100 --json
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
