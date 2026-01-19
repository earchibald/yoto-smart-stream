# Railway PR Environments

## Overview

Railway's PR Environments is a native platform feature that automatically creates ephemeral environments for pull requests. Unlike custom script-based ephemeral environments, PR Environments are fully managed by Railway's GitHub integration with zero configuration required beyond initial setup.

This project uses Railway PR Environments with **production** as the base environment, leveraging **Shared Variables** to inherit configuration like `YOTO_CLIENT_ID`.

## Key Features

### Automatic Lifecycle Management

- **Auto-Creation**: When a PR is opened, Railway automatically creates a new environment
- **Auto-Deployment**: Code changes in the PR trigger automatic deployments
- **Auto-Destruction**: When the PR is closed or merged, the environment is automatically destroyed
- **Zero Configuration**: No GitHub Actions workflows or custom scripts required for deployment
- **Shared Variables**: Can reference variables from the base (production) environment

### Native GitHub Integration

Railway's PR Environments leverage direct GitHub integration:

```
Pull Request → Railway Webhook → Environment Created → Deployment → Live
     ↓
  Updates → Railway Webhook → New Deployment → Updated
     ↓
  Closed → Railway Webhook → Environment Destroyed
```

### Resource Optimization

- Ephemeral environments use a template from the base environment (production)
- Automatically scaled down compared to production
- Zero cost when PR is closed
- Shared configuration with intelligent overrides

## Setup

### Prerequisites

1. **Railway Project**: Connected to GitHub repository
2. **GitHub Integration**: Railway app installed in GitHub
3. **Base Environment**: Production environment configured with Shared Variables

### Enabling PR Environments

**Via Railway Dashboard:**

1. Navigate to your Railway project
2. Go to **Settings** → **GitHub**
3. Locate **PR Environments** section
4. Enable **"Create ephemeral environments for PRs"**
5. Configure settings:
   - **Base Environment**: Select `production`
   - **Auto-Deploy**: Enable automatic deployments on PR updates
   - **Auto-Destroy**: Enable automatic cleanup on PR close/merge
   - **Target Branches**: Specify `main`

**Configuration Example:**

```yaml
PR Environments Settings:
  Enabled: ✓
  Base Environment: production
  Auto-Deploy: ✓
  Auto-Destroy: ✓
  Target Branches: 
    - main
  Service Template: Use services from production
  Variable Inheritance: Inherit from production + shared variables
```

### Setting Up Shared Variables

For PR environments to inherit secrets like `YOTO_CLIENT_ID`:

1. Go to Railway Dashboard → Production Environment → Variables
2. Find or create `YOTO_CLIENT_ID`
3. Set its type to **"Shared Variable"**
4. PR environments will reference it using `${{shared.YOTO_CLIENT_ID}}`

### Environment Naming

Railway automatically names PR environments using a consistent pattern:

- Format: `pr-{number}`
- Examples:
  - PR #123 → Environment `pr-123`
  - PR #456 → Environment `pr-456`

### URL Generation

Railway automatically generates URLs for PR environments:

- Pattern: `{service-name}-pr-{number}.up.railway.app`
- Example: `yoto-smart-stream-pr-123.up.railway.app`
- Accessible immediately after deployment completes

## Configuration

### Variable Inheritance with Shared Variables

PR Environments inherit variables from production and can reference Shared Variables:

**Inherited from Production:**
```bash
# PR environments automatically get:
RAILWAY_ENVIRONMENT_NAME=pr-{number}  # Auto-set by Railway
PORT={auto-assigned}  # Railway assigns unique port
```

**Configured via GitHub Actions:**
```bash
# GitHub Actions workflow (railway-pr-checks.yml) sets:
YOTO_CLIENT_ID=${{shared.YOTO_CLIENT_ID}}  # References production's shared variable
DEBUG=true
LOG_LEVEL=debug
```
```

**Automatic Overrides:**
```bash
ENVIRONMENT=pr-{number}
RAILWAY_ENVIRONMENT_NAME=pr-{number}
RAILWAY_GIT_COMMIT_SHA={PR head SHA}
RAILWAY_GIT_BRANCH={PR source branch}
RAILWAY_GIT_COMMIT_MESSAGE={latest commit message}
```

**Custom Overrides (Optional):**

You can set PR-specific variables via Railway CLI or Dashboard:

```bash
# Set variable for all PR environments
railway variables set DEBUG=true --pr-template

