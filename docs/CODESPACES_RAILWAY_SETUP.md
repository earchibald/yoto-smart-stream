# Railway Token Setup for GitHub Codespaces & Copilot

This guide explains how to configure Railway token access for GitHub Codespaces and GitHub Copilot sessions.

## Why This Matters

GitHub Copilot PR sessions run in GitHub Codespaces. For these sessions to deploy ephemeral Railway environments, they need access to your Railway API token. This guide shows you how to securely provide that access.

## Quick Setup (5 minutes)

### Step 1: Get Your Railway Token

For development environment access, you'll need a Railway token:

1. Go to https://railway.app/account/tokens
2. Click **"Create Token"**
3. Give it a name: `GitHub Codespaces - Development`
4. Copy the token (you'll only see it once!)

**Note:** This should be a **development environment token** with access only to the development Railway project. For security, use separate tokens for each environment (dev/staging/prod).

### Step 2: Add Token to GitHub Codespaces Secrets

**Via GitHub Web UI:**

1. Go to https://github.com/settings/codespaces
2. Scroll to **"Codespaces secrets"**
3. Click **"New secret"**
4. Fill in:
   - **Name:** `RAILWAY_TOKEN`
   - **Value:** Paste your Railway token
   - **Repository access:** Select this repository (`earchibald/yoto-smart-stream`)
5. Click **"Add secret"**

**Via GitHub CLI:**

```bash
gh secret set RAILWAY_TOKEN --user --body "your_railway_token_here" --repos earchibald/yoto-smart-stream
```

### Step 3: Verify Setup

**Start or Restart Codespace:**

If you already have a Codespace running, you need to restart it for the secret to be available:

1. Go to https://github.com/codespaces
2. Find your Codespace for this repo
3. Click **"..." → "Stop codespace"**
4. Wait a few seconds
5. Click **"..." → "Open in browser"** (or your preferred editor)

**Test the Token:**

In your Codespace terminal:

```bash
# Check if token is available
echo $RAILWAY_TOKEN  # Should show your token (or part of it)

# Verify Railway authentication
railway whoami

# Expected output: Your Railway username/email
```

## For Yoto API Credentials (Optional)

If you want your Copilot environments to test with real Yoto API:

### Step 1: Get Yoto Client ID

1. Go to https://yoto.dev/
2. Register/login to your developer account
3. Create or select your application
4. Copy your Client ID

### Step 2: Add to Codespaces Secrets

Same process as Railway token:

1. Go to https://github.com/settings/codespaces
2. Click **"New secret"**
3. Fill in:
   - **Name:** `YOTO_CLIENT_ID`
   - **Value:** Paste your Yoto Client ID
   - **Repository access:** Select this repository
4. Click **"Add secret"**

## Using the Setup

Once configured, you can:

### Deploy Ephemeral Environments from Codespaces

```bash
# Deploy to a custom environment
./scripts/railway_ephemeral_env.sh deploy copilot-my-test

# Check status
./scripts/railway_ephemeral_env.sh status copilot-my-test

# Destroy when done
./scripts/railway_ephemeral_env.sh destroy copilot-my-test
```

### Automatic Deployments

When GitHub Copilot creates a PR:
- GitHub Actions automatically uses the RAILWAY_TOKEN from repository secrets
- Ephemeral environment is created and deployed
- You can test immediately
- Environment is destroyed when PR closes

## Security Best Practices

### ✅ DO:

- Use **Codespaces secrets** (user-level) for RAILWAY_TOKEN
- Rotate Railway tokens periodically
- Use separate Railway tokens for different purposes
- Limit repository access for secrets
- Keep tokens confidential

### ❌ DON'T:

- Commit tokens to git
- Share tokens in PR comments or issues
- Use production tokens for development
- Store tokens in code or documentation
- Use repository secrets for personal tokens

## Troubleshooting

### Token Not Available in Codespace

**Symptom:** `echo $RAILWAY_TOKEN` returns empty

**Solutions:**

1. **Verify secret is set:**
   - Go to https://github.com/settings/codespaces
   - Check `RAILWAY_TOKEN` is listed
   - Verify repository access is granted

2. **Restart Codespace:**
   - Stop and start your Codespace
   - Secrets only load when Codespace starts

3. **Check secret name:**
   - Must be exactly `RAILWAY_TOKEN` (case-sensitive)
   - No spaces or special characters

4. **Verify repository access:**
   - Secret must have access to `earchibald/yoto-smart-stream`

### Railway CLI Not Authenticated

**Symptom:** `railway whoami` fails

**Solutions:**

1. **Check token is set:**
   ```bash
   echo $RAILWAY_TOKEN
   ```

2. **Verify token is valid:**
   - Go to https://railway.app/account/tokens
   - Check token is not expired or deleted
   - Regenerate if needed

3. **Test with new token:**
   - Create fresh token
   - Update Codespaces secret
   - Restart Codespace

### Deployment Fails

**Symptom:** Deployment script fails with authentication error

**Solutions:**

1. **Check Railway project access:**
   ```bash
   railway list
   ```
   
2. **Link to project:**
   ```bash
   railway link
   ```

3. **Verify environment exists:**
   - Check Railway dashboard
   - Environment may need to be created first

## Alternative: Local Authentication

If you prefer not to use Codespaces secrets, you can authenticate locally:

```bash
# Interactive login (opens browser)
railway login

# This stores credentials in Codespace
# Valid for the duration of the Codespace session
```

**Limitations:**
- Only works for current session
- Must re-authenticate if Codespace rebuilds
- Not suitable for automated workflows

## Secret Hierarchy

Understanding where secrets are used:

```
1. GitHub Repository Secrets
   ├── Used by: GitHub Actions workflows
   ├── Examples: RAILWAY_TOKEN, YOTO_CLIENT_ID
   └── Managed at: Repo Settings → Secrets and variables → Actions

2. GitHub Codespaces Secrets (User-level)
   ├── Used by: Your personal Codespaces
   ├── Examples: RAILWAY_TOKEN, YOTO_CLIENT_ID
   └── Managed at: https://github.com/settings/codespaces

3. Railway Environment Variables
   ├── Used by: Deployed applications
   ├── Examples: DATABASE_URL, YOTO_CLIENT_ID
   └── Managed at: Railway Dashboard or via CLI
```

## Workflow Examples

### Example 1: Copilot Session with Deployment

```bash
# In your Codespace (RAILWAY_TOKEN set via secret)

# 1. Copilot creates a feature branch
git checkout -b copilot/add-new-feature

# 2. Make changes with Copilot assistance
# ... code changes ...

# 3. Deploy to test
./scripts/railway_ephemeral_env.sh deploy copilot-add-new-feature

# 4. Test the deployment
./scripts/railway_ephemeral_env.sh status copilot-add-new-feature

# 5. View logs
railway logs -e copilot-add-new-feature

# 6. When satisfied, commit and push
git add .
git commit -m "Add new feature with Copilot"
git push origin copilot/add-new-feature

# 7. Open PR (optional)
gh pr create --title "Add new feature" --body "Copilot-assisted feature"

# 8. Cleanup (if not using PR workflow)
./scripts/railway_ephemeral_env.sh destroy copilot-add-new-feature
```

### Example 2: Testing PR Environment

```bash
# In your Codespace

# 1. Someone opens a PR
# → GitHub Actions automatically deploys to pr-{number}

# 2. Test the PR environment
curl https://yoto-smart-stream-pr-123.up.railway.app/health

# 3. Check logs
railway logs -e pr-123

# 4. Get detailed status
./scripts/railway_ephemeral_env.sh status pr-123
```

## Additional Resources

- **Railway Documentation:** https://docs.railway.app/
- **Railway CLI Reference:** https://docs.railway.app/reference/cli
- **GitHub Codespaces Docs:** https://docs.github.com/en/codespaces
- **GitHub Secrets Guide:** https://docs.github.com/en/codespaces/managing-your-codespaces/managing-secrets-for-your-codespaces

## Support

If you encounter issues:

1. **Check logs:** GitHub Actions logs or Railway logs
2. **Verify secrets:** Ensure they're set correctly
3. **Test authentication:** Run `railway whoami`
4. **Review documentation:** [EPHEMERAL_RAILWAY_ENVIRONMENTS.md](./EPHEMERAL_RAILWAY_ENVIRONMENTS.md)

---

**Last Updated:** 2026-01-10  
**Version:** 1.0.0
