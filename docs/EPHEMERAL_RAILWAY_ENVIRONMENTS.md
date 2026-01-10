# Ephemeral Railway Environments for PR and Copilot Sessions

This document describes the automated ephemeral environment system for testing pull requests and GitHub Copilot sessions using Railway deployments.

## Overview

The Yoto Smart Stream project uses Railway's ephemeral environments to provide isolated, temporary deployments for:

1. **Pull Request (PR) Environments** - Automatic deployments for every PR to test changes
2. **GitHub Copilot Session Environments** - Dedicated environments for Copilot AI coding sessions

These environments are:
- **Ephemeral** - Created on-demand and destroyed automatically
- **Isolated** - Each environment has its own resources and configuration
- **Cost-Effective** - Resources are released immediately after use
- **Automated** - No manual intervention required

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Railway Project                           │
│              (yoto-smart-stream)                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Long-lived Environments:                                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Production (main branch)                            │  │
│  │  - Always running                                    │  │
│  │  - Full resources                                    │  │
│  │  - Customer-facing                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Staging (develop branch)                            │  │
│  │  - Always running                                    │  │
│  │  - Testing environment                               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  Ephemeral Environments (Auto-created/destroyed):           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  PR Environments (pr-123, pr-124, ...)               │  │
│  │  - Created: On PR open                               │  │
│  │  - Destroyed: On PR close/merge                      │  │
│  │  - Minimal resources                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Copilot Environments (copilot-*, ...)               │  │
│  │  - Created: On copilot branch push                   │  │
│  │  - Destroyed: On branch delete                       │  │
│  │  - Testing & development                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## PR Environments

### Automatic Workflow

When you open a pull request:

1. **GitHub Actions triggers** - Detects PR creation
2. **Tests run** - Linting, formatting, unit tests
3. **Environment created** - Railway environment named `pr-{number}`
4. **Deployment** - Application deployed to Railway
5. **Configuration** - Environment variables set automatically
6. **Notification** - PR comment with deployment URL
7. **Available for testing** - Environment accessible via URL

When PR is closed or merged:

1. **GitHub Actions triggers** - Detects PR closure
2. **Environment destroyed** - Railway stops all services
3. **Resources released** - All costs eliminated
4. **Notification** - PR comment confirming cleanup

### Workflow File

`.github/workflows/railway-pr-environments.yml`

### Environment Naming

- Pattern: `pr-{number}`
- Examples: `pr-123`, `pr-456`

### Accessing PR Environments

**Via Railway Dashboard:**
```bash
# Open Railway dashboard
railway open -e pr-123
```

**Via Direct URL:**
```
https://yoto-smart-stream-pr-123.up.railway.app
```

**Health Check:**
```bash
curl https://yoto-smart-stream-pr-123.up.railway.app/health
```

### PR Environment Configuration

Each PR environment automatically receives:

```bash
ENVIRONMENT=preview
DEBUG=true
LOG_LEVEL=debug
PR_NUMBER=123
PR_TITLE="Add new feature"
GIT_SHA=abc123def456
YOTO_CLIENT_ID={synced from GitHub Secrets}
```

## Copilot Session Environments

### Automatic Workflow

When Copilot creates a branch starting with `copilot/`:

1. **Push detected** - GitHub Actions triggers on branch push
2. **Environment name generated** - From branch name (e.g., `copilot-feature-name`)
3. **Deployment** - Application deployed to Railway
4. **Configuration** - Environment variables set for testing
5. **Ready for use** - Environment accessible for Copilot testing

When Copilot branch is deleted:

1. **Delete detected** - GitHub Actions triggers on branch deletion
2. **Environment destroyed** - Railway cleanup initiated
3. **Resources released** - All costs eliminated

### Workflow File

`.github/workflows/railway-copilot-environments.yml`

### Environment Naming

- Pattern: `copilot-{branch-name-normalized}`
- Examples: 
  - Branch `copilot/add-auth` → Environment `copilot-add-auth`
  - Branch `copilot/fix-bug-123` → Environment `copilot-fix-bug-123`

### Manual Control

You can also manually manage Copilot environments:

**Via GitHub Actions UI:**
1. Go to Actions tab
2. Select "Railway Copilot Session Environments"
3. Click "Run workflow"
4. Choose action: `deploy`, `test`, `status`, or `destroy`
5. Enter session ID

**Via Script:**
```bash
# From devcontainer or Codespaces
./scripts/railway_ephemeral_env.sh deploy copilot-my-session
./scripts/railway_ephemeral_env.sh test copilot-my-session
./scripts/railway_ephemeral_env.sh status copilot-my-session
./scripts/railway_ephemeral_env.sh destroy copilot-my-session
```

### Copilot Environment Configuration

Each Copilot environment automatically receives:

```bash
ENVIRONMENT=copilot-preview
DEBUG=true
LOG_LEVEL=debug
SESSION_TYPE=copilot
BRANCH_NAME=copilot/feature-name
GIT_SHA=abc123def456
YOTO_CLIENT_ID={synced from GitHub Secrets}
```

## Setup Requirements

### 1. GitHub Repository Secrets

Configure these secrets in your GitHub repository:

**Settings → Secrets and variables → Actions → New repository secret**

Required secrets:
```
RAILWAY_TOKEN       - Railway API token for deployments
YOTO_CLIENT_ID      - Yoto API client ID (for testing)
```

To get RAILWAY_TOKEN:
1. Go to https://railway.app/account/tokens
2. Click "Create Token"
3. Copy token and add to GitHub Secrets

### 2. GitHub Codespaces Secrets

For Copilot sessions in GitHub Codespaces to access Railway:

**User Settings → Codespaces → Secrets → New secret**

Add:
```
Name: RAILWAY_TOKEN
Value: {your Railway API token}
Repository access: {select this repository}
```

This allows Copilot sessions running in Codespaces to deploy and manage Railway environments directly.

### 3. Railway Project Configuration

**Enable PR Deployments in Railway Dashboard:**

1. Go to Railway project settings
2. Navigate to **GitHub** section
3. Enable **"PR Deploys"**
4. Check **"Create ephemeral environment for each PR"**
5. Check **"Auto-destroy on PR close/merge"**
6. Set **Environment template**: Use `staging` as base

## Using the Ephemeral Environment Script

The script `scripts/railway_ephemeral_env.sh` provides a CLI for managing environments.

### Commands

```bash
# Create environment (optional, usually auto-created)
./scripts/railway_ephemeral_env.sh create pr-123

# Deploy to environment
./scripts/railway_ephemeral_env.sh deploy pr-123

# Test environment
./scripts/railway_ephemeral_env.sh test pr-123

# Check status
./scripts/railway_ephemeral_env.sh status pr-123

# Destroy environment
./scripts/railway_ephemeral_env.sh destroy pr-123

# Show help
./scripts/railway_ephemeral_env.sh help
```

### Environment Variables

The script uses these environment variables:

```bash
RAILWAY_TOKEN       # Railway API token (required for CI/CD)
YOTO_CLIENT_ID      # Yoto API credentials (synced to Railway)
```

### Authentication

**For local development:**
```bash
railway login
```

**For CI/CD (GitHub Actions):**
```bash
export RAILWAY_TOKEN="your_token"
```

**For GitHub Codespaces:**
- Set `RAILWAY_TOKEN` as a Codespace secret (user level)
- Available automatically in all Codespaces

## Testing Workflow

### For PR Authors

1. **Open PR** - Environment auto-deploys
2. **Review PR comment** - Contains deployment URL
3. **Wait 1-2 minutes** - For deployment to complete
4. **Test your changes** - Using the provided URL
5. **Check logs** - Via Railway dashboard if needed
6. **Merge/Close PR** - Environment auto-destroys

### For Reviewers

1. **Open PR page** - View deployment comment
2. **Click deployment URL** - Test the changes
3. **Verify functionality** - Check health endpoint, test APIs
4. **Review logs** - If issues found
5. **Approve/Request changes** - Based on testing

## Cost Optimization

Ephemeral environments are designed to minimize costs:

### Resource Limits

**PR Environments:**
- RAM: 512 MB (web service)
- CPU: 0.5 vCPU
- Storage: 1 GB (ephemeral PostgreSQL)
- Uptime: Only during PR lifecycle

**Copilot Environments:**
- RAM: 512 MB (web service)
- CPU: 0.5 vCPU
- Storage: 1 GB (if needed)
- Uptime: Only during development session

### Automatic Cleanup

- PR environments: Destroyed on PR close/merge
- Copilot environments: Destroyed on branch delete
- No manual cleanup required
- Zero cost when not in use

### Cost Monitoring

**Via Railway Dashboard:**
1. Go to **Project Settings**
2. Click **Usage**
3. Review **Current Month** usage
4. Set up **Billing Alerts**

**Via CLI:**
```bash
railway status  # Check resource usage
railway logs    # Monitor activity
```

## Troubleshooting

### Deployment Fails

**Check GitHub Actions logs:**
1. Go to **Actions** tab
2. Click on failed workflow run
3. Review deployment step logs

**Check Railway logs:**
```bash
railway logs -e pr-123 --tail 100
```

**Common issues:**
- RAILWAY_TOKEN not set or invalid
- Build errors (check dependencies)
- Resource limits exceeded
- Railway service quota reached

### Environment Not Accessible

**Wait for deployment:**
```bash
# Deployments take 1-2 minutes
railway status -e pr-123
```