# Set variable for specific PR environment
railway variables set LOG_LEVEL=debug -e pr-123
```

### Service Configuration

PR Environments inherit service configuration from the base environment:

**From Base Environment:**
- Build configuration
- Start command
- Health check settings
- Resource limits
- Network settings

**Automatic Adjustments:**
- Scaled down resources (typically 50% of base)
- Single replica (no horizontal scaling)
- Ephemeral storage

### Database Handling

**Option 1: Ephemeral Database (Recommended)**
```yaml
Configuration:
  Type: Ephemeral PostgreSQL
  Source: Fresh instance
  Size: Minimal (e.g., 1GB)
  Lifecycle: Destroyed with environment
  Data: Empty or seeded via init scripts
```

**Option 2: Shared Development Database**
```yaml
Configuration:
  Type: Shared development database
  Source: Staging or development database
  Connection: Read DATABASE_URL from base
  Warning: May cause conflicts between PRs
```

**Option 3: Database Per PR**
```yaml
Configuration:
  Type: Isolated database per PR
  Source: Clone from template
  Size: Minimal
  Lifecycle: Destroyed with environment
  Data: Seeded or migrated
```

**Recommended Setup:**

```bash
# Each PR environment gets its own database
# Automatically provisioned by Railway
# DATABASE_URL is automatically set

# Run migrations on deployment
# Add to railway.toml or startup script:
startCommand = "python manage.py migrate && uvicorn main:app --host 0.0.0.0 --port $PORT"
```

## Provisioning Environment Tokens for PR Environments

When you need to provision Railway environment tokens for PR environments (e.g., for Cloud Agent or CI/CD workflows):

### Quick Process

```bash
# 1. Get PR number from GitHub
PR_NUMBER=$(gh pr view --json number -q .number)

# 2. Calculate environment name
RAILWAY_ENV="yoto-smart-stream-pr-${PR_NUMBER}"

# 3. Link workspace to PR environment
railway link --project yoto --service yoto-smart-stream --environment ${RAILWAY_ENV}

# 4. Get Railway dashboard URL
RAILWAY_URL=$(railway open --print)

# 5. Use Playwright to provision token via browser
# Navigate to ${RAILWAY_URL} → Settings → Tokens
# Create token named "pr-${PR_NUMBER}-token" for environment ${RAILWAY_ENV}

# 6. Set environment variables with token value
railway variables set RAILWAY_TOKEN=<token-value> -e ${RAILWAY_ENV}
railway variables set RAILWAY_API_TOKEN=<token-value> -e ${RAILWAY_ENV}
```

### Detailed Steps

**1. Determine PR Number**
```bash
# Using GitHub CLI
gh pr view --json number -q .number
```

**2. Calculate Environment Name**

Railway uses pattern: `{service-name}-pr-{number}`

```bash
# For service "yoto-smart-stream" and PR #88:
RAILWAY_ENV="yoto-smart-stream-pr-88"
```

**3. Link to Environment**

Use long-form flags with names (no UUIDs needed):

```bash
railway link --project yoto --service yoto-smart-stream --environment yoto-smart-stream-pr-88
```

This links your workspace to the specific PR environment.

**4. Get Dashboard URL**

```bash
railway open --print
```

Returns URL like: `https://railway.com/project/f92d5fa2-484e-4d93-9b1f-91c33cc33d0e?environmentId=...`

**5. Provision Token via Browser**

Using Playwright or manual browser:

1. Navigate to URL from step 4
2. Click **Settings** → **Tokens**
3. Click **Create Token**
4. Fill form:
   - **Token Name**: `pr-{number}-token` (e.g., `pr-88-token`)
   - **Environment**: Select `yoto-smart-stream-pr-{number}`
5. Click **Create**
6. **Copy token value immediately** (shown only once)
7. Click **Got it** to close dialog

**Token format:** `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` (UUID)

**6. Set Environment Variables**

```bash
# Set both variables with the copied token value
railway variables set RAILWAY_TOKEN=a1f80cde-030f-4b4f-84aa-07b00c2aa54f -e yoto-smart-stream-pr-88
railway variables set RAILWAY_API_TOKEN=a1f80cde-030f-4b4f-84aa-07b00c2aa54f -e yoto-smart-stream-pr-88

# Verify variables are set
railway variables list -e yoto-smart-stream-pr-88 | grep -E "(RAILWAY_TOKEN|RAILWAY_API_TOKEN)"
```

### Why This Process

**Pattern-Based Naming**: No need to query Railway API for environment names—they follow predictable pattern

**Long-Form Flags**: Using `--project yoto --service yoto-smart-stream` instead of UUIDs makes commands readable and maintainable

**`railway open --print`**: Automatically generates correct dashboard URL with environment context, avoiding manual navigation

**Browser-Based Token Creation**: Railway doesn't expose API for creating project tokens, so Playwright automation provides reliable token provisioning

