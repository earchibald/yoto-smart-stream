# Quick Reference: Ephemeral Railway Environments

## For Developers

### Setup (One-time)

**1. Get Railway Token:**
```bash
# Go to: https://railway.app/account/tokens
# Create new token → Copy it
```

**2. Add to GitHub Codespaces:**
```bash
# Go to: https://github.com/settings/codespaces
# New secret:
#   Name: RAILWAY_TOKEN
#   Value: [paste token]
#   Repo: earchibald/yoto-smart-stream
```

**3. Restart Codespace** (if already running)

### Common Commands

**Deploy to ephemeral environment:**
```bash
./scripts/railway_ephemeral_env.sh deploy copilot-test-123
```

**Check status:**
```bash
./scripts/railway_ephemeral_env.sh status copilot-test-123
```

**View logs:**
```bash
railway logs -e copilot-test-123 --tail 50
```

**Destroy when done:**
```bash
./scripts/railway_ephemeral_env.sh destroy copilot-test-123
```

## For PR Authors

### Automatic Flow

1. **Open PR** → Environment auto-created
2. **Check PR comments** → Find deployment URL
3. **Wait 1-2 minutes** → Deployment completes
4. **Test changes** → Use provided URL
5. **Close/Merge PR** → Environment auto-destroyed

### Manual Testing

**Test health endpoint:**
```bash
curl https://yoto-smart-stream-pr-123.up.railway.app/health
```

**View deployment:**
```bash
railway open -e pr-123
```

## For Copilot Sessions

### Automatic Deployment

When you push to a `copilot/*` branch:
- Environment automatically deploys
- Named: `copilot-{branch-name}`
- Destroyed when branch deleted

### Manual Workflow Trigger

**Via GitHub Actions UI:**
1. Go to **Actions** tab
2. Select **"Railway Copilot Session Environments"**
3. Click **"Run workflow"**
4. Choose action and session ID

## Environment Naming

| Type | Pattern | Example |
|------|---------|---------|
| PR | `pr-{number}` | `pr-123` |
| Copilot | `copilot-{normalized-branch}` | `copilot-add-auth` |

## URLs

**PR Environment:**
```
https://yoto-smart-stream-pr-{number}.up.railway.app
```

**Health Check:**
```
https://yoto-smart-stream-pr-{number}.up.railway.app/health
```

## Troubleshooting

**Token not working?**
```bash
# Check if set
echo $RAILWAY_TOKEN

# Test auth
railway whoami

# Re-login if needed
railway login
```

**Deployment failed?**
- Check GitHub Actions logs
- Check Railway dashboard
- Run: `railway logs -e {env-name}`

**Environment not destroyed?**
```bash
# Manual cleanup
./scripts/railway_ephemeral_env.sh destroy {env-name}
```

## Cost Info

- PR environments: ~$0.01-0.05/hour
- Auto-destroyed when PR closes
- Zero cost when not active

## Documentation

- **Full Guide:** [EPHEMERAL_RAILWAY_ENVIRONMENTS.md](./EPHEMERAL_RAILWAY_ENVIRONMENTS.md)
- **Setup Guide:** [CODESPACES_RAILWAY_SETUP.md](./CODESPACES_RAILWAY_SETUP.md)
- **Railway Docs:** https://docs.railway.app/

## Quick Help

**Script help:**
```bash
./scripts/railway_ephemeral_env.sh help
```

**Railway CLI help:**
```bash
railway --help
railway logs --help
railway status --help
```

---

**Need more help?** See full documentation or ask in GitHub Discussions.
