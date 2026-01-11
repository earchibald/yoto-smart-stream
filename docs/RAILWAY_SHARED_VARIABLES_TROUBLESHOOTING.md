# Railway Shared Variables Troubleshooting Guide

## Problem: `${{shared.YOTO_SERVER_CLIENT_ID}}` Returns Empty String

When using Railway's shared variables feature with the syntax `${{shared.YOTO_SERVER_CLIENT_ID}}` in PR environments, the variable resolves to an empty string instead of the expected value from the production environment.

## Root Cause Analysis

Railway's shared variables feature has specific configuration requirements that are not immediately obvious:

### 1. **Shared Variables Are NOT Automatically Available**

Unlike environment inheritance, shared variables require **explicit configuration** in the Railway web UI. Simply setting a variable in the production environment and using `${{shared.VARIABLE_NAME}}` syntax will NOT work.

### 2. **Three-Step Configuration Required**

For a shared variable to work in PR environments:

1. **Variable must exist** in the source environment (e.g., production)
2. **Variable must be marked as "shared"** in Railway UI
3. **Sharing scope must include** the target environments (PR environments)

### 3. **PR Environments Require Special Handling**

PR environments are dynamically created, so static sharing configuration may not include them. Railway's shared variables feature may need to be configured with:
- "All environments" scope, OR
- Dynamic environment patterns (if supported), OR
- Manual configuration for each PR environment (not practical)

## Current Workaround in This Project

The GitHub workflows (`.github/workflows/railway-pr-checks.yml`) currently work around this limitation by **directly setting variables** using Railway CLI:

```yaml
- name: Configure PR Environment Variables
  env:
    RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
    YOTO_SERVER_CLIENT_ID: ${{ secrets.YOTO_SERVER_CLIENT_ID }}
  run: |
    if [ -n "$YOTO_SERVER_CLIENT_ID" ]; then
      railway variables set YOTO_SERVER_CLIENT_ID="$YOTO_SERVER_CLIENT_ID" -e "pr-${PR_NUMBER}"
    fi
```

This approach:
- ✅ **Works reliably** - Direct assignment always works
- ✅ **Uses GitHub Secrets** - Centralized secret management
- ✅ **Automatic** - Runs on every PR update
- ❌ **Bypasses shared variables** - Doesn't use Railway's native feature
- ❌ **Requires GitHub Actions** - Additional infrastructure

## Proper Fix: Configure Railway Shared Variables

To properly use Railway's shared variables feature:

### Step 1: Access Railway Dashboard

1. Go to: https://railway.app
2. Select project: **yoto-smart-stream**
3. Navigate to the **production** environment

### Step 2: Share the Variable

1. Click on the **Variables** tab in production environment
2. Find the `YOTO_SERVER_CLIENT_ID` variable
3. Click the **⋮** (three dots) menu next to the variable
4. Select **"Share variable"**

### Step 3: Configure Sharing Scope

You have two options:

#### Option A: Share with All Environments (Recommended)

- Select **"All environments"**
- This includes current and future PR environments
- Simplest approach, works automatically

#### Option B: Share with Specific Environments

- Select specific environments:
  - ✅ staging
  - ✅ development
  - ⚠️ **Problem**: PR environments (pr-123, pr-456, etc.) are dynamic
  - ❌ You'd need to add each PR environment manually (not practical)

**Recommendation**: Use Option A for shared variables that should be available everywhere.

### Step 4: Verify Configuration

1. Go to: **Settings** → **Shared Variables**
2. Find `YOTO_SERVER_CLIENT_ID` in the list
3. Verify:
   - **Source**: production
   - **Shared with**: Shows "All environments" or your selected environments

### Step 5: Test in PR Environment

1. Open or update a PR to create/refresh a PR environment
2. Go to the PR environment in Railway dashboard
3. Click **Variables** tab
4. Look for `YOTO_SERVER_CLIENT_ID`
5. The value should display as: `${{shared.YOTO_SERVER_CLIENT_ID}}`
6. **Hover over it** to see the resolved value
7. If it shows the actual value (not empty), it's working!

### Step 6: Update Workflow (Optional)

Once shared variables are working, you can optionally remove the workaround from `.github/workflows/railway-pr-checks.yml`:

```yaml
# This section can be removed or commented out once shared variables work:
# - name: Configure PR Environment Variables
#   env:
#     RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
#     YOTO_SERVER_CLIENT_ID: ${{ secrets.YOTO_SERVER_CLIENT_ID }}
#   run: |
#     if [ -n "$YOTO_SERVER_CLIENT_ID" ]; then
#       railway variables set YOTO_SERVER_CLIENT_ID="$YOTO_SERVER_CLIENT_ID" -e "pr-${PR_NUMBER}"
#     fi
```

