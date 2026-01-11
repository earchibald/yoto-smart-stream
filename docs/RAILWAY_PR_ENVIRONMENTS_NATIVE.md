# Railway Native PR Environments - Quick Start Guide

## What is Railway's Native PR Environments?

Railway's PR Environments is a built-in platform feature that automatically creates and manages ephemeral environments for your pull requests. Unlike custom script-based solutions, this feature requires **zero configuration** beyond initial setup and handles the entire lifecycle automatically.

## Why Use Native PR Environments?

### Benefits

✅ **Zero Configuration** - No GitHub Actions workflows or custom scripts needed  
✅ **Automatic Lifecycle** - Creates on PR open, updates on push, destroys on close/merge  
✅ **Native GitHub Integration** - Status checks and deployment links built-in  
✅ **Cost-Effective** - Only pay while PR is open, automatic cleanup  
✅ **Consistent Configuration** - Inherits from base environment (staging)  
✅ **Reduced Maintenance** - Railway manages everything for you  

### Comparison with Custom Ephemeral Environments

| Feature | Native PR Environments | Custom Ephemeral Envs |
|---------|----------------------|----------------------|
| Setup Complexity | ⭐ Easy (5 min) | ⭐⭐⭐ Complex (30+ min) |
| Maintenance | ⭐ Zero | ⭐⭐⭐ High (scripts, workflows) |
| GitHub Integration | ✓ Built-in | Custom implementation |
| Lifecycle Management | ✓ Automatic | Manual scripting |
| Configuration | Inherits from base | Custom per environment |
| Customization | Limited | Full control |

**Recommendation:** Use Native PR Environments for standard PR workflows. Use custom ephemeral environments only when you need:
- Custom naming conventions
- Non-PR triggered deployments (e.g., Copilot sessions)
- Advanced deployment strategies
- Workarounds for specific limitations

## Current Status in This Project

This project currently has:
- ✅ **Native PR Environments**: Enabled in Railway dashboard
- ⚠️ **Custom Ephemeral Workflow**: Currently disabled (see `.github/workflows/railway-pr-environments.yml`)
- 📝 **Custom Scripts**: Available for special cases (see `scripts/railway_ephemeral_env.sh`)

**Note:** The custom PR workflow is disabled because Yoto OAuth requires static callback URLs, which don't work well with dynamic PR environment URLs. However, Railway's native PR Environments can still be used for:
- Health check testing
- Integration testing
- UI/frontend testing
- Non-OAuth functionality testing

## Quick Setup (5 Minutes)

### Step 1: Enable PR Environments in Railway

1. Go to your Railway project: https://railway.app/dashboard
2. Click on your project (yoto-smart-stream)
3. Navigate to **Settings** → **GitHub**
4. Scroll to **PR Environments** section
5. Click **Enable**
6. Configure:
   - **Base Environment**: Select `staging`
   - **Auto-Deploy on PR updates**: ✓ Enable
   - **Auto-Destroy on PR close/merge**: ✓ Enable
   - **Target Branches**: Add `main` and `develop`
7. Click **Save**

### Step 2: Test It

1. Create a test branch:
   ```bash
   git checkout -b test/railway-pr-env
   git push origin test/railway-pr-env
   ```

2. Open a PR on GitHub targeting `develop` or `main`

3. Watch Railway automatically:
   - Create environment `pr-{number}`
   - Deploy your code
   - Post status check on GitHub

4. Access your PR environment:
   ```
   https://yoto-smart-stream-pr-{number}.up.railway.app
   ```

5. Close the PR and watch Railway automatically destroy the environment

## Using PR Environments

### For Developers

**When you open a PR:**

1. Railway automatically creates `pr-{number}` environment
2. Check the PR status checks for deployment link
3. Wait 1-2 minutes for deployment to complete
4. GitHub Actions automatically validates the deployment
5. Check PR comments for validation results
6. Test your changes at the provided URL

**When you push updates:**

