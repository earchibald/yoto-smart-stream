# GitHub Secrets Setup Guide for Railway Deployment

This guide explains exactly what secrets to configure and where, to enable Railway CLI access for Cloud Agents and development workflows.

## Multi-Environment Deployment Model

**Current Architecture**: The project uses four Railway environments:
1. **Production** (`production` branch) - https://yoto-smart-stream-production.up.railway.app
2. **Staging** (`staging` branch) - https://yoto-smart-stream-staging.up.railway.app
3. **Develop** (`develop` branch) - https://yoto-smart-stream-develop.up.railway.app
4. **PR Environments** (feature branches) - https://yoto-smart-stream-yoto-smart-stream-pr-${PR_ID}.up.railway.app

**Workflow**:
- Feature branches (`copilot/TOPIC` or `copilot-worktree-TIMESTAMP`) branch from and merge to `develop`
- `develop` merges to `staging` for integration testing
- `staging` merges to `production` after successful testing
- PR environments automatically created for `copilot/TOPIC` branches
- Railway deployments use native GitHub integration (automatic on push)

## Railway Authentication Setup

This project uses **OAuth-based authentication** for Railway CLI access, rather than per-environment tokens. This provides a simpler, more secure authentication model.

### One-Time Setup: Create RAILWAY_API_TOKEN

**Step 1: Login to Railway on your local laptop (browserless mode)**

```bash
# Browserless login displays a link to copy/paste
railway login --browserless
# Click the displayed link and authenticate via GitHub OAuth in your browser
```

**Step 2: Extract user token and set as GitHub Secret**

```bash
# Extract token from Railway config and set as GitHub Secret for copilot environment
gh secret set --env copilot RAILWAY_API_TOKEN --body="$(jq -r '.user.token' ~/.railway/config.json)"
```

This creates a `RAILWAY_API_TOKEN` in your GitHub repository's `copilot` environment that Cloud Agents can use for Railway CLI operations.

### How It Works

- **Local development**: Use `railway login` directly (stores credentials locally)
- **Cloud Agents**: Automatically use `RAILWAY_API_TOKEN` from the `copilot` environment
- **All environments**: Single token provides access to all Railway environments (production, staging, develop, PR environments)
- **Railway CLI**: Automatically detects and uses `RAILWAY_API_TOKEN` when available

### Benefits

✅ **Simplified Management**: One token for all environments instead of per-environment tokens  
✅ **OAuth Security**: Uses GitHub OAuth flow, more secure than manually created tokens  
✅ **Automatic Detection**: Railway CLI automatically detects and uses the token  
✅ **Full Permissions**: User-level permissions apply across all projects and environments

