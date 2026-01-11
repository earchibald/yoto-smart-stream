# Railway Shared Development Environment

## Overview

Due to Yoto OAuth requirements for **static callback URLs**, we cannot use ephemeral environments with dynamic URLs for authentication. Instead, this project uses:

- **Production Environment** - Static, production-facing (main branch)
- **Staging Environment** - Static, pre-production testing (develop branch)  
- **Development Environment** - Static, shared for PR/Copilot testing (manual deployment with coordination)

## The Problem with Ephemeral Environments

When you register a Yoto application at https://yoto.dev/, you must specify callback URLs for OAuth authentication. These URLs must be:

1. **Pre-registered** in the Yoto developer portal
2. **Static** - cannot change between deployments
3. **Explicitly allowed** - dynamic URLs like `pr-123.up.railway.app` cannot authenticate

Ephemeral environments with dynamic URLs (`pr-123`, `copilot-abc`) would have different URLs each time, which Yoto's OAuth would reject.

## Solution: Shared Development Environment

We use a **single shared development environment** with a **coordination mechanism** to avoid conflicts:

```
Production    - https://yoto-smart-stream-production.up.railway.app       (main branch, auto-deploy)
Staging       - https://yoto-smart-stream-staging.up.railway.app (develop branch, auto-deploy)
Development   - https://yoto-smart-stream-development.up.railway.app   (manual, coordinated access)
```

### Coordination Mechanism

The development environment uses a **lock file** system:

1. Before deploying, a session **acquires the lock**
2. Lock file tracks who is using the environment
3. After testing, the session **releases the lock**
4. Stale locks (>2 hours) are auto-released

This prevents multiple developers/sessions from deploying simultaneously and interfering with each other.

## Usage

### For Copilot Sessions

When working in a Copilot session and you need to test on Railway:

**1. Check if environment is free:**

Go to: **Actions** → **Railway Development (Shared Environment)** → **Run workflow**
- Action: `status`
- Session ID: `copilot-your-feature`

**2. Acquire lock and deploy (if free):**

- Action: `acquire-and-deploy`
- Session ID: `copilot-your-feature`
- Force: `false` (only check this if you need to override)

**3. Test your changes:**

- URL: https://yoto-smart-stream-development.up.railway.app
- Use Yoto OAuth with this static URL
- Test your features

**4. Release lock when done:**

- Action: `release`
- Session ID: `copilot-your-feature`

### For PR Testing

**1. Check status:**
```bash
# Via GitHub Actions UI
Actions → Railway Development → Run workflow → status
```

**2. Deploy PR changes:**
```bash
# Via GitHub Actions UI
Actions → Railway Development → Run workflow
- Action: acquire-and-deploy
- Session ID: pr-123
```

**3. Test at static URL:**
```
https://yoto-smart-stream-development.up.railway.app
```

**4. Release when done:**
```bash
Actions → Railway Development → Run workflow
- Action: release
- Session ID: pr-123
```

## Deployment Guards

The workflow only deploys when there are **substantive changes**:

✅ **Deploys for:**
- Python code changes (.py files)
- Configuration changes (.toml, .json, .yml)
- Dependency changes (requirements.txt, package.json)
- Script changes (.sh)

❌ **Skips for:**
- Documentation only (.md files)
- README updates
- Comment changes
- Whitespace changes

You can override this with the `force` option if needed.

## Lock File Details

Lock files are stored in `.railway-locks/` directory:

```json
{
  "session_id": "copilot-add-feature",
  "timestamp": "2026-01-10T20:00:00Z",
  "actor": "username",
  "run_id": "123456",
  "sha": "abc123"
}
```

### Lock Behavior

- **Automatic acquisition** - Workflow creates lock on deploy
- **Ownership check** - Only lock owner can release
- **Stale lock auto-release** - Locks older than 2 hours are auto-released
- **Force override** - Emergency override available (use with caution)

## Best Practices

### ✅ DO:

- Check status before deploying
- Use descriptive session IDs (`copilot-feature-name`, `pr-123`)
- Release lock as soon as you're done testing
- Deploy only when you have substantive code changes
- Coordinate with team if you need extended testing time

### ❌ DON'T:

- Deploy documentation-only changes
- Hold locks for extended periods (>2 hours)
- Force override without checking with team
- Leave sessions running without releasing
- Deploy without checking status first

## Static URLs for Yoto OAuth

Register these URLs in your Yoto application at https://yoto.dev/:

```
Callback URLs:
- https://yoto-smart-stream-development.up.railway.app/callback
- https://yoto-smart-stream-staging.up.railway.app/callback
- https://yoto-smart-stream-production.up.railway.app/callback

Audio Streaming Base URLs:
- https://yoto-smart-stream-development.up.railway.app/audio
- https://yoto-smart-stream-staging.up.railway.app/audio  
- https://yoto-smart-stream-production.up.railway.app/audio
```