1. Railway automatically redeploys
2. Same URL, updated code
3. Watch status checks for deployment progress
4. Validation runs automatically on each update

**When you close/merge:**

1. Railway automatically destroys environment
2. No cleanup needed
3. Zero ongoing costs

### Validating Your PR Environment

Each PR deployment is automatically validated by GitHub Actions. You can also manually validate:

```bash
# Validate a specific PR environment
python scripts/validate_pr_environment.py https://yoto-smart-stream-pr-42.up.railway.app

# Wait for deployment and validate
python scripts/validate_pr_environment.py https://yoto-smart-stream-pr-42.up.railway.app --wait
```

For detailed validation instructions, see **[Validating PR Environments](VALIDATING_PR_ENVIRONMENTS.md)**.

### Accessing Your PR Environment

**Via GitHub:**
- Check PR status checks for "Railway" deployment
- Click "View deployment" link

**Via URL Pattern:**
```bash
# Health check
curl https://yoto-smart-stream-pr-{NUMBER}.up.railway.app/health

# Example for PR #42
curl https://yoto-smart-stream-pr-42.up.railway.app/health
```

**Via Railway CLI:**
```bash
# View status
railway status -e pr-42

# View logs
railway logs -e pr-42 --tail 100 --follow

# Run commands
railway run -e pr-42 python manage.py shell
```

**Via Railway Dashboard:**
```bash
# Open environment in browser
railway open -e pr-42
```

### Testing in PR Environments

**What you can test:**
- ✅ Health endpoints
- ✅ API endpoints (non-OAuth)
- ✅ Database migrations
- ✅ UI/frontend components
- ✅ Integration tests
- ✅ Build and deployment process

**What won't work:**
- ❌ Yoto OAuth flow (requires static callback URLs)
- ❌ Features requiring OAuth authentication
- ❌ Production-level load testing

**Testing workflow:**
```bash
# 1. Check health
curl https://yoto-smart-stream-pr-{NUMBER}.up.railway.app/health

# 2. Test API endpoints
curl https://yoto-smart-stream-pr-{NUMBER}.up.railway.app/api/cards

# 3. Check logs for errors
railway logs -e pr-{NUMBER} --filter "ERROR"

# 4. Run integration tests
pytest tests/integration/ --base-url=https://yoto-smart-stream-pr-{NUMBER}.up.railway.app
```

## Configuration

### Environment Variables

PR environments automatically inherit variables from the base environment (staging):

**Inherited:**
- `YOTO_CLIENT_ID`
- `DATABASE_URL` (new ephemeral database)
- `PORT` (auto-assigned by Railway)
- All other staging variables

**Automatically Set by Railway:**
- `RAILWAY_ENVIRONMENT_NAME=pr-{number}` - Used by the application as the environment name
- `RAILWAY_GIT_COMMIT_SHA={commit SHA}`
- `RAILWAY_GIT_BRANCH={source branch}`

**Automatically Configured by GitHub Actions:**
- `YOTO_CLIENT_ID` - Synced from GitHub secrets by workflow

The `railway-pr-checks.yml` workflow automatically configures these essential variables when a PR is opened or updated, ensuring the PR environment has the correct configuration for testing. The application now uses `RAILWAY_ENVIRONMENT_NAME` directly instead of a custom `ENVIRONMENT` variable.

### Custom Variables

Add PR-specific variables via Railway CLI:

```bash
# Set for specific PR
railway variables set DEBUG=true -e pr-42
railway variables set LOG_LEVEL=debug -e pr-42

# Set for all future PRs (via base environment)
railway variables set DEFAULT_TIMEOUT=300 -e staging
```

### Database Configuration

Each PR environment gets its own ephemeral PostgreSQL database:

**Characteristics:**
- Fresh database instance
- Minimal size (1 GB)
- Empty on creation
- Destroyed with environment

**Running Migrations:**

Option 1 - Automatic (Recommended):
```toml
# railway.toml
[deploy]
startCommand = "python manage.py migrate && uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port $PORT"
```