### Verification

```bash
# Check environment is linked
railway status --json

# List all variables (check for RAILWAY_TOKEN and RAILWAY_API_TOKEN)
railway variables list -e yoto-smart-stream-pr-88

# Test deployment with new tokens
railway up -e yoto-smart-stream-pr-88
```

## Usage

### For Developers

**Opening a PR:**

1. Create feature branch: `git checkout -b feature/my-feature`
2. Push changes: `git push origin feature/my-feature`
3. Open PR on GitHub
4. Railway automatically:
   - Creates environment `pr-{number}`
   - Deploys your code
   - Posts deployment URL as PR check status

**Accessing PR Environment:**

```bash
# Via Railway CLI
railway link
railway status -e pr-123
railway logs -e pr-123

# Via URL
open https://yoto-smart-stream-pr-123.up.railway.app

# Check health
curl https://yoto-smart-stream-pr-123.up.railway.app/health
```

**Testing Changes:**

```bash
# View logs
railway logs -e pr-123 --tail 100 --follow

# Execute commands in environment
railway run -e pr-123 python manage.py shell

# Check deployment status
railway status -e pr-123
```

**Updating PR:**

1. Push new commits to PR branch
2. Railway automatically redeploys
3. Environment URL remains the same
4. Previous deployment available for rollback

**Closing PR:**

1. Merge or close PR on GitHub
2. Railway automatically destroys environment
3. All resources released
4. Zero ongoing costs

### For Reviewers

**Reviewing a PR:**

1. Navigate to PR on GitHub
2. Find Railway deployment check
3. Click "View deployment" link
4. Test the deployed application
5. Review logs if needed
6. Approve or request changes

**Common Review Tasks:**

```bash
# Health check
curl https://yoto-smart-stream-pr-{number}.up.railway.app/health

# Test specific endpoints
curl https://yoto-smart-stream-pr-{number}.up.railway.app/api/cards

# Check logs for errors
railway logs -e pr-{number} --filter "ERROR"
```

## Integration with GitHub

### GitHub Status Checks

Railway automatically updates PR status checks:

**Status Types:**
- ✓ **Success**: Deployment completed and healthy
- ⏳ **Pending**: Deployment in progress
- ✗ **Failed**: Deployment failed (build or runtime error)

**Check Details:**
- Deployment ID
- Deployment URL
- Build logs link
- Deployment time

### GitHub Checks API

Railway uses GitHub Checks API to provide rich deployment information:

```yaml
Check Run:
  Name: "Railway - pr-{number}"
  Status: completed
  Conclusion: success
  Details URL: https://railway.app/project/{id}/environment/pr-{number}
  Output:
    Title: "Deployment Successful"
    Summary: |
      Environment: pr-123
      Service: web
      URL: https://yoto-smart-stream-pr-123.up.railway.app
      Deployment ID: abc-123-def
```

### GitHub Environments

Railway can create GitHub Environments for PR deployments:

**Configuration:**
```yaml
GitHub Environment:
  Name: pr-{number}
  Protection Rules: Optional (require reviews, wait timer)
  Deployment Branches: Automatic
  Environment Variables: Synced from Railway
```

**Benefits:**
- Deployment history in GitHub
- Protection rules for critical branches
- Environment-specific secrets
- Deployment logs and status

## Workflow Patterns

### Basic PR Workflow

```
Developer        GitHub          Railway              Reviewer
    |              |               |                    |
    |-- Create PR ->|               |                    |
    |              |-- Webhook ---->|                    |
    |              |               |-- Create Env        |
    |              |               |-- Deploy            |
    |              |<-- Status -----|                    |
    |              |                                     |
    |              |<----------- View Deployment --------|
    |              |                                     |
    |-- Push ----->|                                     |
    |              |-- Webhook ---->|                    |
    |              |               |-- Redeploy          |
    |              |<-- Status -----|                    |
    |              |                                     |
    |-- Merge ---->|                                     |
    |              |-- Webhook ---->|                    |
    |              |               |-- Destroy Env       |
```

### With CI/CD Integration

```yaml
# .github/workflows/pr-check.yml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/
      
      # Railway deployment happens automatically
      # This workflow only runs tests
      
  integration-test:
    runs-on: ubuntu-latest
    needs: test
    steps:
      - name: Wait for Railway deployment
        run: sleep 60
      
      - name: Test PR environment
        env:
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          URL="https://yoto-smart-stream-pr-${PR_NUMBER}.up.railway.app"
          curl -f "${URL}/health" || exit 1
          # Run integration tests against URL
```

### Database Migration Pattern

