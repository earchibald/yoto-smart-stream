# GitHub Copilot Workspace Network Configuration

## Overview

This document explains the network access and MCP server configuration for GitHub Copilot Workspace to enable testing, validation, and management of Railway deployments.

## Configuration Components

The `.github/copilot-workspace.yml` file contains two main configuration sections:

1. **Network Configuration** - Controls which external domains Copilot can access
2. **MCP Servers Configuration** - Enables Model Context Protocol servers for specialized tools

## Problem

GitHub Copilot Workspace has restricted network access by default for security reasons. This prevents the AI agent from directly testing Railway deployment URLs like:

- `https://yoto-smart-stream-production.up.railway.app`
- `https://yoto-smart-stream-staging.up.railway.app`
- `https://yoto-smart-stream-development.up.railway.app`
- `https://yoto-smart-stream-pr-{number}.up.railway.app`

## Solution

The configuration is defined in `.github/copilot-workspace.yml`, which includes both network access and MCP server setup.

### Configuration File

**Location:** `.github/copilot-workspace.yml`

This file contains two main sections:

#### 1. Network Configuration

```yaml
network:
  allowed_domains:
    # Railway.app platform URLs
    - "*.up.railway.app"         # All Railway deployment URLs
    - "railway.app"              # Railway dashboard and API
    - "backboard.railway.app"    # Railway GraphQL API
    
    # Yoto API URLs (for testing and development)
    - "api.yoto.io"              # Yoto REST API
    - "mqtt.yoto.io"             # Yoto MQTT broker
    - "yoto.dev"                 # Yoto developer portal
```

#### 2. MCP Servers Configuration

```yaml
mcp_servers:
  railway-mcp-server:
    command: npx
    args:
      - "-y"
      - "@railway/mcp-server"
    description: |
      Railway MCP Server provides tools for managing Railway infrastructure
```

The Railway MCP server provides specialized tools for managing Railway resources directly from Copilot Workspace.

### Allowed Domains

The configuration allows access to:

1. **Railway Deployment URLs** (`*.up.railway.app`)
   - All environment deployments (production, staging, development)
   - PR-specific environments
   - Ephemeral environments

2. **Railway Platform APIs**
   - `railway.app` - Main platform and API endpoints
   - `backboard.railway.app` - GraphQL API for advanced operations

3. **Yoto APIs** (for development and testing)
   - `api.yoto.io` - REST API for player control and card management
   - `mqtt.yoto.io` - MQTT broker for real-time events
   - `yoto.dev` - Developer portal for app registration

## Railway URL Patterns

### Production Environment
- **URL:** `https://yoto-smart-stream-production.up.railway.app`
- **Trigger:** Automatic deployment on merge to `main` branch
- **Purpose:** Live production service

### Staging Environment
- **URL:** `https://yoto-smart-stream-staging.up.railway.app`
- **Trigger:** Automatic deployment on merge to `develop` branch
- **Purpose:** Pre-production testing

### Development Environment (Shared)
- **URL:** `https://yoto-smart-stream-development.up.railway.app`
- **Trigger:** Manual deployment via GitHub Actions
- **Purpose:** Shared testing environment with coordination

### PR Environments
- **URL Pattern:** `https://yoto-smart-stream-pr-{number}.up.railway.app`
- **Trigger:** Automatic deployment when PR is opened
- **Purpose:** Isolated testing for each pull request
- **Example:** PR #42 → `https://yoto-smart-stream-pr-42.up.railway.app`

## How It Works

### 1. Network Configuration

1. **Configuration Loading**
   - GitHub Copilot Workspace reads `.github/copilot-workspace.yml` on startup
   - Allowed domains are added to the network allowlist
   - The AI agent can now make HTTP requests to these domains

2. **Testing Capabilities**
   - Copilot can curl endpoints to verify deployment health
   - Can check API responses and status codes
   - Can validate that deployments are functioning correctly
   - Can verify Railway platform API access

3. **Security**
   - Only explicitly allowed domains are accessible
   - Wildcard pattern `*.up.railway.app` covers all Railway deployments
   - Other domains remain blocked for security

### 2. Railway MCP Server

The Railway MCP (Model Context Protocol) server provides specialized tools for Railway management:

**Available Tools:**
- **check-railway-status** - Verify Railway CLI installation and login status
- **Project Management:**
  - `list-projects` - List all Railway projects
  - `create-project-and-link` - Create and link new projects
- **Service Management:**
  - `list-services` - List services in a project
  - `link-service` - Link a service to the current directory
  - `deploy` - Deploy a service
  - `deploy-template` - Deploy from Railway Template Library
