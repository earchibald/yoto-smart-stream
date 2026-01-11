# Railway Deployment Quick Reference

Quick reference for deploying Yoto Smart Stream to Railway.

## Prerequisites

```bash
# Install Railway CLI (done automatically in devcontainer)
npm i -g @railway/cli

# Authenticate
railway login

# Link to project
railway link
```

## Deployment Commands

### Manual Deployment (from devcontainer)

```bash
# Dry run (preview what will happen)
./scripts/deploy.sh staging --dry-run

# Deploy to staging
./scripts/deploy.sh staging

# Deploy to development
./scripts/deploy.sh development

# Production is BLOCKED
./scripts/deploy.sh production  # ❌ Will fail with error
```

### Automated Deployment (via GitHub Actions)

```bash
# Push to develop branch → auto-deploys to staging
git checkout develop
git push origin develop

# Monitor deployment
# Go to: https://github.com/earchibald/yoto-smart-stream/actions
```

## Monitoring

```bash
# View logs
railway logs -e staging -f

# Check status
railway status -e staging

# Open dashboard
railway open -e staging
```

## Environment Variables

Set via Railway CLI or Dashboard:

```bash
# Required
railway variables set YOTO_SERVER_CLIENT_ID="your_id" -e staging

# Optional
railway variables set DEBUG=true -e staging
railway variables set LOG_LEVEL=DEBUG -e staging
railway variables set PUBLIC_URL="https://your-app.up.railway.app" -e staging
```

## Testing

```bash
# Verify deployment setup
python scripts/test_deployment_setup.py

# Check health endpoint
curl https://your-app.up.railway.app/health
```

## Troubleshooting

### Railway CLI not found
```bash
npm i -g @railway/cli
```

### Not authenticated
```bash
railway login
```

### Deployment fails
```bash
# Check logs
railway logs -e staging

# Verify tests pass
pytest tests/ -v
```

## Environment Status

| Environment | Branch | Status | Auto-Deploy |
|-------------|--------|--------|-------------|
| Production | `main` | ⏸️ Disabled | ❌ No |
| Staging | `develop` | ✅ Active | ✅ Yes |
| Development | manual | ✅ Active | ❌ No |

## Key Files

- `railway.toml` - Railway configuration
- `scripts/deploy.sh` - Deployment script
- `.github/workflows/railway-deploy.yml` - CI/CD workflow
- `docs/RAILWAY_DEPLOYMENT.md` - Full documentation

## Support

- **Full Guide**: [docs/RAILWAY_DEPLOYMENT.md](../docs/RAILWAY_DEPLOYMENT.md)
- **Railway Docs**: https://docs.railway.app/
- **Issues**: https://github.com/earchibald/yoto-smart-stream/issues