```yaml
# railway.toml - Automatic migrations on deployment
[deploy]
startCommand = """
  python manage.py migrate --check && \
  python manage.py migrate && \
  uvicorn main:app --host 0.0.0.0 --port $PORT
"""
```

Or via separate migration job:

```yaml
# .github/workflows/pr-migrate.yml
name: PR Database Migration

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Run migrations
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
          PR_NUMBER: ${{ github.event.pull_request.number }}
        run: |
          railway run -e pr-${PR_NUMBER} python manage.py migrate
```

## Comparison with Custom Ephemeral Environments

### Railway Native PR Environments

**Pros:**
- ✓ Zero configuration after initial setup
- ✓ Fully managed by Railway platform
- ✓ Automatic lifecycle management
- ✓ Native GitHub integration
- ✓ GitHub status checks built-in
- ✓ Consistent with Railway ecosystem
- ✓ Better resource management

**Cons:**
- ✗ Limited customization of lifecycle
- ✗ Depends on Railway's GitHub app permissions
- ✗ Less control over deployment timing
- ✗ Fixed naming convention

**Best For:**
- Standard PR workflows
- Teams wanting minimal maintenance
- Projects with straightforward deployment needs
- When Railway's defaults align with your workflow

### Custom Ephemeral Environments (Script-Based)

**Pros:**
- ✓ Full control over lifecycle
- ✓ Custom naming conventions
- ✓ Flexible deployment triggers
- ✓ Can work without GitHub integration
- ✓ Advanced deployment strategies
- ✓ Custom notifications and comments

**Cons:**
- ✗ Requires GitHub Actions workflows
- ✗ Custom scripts to maintain
- ✗ Manual status check management
- ✗ More complexity
- ✗ Potential for errors in automation

**Best For:**
- Custom deployment workflows
- Non-standard environment naming
- Complex PR approval processes
- When GitHub integration unavailable
- Advanced deployment strategies

### Recommendation

**Use Railway Native PR Environments when:**
- You want simplicity and zero maintenance
- Standard PR workflow meets your needs
- You trust Railway's automation
- You want GitHub integration out-of-the-box

**Use Custom Ephemeral Environments when:**
- You need custom lifecycle control
- You have complex approval processes
- You need custom environment naming
- You require advanced deployment strategies
- You're working around platform limitations (like OAuth callback URLs)

## Monitoring and Debugging

### Viewing Logs

```bash
# Real-time logs
railway logs -e pr-123 --follow

# Filtered logs
railway logs -e pr-123 --filter "ERROR"
railway logs -e pr-123 --filter "health"

# Tail last N lines
railway logs -e pr-123 --tail 100

# Export logs
railway logs -e pr-123 > pr-123-logs.txt
```

### Checking Status

```bash
# Environment status
railway status -e pr-123

# Deployment status
railway deployments -e pr-123

# Resource usage
railway status -e pr-123 --json | jq '.resources'
```

### Debugging Failed Deployments

**Build Failures:**
```bash
# View build logs
railway logs -e pr-123 --deployment {id}

# Common issues:
# - Missing dependencies
# - Build command errors
# - Resource limits exceeded
```

**Runtime Failures:**
```bash
# View application logs
railway logs -e pr-123 --tail 200

# Common issues:
# - Port binding errors
# - Environment variable issues
# - Database connection failures
# - Health check timeouts
```

**Health Check Failures:**
```bash
# Test health endpoint
curl -v https://yoto-smart-stream-pr-123.up.railway.app/health

# Check health check configuration
railway status -e pr-123 | grep health
```

### Performance Monitoring

```bash
# Check resource usage
railway status -e pr-123 --json | jq '.metrics'

# Monitor over time
watch -n 5 'railway status -e pr-123'

# Check deployment timing
railway deployments -e pr-123 --json | jq '.[0].duration'
```

## Best Practices

### ✅ DO:

1. **Enable PR Environments for all target branches** (main, develop)
2. **Use staging as base template** for consistent configuration
3. **Implement health checks** for reliable deployments
4. **Set appropriate resource limits** for PR environments
5. **Use ephemeral databases** for isolation
6. **Run migrations on deployment** automatically
7. **Monitor deployment status** via GitHub checks
8. **Clean up manually if needed** (for stuck environments)
9. **Test in PR environment** before requesting review
10. **Document environment URLs** in PR description

### ❌ DON'T:

1. Don't use production credentials in PR environments
2. Don't share production database with PR environments
3. Don't leave PRs open indefinitely (costs money)
4. Don't skip health checks
5. Don't ignore deployment failures
6. Don't use PR environments for load testing
7. Don't share sensitive data in PR environments
8. Don't manually create PR environments (let Railway handle it)
9. Don't override auto-destroy (let Railway clean up)
10. Don't deploy production-level resources to PR environments

