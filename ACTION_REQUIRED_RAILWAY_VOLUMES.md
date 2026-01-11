# IMMEDIATE ACTION REQUIRED: Configure Railway Volumes

## Problem Solved

This PR addresses the issue where:
- ✅ Railway volumes defined in `railway.toml` were not being created
- ✅ `railway.toml` changes were not being applied automatically
- ✅ Fixed `railway.toml` syntax error (watchPatterns was nested incorrectly)

## What Was Implemented

1. **New Automated Workflow** (`.github/workflows/railway-config-sync.yml`)
   - Automatically detects and applies `railway.toml` changes
   - Triggers on push to main/develop when railway.toml is modified
   - Can be manually triggered for any environment

2. **Enhanced Deployment Workflow** (`railway-deploy.yml`)
   - Now checks for railway.toml configuration
   - Verifies volume configuration after deployment
   - Provides clear verification steps

3. **Fixed railway.toml**
   - Corrected TOML structure
   - `watchPatterns` now at correct level
   - Volume configuration validated

4. **Comprehensive Documentation**
   - `docs/RAILWAY_CONFIG_SYNC.md` - Full configuration sync guide
   - Updated railway-service-management skill documentation

## IMMEDIATE ACTION: Apply Configuration NOW

You need to trigger a Railway deployment to apply the railway.toml configuration and create the volumes. Choose ONE of the options below:

### Option 1: GitHub Actions Workflow (RECOMMENDED - Fastest)

**Step-by-step:**

1. Go to GitHub Actions:
   ```
   https://github.com/earchibald/yoto-smart-stream/actions/workflows/railway-config-sync.yml
   ```

2. Click the **"Run workflow"** dropdown button (top right)

3. Select inputs:
   - Branch: `copilot/check-reconfigure-railway-toml` (or `main` after merge)
   - Environment: `production`
   - Force: `false`

4. Click **"Run workflow"**

5. Wait 1-2 minutes for completion

6. Verify volumes created (see Verification section below)

**Why this option?**
- Fastest and most reliable
- Automated validation and error reporting
- Provides clear logs and verification steps

### Option 2: Railway CLI (If you have Railway CLI installed)

**Prerequisites:**
```bash
# Install Railway CLI (if not installed)
npm i -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link
```

**Apply configuration:**
```bash
# Checkout this branch
git checkout copilot/check-reconfigure-railway-toml

# Trigger redeployment to apply railway.toml
railway up --environment production --detach

# Wait 30-60 seconds, then verify
railway status -e production
```

### Option 3: Railway Dashboard (Manual)

1. Go to Railway Dashboard:
   ```
   https://railway.app/dashboard
   ```

2. Select your **yoto-smart-stream** project

3. Select the **service** (web application)

4. Navigate to **"Deployments"** tab

5. Find the **latest deployment**

6. Click **"Redeploy"** button

7. Wait for redeployment to complete (~1-2 minutes)

8. Verify volumes created (see Verification section below)

## Verification: Confirm Volumes Were Created

After applying configuration using any option above, verify volumes:

### Via Railway Dashboard (Visual)

1. Go to: https://railway.app/dashboard
2. Select **yoto-smart-stream** project
3. Select the **service**
4. Navigate to: **Settings → Volumes**
5. You should see:
   ```
   ✓ Volume: data
   ✓ Mount Path: /data
   ✓ Status: Active
   ```

### Via Railway CLI (Command-line)

```bash
# Check service status (shows volumes)
railway status -e production

# Expected output should include:
# Volumes:
#   - data -> /data
```

### Via Application Logs

```bash
# Check logs for volume mount confirmation
railway logs -e production --tail 50 | grep -i data
railway logs -e production --tail 50 | grep "/data"

# Application should log volume accessibility on startup
```

## What Happens After Verification?

Once volumes are created:

1. **Data persists across deployments** - Yoto OAuth tokens won't be lost on redeploy
2. **Application can store state** - /data directory survives restarts
3. **Future deployments** - Volumes automatically persist

## Automatic Configuration in Future

After merging this PR:

- ✅ **Any push to main with railway.toml changes** → Automatic reconfiguration
- ✅ **Any push to develop with railway.toml changes** → Automatic reconfiguration
- ✅ **Manual trigger available** → Run workflow for any environment anytime

## Troubleshooting

### Problem: Workflow run fails

**Check:**
1. GitHub Secrets are set: `RAILWAY_TOKEN_PROD`, `RAILWAY_TOKEN_STAGING`, `RAILWAY_TOKEN_DEV`
2. Railway CLI has access to the project
3. Railway service is not paused or deleted

**Solution:**
- Try Option 3 (Railway Dashboard manual redeploy)
- Check GitHub Actions logs for specific error

### Problem: Volumes don't appear after redeployment

**Check:**
1. Verify railway.toml syntax: `python -c "import toml; toml.load('railway.toml')"`
2. Confirm you're checking the correct environment (volumes are per-environment)
3. Check Railway logs for errors: `railway logs -e production`

**Solution:**
- Try redeploying again (sometimes takes 2 attempts)
- Verify railway.toml is at repository root
- Check Railway Dashboard for deployment errors

### Problem: "railway: command not found"

**Solution:**
```bash
# Install Railway CLI
npm i -g @railway/cli

# Or use npx
npx @railway/cli login
npx @railway/cli up -e production
```

## Summary

**Current Status:**
- ✅ railway.toml is fixed and validated
- ✅ Automated workflows are in place
- ✅ Documentation is complete
- ⏳ **ACTION REQUIRED**: Trigger deployment to create volumes

**Next Action:**
Choose Option 1, 2, or 3 above to apply configuration and create volumes NOW.

**After Action:**
Verify volumes in Railway Dashboard (Settings → Volumes).

## Questions?

- See: `docs/RAILWAY_CONFIG_SYNC.md` for detailed guide
- See: `.github/skills/railway-service-management/reference/deployment_workflows.md` for Railway patterns
- Railway Support: https://discord.gg/railway
