# Railway Token Setup - Separate Tokens per Environment

## Overview

This project uses **separate Railway tokens** for each environment to improve security and access control:

- `RAILWAY_TOKEN_PROD` - Production environment (restricted access)
- `RAILWAY_TOKEN_STAGING` - Staging environment (QA/testing)
- `RAILWAY_TOKEN_DEV` - Development environment (active development)

## Why Separate Tokens?

✅ **Security Isolation**
- Production compromises don't affect dev/staging
- Limit blast radius of token leaks

✅ **Access Control**
- Different team members can have different environment access
- Junior developers can have dev access only

✅ **Auditing**
- Track which environment each deployment came from
- Better compliance and security logging

✅ **Token Rotation**
- Rotate tokens per environment without global disruption
- Revoke access to one environment independently

## Token Setup

### 1. Create Railway Tokens

Go to https://railway.app/account/tokens and create three tokens:

**Production Token:**
```
Name: Production Deployments
Description: For automated production deployments from main branch
Access: Production project/environment only
```

**Staging Token:**
```
Name: Staging Deployments  
Description: For automated staging deployments from develop branch
Access: Staging project/environment only
```

**Development Token:**
```
Name: Development Deployments
Description: For shared development environment with coordination
Access: Development project/environment only
```

### 2. Add to GitHub Secrets

**Repository Secrets** (for GitHub Actions):

1. Go to: `https://github.com/earchibald/yoto-smart-stream/settings/secrets/actions`
2. Click **"New repository secret"**
3. Add each token:

```
Name: RAILWAY_TOKEN_PROD
Value: [paste production token]

Name: RAILWAY_TOKEN_STAGING  
Value: [paste staging token]

Name: RAILWAY_TOKEN_DEV
Value: [paste development token]
```

**Codespaces Secrets** (for developers):

1. Go to: `https://github.com/settings/codespaces`
2. Click **"New secret"**
3. Add development token (for local/Copilot work):

```
Name: RAILWAY_TOKEN
Value: [paste development token - same as RAILWAY_TOKEN_DEV]
Repository access: earchibald/yoto-smart-stream
```

Note: For Codespaces, use just `RAILWAY_TOKEN` (without suffix) for convenience.

## Token Usage by Workflow

### Production Deployments

**Workflow:** `.github/workflows/railway-deploy.yml` (deploy-production job)
**Token:** `RAILWAY_TOKEN_PROD`
**Trigger:** Manual only (disabled by default)
**Environment:** production

```yaml
env:
  RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_PROD }}
```

### Staging Deployments

**Workflow:** `.github/workflows/railway-deploy.yml` (deploy-staging job)
**Token:** `RAILWAY_TOKEN_STAGING`
**Trigger:** Automatic on push to `develop` branch
**Environment:** staging

```yaml
env:
  RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_STAGING }}
```

### Development Deployments

**Workflow:** `.github/workflows/railway-development-shared.yml`
**Token:** `RAILWAY_TOKEN_DEV`
**Trigger:** Manual with coordination
**Environment:** development

```yaml
env:
  RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN_DEV }}
```

### Codespace/Local Development

**Context:** GitHub Codespaces, local devcontainer
**Token:** `RAILWAY_TOKEN` (user-level Codespaces secret)
**Usage:** Manual deployments, CLI operations
**Environment:** development (typically)

```bash
# Automatically available in Codespace
echo $RAILWAY_TOKEN

# Use with Railway CLI
railway status -e development
```

## Token Permissions

### Recommended Permissions per Token

**Production Token (`RAILWAY_TOKEN_PROD`):**
- ✅ Deploy to production environment
- ✅ View production logs and status
- ✅ Set production environment variables
- ❌ No access to staging/development

**Staging Token (`RAILWAY_TOKEN_STAGING`):**
- ✅ Deploy to staging environment
- ✅ View staging logs and status
- ✅ Set staging environment variables
- ❌ No access to production/development

**Development Token (`RAILWAY_TOKEN_DEV`):**
- ✅ Deploy to development environment
- ✅ View development logs and status
- ✅ Set development environment variables
- ❌ No access to production/staging

## Token Rotation

When to rotate tokens:
- Regular schedule (quarterly recommended)
- After team member departure
- Suspected compromise
- After security incident

### How to Rotate

