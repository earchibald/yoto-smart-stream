# Cloud Agent Railway Token Provisioning

## Overview

This guide explains how to enable Railway access for Cloud Agents (GitHub Copilot Workspace running in GitHub Actions) when working on Pull Requests. Due to Railway API limitations, environment tokens for PR environments cannot be automatically provisioned, so a manual step is required.

## The Problem

Railway does not provide an API to automatically create environment-specific tokens. For Cloud Agents working on PRs to have full Railway access (deploy, logs, variables, etc.), we need Railway environment tokens that have been manually created and configured.

## The Solution

We use a hybrid approach:
1. **Cloud Agent**: Leverages GitHub environment secrets/variables for most services (inherited from `copilot` environment)
2. **User (Local)**: Provisions Railway environment token for the specific PR environment when Railway access is needed
3. **Cloud Agent**: Detects the provisioned token and gains full Railway access

## Workflow

### Step 1: Cloud Agent Starts Work on PR

When a Cloud Agent starts work on a PR, it automatically has access to:
- ✅ GitHub repository
- ✅ Most secrets from `copilot` GitHub environment (YOTO_CLIENT_ID, etc.)
- ⚠️ Limited Railway access (read-only via Railway MCP with general token)

At this stage, the agent **cannot**:
- ❌ Deploy to the PR's Railway environment
- ❌ Set environment variables in the PR environment
- ❌ View PR environment-specific logs

### Step 2: User Provisions Railway PR Environment Token (Manual)

When full Railway access is needed, **you** need to provision a token:

**Option A: Using Railway UI**

1. Pull the PR branch locally:
   ```bash
   # Get the PR number from GitHub
   gh pr list

   # Checkout the PR branch
   gh pr checkout <PR_NUMBER>
   ```

2. Create Railway environment token:
   ```bash
   # Go to Railway dashboard
   open https://railway.app/account/tokens

   # Click "Create Token"
   # Name: pr-<PR_NUMBER>-token  (e.g., "pr-123-token")
   # Scope: Select the yoto-smart-stream project
   # Environment: Select the pr-<PR_NUMBER> environment
   # Click "Create"
   # Copy the token (you only see it once!)
   ```

3. Set the token in the PR's Railway environment:
   ```bash
   # Install Railway CLI if needed
   npm install -g @railway/cli

   # Authenticate
   railway login

   # Link to project (if not already linked)
   railway link

   # Set the token as environment variables in the PR environment
   railway variables set RAILWAY_TOKEN="<TOKEN_YOU_JUST_CREATED>" -e pr-<PR_NUMBER>
   railway variables set RAILWAY_API_TOKEN="<TOKEN_YOU_JUST_CREATED>" -e pr-<PR_NUMBER>
   ```

**Option B: Using Railway MCP Server (Recommended)**

If you have the Railway MCP server available in your local VS Code:

1. Pull the PR branch locally:
   ```bash
   gh pr checkout <PR_NUMBER>
   ```

2. Use natural language to provision the token:
   ```
   Create a new Railway environment token named "pr-<PR_NUMBER>-token"
   with access to the pr-<PR_NUMBER> environment. Then set RAILWAY_TOKEN
   and RAILWAY_API_TOKEN variables in the pr-<PR_NUMBER> environment
   to the newly created token.
   ```

The Railway MCP server will:
- Guide you through creating the token via Railway dashboard (as tokens can only be created via UI)
- Help you set the environment variables once you provide the token

### Step 3: Cloud Agent Gains Full Railway Access

Once the token is provisioned:

1. The Cloud Agent's Railway MCP server will detect the token in the PR environment
2. The agent can now:
   - ✅ Deploy to the PR environment
   - ✅ Manage environment variables
   - ✅ View environment-specific logs
   - ✅ Run railway commands scoped to the PR environment

The agent will automatically use the PR-specific token when working in that PR's context.

## Token Naming Convention

**IMPORTANT**: Tokens must follow this naming pattern:
```
pr-{PR_NUMBER}-token
```

Examples:
- PR #123 → `pr-123-token`
- PR #456 → `pr-456-token`

This naming convention:
- Makes tokens easy to identify
- Allows automated cleanup
- Clearly associates tokens with specific PRs

## Token Lifecycle

### Creation
- Created manually by user when Railway access is needed
- Scoped to specific PR environment
- Set as RAILWAY_TOKEN and RAILWAY_API_TOKEN in the PR environment

### Usage
- Cloud Agent automatically detects and uses the token
- Token is used for all Railway operations in that PR environment
- Token is isolated to the specific PR (cannot access other environments)

### Cleanup
When the PR is closed or merged:

**Automatic Cleanup:**
- Railway PR environment is automatically destroyed (taking the environment variables with it)
- No action needed for environment variables

**Manual Cleanup (Recommended):**
1. Go to https://railway.app/account/tokens
2. Find the token named `pr-<PR_NUMBER>-token`
3. Click "Revoke"
4. Confirm revocation

This prevents orphaned tokens from accumulating.

## Security Considerations

### Token Scope
- ✅ **DO**: Create tokens scoped to a single PR environment
- ✅ **DO**: Use descriptive names (pr-123-token)
- ✅ **DO**: Revoke tokens when PR is closed
- ❌ **DON'T**: Use production tokens for PR environments
- ❌ **DON'T**: Share tokens across multiple PRs

### Token Storage
- ✅ **DO**: Store tokens in Railway environment variables (RAILWAY_TOKEN, RAILWAY_API_TOKEN)
- ✅ **DO**: Keep tokens secret (never commit to git)
- ❌ **DON'T**: Store tokens in GitHub Secrets (they're PR-specific and short-lived)
- ❌ **DON'T**: Share tokens in plain text (chat, email, etc.)

