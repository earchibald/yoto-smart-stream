# Configuration Management for Railway

## Overview

Effective configuration management is crucial for maintaining multiple environments and ensuring secure, consistent deployments. This guide covers environment variables, configuration patterns, and best practices.

## Configuration Hierarchy

### Variable Precedence (Highest to Lowest)

1. **Service Variables** - Specific to a service within an environment
2. **Environment Variables** - Specific to an environment
3. **Shared Variables** - Project-level, available to all services
4. **Railway System Variables** - Automatically provided by Railway
5. **Default Values** - Hardcoded fallbacks in application

## Railway-Provided Variables

### Automatic Variables

```bash
# Always available
PORT                      # Port your service should listen on (required)
RAILWAY_ENVIRONMENT_NAME  # Current environment name (e.g., "staging", "production", "pr-123")
RAILWAY_SERVICE_NAME      # Service name
RAILWAY_PROJECT_ID        # Unique project identifier
RAILWAY_DEPLOYMENT_ID     # Current deployment identifier

# Git information
RAILWAY_GIT_BRANCH        # Branch that triggered deployment
RAILWAY_GIT_COMMIT_SHA    # Full commit SHA
RAILWAY_GIT_COMMIT_MESSAGE # Commit message
RAILWAY_GIT_AUTHOR        # Commit author
RAILWAY_GIT_REPO_NAME     # Repository name
RAILWAY_GIT_REPO_OWNER    # Repository owner

# Service URLs
RAILWAY_PUBLIC_DOMAIN     # Public URL for this service
RAILWAY_PRIVATE_DOMAIN    # Internal URL for service-to-service communication

# Build information
RAILWAY_BUILDER           # Build method (NIXPACKS/DOCKERFILE)
```

### Using Railway Variables

```python
# config.py
import os

class Config:
    # Use Railway-provided PORT
    PORT = int(os.getenv("PORT", 8000))
    
    # Environment detection - Use RAILWAY_ENVIRONMENT_NAME
    ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
    
    # Service information
    SERVICE_NAME = os.getenv("RAILWAY_SERVICE_NAME", "unknown")
    
    # Deployment tracking
    DEPLOYMENT_ID = os.getenv("RAILWAY_DEPLOYMENT_ID", "local")
    GIT_SHA = os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown")
```

## Configuration Patterns

### Environment-Based Configuration

```python
# config.py - Environment-based configuration
import os
from typing import Optional

class BaseConfig:
    """Base configuration shared across all environments"""
    
    # Application
    APP_NAME = "Yoto Smart Stream"
    API_VERSION = "v1"
    
    # Railway automatic variables
    PORT = int(os.getenv("PORT", 8000))
    ENVIRONMENT = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
    
    # Yoto API
    YOTO_CLIENT_ID = os.getenv("YOTO_CLIENT_ID", "")
    YOTO_CLIENT_SECRET = os.getenv("YOTO_CLIENT_SECRET", "")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "")
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        required = ["YOTO_CLIENT_ID", "YOTO_CLIENT_SECRET", "DATABASE_URL"]
        missing = [var for var in required if not getattr(cls, var)]
        
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")


class DevelopmentConfig(BaseConfig):
    """Development environment configuration"""
    DEBUG = True
    LOG_LEVEL = "DEBUG"
    WORKERS = 1
    RELOAD = True
    TESTING = False
    
    # Development-specific
    CORS_ORIGINS = ["*"]
    RATE_LIMIT_ENABLED = False


class StagingConfig(BaseConfig):
    """Staging environment configuration"""
    DEBUG = True
    LOG_LEVEL = "INFO"
    WORKERS = 2
    RELOAD = False
    TESTING = False
    
    # Staging-specific
    CORS_ORIGINS = ["https://staging.example.com"]
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT = "100/minute"


class ProductionConfig(BaseConfig):
    """Production environment configuration"""
    DEBUG = False
    LOG_LEVEL = "WARNING"
    WORKERS = 4
    RELOAD = False
    TESTING = False
    
    # Production-specific
    CORS_ORIGINS = ["https://example.com"]
    RATE_LIMIT_ENABLED = True
    RATE_LIMIT = "60/minute"
    
    # Additional security
    SECURE_COOKIES = True
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True

# Configuration factory
def get_config():
    """Get configuration based on RAILWAY_ENVIRONMENT_NAME"""
    env = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development").lower()
    
    config_map = {
        "development": DevelopmentConfig,
        "staging": StagingConfig,
        "production": ProductionConfig,
    }
    
    config_class = config_map.get(env, DevelopmentConfig)
    config_class.validate()
    
    return config_class()


# Load configuration
Config = get_config()
```

