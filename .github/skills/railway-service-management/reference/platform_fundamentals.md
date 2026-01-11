# Railway Platform Fundamentals

## Overview

Railway.app is a modern Platform-as-a-Service (PaaS) that simplifies application deployment and infrastructure management. It provides a seamless experience from development to production with minimal configuration.

## Core Concepts

### Projects

**What:** A project is the top-level container in Railway that holds all your environments, services, and resources.

**Key Features:**
- Single billing unit
- Shared team access
- Contains multiple environments
- Centralized logging and monitoring

**Example Structure:**
```
yoto-smart-stream (Project)
├── production (Environment)
│   ├── web (Service)
│   ├── postgres (Service)
│   └── redis (Service)
├── staging (Environment)
│   ├── web (Service)
│   └── postgres (Service)
└── pr-123 (Environment - ephemeral)
    └── web (Service)
```

### Environments

**What:** Isolated deployment contexts within a project. Each environment has its own services, variables, and deployments.

**Types:**
1. **Production** - Customer-facing, stable releases
2. **Staging** - Pre-production testing and QA
3. **Development** - Active development and testing
4. **PR Environments** - Ephemeral environments for pull requests

**Characteristics:**
- Separate configurations per environment
- Independent resource allocation
- Environment-specific URLs
- Isolated databases and services

### Services

**What:** Individual deployable units within an environment (applications, databases, caching layers).

**Service Types:**

1. **Application Services**
   - Your code (FastAPI, Flask, Express, etc.)
   - Build from GitHub repository
   - Configurable start commands
   - Custom health checks

2. **Database Services**
   - PostgreSQL (most common)
   - MySQL
   - MongoDB
   - Managed by Railway with automatic backups

3. **Caching Services**
   - Redis
   - Managed by Railway
   - Shared or dedicated instances

4. **Custom Services**
   - Message queues (RabbitMQ)
   - Search engines (Elasticsearch)
   - Any containerized service

### Deployments

**What:** Immutable builds of your service at a specific point in time.

**Lifecycle:**
1. **Triggered** - By git push, manual deploy, or API call
2. **Building** - Code is built into container image
3. **Deploying** - Container is started with environment variables
4. **Active** - Deployment is live and serving traffic
5. **Crashed/Failed** - Deployment failed health checks

**Key Features:**
- Instant rollback to previous deployments
- Deployment history retained
- Zero-downtime deployments (when configured)
- Automatic restarts on failure

## Railway Architecture

### Build Process

```
GitHub Repository
       ↓
Railway detects change
       ↓
Clone repository
       ↓
Detect build method (Nixpacks/Dockerfile)
       ↓
Build container image
       ↓
Push to Railway registry
       ↓
Deploy to environment
       ↓
Run health check
       ↓
Service live
```

### Networking

**Internal Networking:**
- Services within same environment can communicate via private network
- Use service names as hostnames (e.g., `postgres:5432`)
- Low latency, no external bandwidth charges

**External Access:**
- Each service gets a unique public URL (e.g., `myapp.up.railway.app`)
- Custom domains supported (CNAME or ALIAS records)
- HTTPS automatically provisioned via Let's Encrypt

**Example:**
```python
# Internal connection (same environment)
DATABASE_URL = "postgresql://postgres:5432/mydb"

# External connection (different environment or local dev)
DATABASE_URL = "postgresql://user:pass@postgres.railway.internal:5432/mydb"
```

### Resource Allocation

**Default Limits (Free Tier):**
- 512 MB RAM per service
- 1 vCPU shared
- 1 GB storage
- $5/month usage credit

**Paid Plans:**
- Custom RAM allocation (up to 32 GB)
- Dedicated vCPUs
- Increased storage
- Pay-as-you-go pricing

**Scaling Options:**
- Vertical: Increase RAM/CPU per instance
- Horizontal: Multiple replicas (load balanced)

## Build Methods

### Nixpacks (Automatic)

Railway's default build system that automatically detects your tech stack.

**Supported Languages:**
- Python (detects requirements.txt, pyproject.toml)
- Node.js (detects package.json)
- Go (detects go.mod)
- Ruby (detects Gemfile)
- PHP (detects composer.json)
- Rust (detects Cargo.toml)

**Python Example:**
```bash
# Railway automatically detects:
# - requirements.txt → pip install -r requirements.txt
# - Procfile → uses specified command
# - Or: gunicorn main:app (default for Python web apps)
```

### Dockerfile (Custom)

For complete control over the build process.

**Example:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

### railway.toml (Configuration)

Optional file for fine-tuning build and deploy process.

