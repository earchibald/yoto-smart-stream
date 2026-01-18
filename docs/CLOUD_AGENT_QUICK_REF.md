# Cloud Agent Quick Reference

Quick reference guide for enabling Cloud Agent (GitHub Copilot Workspace) Railway access.

## TL;DR - I need Railway access for a PR

```bash
# 1. Checkout the PR branch
gh pr checkout <PR_NUMBER>

# 2. Provision Railway token
./scripts/provision_pr_railway_token.sh --pr <PR_NUMBER>

# 3. Done! Cloud Agent can now deploy and manage Railway
```

## What is a Cloud Agent?

A Cloud Agent is GitHub Copilot Workspace running in GitHub Actions. It helps you:
- Develop features automatically
- Run tests and deployments
- Make code changes in PRs
- Perform end-to-end development workflows

## When do I need to provision Railway tokens?

**You only need to provision Railway tokens if:**
- Cloud Agent needs to deploy code to Railway
- Cloud Agent needs to view Railway logs
- Cloud Agent needs to manage Railway environment variables
- Cloud Agent is working on a PR that requires Railway integration testing

**You DON'T need tokens if:**
- Cloud Agent is only making code changes
- Cloud Agent is running tests locally
- Cloud Agent is not interacting with Railway

## Quick Commands

### Provision Railway Token for PR
```bash
# Auto-detect PR from current branch
./scripts/provision_pr_railway_token.sh

# Specify PR number
./scripts/provision_pr_railway_token.sh --pr 123
```

### Check if Token is Provisioned
```bash
# Auto-detect PR
./scripts/check_pr_railway_token.sh

# Specify PR number
./scripts/check_pr_railway_token.sh 123
```

### View Environment Variables
```bash
# See all variables in PR environment
railway variables -e pr-123

# Check if tokens are set
railway variables -e pr-123 | grep RAILWAY
```

### Revoke Token (After PR is Closed)
```bash
# Go to Railway dashboard
open https://railway.app/account/tokens

# Find token: pr-123-token
# Click "Revoke"
```

## Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Cloud Agent Starts Work on PR                           │
│    • Has access to most services via copilot environment   │
│    • Limited Railway access (read-only)                    │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Agent Needs Railway Access (Deploy/Logs/Variables)      │
│    • Agent detects no PR-specific Railway token            │
│    • Agent prompts: "Provision Railway token for PR #123"  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. You Provision Token (Local Machine)                     │
│    • Pull PR branch                                         │
│    • Run: ./scripts/provision_pr_railway_token.sh          │
│    • Create token via Railway UI                           │
│    • Script sets token in PR environment                   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Cloud Agent Gains Full Railway Access                   │
│    • Agent detects provisioned token                        │
│    • Agent can deploy, view logs, manage variables         │
│    • Agent continues work with full Railway capabilities   │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. PR is Closed/Merged                                      │
│    • Railway automatically destroys PR environment          │
│    • You manually revoke token (cleanup)                    │
└─────────────────────────────────────────────────────────────┘
```

## Token Naming Convention

**Format:** `pr-{NUMBER}-token`

Examples:
- PR #123 → `pr-123-token`
- PR #456 → `pr-456-token`

This makes tokens easy to:
- Identify which PR they belong to
- Find when cleaning up
- Manage in Railway dashboard

## Common Scenarios

### Scenario 1: Cloud Agent Can't Deploy

**Symptoms:**
```
Agent: "❌ Failed to deploy: Unauthorized"
Agent: "Need Railway token for pr-123"
```

**Solution:**
```bash
# 1. Checkout PR
gh pr checkout 123

# 2. Provision token
./scripts/provision_pr_railway_token.sh --pr 123

# 3. Agent automatically detects and continues
```

### Scenario 2: Checking Token Status

**Want to know if token is provisioned:**
```bash
./scripts/check_pr_railway_token.sh 123
```

**Output:**
```
✅ RAILWAY_TOKEN is set
✅ RAILWAY_API_TOKEN is set
✅ All required Railway tokens are configured
```

### Scenario 3: Token Already Exists

**If you run provision script again:**
- Script will overwrite with new token
- Old token still exists in Railway (should be revoked)
- Only the new token will work

**Best practice:**
- Revoke old token before creating new one
- Use one token per PR

### Scenario 4: Multiple PRs

**Each PR needs its own token:**
```bash
# PR #123
./scripts/provision_pr_railway_token.sh --pr 123

# PR #456
./scripts/provision_pr_railway_token.sh --pr 456

# PR #789
./scripts/provision_pr_railway_token.sh --pr 789
```

**Tokens are isolated:**
- pr-123-token → Only works for pr-123 environment
- pr-456-token → Only works for pr-456 environment
- pr-789-token → Only works for pr-789 environment

## Security Best Practices

### ✅ DO:
- Create tokens scoped to single PR environment
- Use descriptive names (pr-123-token)
- Revoke tokens when PR is closed
- Keep tokens in Railway environment variables only
- Use the provisioning script (it's secure)

### ❌ DON'T:
- Share tokens across multiple PRs
- Use production tokens for PR environments
- Commit tokens to git
- Share tokens in plain text (chat, email)
- Leave orphaned tokens after PR closes

## Troubleshooting

### Railway CLI Not Found
```bash
# Install Railway CLI
npm install -g @railway/cli

# Verify installation
railway --version
```

### Not Authenticated to Railway
```bash
# Login to Railway
railway login

# Verify authentication
railway whoami
```

### PR Environment Doesn't Exist
- Wait a few minutes (Railway may still be creating it)
- Check Railway dashboard: https://railway.app/dashboard
- Verify PR Environments is enabled in Railway settings
- Ensure PR targets main or develop branch

### Token Not Working
```bash
# Verify token is set
railway variables -e pr-123 | grep RAILWAY

# If missing, provision again
./scripts/provision_pr_railway_token.sh --pr 123
```

### Can't Create Token in Railway UI
- Token creation is manual (Railway API limitation)
- Use Railway UI: https://railway.app/account/tokens
- Follow on-screen instructions
- Copy token immediately (you only see it once)

## Full Documentation

- **Complete Guide**: [docs/CLOUD_AGENT_RAILWAY_TOKENS.md](../docs/CLOUD_AGENT_RAILWAY_TOKENS.md)
- **GitHub Secrets Setup**: [GITHUB_SECRETS_SETUP.md](../GITHUB_SECRETS_SETUP.md)
- **Railway Token Setup**: [docs/RAILWAY_TOKEN_SETUP.md](../docs/RAILWAY_TOKEN_SETUP.md)

## Support

### Links
- Railway Dashboard: https://railway.app/dashboard
- Railway Tokens: https://railway.app/account/tokens
- GitHub Settings: https://github.com/earchibald/yoto-smart-stream/settings

### Getting Help
- Check script output for specific error messages
- Review documentation links above
- Check Railway status: https://status.railway.app/

---

**Remember:** Provision tokens only when Cloud Agent needs Railway access. Many PRs don't need Railway interaction at all!