### Using Configuration

```python
# main.py
from fastapi import FastAPI
from config import Config

app = FastAPI(
    title=Config.APP_NAME,
    debug=Config.DEBUG
)

@app.on_event("startup")
async def startup():
    print(f"Starting {Config.APP_NAME}")
    print(f"Environment: {Config.ENVIRONMENT}")
    print(f"Debug: {Config.DEBUG}")
    print(f"Workers: {Config.WORKERS}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=Config.PORT,
        workers=Config.WORKERS,
        reload=Config.RELOAD,
        log_level=Config.LOG_LEVEL.lower()
    )
```

## Setting Variables in Railway

### Via Railway CLI

```bash
# Set single variable
railway variables set KEY=value -e production

# Set multiple variables
railway variables set \
    DEBUG=false \
    LOG_LEVEL=warning \
    WORKERS=4 \
    -e production

# Set from file
cat << EOF > prod-vars.txt
DEBUG=false
LOG_LEVEL=warning
WORKERS=4
EOF
railway variables set -f prod-vars.txt -e production

# Set reference variable (to another service)
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}' -e production
railway variables set REDIS_URL='${{Redis.REDIS_URL}}' -e production

# Delete variable
railway variables delete KEY -e production

# List all variables
railway variables -e production
```

### Via Railway Dashboard

1. Navigate to project → environment → service
2. Click **Variables** tab
3. Click **Add Variable**
4. Enter key-value pairs
5. Click **Deploy** to apply changes

### Via GitHub Actions

```yaml
# .github/workflows/sync-variables.yml
name: Sync Variables to Railway

on:
  workflow_dispatch:
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production

jobs:
  sync:
    runs-on: ubuntu-latest
    
    steps:
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Sync application variables
        run: |
          railway variables set YOTO_CLIENT_ID="${{ secrets.YOTO_CLIENT_ID }}" \
            -e ${{ github.event.inputs.environment }}
          railway variables set YOTO_CLIENT_SECRET="${{ secrets.YOTO_CLIENT_SECRET }}" \
            -e ${{ github.event.inputs.environment }}
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
      
      - name: Set environment-specific variables
        run: |
          if [[ "${{ github.event.inputs.environment }}" == "production" ]]; then
            railway variables set DEBUG=false -e production
            railway variables set LOG_LEVEL=warning -e production
            railway variables set WORKERS=4 -e production
          else
            railway variables set DEBUG=true -e staging
            railway variables set LOG_LEVEL=info -e staging
            railway variables set WORKERS=2 -e staging
          fi
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Reference Variables

### Service-to-Service References

```bash
# Web service references database
railway variables set DATABASE_URL='${{Postgres.DATABASE_URL}}' -e production

# Web service references Redis
railway variables set REDIS_URL='${{Redis.REDIS_URL}}' -e production

# API service references another service
railway variables set INTERNAL_API_URL='${{InternalAPI.RAILWAY_PRIVATE_DOMAIN}}' -e production
```

### Common Reference Patterns

```bash
# Database plugins
${{Postgres.DATABASE_URL}}          # Full PostgreSQL connection string
${{Postgres.PGHOST}}                # PostgreSQL host
${{Postgres.PGPORT}}                # PostgreSQL port
${{Postgres.PGDATABASE}}            # Database name
${{Postgres.PGUSER}}                # Database user
${{Postgres.PGPASSWORD}}            # Database password

# Redis plugins
${{Redis.REDIS_URL}}                # Full Redis connection string
${{Redis.REDIS_HOST}}               # Redis host
${{Redis.REDIS_PORT}}               # Redis port

# Service URLs
${{ServiceName.RAILWAY_PUBLIC_DOMAIN}}   # Public URL
${{ServiceName.RAILWAY_PRIVATE_DOMAIN}}  # Internal URL
```

## Configuration Files

### railway.toml

```toml
# railway.toml - Railway-specific configuration
[build]
builder = "NIXPACKS"  # or "DOCKERFILE"
buildCommand = "pip install -r requirements.txt"
watchPatterns = ["**/*.py", "requirements.txt"]