Option 2 - Manual:
```bash
railway run -e pr-42 python manage.py migrate
```

Option 3 - GitHub Actions:
```yaml
# .github/workflows/pr-checks.yml
- name: Run migrations
  run: |
    railway run -e pr-${{ github.event.pull_request.number }} python manage.py migrate
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## GitHub Integration

### Status Checks

Railway automatically updates PR status checks:

**Check Information:**
- Deployment status (pending, success, failed)
- Deployment URL
- Build logs link
- Deployment time

**In PR:**
```
✓ Railway — Deployment successful
  View deployment: https://yoto-smart-stream-pr-42.up.railway.app
  Details: View logs
```

### Optional: GitHub Actions Integration

While Railway handles deployments, you can add GitHub Actions for testing:

```yaml
# .github/workflows/pr-checks.yml
name: PR Checks

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
          pytest tests/ -v
      
      # Railway deployment happens automatically in parallel

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
          
          # Wait for health check
          for i in {1..10}; do
            if curl -f "${URL}/health"; then
              echo "✓ Health check passed"
              break
            fi
            echo "Waiting for deployment... ($i/10)"
            sleep 10
          done
          
          # Run integration tests
          pytest tests/integration/ --base-url="${URL}"
```

## Cost Management

### Cost Estimation

**Per PR Environment:**
- Web service: ~$0.01-0.02/hour
- Database: ~$0.005-0.01/hour
- **Total: ~$0.015-0.03/hour**

**Typical PR Lifecycle:**
- Average open time: 2-4 hours
- **Average cost per PR: $0.03-0.12**

### Cost Optimization

**Automatic:**
- ✓ Auto-destroy on PR close/merge
- ✓ Scaled-down resources vs production
- ✓ Single replica (no horizontal scaling)

**Manual:**
```bash
# Close stale PRs promptly
# Monitor active PR environments
railway status --all | grep "pr-"

# Manual cleanup if needed
railway down -e pr-42
```

### Billing Alerts

Set up in Railway Dashboard:
1. Go to **Settings** → **Billing**
2. Click **Alerts**
3. Set thresholds:
   - Monthly spend > $50
   - Active PR environments > 10
   - Individual environment > $1/day

## Troubleshooting

### Environment Not Created

**Symptoms:** PR opened but no Railway environment created

**Check:**
```bash
# 1. Verify PR Environments enabled
# Railway Dashboard → Settings → GitHub → PR Environments

# 2. Check target branches
# Ensure PR targets main or develop

# 3. Check Railway GitHub app permissions
# GitHub → Settings → Applications → Railway
```

### Deployment Failed

**Check Build Logs:**
```bash
# Via CLI
railway logs -e pr-42 --deployment {id}

# Via Dashboard
railway open -e pr-42
```

**Common Issues:**
- Missing dependencies in requirements.txt
- Python version mismatch
- Build command errors
- Environment variable issues

**Solutions:**
```bash
# Fix dependencies
# Update requirements.txt
git commit -am "Fix dependencies"
git push  # Railway redeploys automatically

# Check logs for specifics
railway logs -e pr-42 --tail 200
```

### Cannot Access URL

**Symptoms:** URL returns 404 or connection refused

**Debug:**
```bash
# 1. Check deployment status
railway status -e pr-42

# 2. Verify health check
curl -v https://yoto-smart-stream-pr-42.up.railway.app/health

# 3. Check application logs
railway logs -e pr-42 --tail 100

# 4. Verify PORT binding
# Ensure app listens on $PORT environment variable
```

**Common Issues:**
- App not listening on correct port
- Health check failing
- Start command incorrect
- Application crash on startup

### Environment Not Destroyed

**Symptoms:** PR closed but environment still running

**Manual Cleanup:**
```bash
# Via CLI
railway down -e pr-42

