# Migration Guide: Ephemeral to Static Environments

## What Changed and Why

### The Problem

The initial implementation used **ephemeral environments** with dynamic URLs:
- `pr-123.up.railway.app`
- `copilot-add-feature.up.railway.app`

However, **Yoto OAuth requires static callback URLs** that must be pre-registered in the Yoto developer portal. Dynamic URLs cannot authenticate with Yoto API.

### The Solution

Switched to **static environments** with **coordination**:
- `yoto-smart-stream-production.up.railway.app` (production)
- `yoto-smart-stream-staging.up.railway.app` (staging)
- `yoto-smart-stream-development.up.railway.app` (development - shared)

Added **separate Railway tokens** per environment for better security.

## Quick Migration Steps

### 1. Create Three Railway Tokens

Go to https://railway.app/account/tokens and create:

```
Token 1: "Production Token"
→ Save as: RAILWAY_TOKEN_PROD

Token 2: "Staging Token"  
→ Save as: RAILWAY_TOKEN_STAGING

Token 3: "Development Token"
→ Save as: RAILWAY_TOKEN_DEV
```

### 2. Update GitHub Repository Secrets

**Remove old secret (if exists):**
- `RAILWAY_TOKEN` (single token)

**Add new secrets:**
1. Go to: Settings → Secrets and variables → Actions
2. Add three new secrets:
   - `RAILWAY_TOKEN_PROD` - Production token
   - `RAILWAY_TOKEN_STAGING` - Staging token
   - `RAILWAY_TOKEN_DEV` - Development token

### 3. Update Codespaces Secrets

**Keep or update:**
1. Go to: https://github.com/settings/codespaces
2. Find: `RAILWAY_TOKEN`
3. Update value to: Development token (same as RAILWAY_TOKEN_DEV)
4. Repository access: earchibald/yoto-smart-stream

### 4. Register Static URLs in Yoto Portal

1. Go to: https://yoto.dev/
2. Find your application
3. Add these callback URLs:
   ```
   https://yoto-smart-stream-production.up.railway.app/callback
   https://yoto-smart-stream-staging.up.railway.app/callback
   https://yoto-smart-stream-development.up.railway.app/callback
   ```

### 5. Test the Setup

**Test staging (automatic):**
```bash
git checkout develop
git push origin develop
# Check GitHub Actions for successful deployment
```

**Test development (manual):**
```
1. Go to: Actions → Railway Development (Shared Environment)
2. Run workflow:
   - action: status
   - session_id: test-migration
3. Run workflow:
   - action: acquire-and-deploy
   - session_id: test-migration
4. Verify at: https://yoto-smart-stream-development.up.railway.app
5. Run workflow:
   - action: release
   - session_id: test-migration
```

## What's Different

### Before (Ephemeral)

**PR opened → Automatic deployment**
- Environment: `pr-123.up.railway.app`
- No coordination needed
- Each PR had unique URL
- ❌ URLs not registered in Yoto portal

**Copilot branch pushed → Automatic deployment**
- Environment: `copilot-feature.up.railway.app`
- No coordination needed
- Each branch had unique URL
- ❌ URLs not registered in Yoto portal

### After (Static + Coordination)

**PR needs testing → Manual deployment**
- Environment: `yoto-smart-stream-development.up.railway.app` (shared)
- Coordination required (lock system)
- Static URL
- ✅ URL registered in Yoto portal

**Copilot needs testing → Manual deployment**
- Environment: `yoto-smart-stream-development.up.railway.app` (shared)
- Coordination required (lock system)
- Static URL
- ✅ URL registered in Yoto portal

## Workflow Changes

### Automatic Workflows (No Changes Needed)

**Staging Deployment:**
```yaml
# Still automatic on push to develop
Trigger: push to develop branch
Token: RAILWAY_TOKEN_STAGING
Environment: staging (static URL)
```

### New Manual Workflow

**Development Deployment:**
```yaml
# New: Manual with coordination
Trigger: workflow_dispatch (manual)
Token: RAILWAY_TOKEN_DEV
Environment: development (static URL, shared)
Coordination: Lock file system
```

### Disabled Workflows

**PR Environments:**
```yaml
# Disabled (can still trigger manually if needed)
Trigger: Commented out
Reason: OAuth callback URL requirement
```