**Check health endpoint:**
```bash
curl https://yoto-smart-stream-pr-123.up.railway.app/health
```

**View recent logs:**
```bash
railway logs -e pr-123 --tail 50
```

### Environment Not Destroyed

**Manual cleanup:**
```bash
./scripts/railway_ephemeral_env.sh destroy pr-123
```

**Or via Railway Dashboard:**
1. Go to project
2. Select environment
3. Click **Delete Environment**

### RAILWAY_TOKEN Issues in Codespaces

**Verify secret is set:**
1. Go to **User Settings** → **Codespaces** → **Secrets**
2. Verify `RAILWAY_TOKEN` is listed
3. Check repository access is granted

**Test in Codespace:**
```bash
echo $RAILWAY_TOKEN  # Should show token (or part of it)
railway whoami       # Should show authenticated user
```

## Best Practices

### For Developers

✅ **DO:**
- Open PRs early to get automatic environments
- Test changes in PR environment before requesting review
- Use PR environment URL in PR description
- Close PRs when done to free resources
- Check logs if deployment fails

❌ **DON'T:**
- Leave PRs open indefinitely
- Try to use PR environments for production testing
- Share PR environment URLs with customers
- Store production data in PR environments

### For Copilot Sessions

✅ **DO:**
- Use Copilot environments for AI-assisted development
- Set RAILWAY_TOKEN in Codespaces secrets
- Delete branches when session complete
- Use manual workflow triggers for control

❌ **DON'T:**
- Leave copilot branches indefinitely
- Use copilot environments for production testing
- Share copilot credentials

## Security Considerations

### Secrets Management

- **GitHub Secrets** - Secure storage for RAILWAY_TOKEN, YOTO_CLIENT_ID
- **Railway Variables** - Synced automatically, never exposed in logs
- **Codespaces Secrets** - User-level, not repository-level

### Access Control

- PR environments: Public URLs (treat as development)
- Copilot environments: Public URLs (treat as development)
- Production: Separate environment, different credentials

### Data Protection

- Never use production data in PR/Copilot environments
- Use test data only
- Ephemeral databases - data lost on cleanup
- No backups for ephemeral environments

## Monitoring

### Active Environments

**Via Railway Dashboard:**
- View all active environments
- Check resource usage
- Monitor costs

**Via CLI:**
```bash
railway list              # List all projects
railway status            # Show current environment
railway status -e pr-123  # Show specific environment
```

### Logs

**Real-time logs:**
```bash
railway logs -e pr-123 --follow
```

**Filtered logs:**
```bash
railway logs -e pr-123 --filter "ERROR"
railway logs -e pr-123 --filter "health"
```

## Support

### Resources

- **Railway Documentation**: https://docs.railway.app/
- **Railway CLI Reference**: https://docs.railway.app/reference/cli
- **Railway Discord**: https://discord.gg/railway
- **GitHub Actions Docs**: https://docs.github.com/en/actions

### Getting Help

**For Railway issues:**
- Check Railway status: https://status.railway.app/
- Search Railway docs
- Ask in Railway Discord

**For workflow issues:**
- Check GitHub Actions logs
- Review this documentation
- Check script output

## Migration and Updates

### From Manual Deployments

If you were manually deploying to Railway:

1. Add RAILWAY_TOKEN to GitHub Secrets
2. Workflows will handle deployments automatically
3. No need to run `railway up` manually for PRs
4. Continue using CLI for production deployments

### Updating Workflows

When modifying workflows:

1. Test changes in a PR first
2. Use `workflow_dispatch` for manual testing
3. Review Actions logs carefully
4. Update documentation as needed

## FAQ

**Q: How long does a PR environment take to deploy?**  
A: Typically 1-2 minutes from PR creation.

**Q: What happens if I forget to close a PR?**  
A: The environment stays running and incurs costs. Close PRs promptly.

**Q: Can I access PR environment from my local machine?**  
A: Yes, use the public URL provided in the PR comment.

**Q: How do I get Railway token for Codespaces?**  
A: Create a token at https://railway.app/account/tokens and add to Codespaces secrets.

**Q: Are PR environments secure?**  
A: They use public URLs. Don't use production data or credentials.

**Q: How much do ephemeral environments cost?**  
A: Minimal - only ~$0.01-0.05 per hour per environment, auto-destroyed when done.

**Q: Can I customize the environment configuration?**  
A: Yes, modify the workflow files or script as needed.

**Q: What if deployment fails?**  
A: Check GitHub Actions logs and Railway logs for error details.

**Q: Can I manually create an environment?**  
A: Yes, use the script: `./scripts/railway_ephemeral_env.sh create my-env`

---

**Last Updated:** 2026-01-10  
**Version:** 1.0.0