- **Environment Management:**
  - `create-environment` - Create new environments
  - `link-environment` - Link environment to directory
- **Configuration & Variables:**
  - `list-variables` - List environment variables
  - `set-variables` - Set environment variables
  - `generate-domain` - Generate railway.app domains
- **Monitoring & Logs:**
  - `get-logs` - Retrieve build/deployment logs with filtering

**Prerequisites:**
- Railway CLI must be installed (`railway` command available)
- User must be logged in to Railway (`railway login`)
- CLI version auto-detected for feature compatibility

**Documentation:** https://github.com/railwayapp/railway-mcp-server

## Usage Examples

### Network Access Examples

With network configuration, Copilot Workspace can:

#### Check Deployment Health

```bash
curl https://yoto-smart-stream-production.up.railway.app/api/health
curl https://yoto-smart-stream-pr-42.up.railway.app/health
```

### Validate API Endpoints

```bash
curl https://yoto-smart-stream-staging.up.railway.app/api/cards
curl https://yoto-smart-stream-development.up.railway.app/api/players
```

### Test Railway CLI Operations

```bash
# These commands can now access Railway's APIs
railway status
railway logs
railway list
```

### Verify Yoto API Access

```bash
curl https://api.yoto.io/v1/me
# (with proper authentication headers)
```

### Railway MCP Server Examples

The Railway MCP server enables natural language commands for Railway management:

#### Create and Deploy a New Project

```
Create a Next.js app in this directory and deploy it to Railway. 
Make sure to also assign it a domain.
```

The MCP server will:
1. Create a new Railway project
2. Link it to the current directory
3. Deploy the service
4. Generate a railway.app domain

#### Deploy from Template

```
Deploy a Postgres database
```

```
Deploy a Redis cache for our application
```

The MCP server will automatically select the appropriate template from the Railway Template Library.

#### Environment Management

```
Create a new development environment called 'development' that duplicates production.
Once created, set it as my current linked environment.
```

#### Pull Environment Variables

```
Pull environment variables for my project and save them in a .env file
```

#### Check Logs

```
Show me the last 100 lines of deployment logs for my service
```

With Railway CLI v4.9.0+, you can also filter logs:
```
Show me error logs from the last deployment
```

#### List and Manage Services

```
List all services in my project
```

```
Link the backend service to this directory
```

## Maintenance

### Adding New Domains

If you need to allow access to additional domains:

1. Edit `.github/copilot-workspace.yml`
2. Add the domain to the `allowed_domains` list
3. Include a comment explaining why it's needed
4. Commit and push the changes
5. Restart any active Copilot Workspace sessions

### Removing Domains

Only remove domains if:
- They're no longer used by the project
- The service has been shut down
- Security policy requires removal

## Related Documentation

- [Railway Deployment Guide](./RAILWAY_DEPLOYMENT.md)
- [Railway PR Environments](./RAILWAY_PR_ENVIRONMENTS_NATIVE.md)
- [Codespaces Railway Setup](./CODESPACES_RAILWAY_SETUP.md)
- [Railway Token Setup](./RAILWAY_TOKEN_SETUP.md)

## Troubleshooting

### Network Access Issues

#### Copilot Cannot Access Railway URLs

**Symptoms:**
- Network errors when curling Railway URLs
- "Domain not allowed" or similar errors
- Timeouts when accessing *.up.railway.app

**Solutions:**

1. **Verify configuration file exists:**
   ```bash
   ls -la .github/copilot-workspace.yml
   ```