## Troubleshooting

### Environment Not Created

**Possible Causes:**
- PR Environments not enabled in Railway
- Target branch not configured
- GitHub integration issues
- Railway project limits reached

**Solution:**
```bash
# Check Railway settings
railway open

# Verify GitHub integration
# Railway Dashboard → Settings → GitHub

# Check project limits
# Railway Dashboard → Settings → Usage
```

### Deployment Failed

**Check Build Logs:**
```bash
railway logs -e pr-123 --deployment {id}
```

**Common Issues:**
- Dependencies missing from requirements.txt
- Python version mismatch
- Build command errors

### Environment Not Destroyed

**Manual Cleanup:**
```bash
# Via Railway CLI
railway down -e pr-123

# Or via Dashboard
# Railway → Environments → pr-123 → Delete
```

### Cannot Access URL

**Verify Deployment:**
```bash
# Check deployment status
railway status -e pr-123

# View logs
railway logs -e pr-123 --tail 50

# Test health endpoint
curl -v https://yoto-smart-stream-pr-123.up.railway.app/health
```

## Cost Management

### Resource Optimization

**PR Environment Resources:**
```yaml
Recommended Limits:
  RAM: 512 MB (vs 1-2 GB for staging)
  CPU: 0.5 vCPU (vs 1+ for staging)
  Database: 1 GB (vs 5-10 GB for staging)
  Replicas: 1 (vs 2+ for production)
```

**Cost Estimation:**
```
Per PR Environment:
  Web Service: ~$0.01-0.02/hour
  Database: ~$0.005-0.01/hour
  Total: ~$0.015-0.03/hour
  
Average PR Lifecycle: 2-4 hours
Average Cost per PR: $0.03-0.12
```

### Cost Controls

1. **Auto-destroy on merge/close** (enabled by default)
2. **Set resource limits** in base template
3. **Monitor active PR count** regularly
4. **Close stale PRs** promptly
5. **Use shared development database** if appropriate (with caution)

### Billing Alerts

```bash
# Set up in Railway Dashboard
Settings → Billing → Alerts

Recommended alerts:
- Monthly spend > $50
- Active environments > 10
- Individual environment > $1/day
```

## Security Considerations

### Secrets Management

**Safe:**
- ✓ Inherit non-sensitive variables from base
- ✓ Use Railway's variable management
- ✓ Separate credentials for non-prod environments

**Unsafe:**
- ✗ Using production credentials
- ✗ Hardcoding secrets in code
- ✗ Exposing secrets in logs or URLs

### Access Control

**Railway Access:**
```yaml
Team Roles:
  Admin: Can modify PR environment settings
  Developer: Can view and deploy PR environments
  Viewer: Can only view PR environments
```

**GitHub Access:**
```yaml
Branch Protection:
  Require PR reviews: Recommended
  Require status checks: Recommended (Railway deployment)
  Restrict pushes: To protect target branches
```

### Data Protection

**Guidelines:**
- Use test data only in PR environments
- Never copy production data to PR environments
- Ephemeral databases should use synthetic or sanitized data
- Treat PR environment URLs as public (though obscure)

## Migration Guide

### From Custom Ephemeral Environments to Native PR Environments

**Step 1: Enable Railway PR Environments**
```bash
# In Railway Dashboard:
# Settings → GitHub → PR Environments → Enable
```

**Step 2: Disable Custom Workflow (if applicable)**
```yaml
# .github/workflows/railway-pr-environments.yml
# Comment out or remove custom PR deployment workflow
```

**Step 3: Update Documentation**
```bash
# Update team documentation to reference Railway native PR Environments
# Remove references to custom scripts if no longer needed
```

**Step 4: Test**
```bash
# Open a test PR
# Verify Railway creates environment automatically
# Test deployment and auto-destroy
```

**Step 5: Monitor**
```bash
# Monitor first few PRs
# Verify costs are as expected
# Adjust base template if needed
```

### Keeping Both Systems

You can keep custom ephemeral environments for special cases:

```yaml
# Use Railway native PR Environments by default
# Use custom environments for:
#   - Non-PR testing (Copilot sessions)
#   - Custom naming requirements
#   - Special deployment strategies
```

---

**Related Documentation:**
- [Deployment Workflows](./deployment_workflows.md)
- [Multi-Environment Architecture](./multi_environment_architecture.md)
- [Configuration Management](./configuration_management.md)
- [Cost Optimization](./cost_optimization.md)