[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT --workers $WORKERS"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10

# Volume mounts (persistent storage)
[[deploy.volumes]]
name = "uploads"
mountPath = "/app/uploads"

[[deploy.volumes]]
name = "data"
mountPath = "/app/data"

# Port configuration
[deploy.ports]
web = 8000
```

### .env.example

```bash
# .env.example - Template for local development
# Copy to .env and fill in actual values

# Yoto API Configuration
YOTO_CLIENT_ID=your_client_id_here
YOTO_CLIENT_SECRET=your_client_secret_here

# Database Configuration
DATABASE_URL=postgresql://localhost:5432/yoto_dev

# Redis Configuration (optional)
REDIS_URL=redis://localhost:6379

# Application Configuration
# Note: In Railway, use RAILWAY_ENVIRONMENT_NAME (automatically set)
# For local development, you can set ENVIRONMENT if needed
DEBUG=true
LOG_LEVEL=debug
PORT=8000
WORKERS=1

# Feature Flags
ENABLE_MQTT=true
ENABLE_ICON_MANAGEMENT=true

# External Services (optional)
SENTRY_DSN=
```

## Environment-Specific Variables

### Development Environment

```bash
# Development - use test/local values
# Note: In Railway, RAILWAY_ENVIRONMENT_NAME is automatically set to "development"
DEBUG=true
LOG_LEVEL=debug
WORKERS=1
RELOAD=true

# Local services
DATABASE_URL=postgresql://localhost:5432/yoto_dev
REDIS_URL=redis://localhost:6379

# Yoto test credentials
YOTO_CLIENT_ID=dev_client_id
YOTO_CLIENT_SECRET=dev_secret

# Feature flags (enable all for testing)
ENABLE_MQTT=true
ENABLE_ICON_MANAGEMENT=true
ENABLE_DEBUG_TOOLBAR=true

# No external services
SENTRY_DSN=
```

### Staging Environment

```bash
# Staging - production-like settings
# Note: In Railway, RAILWAY_ENVIRONMENT_NAME is automatically set to "staging"
DEBUG=true  # Keep some debugging for QA
LOG_LEVEL=info
WORKERS=2
RELOAD=false

# Railway-managed services
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Real Yoto credentials (synced from GitHub Secrets via GitHub Actions)
YOTO_CLIENT_ID=<actual_value_from_github_secrets>
YOTO_CLIENT_SECRET=<actual_value_from_github_secrets>

# Feature flags
ENABLE_MQTT=true
ENABLE_ICON_MANAGEMENT=true
ENABLE_DEBUG_TOOLBAR=false

# Staging-specific external services
SENTRY_DSN=${{ secrets.SENTRY_DSN_STAGING }}
```

### Production Environment

```bash
# Production - optimized for performance and security
# Note: In Railway, RAILWAY_ENVIRONMENT_NAME is automatically set to "production"
DEBUG=false
LOG_LEVEL=warning
WORKERS=4
RELOAD=false

# Railway-managed services
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}

# Production Yoto credentials (synced from GitHub Secrets via GitHub Actions)
YOTO_CLIENT_ID=<actual_value_from_github_secrets>
YOTO_CLIENT_SECRET=<actual_value_from_github_secrets>

# Feature flags (stable features only)
ENABLE_MQTT=true
ENABLE_ICON_MANAGEMENT=true
ENABLE_DEBUG_TOOLBAR=false

# Production monitoring
SENTRY_DSN=<actual_value_from_github_secrets>

# Security
SECURE_COOKIES=true
SESSION_COOKIE_SECURE=true
SESSION_COOKIE_HTTPONLY=true
CORS_ORIGINS=https://yourdomain.com

# Performance
RATE_LIMIT_ENABLED=true
RATE_LIMIT=60/minute
CACHE_TTL=300
```

## Feature Flags

### Implementation

```python
# feature_flags.py
import os

class FeatureFlags:
    """Feature flag management"""
    
    @staticmethod
    def is_enabled(flag_name: str) -> bool:
        """Check if feature flag is enabled"""
        env_var = f"ENABLE_{flag_name.upper()}"
        return os.getenv(env_var, "false").lower() == "true"
    
    # Predefined flags
    MQTT_ENABLED = is_enabled("MQTT")
    ICON_MANAGEMENT_ENABLED = is_enabled("ICON_MANAGEMENT")
    DEBUG_TOOLBAR_ENABLED = is_enabled("DEBUG_TOOLBAR")
    RATE_LIMITING_ENABLED = is_enabled("RATE_LIMITING")