**Example:**
```toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt && pip install -r requirements-prod.txt"

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT --workers 4"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

## Variable Management

### Variable Types

1. **Raw Variables** - Plain text values
   ```
   DEBUG=true
   LOG_LEVEL=info
   ```

2. **Reference Variables** - Point to other service variables
   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   ```

3. **Shared Variables** - Defined at project level, available to all services
   ```
   REGION=us-east-1
   CDN_URL=https://cdn.example.com
   ```

### Variable Precedence

1. Service-specific variables (highest priority)
2. Environment variables
3. Shared project variables
4. Railway-provided variables (e.g., PORT, RAILWAY_ENVIRONMENT_NAME)

### Railway-Provided Variables

```bash
PORT                    # Port to bind to (required)
RAILWAY_ENVIRONMENT_NAME # Environment name (production, staging, etc.)
RAILWAY_SERVICE_NAME    # Service name
RAILWAY_PROJECT_ID      # Project ID
RAILWAY_DEPLOYMENT_ID   # Current deployment ID
RAILWAY_GIT_BRANCH      # Git branch that triggered deployment
RAILWAY_GIT_COMMIT_SHA  # Commit SHA
```

## Data Persistence

### Volumes

**What:** Persistent storage that survives deployments and restarts.

**Use Cases:**
- File uploads
- SQLite databases
- Logs
- Cache files
- Authentication tokens (e.g., OAuth refresh tokens)

**Configuration in railway.toml:**
```toml
# railway.toml
[deploy]
# Define persistent volumes
[[deploy.volumes]]
name = "uploads"
mountPath = "/app/uploads"

[[deploy.volumes]]
name = "data"
mountPath = "/data"
```

**Alternative Array Syntax:**
```toml
# railway.toml
[deploy]
volumes = [
  { name = "uploads", mountPath = "/app/uploads" },
  { name = "data", mountPath = "/data" }
]
```

**Best Practices:**
- Use absolute paths for mount points (e.g., `/data`, `/app/uploads`)
- Ensure your application creates parent directories if they don't exist
- Volumes are specific to each environment (production, staging, PR environments each have separate volumes)
- Volume data persists across deployments but is tied to the service instance

**Real-World Example - Persistent Auth Tokens:**
```toml
# railway.toml - Store OAuth refresh tokens
[[deploy.volumes]]
name = "data"
mountPath = "/data"
```

```python
# config.py - Use volume for token storage
import os
from pathlib import Path

def get_token_path():
    # Use /data volume on Railway, local path in development
    if os.environ.get("RAILWAY_ENVIRONMENT_NAME"):
        return Path("/data/.yoto_refresh_token")
    return Path(".yoto_refresh_token")
```

**Limitations:**
- Not suitable for multi-replica services (no shared filesystem)
- For shared storage across replicas, use S3, Cloudinary, or similar object storage
- Volume size limits apply (check Railway dashboard for current limits)

### Databases

**Managed Databases:**
- Automatic backups (daily)
- Point-in-time recovery
- Connection pooling
- Automatic scaling (paid plans)

**Database Plugins:**
```bash
# Add PostgreSQL
railway add --plugin postgresql

# Add MySQL
railway add --plugin mysql

# Add MongoDB
railway add --plugin mongodb

# Add Redis
railway add --plugin redis
```

## Service Communication

### Same Environment

```python
# Python example - connecting to services in same environment
import os

# PostgreSQL (using reference variable)
DATABASE_URL = os.getenv("DATABASE_URL")  # ${{Postgres.DATABASE_URL}}

# Redis (using reference variable)
REDIS_URL = os.getenv("REDIS_URL")  # ${{Redis.REDIS_URL}}

# Another service in same environment
API_URL = os.getenv("API_URL")  # ${{API.RAILWAY_PUBLIC_DOMAIN}}
```

### Cross-Environment

Not recommended for production, but possible:
```python
# Use public URLs for cross-environment communication
STAGING_API = "https://staging.myapp.railway.app"
```

## Deployment Triggers

### Automatic Triggers

1. **GitHub Push**
   - Commit pushed to watched branch
   - Railway automatically deploys

2. **PR Creation**
   - Optional: Create ephemeral environment for PR
   - Destroyed when PR is closed/merged

3. **Manual Deploy**
   - Via Railway dashboard
   - Via Railway CLI
   - Via API

### Deployment Strategies

**Rolling Deployment (Default):**
- New version deployed alongside old
- Health check passes
- Traffic switched to new version
- Old version shut down

**Blue-Green Deployment (Manual):**
- Deploy to separate environment
- Test thoroughly
- Switch traffic via DNS/load balancer
- Keep old environment for rollback

## Health Checks

### Configuration

```toml
# railway.toml
[deploy]
healthcheckPath = "/health"
healthcheckTimeout = 100  # seconds
```

### Implementation