However, keeping it provides a safety net if shared variables fail.

## Why Shared Variables Might Return Empty String

### Common Causes:

1. **Variable Not Marked as Shared**
   - Variable exists in production but not configured as shared
   - Solution: Follow Step 2 above

2. **Sharing Scope Doesn't Include PR Environments**
   - Variable is shared, but only with specific environments
   - PR environments not included in the scope
   - Solution: Use "All environments" scope

3. **Typo in Variable Reference**
   - Incorrect syntax: `${{production.YOTO_SERVER_CLIENT_ID}}`
   - Correct syntax: `${{shared.YOTO_SERVER_CLIENT_ID}}`
   - Note: Variable name is case-sensitive

4. **Variable Propagation Delay**
   - Rarely, newly shared variables take a few seconds to propagate
   - Solution: Redeploy or wait 30-60 seconds

5. **Railway Platform Issue**
   - Shared variables feature may have limitations or bugs
   - Check Railway status: https://status.railway.app
   - Contact Railway support if persistent

## Diagnostic Tool

This repository includes a diagnostic script to help troubleshoot:

```bash
# Run the diagnostic tool
python scripts/diagnose_railway_shared_variables.py

# Requires:
# - Railway CLI installed (npm i -g @railway/cli)
# - RAILWAY_TOKEN environment variable set
```

The tool will:
- ✅ Check Railway CLI installation and authentication
- ✅ List all environments in your project
- ✅ Check YOTO_SERVER_CLIENT_ID in each environment
- ✅ Provide detailed troubleshooting steps
- ✅ Explain correct syntax and configuration

## Alternative Approaches

If Railway's shared variables continue to have issues:

### Approach 1: Direct Variable Setting (Current Workaround)

Continue using GitHub Actions to set variables directly:

**Pros:**
- Reliable and tested
- Uses GitHub Secrets (centralized)
- Automatic on PR updates

**Cons:**
- Requires GitHub Actions workflow
- Bypasses Railway's native feature
- More complex setup

### Approach 2: Railway Environment Variables API

Use Railway's API to programmatically set variables:

```bash
# Using Railway API (requires GraphQL knowledge)
curl -X POST https://backboard.railway.app/graphql \
  -H "Authorization: Bearer $RAILWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "mutation { ... }"}'
```

**Pros:**
- Programmatic control
- Can be automated

**Cons:**
- Complex GraphQL API
- Requires API token management
- More error-prone

### Approach 3: Use Railway CLI in Docker Build

Include variable setting in your Docker build or start command:

```dockerfile
# In Dockerfile or railway.toml
CMD railway variables get YOTO_SERVER_CLIENT_ID -e production | \
    xargs -I {} railway variables set YOTO_SERVER_CLIENT_ID={} && \
    uvicorn app:app
```

**Pros:**
- Self-contained
- No GitHub Actions needed

**Cons:**
- Increases startup time
- Requires Railway CLI in container
- More complex error handling

## Recommendations

1. **Short-term**: Keep the current GitHub Actions workaround
   - It's working and reliable
   - No rush to change what's working

2. **Medium-term**: Configure Railway shared variables properly
   - Follow the steps in "Proper Fix" section above
   - Keep both approaches running in parallel
   - Monitor to see if shared variables work

3. **Long-term**: Standardize on one approach
   - If shared variables work reliably, remove workflow workaround
   - If shared variables remain problematic, document the limitation
   - Consider raising issue with Railway support

## Additional Resources

- **Railway Shared Variables Docs**: https://docs.railway.app/guides/variables#shared-variables
- **Railway Dashboard**: https://railway.app
- **Railway Support**: https://help.railway.app
- **Railway Discord**: https://discord.gg/railway
- **This Project's Workflow**: `.github/workflows/railway-pr-checks.yml`

## Questions to Ask Railway Support

If the issue persists after proper configuration:

1. Do shared variables work with dynamically created PR environments?
2. Is there a way to set sharing scope to include future PR environments?
3. Are there known limitations with `${{shared.VARIABLE}}` syntax?
4. Can shared variables use wildcards (e.g., `pr-*`) in sharing scope?
5. Is there a CLI command to configure shared variables programmatically?

## Conclusion

The `${{shared.YOTO_SERVER_CLIENT_ID}}` empty string issue is most likely due to:
- Missing shared variable configuration in Railway UI, OR
- Sharing scope that doesn't include PR environments

**Action Required**:
1. Configure the variable as shared in Railway dashboard (production → Variables → ⋮ → Share variable)
2. Set sharing scope to "All environments"
3. Verify in a PR environment that the variable resolves to a value
4. Keep the GitHub Actions workaround as a safety net

If problems persist after configuration, the current GitHub Actions workaround is a reliable alternative that doesn't depend on Railway's shared variables feature.