# Via Dashboard
# Railway → Environments → pr-42 → Delete
```

## Migration from Custom Ephemeral Environments

### Current State

This project has custom ephemeral environment infrastructure:
- Scripts: `scripts/railway_ephemeral_env.sh`
- Workflow: `.github/workflows/railway-pr-environments.yml` (disabled)
- Docs: `docs/EPHEMERAL_RAILWAY_ENVIRONMENTS.md`

### Migration Strategy

**Option 1: Full Migration (Recommended for standard PRs)**

1. Enable Railway native PR Environments (already done)
2. Keep custom workflow disabled
3. Keep custom scripts for non-PR use cases (Copilot sessions, etc.)
4. Update documentation to prefer native approach

**Option 2: Hybrid Approach (Current)**

1. Use Railway native PR Environments for automatic deployments
2. Keep custom scripts available for:
   - Copilot session environments
   - Custom testing environments
   - Non-PR development environments
3. Document when to use each approach

**Option 3: Keep Custom Only**

1. Disable Railway native PR Environments
2. Continue using custom workflow and scripts
3. More maintenance but full control

### Recommended: Hybrid Approach

**Use Railway Native PR Environments:**
- ✓ Standard pull request workflows
- ✓ Main and develop branch PRs
- ✓ Automatic deployment and cleanup
- ✓ Zero maintenance

**Use Custom Ephemeral Environments:**
- ✓ GitHub Copilot session testing
- ✓ Custom environment names
- ✓ Non-PR triggered deployments
- ✓ Advanced deployment strategies

## Best Practices

### ✅ DO:

1. **Enable for all target branches** (main, develop)
2. **Use staging as base template**
3. **Test in PR environment before requesting review**
4. **Close PRs promptly** to minimize costs
5. **Monitor deployment status** via GitHub checks
6. **Use health checks** for reliable deployments
7. **Run migrations automatically** on deployment
8. **Set appropriate resource limits**
9. **Document test results** in PR comments
10. **Check logs** if deployment fails

### ❌ DON'T:

1. Don't use production credentials
2. Don't share production database
3. Don't leave PRs open indefinitely
4. Don't skip health checks
5. Don't ignore deployment failures
6. Don't manually create PR environments
7. Don't override auto-destroy
8. Don't use for load testing
9. Don't share sensitive data
10. Don't deploy production-level resources

## Support and Resources

### Documentation

- **This Guide**: Quick start for native PR Environments
- **Skill Reference**: `.github/skills/railway-service-management/reference/pr_environments.md`
- **Railway Docs**: https://docs.railway.app/ (if accessible)
- **Custom Ephemeral Docs**: `docs/EPHEMERAL_RAILWAY_ENVIRONMENTS.md`

### Commands Reference

```bash
# View environment status
railway status -e pr-{NUMBER}

# View logs
railway logs -e pr-{NUMBER} --tail 100 --follow

# Run migrations
railway run -e pr-{NUMBER} python manage.py migrate

# Execute shell commands
railway run -e pr-{NUMBER} python manage.py shell

# Manual cleanup
railway down -e pr-{NUMBER}

# Open in dashboard
railway open -e pr-{NUMBER}
```

### Getting Help

**Railway Issues:**
- Check Railway status: https://status.railway.app/
- Railway Discord: https://discord.gg/railway
- Railway Dashboard: https://railway.app/dashboard

**GitHub Issues:**
- Check Actions logs in GitHub
- Review PR status checks
- Check repository settings

**Project-Specific:**
- Review project documentation
- Check custom scripts if needed
- Consult team members

## Summary

Railway's native PR Environments provide a **zero-configuration, fully-managed solution** for ephemeral PR deployments. For this project:

1. ✅ **Native PR Environments are enabled** and ready to use
2. ✅ **Automatic lifecycle management** - no manual intervention needed
3. ✅ **GitHub integration** provides deployment status in PRs
4. ✅ **Custom scripts remain available** for special use cases
5. ⚠️ **OAuth limitations** - some features won't work due to dynamic URLs

**Start using it today:** Just open a PR and Railway handles the rest!

---

**Last Updated:** 2026-01-11  
**Version:** 1.0.0  
**Status:** Active and Recommended