**1. Create new token:**
```bash
# Go to https://railway.app/account/tokens
# Create new token with same permissions
# Copy the new token
```

**2. Update GitHub Secret:**
```bash
# Go to repository settings → Secrets
# Edit the secret (e.g., RAILWAY_TOKEN_PROD)
# Paste new token
# Save
```

**3. Update Codespaces (if needed):**
```bash
# Go to https://github.com/settings/codespaces
# Edit RAILWAY_TOKEN secret
# Paste new development token
# Restart any active Codespaces
```

**4. Revoke old token:**
```bash
# Go to https://railway.app/account/tokens
# Find old token
# Click "Revoke"
```

**5. Test:**
```bash
# Trigger a deployment to verify new token works
# Check workflow logs for authentication success
```

## Troubleshooting

### Authentication Failed

**Error:** `401 Unauthorized` or `Invalid token`

**Solution:**
1. Check which workflow is failing
2. Verify correct secret name is used (`_PROD`, `_STAGING`, or `_DEV`)
3. Ensure token is not expired or revoked
4. Regenerate token if needed

### Wrong Environment Deployed

**Error:** Deployment went to wrong environment

**Solution:**
1. Check workflow file uses correct token for environment
2. Verify `-e` flag matches token permissions
3. Ensure token has access to target environment

### Codespace Token Not Working

**Error:** `railway whoami` fails in Codespace

**Solution:**
1. Verify `RAILWAY_TOKEN` is set in Codespaces secrets
2. Check repository access is granted for the secret
3. Restart Codespace to load new secrets
4. Test with: `echo $RAILWAY_TOKEN` (should show partial token)

### Token Leaked

**Immediate Actions:**
1. Go to https://railway.app/account/tokens
2. Revoke the compromised token immediately
3. Generate new token
4. Update GitHub secrets
5. Check Railway audit logs for unauthorized activity
6. Consider rotating all tokens if unsure which was leaked

## Security Best Practices

✅ **DO:**
- Use separate tokens per environment
- Rotate tokens regularly (quarterly)
- Revoke tokens when no longer needed
- Use descriptive token names
- Monitor Railway audit logs
- Keep tokens in secrets managers only (GitHub Secrets, Codespaces)

❌ **DON'T:**
- Share tokens between environments
- Commit tokens to git
- Share tokens in chat/email
- Use same token for all environments
- Give production access to all developers
- Store tokens in plain text files

## Validation Checklist

After setup, verify:

- [ ] Three tokens created in Railway
- [ ] `RAILWAY_TOKEN_PROD` added to GitHub repository secrets
- [ ] `RAILWAY_TOKEN_STAGING` added to GitHub repository secrets
- [ ] `RAILWAY_TOKEN_DEV` added to GitHub repository secrets
- [ ] `RAILWAY_TOKEN` added to Codespaces secrets (dev token)
- [ ] Each token has access only to its respective environment
- [ ] Test deployment to staging succeeds
- [ ] Test deployment to development succeeds (manual)
- [ ] Production deployment is disabled by default
- [ ] Codespace can authenticate with development environment

## Migration from Single Token

If you previously used a single `RAILWAY_TOKEN`:

**Steps:**

1. **Create new environment-specific tokens** (see "Create Railway Tokens" above)

2. **Update GitHub repository secrets:**
   - Rename `RAILWAY_TOKEN` → `RAILWAY_TOKEN_STAGING` (for backward compatibility)
   - Add `RAILWAY_TOKEN_PROD`
   - Add `RAILWAY_TOKEN_DEV`

3. **Update Codespaces:**
   - Keep `RAILWAY_TOKEN` in Codespaces (no suffix)
   - Use development token as value

4. **Test deployments:**
   - Push to `develop` → staging should deploy with `RAILWAY_TOKEN_STAGING`
   - Manual dev deployment → should use `RAILWAY_TOKEN_DEV`

5. **Revoke old single token** (if it had broad access)

## Support

- **Railway Tokens:** https://railway.app/account/tokens
- **GitHub Secrets:** https://docs.github.com/en/actions/security-guides/encrypted-secrets
- **Codespaces Secrets:** https://docs.github.com/en/codespaces/managing-your-codespaces/managing-secrets-for-your-codespaces

---

**Last Updated:** 2026-01-10  
**Security Level:** High  
**Compliance:** Follows least-privilege principle