## Railway Shared Variables Configuration

### Startup Wait for Variable Initialization

When deploying to the shared development environment, Railway shared variables may take a few seconds to initialize. To prevent startup failures:

**Set in Railway Dashboard:**
1. Go to Railway → Yoto Smart Stream → development environment
2. Navigate to Variables tab
3. Add: `RAILWAY_STARTUP_WAIT_SECONDS=10`

**Or via Railway CLI:**
```bash
railway variables set RAILWAY_STARTUP_WAIT_SECONDS=10 -e development
```

**Recommended Values:**
- Production/Staging: `0` (no wait needed)
- Development (shared): `5-10` seconds
- Maximum: `30` seconds

**What it does:**
- Adds a configurable delay at application startup
- Ensures environment variables are loaded before use
- Logs startup wait progress for visibility

**When enabled, you'll see in logs:**
```
⏳ Waiting 10 seconds for Railway variables to initialize...
✓ Railway startup wait complete
```

## Troubleshooting

### Variables not loading at startup

**Problem:** Application starts but environment variables are not available, causing initialization failures.

**Symptoms:**
- "Could not initialize Yoto API: A client_id must be provided"
- Missing configuration values that should be set
- Errors accessing expected environment variables

**Solution:**
1. **Increase startup wait time:**
   ```bash
   railway variables set RAILWAY_STARTUP_WAIT_SECONDS=10 -e development
   ```

2. **Verify variables are set:**
   ```bash
   railway variables -e development
   ```

3. **Check deployment logs:**
   - Look for "⏳ Waiting N seconds..." message
   - Verify wait completes before variable access
   - Check if variables are available after wait

4. **If still failing:**
   - Increase wait time to 15-20 seconds
   - Check Railway status page for service issues
   - Try redeploying the service

### Lock is held by another session

**Problem:** Workflow fails with "Development environment is locked"

**Solution:**
1. Check lock status to see who has it
2. Contact the lock owner to release
3. Wait for auto-release (2 hours)
4. Use `force` option if urgent (coordinate with team)

### Lock is stale but not released

**Problem:** Lock exists but owner is no longer using it

**Solution:**
- Stale locks (>2 hours) are automatically released
- Or use `force` option to override

### Need to deploy urgently

**Problem:** Need to test but environment is locked

**Solution:**
1. Check with lock owner first
2. If no response and urgent, use `force` option
3. Be aware you may interfere with their testing

### No substantive changes detected

**Problem:** Workflow skips deployment

**Solution:**
- If you really need to deploy, use `force` option
- Or make a small code change to trigger deployment
- Documentation-only changes don't need Railway deployment

## Workflow Commands

### Via GitHub Actions UI

1. Go to **Actions** tab
2. Select **Railway Development (Shared Environment)**
3. Click **Run workflow**
4. Fill in parameters:
   - **session_id**: Your unique session identifier
   - **action**: What you want to do
   - **force**: Override locks/guards (use carefully)

### Via GitHub CLI

```bash
# Check status
gh workflow run railway-development-shared.yml \
  -f action=status \
  -f session_id=copilot-test

# Acquire and deploy
gh workflow run railway-development-shared.yml \
  -f action=acquire-and-deploy \
  -f session_id=copilot-test

# Release lock
gh workflow run railway-development-shared.yml \
  -f action=release \
  -f session_id=copilot-test
```

## Migration from Ephemeral Environments

If you were using the previous ephemeral environment approach:

**What changed:**
- ❌ No automatic PR environment creation
- ❌ No automatic Copilot branch deployments
- ✅ Manual deployment to shared development environment
- ✅ Coordination mechanism to avoid conflicts
- ✅ Static URLs that work with Yoto OAuth

**What to do:**
- Use the new shared development workflow
- Register static URLs in Yoto developer portal
- Coordinate with team members
- Release locks when done testing

## Cost Impact

**Before (Ephemeral):**
- Multiple environments running simultaneously
- Cost: $0.01-0.05/hour per environment
- Unpredictable total cost

**After (Shared):**
- Single shared development environment
- Cost: ~$0.05-0.10/hour (always running)
- Predictable, lower total cost

## Support

- **Workflow:** `.github/workflows/railway-development-shared.yml`
- **Lock Directory:** `.railway-locks/`
- **Static URLs:** Configured in Railway dashboard
- **Questions:** Open GitHub issue or discussion

---

**Last Updated:** 2026-01-10  
**Version:** 2.0.0 (Shared Environment)  
**Reason:** Yoto OAuth requires static callback URLs