2. **Check YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('.github/copilot-workspace.yml'))"
   ```

3. **Restart Copilot Workspace session:**
   - Stop the current session
   - Start a new session to reload configuration

4. **Check wildcard pattern:**
   - Ensure `*.up.railway.app` is in the allowed_domains list
   - Verify no typos in the domain name

#### Configuration Not Taking Effect

**Possible causes:**

1. **YAML syntax error** - Validate the file
2. **Session not restarted** - Restart Copilot Workspace
3. **Wrong file location** - Must be in `.github/` directory
4. **Cache issues** - Clear cache and restart

### Railway MCP Server Issues

#### MCP Server Not Available

**Symptoms:**
- Railway management commands not working
- "Railway MCP server not found" errors
- No Railway tools available in Copilot

**Solutions:**

1. **Verify MCP configuration exists:**
   ```bash
   grep -A 10 "mcp_servers:" .github/copilot-workspace.yml
   ```

2. **Check npx is available:**
   ```bash
   npx --version
   ```

3. **Test the Railway MCP server manually:**
   ```bash
   npx -y @railway/mcp-server
   ```

4. **Restart Copilot Workspace:**
   - Configuration changes require a session restart
   - Close and reopen the workspace

#### Railway CLI Not Installed

**Symptoms:**
- "Railway CLI not found" errors
- MCP server reports CLI is not available
- Commands fail with "railway: command not found"

**Solutions:**

1. **Install Railway CLI:**
   ```bash
   # Using npm
   npm install -g @railway/cli
   
   # Or using curl
   curl -fsSL https://railway.app/install.sh | sh
   ```

2. **Verify installation:**
   ```bash
   railway --version
   ```

3. **Login to Railway:**
   ```bash
   railway login
   ```

4. **Set RAILWAY_TOKEN (for CI/CD):**
   ```bash
   export RAILWAY_TOKEN="your-token-here"
   ```

#### MCP Server Commands Fail

**Symptoms:**
- Individual commands return errors
- "Permission denied" or "Unauthorized" errors
- Commands timeout or hang

**Solutions:**

1. **Check Railway login status:**
   ```bash
   railway whoami
   ```

2. **Re-login if needed:**
   ```bash
   railway login
   ```

3. **Verify project linking:**
   ```bash
   railway status
   ```

4. **Check Railway service status:**
   - Visit https://railway.app/ to check for outages
   - Verify your account has proper permissions

5. **Update Railway CLI:**
   ```bash
   npm update -g @railway/cli
   ```

6. **Check CLI version compatibility:**
   ```bash
   railway --version
   # MCP server requires Railway CLI v3.0.0 or higher
   ```

## Best Practices

### Network Configuration

1. **Use wildcards carefully** - `*.up.railway.app` is safe as it's Railway's official subdomain
2. **Document all domains** - Add comments explaining why each domain is allowed
3. **Review periodically** - Remove unused domains to maintain security
4. **Test after changes** - Verify configuration works after modifications
5. **Keep it minimal** - Only allow domains actually needed for development/testing

### Railway MCP Server Usage

1. **Natural Language Commands** - Use descriptive, natural language for best results
   - ✅ "Deploy a Postgres database for my application"
   - ❌ "db deploy"

2. **Be Specific** - Provide context for better command interpretation
   - ✅ "Create a development environment that duplicates production settings"
   - ❌ "Make a new environment"

3. **Check Prerequisites** - Ensure Railway CLI is installed and you're logged in
   ```bash
   railway whoami
   railway status
   ```

4. **Use Templates** - Leverage Railway's template library for common services
   - Postgres, Redis, MongoDB, MySQL
   - Message queues (RabbitMQ, Kafka)
   - Monitoring tools (Prometheus, Grafana)

5. **Environment Variables** - Use MCP server for secure variable management
   - Pull variables before local development
   - Set variables for new services
   - Never commit secrets to git

6. **Monitor Deployments** - Use log filtering for efficient debugging
   - Filter by severity (error, warning, info)
   - Limit output with line counts
   - Focus on recent deployments

## Security Considerations

### Network Access

- **Wildcard domains:** The `*.up.railway.app` wildcard is safe because:
  - It's Railway's official deployment subdomain
  - All deployments go through Railway's security
  - Only applies to Railway infrastructure

- **API domains:** Yoto API domains are allowed because:
  - Required for development and testing
  - All API calls require authentication
  - No sensitive data exposed without auth

- **Railway platform:** Access to `railway.app` and `backboard.railway.app` allows:
  - Deployment status checks
  - Log retrieval
  - Environment management
  - Requires valid RAILWAY_TOKEN for operations

### Railway MCP Server

- **Authentication Required:** All Railway operations require valid authentication
  - CLI login or RAILWAY_TOKEN environment variable
  - Tokens should be kept secure and never committed to git
  
- **No Destructive Actions:** The MCP server is designed without destructive operations
  - Cannot delete projects or services
  - Cannot remove environments
  - Safe for automated agent usage
  
- **Command Monitoring:** Always review commands before execution
  - Check which environment is targeted
  - Verify service names and settings
  - Confirm variable changes before applying

- **Access Control:** Railway permissions still apply
  - User must have appropriate project access
  - Team permissions are enforced
  - Cannot modify resources without permission

- **Token Security:**
  - Use GitHub Secrets for CI/CD workflows
  - Rotate tokens periodically
  - Different tokens for prod/staging/dev environments
  - Tokens stored in: RAILWAY_TOKEN_PROD, RAILWAY_TOKEN_STAGING, RAILWAY_TOKEN_DEV

---

**Last Updated:** 2026-01-11  
**Configuration Version:** 2.0.0 (Added Railway MCP Server)  
**Maintained By:** GitHub Copilot Workspace