# Usage in code
from feature_flags import FeatureFlags

if FeatureFlags.MQTT_ENABLED:
    # Enable MQTT functionality
    mqtt_client.connect()
```

### Setting Feature Flags

```bash
# Enable feature in production
railway variables set ENABLE_MQTT=true -e production

# Disable feature in staging
railway variables set ENABLE_ICON_MANAGEMENT=false -e staging

# Toggle feature via GitHub Actions
gh workflow run toggle-feature.yml \
    -f environment=production \
    -f feature=MQTT \
    -f enabled=true
```

## Configuration Validation

### Startup Validation

```python
# validators.py
import os
import sys

def validate_config():
    """Validate configuration on startup"""
    
    errors = []
    warnings = []
    
    # Required variables
    required = [
        "YOTO_CLIENT_ID",
        "YOTO_CLIENT_SECRET",
        "DATABASE_URL",
        "PORT",
    ]
    
    for var in required:
        if not os.getenv(var):
            errors.append(f"Missing required variable: {var}")
    
    # Environment-specific requirements
    environment = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
    
    if environment == "production":
        if os.getenv("DEBUG", "false").lower() == "true":
            warnings.append("DEBUG=true in production (should be false)")
        
        if not os.getenv("SENTRY_DSN"):
            warnings.append("SENTRY_DSN not set in production")
        
        if os.getenv("LOG_LEVEL", "").lower() not in ["warning", "error"]:
            warnings.append("LOG_LEVEL should be 'warning' or 'error' in production")
    
    # Print results
    if errors:
        print("❌ Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    
    if warnings:
        print("⚠️  Configuration Warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    
    print("✅ Configuration validated successfully")

# Run on import
validate_config()
```

### Runtime Validation

```python
# middleware.py
from fastapi import Request, HTTPException
from config import Config

async def validate_environment(request: Request, call_next):
    """Middleware to validate environment on each request"""
    
    # Check critical config is still present
    if not Config.YOTO_CLIENT_ID:
        raise HTTPException(
            status_code=500,
            detail="Service configuration error"
        )
    
    response = await call_next(request)
    return response
```

## Configuration Updates

### Zero-Downtime Variable Updates

```bash
# Railway automatically restarts service when variables change
# To minimize downtime:

# 1. Update variable
railway variables set NEW_FEATURE_ENABLED=true -e production

# 2. Railway triggers rolling restart
# 3. New instances start with new config
# 4. Old instances shut down after health check passes
```

### Bulk Variable Updates

```bash
#!/bin/bash
# scripts/update-config.sh - Bulk update variables

ENVIRONMENT=${1:-staging}

echo "Updating configuration for $ENVIRONMENT..."

# Application variables
railway variables set DEBUG=false -e "$ENVIRONMENT"
railway variables set LOG_LEVEL=warning -e "$ENVIRONMENT"
railway variables set WORKERS=4 -e "$ENVIRONMENT"

# Feature flags
railway variables set ENABLE_MQTT=true -e "$ENVIRONMENT"
railway variables set ENABLE_ICON_MANAGEMENT=true -e "$ENVIRONMENT"

# External services
railway variables set SENTRY_DSN="${SENTRY_DSN}" -e "$ENVIRONMENT"

echo "✅ Configuration updated"
```

## Best Practices

### ✅ DO:

1. Use Railway's reference variables for service URLs
2. Validate configuration on application startup
3. Use environment-based configuration classes
4. Store sensitive data in GitHub Secrets
5. Use feature flags for gradual rollouts
6. Document all configuration variables in .env.example
7. Use different log levels per environment
8. Implement configuration validation
9. Use Railway's automatic PORT variable
10. Keep production configs minimal and secure

### ❌ DON'T:

1. Hardcode configuration values in code
2. Commit .env files to version control
3. Use production credentials in development
4. Skip configuration validation
5. Use DEBUG=true in production
6. Store secrets in configuration files
7. Use verbose logging in production
8. Ignore Railway-provided variables
9. Mix environment-specific logic in code
10. Update production config without testing in staging

---

**Next Steps:**
- Review [Secrets Management](./secrets_management.md)
- Set up [Database & Services](./database_services.md)
- Configure [Monitoring & Logging](./monitoring_logging.md)