### Access Control
Railway tokens for PR environments should have:
- **Project Access**: yoto-smart-stream project only
- **Environment Access**: Specific pr-<NUMBER> environment only
- **No Production Access**: Cannot touch production or staging
- **Limited Lifetime**: Revoke when PR is closed

## Troubleshooting

### Cloud Agent Cannot Deploy

**Symptoms:**
- Agent reports "Unauthorized" when trying to deploy
- Agent cannot access Railway logs or variables
- Agent cannot perform Railway operations

**Solution:**
Check if Railway token is provisioned:

```bash
# Check if RAILWAY_TOKEN is set in PR environment
railway variables -e pr-<PR_NUMBER> | grep RAILWAY_TOKEN

# If not present, provision the token (see Step 2 above)
```

### Railway Token Not Working

**Symptoms:**
- Token is set but agent still gets "Unauthorized"
- Operations fail with authentication errors

**Possible Causes:**
1. Token expired or revoked
2. Token not scoped to correct environment
3. Token not set correctly in environment variables

**Solution:**
```bash
# Verify token is set correctly
railway variables -e pr-<PR_NUMBER> | grep RAILWAY

# Should show:
# RAILWAY_TOKEN=<your-token>
# RAILWAY_API_TOKEN=<your-token>

# If missing or incorrect, re-provision the token
railway variables set RAILWAY_TOKEN="<new-token>" -e pr-<PR_NUMBER>
railway variables set RAILWAY_API_TOKEN="<new-token>" -e pr-<PR_NUMBER>
```

### Token Scoped to Wrong Environment

**Symptoms:**
- Token works for other environments but not PR environment
- "Forbidden" errors when accessing PR environment

**Solution:**
Create a new token with correct scope:
1. Go to https://railway.app/account/tokens
2. Revoke the incorrect token
3. Create new token scoped to pr-<PR_NUMBER> environment
4. Update environment variables with new token

## GitHub Environment Configuration

The `copilot` GitHub environment provides base secrets and variables for Cloud Agents:

### Environment Secrets (Inherited)
- `YOTO_CLIENT_ID` - Yoto API client ID
- `RAILWAY_API_TOKEN` - Base Railway token (read-only, for general queries)
- Other service credentials as needed

### Environment Variables (Inherited)
- Configuration values shared across all PR Cloud Agent sessions

### Not Included (PR-Specific)
- ❌ `RAILWAY_TOKEN` - Must be provisioned per PR
- ❌ `RAILWAY_API_TOKEN` - Must be provisioned per PR (different from base token)

## Integration with Cloud Agent Workflow

### Typical Development Flow

1. **Start**: Cloud Agent begins work on PR
   ```
   Agent: "I'll start working on issue #123"
   Agent: "⚠️  Note: Railway deployment access not configured for this PR"
   Agent: "To enable Railway operations, provision a token (see docs/CLOUD_AGENT_RAILWAY_TOKENS.md)"
   ```

2. **User Provisions Token** (if needed):
   ```bash
   gh pr checkout 123
   # Follow "Step 2: User Provisions Railway PR Environment Token" above
   ```

3. **Continue**: Agent detects token and gains full access
   ```
   Agent: "✅ Railway token detected for pr-123"
   Agent: "Deploying changes to Railway PR environment..."
   Agent: "✅ Deployment successful"
   ```

4. **Complete**: PR is merged/closed
   ```bash
   # Revoke the token manually
   # Railway auto-destroys PR environment (including environment variables)
   ```

### Detection Logic

The Cloud Agent detects Railway access by:
1. Checking if `RAILWAY_TOKEN` exists in PR environment variables
2. Testing Railway authentication for the PR environment
3. If found, using PR-specific token
4. If not found, falling back to read-only general token

## Best Practices

### For Users

1. **Provision tokens only when needed**
   - Most work doesn't require Railway deployment
   - Save time by only provisioning when deploying/testing

2. **Name tokens consistently**
   - Always use `pr-<NUMBER>-token` format
   - Makes management easier

3. **Revoke tokens promptly**
   - Clean up when PR is closed
   - Prevents token accumulation

4. **Use environment-scoped tokens**
   - Never use production tokens for PR work
   - Keep permissions minimal

### For Cloud Agents

1. **Detect token availability**
   - Check before attempting Railway operations
   - Provide clear error messages if token missing

2. **Use PR-specific tokens**
   - Prefer `RAILWAY_TOKEN` from PR environment over general token
   - Fall back gracefully if not available

3. **Report status clearly**
   - Inform user about token requirements
   - Provide links to provisioning docs

## Alternative: Future Automation

In the future, if Railway provides an API for token management, we could automate this:

**Potential Automated Workflow:**
1. GitHub Actions workflow triggers on PR open
2. Workflow calls Railway API to create environment-specific token
3. Workflow stores token in Railway PR environment variables
4. Token is automatically revoked when PR is closed

**Current Limitation:**
Railway's current API does not support programmatic token creation, so manual provisioning is required.

## Summary

**Quick Reference:**

1. **Cloud Agent starts on PR** → Has limited Railway access
2. **You provision Railway token** → Manual step when needed
   - Create token: `pr-<PR_NUMBER>-token`
   - Set in Railway: `RAILWAY_TOKEN` and `RAILWAY_API_TOKEN`
3. **Cloud Agent gains full access** → Can deploy and manage Railway
4. **PR closes** → Revoke token manually, Railway auto-cleans environment

**Key Point:** This manual step is **only needed when the Cloud Agent needs to deploy or manage Railway**. For many PRs, Railway access isn't needed at all.

---

**Last Updated:** 2026-01-18
**Status:** Active
**Automation Status:** Manual provisioning required (Railway API limitation)