**For detailed Railway authentication information**, see the [railway-service-management skill](/.github/skills/railway-service-management/SKILL.md), specifically the [Cloud Agent Authentication section](/.github/skills/railway-service-management/reference/cli_scripts.md#cloud-agent-authentication-railway_api_token-mode).

## YOTO_CLIENT_ID Configuration

**Important**: `YOTO_CLIENT_ID` is **NOT** stored as a GitHub Secret. Instead, it is:
1. Set directly in the Railway production environment as a **Shared Variable**
2. PR Environments automatically reference it using Railway's template syntax: `${{shared.YOTO_CLIENT_ID}}`

### How to Set YOTO_CLIENT_ID in Railway:

1. Go to https://railway.app/dashboard
2. Select your project
3. Go to the **production** environment
4. Navigate to **Variables** tab
5. Add a new variable:
   - **Name**: `YOTO_CLIENT_ID`
   - **Value**: Your Yoto Client ID from https://yoto.dev/
   - **Type**: Select "Shared Variable" (this allows PR environments to reference it)
6. Save the variable

PR Environments will automatically inherit this value through the `${{shared.YOTO_CLIENT_ID}}` reference that is set by the GitHub Actions workflow.

## GitHub Environment: copilot

To support Cloud Agent (GitHub Copilot Workspace) operations, you need to configure a GitHub Environment named `copilot` with the Railway API token and other credentials.

### What is the copilot Environment?

The `copilot` environment provides secrets and variables for Cloud Agents running in GitHub Actions. These agents get access to:
- Railway authentication via `RAILWAY_API_TOKEN` (see above)
- Yoto API credentials
- Other service credentials needed for development

### Creating the copilot Environment

1. Go to your GitHub repository: https://github.com/earchibald/yoto-smart-stream
2. Click **Settings** (top navigation)
3. In the left sidebar, click **Environments**
4. Click **New environment**
5. Name: `copilot` (exact name required)
6. Click **Configure environment**

### Required Secrets for copilot Environment

Add these secrets to the `copilot` environment:

#### 1. RAILWAY_API_TOKEN (Required)

**What it is**: OAuth token extracted from your local Railway login that provides full access to all Railway environments.

**How to add it**: Follow the [Railway Authentication Setup](#railway-authentication-setup) section above. This is the primary authentication method for Railway CLI operations.

#### 2. YOTO_CLIENT_ID

**What it is**: Your Yoto API client ID for authentication

**How to get it**:
1. Go to https://yoto.dev/
2. Sign in with your Yoto account
3. Create or view your app
4. Copy the Client ID

**How to add it**:
1. In the `copilot` environment configuration page
2. Click **Add secret** under "Environment secrets"
3. Name: `YOTO_CLIENT_ID`
4. Value: Paste your Client ID
5. Click **Add secret**

### Optional Secrets

Add these if needed for your development workflow:

- `AWS_ACCESS_KEY_ID` - For AWS deployments
- `AWS_SECRET_ACCESS_KEY` - For AWS deployments
- `AWS_REGION` - AWS region (e.g., us-east-1)
- Other service credentials as needed

### Environment Protection Rules (Optional)

You can optionally configure protection rules for the `copilot` environment:

1. **Required reviewers**: Not needed for copilot (automated agent access)
2. **Wait timer**: Not needed for copilot (no deployment delays)
3. **Deployment branches**: All branches (copilot agents work on any PR)

Leave these unconfigured unless you have specific security requirements.

### Verification

After configuring the `copilot` environment:

1. Go to: Repository → Settings → Environments
2. You should see:
   - ✅ `copilot` environment listed
   - ✅ Secrets configured (names visible, values hidden)
3. Test by triggering a Copilot workflow (if available)

### Verification

After configuring the `copilot` environment:

1. Go to: Repository → Settings → Environments
2. You should see:
   - ✅ `copilot` environment listed
   - ✅ `RAILWAY_API_TOKEN` configured (name visible, value hidden)
   - ✅ `YOTO_CLIENT_ID` configured (name visible, value hidden)

## Automatic Railway Deployments

Railway deployments are handled automatically via Railway's native GitHub integration:

- **Push to `develop`** → Automatic deploy to develop environment
- **Push to `staging`** → Automatic deploy to staging environment  
- **Push to `production`** → Automatic deploy to production environment
- **Open PR to `develop`** → Railway automatically creates PR environment
- **Close/merge PR** → Railway automatically destroys PR environment

No GitHub Actions workflows are required for deployments. Railway monitors the repository and deploys automatically when branches are updated.

## Verification

After completing the setup:

1. Go to: Repository → Settings → Environments
2. You should see:
   - ✅ `copilot` environment with `RAILWAY_API_TOKEN` and `YOTO_CLIENT_ID`

3. Test Railway CLI access (in a Cloud Agent session):
```bash
railway login  # Should authenticate using RAILWAY_API_TOKEN
railway status  # Should show Railway project information
```

## Troubleshooting

### "RAILWAY_API_TOKEN not found" error

**Problem**: Cloud Agent can't find the Railway token.

**Solution**: Verify `RAILWAY_API_TOKEN` is added to the `copilot` environment (not repository secrets).

### Token doesn't work

**Problem**: Railway CLI fails with authentication error.

**Solution**:
1. Re-run the setup on your local laptop: `railway login --browserless`
2. Re-extract and update the secret: `gh secret set --env copilot RAILWAY_API_TOKEN --body="$(jq -r '.user.token' ~/.railway/config.json)"`

### YOTO_CLIENT_ID not working in PR environments

**Problem**: PR environments can't access Yoto API.

**Solution**:
1. Verify `YOTO_CLIENT_ID` is set as a **Shared Variable** in Railway production environment
2. Check that PR environment has `YOTO_CLIENT_ID` set to `${{shared.YOTO_CLIENT_ID}}`
3. Ensure the production environment is named exactly "production" in Railway

## Summary

**Quick checklist for Railway authentication setup:**

- [ ] Login to Railway on local laptop: `railway login --browserless`
- [ ] Extract and set `RAILWAY_API_TOKEN` in copilot environment
- [ ] Set `YOTO_CLIENT_ID` as Shared Variable in Railway production environment
- [ ] Create `copilot` GitHub environment
- [ ] Add `YOTO_CLIENT_ID` to copilot environment
- [ ] Verify Railway CLI works in Cloud Agent sessions

**Important Notes:**
- Deployments are automatic via Railway's native GitHub integration
- Single `RAILWAY_API_TOKEN` provides access to all environments
- OAuth-based authentication is more secure than per-environment tokens
- Cloud Agents use the `copilot` environment for credentials
- Railway CLI automatically detects and uses `RAILWAY_API_TOKEN`

**For detailed Railway CLI operations**, see the [railway-service-management skill](/.github/skills/railway-service-management/SKILL.md).

---

Once configured, Cloud Agents have full Railway CLI access, and all deployments happen automatically when code is pushed to the respective branches!
