# GitHub Secrets Setup Guide for Railway Deployment

This guide explains exactly what secrets to configure and where, to enable automated Railway deployments.

## Simplified Workflow for Development

**Current Focus**: PR work deploys only to the `development` Railway environment. Staging and production workflows are not needed yet (there's no `develop` branch for staging).

## Required GitHub Secrets

You need to add these secrets to your GitHub repository:

### 1. RAILWAY_TOKEN_DEV (Required for development deployment)

**What it is**: An API token that allows GitHub Actions to deploy to Railway development environment on your behalf.

**How to get it**:
1. Go to https://railway.app/account/tokens
2. Click "Create Token"
3. Give it a name like "GitHub Actions Development"
4. Copy the token (you'll only see it once!)

**Where to add it**:
1. Go to your GitHub repository: https://github.com/earchibald/yoto-smart-stream
2. Click **Settings** (top navigation)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Name: `RAILWAY_TOKEN_DEV` (exact name required)
6. Value: Paste the token from Railway
7. Click **Add secret**

### 2. YOTO_CLIENT_ID (Optional but recommended)

**What it is**: Your Yoto API client ID for authentication with Yoto services.

**How to get it**:
1. Go to https://yoto.dev/get-started/start-here/
2. Register your application
3. Copy your Client ID

**Where to add it**:
1. Same location as above: Repository → Settings → Secrets and variables → Actions
2. Click **New repository secret**
3. Name: `YOTO_CLIENT_ID`
4. Value: Paste your Yoto Client ID
5. Click **Add secret**

## Visual Guide

### Step 1: Navigate to Repository Settings
```
GitHub Repository → Settings tab
```

### Step 2: Find Secrets Section
```
Left sidebar → Secrets and variables → Actions
```

### Step 3: Add Secrets
```
Click "New repository secret"
Enter name: RAILWAY_TOKEN_DEV
Paste value from Railway
Click "Add secret"

Repeat for YOTO_CLIENT_ID (optional)
```

## After Adding Secrets

Once `RAILWAY_TOKEN_DEV` is added, you can deploy using any of these methods:

### Method 1: Via GitHub Actions UI (Easiest)

1. Go to the **Actions** tab in your repository
2. Click on **"Railway Development (Shared Environment)"** workflow
3. Click **"Run workflow"** button (top right)
4. Fill in the form:
   - **Branch**: Select `copilot/build-server-and-setup-railway`
   - **session_id**: Enter `copilot-build-server`
   - **action**: Select `acquire-and-deploy`
5. Click **"Run workflow"**
6. Wait for deployment to complete (check the running workflow)

### Method 2: Via GitHub CLI

If you have GitHub CLI installed:

```bash
gh workflow run "Railway Development (Shared Environment)" \
  --ref copilot/build-server-and-setup-railway \
  --field session_id="copilot-build-server" \
  --field action="acquire-and-deploy"
```

### Method 3: Merge to Develop

Merging this PR to the `develop` branch will automatically trigger deployment to the staging environment.

## Verification

After adding secrets, verify they're configured:

1. Go to: Repository → Settings → Secrets and variables → Actions
2. You should see:
   - ✅ `RAILWAY_TOKEN_DEV` (required)
   - ✅ `YOTO_CLIENT_ID` (optional)

The values are hidden for security, but you should see the secret names listed.

## Troubleshooting

### "Secret not found" error in workflow

**Problem**: Workflow runs but can't find `RAILWAY_TOKEN_DEV`.

**Solution**: Make sure you named it exactly `RAILWAY_TOKEN_DEV` (all caps, with underscores).

### Token doesn't work

**Problem**: Deployment fails with authentication error.

**Solution**:
1. Generate a new token from Railway
2. Update the secret in GitHub (you can edit existing secrets)
3. Make sure the token has permissions for your Railway project

### Where are Codespace secrets different from repository secrets?

**Codespaces Secrets** (for development in Codespaces):
- Location: https://github.com/settings/codespaces (your personal settings)
- Used by: Your personal Codespaces
- Scope: User-level

**Repository Secrets** (for GitHub Actions):
- Location: Repository → Settings → Secrets and variables → Actions
- Used by: GitHub Actions workflows
- Scope: Repository-level

Both are needed for full functionality:
- **Repository secrets** → For automated deployments via GitHub Actions
- **Codespaces secrets** → For manual deployments from your Codespace

## Summary

**Quick checklist to enable development deployment:**

- [ ] Get Railway token from https://railway.app/account/tokens
- [ ] Add `RAILWAY_TOKEN_DEV` to repository secrets
- [ ] (Optional) Get Yoto Client ID from https://yoto.dev/
- [ ] (Optional) Add `YOTO_CLIENT_ID` to repository secrets
- [ ] Go to Actions tab and run "Railway Development (Shared Environment)" workflow
- [ ] Monitor deployment progress in Actions tab

**Important**: Use `RAILWAY_TOKEN_DEV` for development deployments. Future staging/production deployments would use `RAILWAY_TOKEN_STAGING` and `RAILWAY_TOKEN_PROD` respectively, but those are not needed yet.

**Still confused?** 
- Repository secrets location: https://github.com/earchibald/yoto-smart-stream/settings/secrets/actions
- You need **repository-level** secrets, not Codespace secrets, for GitHub Actions to work
- The secret must be named exactly: `RAILWAY_TOKEN_DEV`

---

Once secrets are configured, GitHub Actions will have access to deploy to Railway development environment automatically!
