# GitHub Secrets Setup Guide for Railway Deployment

This guide explains exactly what secrets to configure and where, to enable automated Railway deployments.

## Simplified Deployment Model

**Current Architecture**: The project uses ONLY two types of Railway environments:
1. **Production** - Deployed from `main` branch
2. **PR Environments** - Automatically created by Railway for each pull request

There are **NO** staging or development environments.

## Required GitHub Secrets

You need to add these secrets to your GitHub repository:

### 1. RAILWAY_TOKEN_PROD (Required for production deployment)

**What it is**: An API token that allows GitHub Actions to deploy to Railway production environment on your behalf.

**How to get it**:
1. Go to https://railway.app/account/tokens
2. Click "Create Token"
3. Give it a name like "GitHub Actions Production"
4. Copy the token (you'll only see it once!)

**Where to add it**:
1. Go to your GitHub repository: https://github.com/earchibald/yoto-smart-stream
2. Click **Settings** (top navigation)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Name: `RAILWAY_TOKEN_PROD` (exact name required)
6. Value: Paste the token from Railway
7. Click **Add secret**

## YOTO_SERVER_CLIENT_ID Configuration

**Important**: `YOTO_SERVER_CLIENT_ID` is **NOT** stored as a GitHub Secret. Instead, it is:
1. Set directly in the Railway production environment as a **Shared Variable**
2. PR Environments automatically reference it using Railway's template syntax: `${{shared.YOTO_SERVER_CLIENT_ID}}`

### How to Set YOTO_SERVER_CLIENT_ID in Railway:

1. Go to https://railway.app/dashboard
2. Select your project
3. Go to the **production** environment
4. Navigate to **Variables** tab
5. Add a new variable:
   - **Name**: `YOTO_SERVER_CLIENT_ID`
   - **Value**: Your Yoto Client ID from https://yoto.dev/
   - **Type**: Select "Shared Variable" (this allows PR environments to reference it)
6. Save the variable

PR Environments will automatically inherit this value through the `${{shared.YOTO_SERVER_CLIENT_ID}}` reference that is set by the GitHub Actions workflow.

## Visual Guide

### Step 1: Navigate to Repository Settings
```
GitHub Repository → Settings tab
```

### Step 2: Find Secrets Section
```
Left sidebar → Secrets and variables → Actions
```

### Step 3: Add Secret
```
Click "New repository secret"
Enter name: RAILWAY_TOKEN_PROD
Paste value from Railway
Click "Add secret"
```

## After Adding Secrets

Once `RAILWAY_TOKEN_PROD` is added, production deployments will happen automatically when code is pushed to the `main` branch.

**⚠️ Important**: Since production deployments are automatic on push to `main`, ensure:
- All PRs are thoroughly tested in PR environments before merging
- Code reviews are completed and approved
- You have a rollback plan if issues occur (can redeploy previous commit)
- Critical changes are tested with extra care

### Production Deployment (Automatic)

Deployments to production happen automatically when you merge to `main`:

1. Merge your PR to `main` branch (after thorough testing and review)
2. GitHub Actions automatically runs the deployment workflow
3. The production environment at https://yoto-smart-stream-production.up.railway.app is updated

### PR Environments (Automatic)

Railway automatically creates ephemeral environments for every pull request:

1. Open a PR targeting `main`
2. Railway automatically creates a `pr-{number}` environment
3. The PR environment inherits `YOTO_SERVER_CLIENT_ID` from production via shared variables
4. GitHub Actions validates the deployment
5. When you close/merge the PR, Railway automatically destroys the environment

## Verification

After adding secrets, verify they're configured:

1. Go to: Repository → Settings → Secrets and variables → Actions
2. You should see:
   - ✅ `RAILWAY_TOKEN_PROD` (required for production deployments)

The values are hidden for security, but you should see the secret names listed.

## Troubleshooting

### "Secret not found" error in workflow

**Problem**: Workflow runs but can't find `RAILWAY_TOKEN_PROD`.

**Solution**: Make sure you named it exactly `RAILWAY_TOKEN_PROD` (all caps, with underscores).

### Token doesn't work

**Problem**: Deployment fails with authentication error.

**Solution**:
1. Generate a new token from Railway
2. Update the secret in GitHub (you can edit existing secrets)
3. Make sure the token has permissions for your Railway project

### YOTO_SERVER_CLIENT_ID not working in PR environments

**Problem**: PR environments can't access Yoto API.

**Solution**:
1. Verify `YOTO_SERVER_CLIENT_ID` is set as a **Shared Variable** in Railway production environment
2. Check that PR environment has `YOTO_SERVER_CLIENT_ID` set to `${{shared.YOTO_SERVER_CLIENT_ID}}`
3. Ensure the production environment is named exactly "production" in Railway

### Where are Codespace secrets different from repository secrets?

**Codespaces Secrets** (for development in Codespaces):
- Location: https://github.com/settings/codespaces (your personal settings)
- Used by: Your personal Codespaces
- Scope: User-level

**Repository Secrets** (for GitHub Actions):
- Location: Repository → Settings → Secrets and variables → Actions
- Used by: GitHub Actions workflows
- Scope: Repository-level

For this project, you only need **repository secrets** for automated deployments via GitHub Actions.

## Summary

**Quick checklist to enable production deployment:**

- [ ] Get Railway token from https://railway.app/account/tokens
- [ ] Add `RAILWAY_TOKEN_PROD` to repository secrets
- [ ] Set `YOTO_SERVER_CLIENT_ID` as a Shared Variable in Railway production environment
- [ ] Merge to `main` branch to trigger automatic production deployment
- [ ] Open a PR to test PR Environment creation

**Important Notes:**
- Production deployments are automatic on push to `main` branch
- PR Environments are automatically created by Railway for each pull request
- `YOTO_SERVER_CLIENT_ID` is stored in Railway (as a Shared Variable), not in GitHub Secrets
- There are no staging or development environments

**Still confused?** 
- Repository secrets location: https://github.com/earchibald/yoto-smart-stream/settings/secrets/actions
- You need **repository-level** secrets for GitHub Actions to work
- The secret must be named exactly: `RAILWAY_TOKEN_PROD`
- Railway production environment must have `YOTO_SERVER_CLIENT_ID` set as a Shared Variable

---

Once secrets are configured, GitHub Actions will automatically deploy to Railway production when you push to `main`, and Railway will automatically create PR environments for pull requests!