**Copilot Environments:**
```yaml
# Disabled (can still trigger manually if needed)
Trigger: Commented out
Reason: OAuth callback URL requirement
```

## Using the New System

### For PR Testing

**Old way:**
```bash
1. Open PR
2. Wait for automatic deployment
3. Test at pr-123.up.railway.app
4. Close PR (automatic cleanup)
```

**New way:**
```bash
1. Open PR
2. Go to: Actions → Railway Development (Shared Environment)
3. Check status (ensure it's free)
4. Run acquire-and-deploy with session_id: pr-123
5. Test at yoto-smart-stream-development.up.railway.app
6. Run release with session_id: pr-123
```

### For Copilot Sessions

**Old way:**
```bash
1. Push to copilot/* branch
2. Wait for automatic deployment
3. Test at copilot-feature.up.railway.app
4. Delete branch (automatic cleanup)
```

**New way:**
```bash
1. Work in Copilot session
2. When ready to test:
   - Actions → Railway Development (Shared Environment)
   - acquire-and-deploy with session_id: copilot-session-xyz
3. Test at yoto-smart-stream-development.up.railway.app
4. When done:
   - Actions → Railway Development (Shared Environment)
   - release with session_id: copilot-session-xyz
```

## Coordination System

### Lock File

Located at: `.railway-locks/.railway-dev-lock.json`

**When deployed:**
```json
{
  "session_id": "pr-123",
  "timestamp": "2026-01-10T20:00:00Z",
  "actor": "username",
  "run_id": "123456",
  "sha": "abc123"
}
```

### Lock Behavior

- **Check before deploy** - Fails if locked by another session
- **Auto-release stale locks** - >2 hours old
- **Force override available** - For urgent cases
- **Manual release** - Use 'release' action when done

## Benefits of New Approach

✅ **OAuth Compatible**
- Static URLs work with Yoto authentication
- Pre-registered callback URLs
- No authentication errors

✅ **Better Security**
- Separate tokens per environment
- Easier token rotation
- Limit blast radius of compromises

✅ **Cost Effective**
- One shared dev environment vs many ephemeral
- Predictable costs
- No orphaned environments

✅ **Deployment Control**
- Only deploys substantive changes
- Skips doc-only changes
- Force override available

## Troubleshooting

### Migration Issues

**Issue:** Old RAILWAY_TOKEN secret still exists
**Fix:** Remove it to avoid confusion, use new env-specific tokens

**Issue:** Workflows failing with authentication errors
**Fix:** Ensure all three new tokens are added to GitHub Secrets

**Issue:** Can't deploy to development
**Fix:** Check lock status first, may need to force or wait for release

### Common Questions

**Q: Can I still use ephemeral environments?**
A: Manual trigger available, but won't work with Yoto OAuth

**Q: What if I need urgent dev testing but it's locked?**
A: Use force option in acquire-and-deploy (coordinate with lock owner first)

**Q: Do I need separate Yoto API credentials per environment?**
A: No, same YOTO_SERVER_CLIENT_ID works for all. Register all URLs in Yoto portal.

**Q: What happens to my existing PR environments?**
A: They still exist in Railway. Manually delete them if needed.

## Rollback (If Needed)

If you need to rollback to ephemeral environments:

1. **Re-enable automatic triggers:**
   - Edit `.github/workflows/railway-pr-environments.yml`
   - Uncomment `pull_request:` triggers
   - Same for `railway-copilot-environments.yml`

2. **Use single token:**
   - Rename one of the env tokens to `RAILWAY_TOKEN`
   - Update workflows to use `RAILWAY_TOKEN`

3. **Accept OAuth limitations:**
   - Understand that Yoto OAuth won't work
   - Use for non-OAuth testing only

**Note:** Not recommended due to OAuth incompatibility.

## Support

- **Full Guide:** `docs/RAILWAY_SHARED_DEVELOPMENT.md`
- **Token Setup:** `docs/RAILWAY_TOKEN_SETUP.md`
- **Questions:** Open GitHub issue

---

**Migration Date:** 2026-01-10  
**Reason:** Yoto OAuth static callback URL requirement  
**Status:** Complete