```python
# Python/FastAPI example
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
async def health_check():
    """Railway health check endpoint"""
    return {
        "status": "healthy",
        "service": "yoto-smart-stream",
        "version": "1.0.0"
    }
```

**Health Check Behavior:**
- Railway polls health check endpoint
- If fails, deployment marked as failed
- Previous deployment kept running
- Automatic rollback if health check never passes

## Logging

### Log Streaming

```bash
# View logs in real-time
railway logs -e production

# Filter logs
railway logs -e production --filter "ERROR"

# Follow logs
railway logs -e production --follow

# View specific service
railway logs -s web -e production
```

### Log Structure

```json
{
  "timestamp": "2024-01-10T19:00:00Z",
  "level": "info",
  "message": "Starting server on port 8000",
  "service": "web",
  "environment": "production"
}
```

### Best Practices

1. Use structured logging (JSON)
2. Include request IDs for tracing
3. Log at appropriate levels (DEBUG, INFO, WARNING, ERROR)
4. Don't log secrets or PII
5. Use log aggregation for production (e.g., Sentry, Datadog)

## Railway CLI

### Installation

```bash
# npm
npm i -g @railway/cli

# Homebrew (macOS)
brew install railway

# Scoop (Windows)
scoop install railway
```

### Common Commands

```bash
# Authentication
railway login
railway whoami

# Project management
railway init          # Create new project
railway link          # Link to existing project
railway list          # List all projects

# Deployment
railway up            # Deploy current directory
railway up -e prod    # Deploy to specific environment
railway redeploy      # Redeploy last successful build

# Variables
railway variables                      # List variables
railway variables set KEY=value        # Set variable
railway variables set KEY=value -e prod  # Set in specific env
railway variables delete KEY           # Delete variable

# Services
railway status        # View service status
railway logs          # Stream logs
railway connect       # Connect to service (e.g., database)
railway run           # Run command in Railway context

# Environments
railway environment   # List environments
railway environment add staging  # Add new environment
```

## Railway Dashboard

### Key Features

1. **Project Overview**
   - All environments and services
   - Resource usage
   - Deployment status

2. **Service View**
   - Deployment history
   - Logs
   - Metrics (CPU, memory, network)
   - Variables
   - Settings

3. **Deployments**
   - Build logs
   - Deployment timeline
   - Rollback button
   - Health check status

4. **Settings**
   - GitHub integration
   - Custom domains
   - Team management
   - Billing

## Pricing

### Free Tier
- $5 usage credit per month
- All features included
- Suitable for hobby projects and development

### Paid Plans
- Pay-as-you-go after free tier
- ~$0.000231 per GB-hour of RAM
- ~$0.000463 per vCPU-hour
- Volume storage: $0.25 per GB/month
- Network egress: $0.10 per GB

### Cost Estimation

**Small Production App:**
- 1 web service (512 MB RAM, 0.5 vCPU)
- 1 PostgreSQL (512 MB RAM)
- ~$10-15/month

**Medium Production App:**
- 2 web replicas (1 GB RAM each, 1 vCPU)
- 1 PostgreSQL (2 GB RAM)
- 1 Redis (512 MB RAM)
- ~$30-40/month

## Best Practices

### ✅ DO:

1. Use environments for different stages (dev, staging, prod)
2. Configure health check endpoints
3. Use Railway's reference variables for service URLs
4. Monitor resource usage and right-size services
5. Set up automatic deployments from main branches
6. Use railway.toml for complex configurations
7. Implement structured logging
8. Set restart policies for resilience

### ❌ DON'T:

1. Commit secrets to repository
2. Run multiple environments in single Railway environment
3. Ignore deployment failures
4. Over-provision resources unnecessarily
5. Skip health checks
6. Use volumes for multi-replica services
7. Hardcode service URLs
8. Ignore logs and metrics

## Troubleshooting

### Deployment Fails

```bash
# Check build logs
railway logs -e production

# Common issues:
# - Missing dependencies in requirements.txt
# - Port not set to $PORT
# - Health check failing
# - Build timeout (increase in settings)
```

### Service Not Responding

```bash
# Check if service is running
railway status -e production

# Check logs for errors
railway logs -e production --filter "ERROR"

# Verify environment variables
railway variables -e production

# Restart service
railway restart -s web -e production
```

### Database Connection Issues

```bash
# Verify DATABASE_URL is set
railway variables -e production | grep DATABASE_URL

# Test connection
railway connect postgres -e production

# Check if database service is running
railway status -e production
```

---

**Next Steps:**
- Review [Multi-Environment Architecture](./multi_environment_architecture.md)
- Set up [Secrets Management](./secrets_management.md)
- Configure [Deployment Workflows](./deployment_workflows.md)
