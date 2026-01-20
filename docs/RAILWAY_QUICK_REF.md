# Railway Quick Reference

Quick reference for Railway operations with Yoto Smart Stream.

## Railway CLI Setup

### Authentication

```bash
# Local development - use OAuth login
railway login --browserless

# Cloud Agents - RAILWAY_API_TOKEN is automatically configured
railway login  # Authenticates using RAILWAY_API_TOKEN from copilot environment
```

**For complete authentication setup**, see:
- [GITHUB_SECRETS_SETUP.md](../GITHUB_SECRETS_SETUP.md#railway-authentication-setup)
- [RAILWAY_TOKEN_SETUP.md](RAILWAY_TOKEN_SETUP.md)
- [railway-service-management skill - Cloud Agent Authentication](../.github/skills/railway-service-management/reference/cli_scripts.md#cloud-agent-authentication-railway_api_token-mode)

### Link to Project

```bash
# Link to project and environment
railway link --project yoto --service yoto-smart-stream --environment <env-name>

# Or link separately
railway service link yoto-smart-stream
railway environment link <env-name>

# Verify
railway status --json
```

## Deployments

**Railway deployments are automatic via native GitHub integration.**

| Branch | Environment | URL | Auto-Deploy |
|--------|-------------|-----|-------------|
| `production` | production | https://yoto-smart-stream-production.up.railway.app | ✅ Yes |
| `staging` | staging | https://yoto-smart-stream-staging.up.railway.app | ✅ Yes |
| `develop` | develop | https://yoto-smart-stream-develop.up.railway.app | ✅ Yes |
| `copilot/TOPIC` | pr-{number} | https://yoto-smart-stream-yoto-smart-stream-pr-{number}.up.railway.app | ✅ Yes |

**Workflow:**
1. Push code to branch → Railway automatically deploys
2. Open PR to `develop` → Railway creates PR environment
3. Close/merge PR → Railway destroys PR environment

**For detailed deployment workflows**, see the [railway-service-management skill - Deployment Workflows](../.github/skills/railway-service-management/reference/deployment_workflows.md).

## Monitoring & Operations

### View Logs

```bash
# Follow logs (with filters for efficiency)
railway logs -e production --filter "@level:error"
railway logs -e staging --filter "uvicorn OR startup"

# Recent logs
railway logs -e develop --lines 50
```

### Check Status

```bash
# Service status
railway status -e production --json

# Deployment list
railway deployment list -e staging --json

# Monitor deployment loop
sleep 5 && while true; do STATUS=$(railway deployment list --json | jq -r '.[0].status'); echo "[$(date '+%H:%M:%S')] Status: $STATUS"; if [ "$STATUS" = "SUCCESS" ]; then echo "✅ Succeeded!"; break; elif [ "$STATUS" = "FAILURE" ]; then echo "❌ Failed!"; exit 1; fi; sleep 5; done
```

### Open Dashboard

```bash
railway open -e production
```

**For complete CLI command reference**, see the [railway-service-management skill - Essential Commands](../.github/skills/railway-service-management/reference/cli_scripts.md#essential-commands).

## Environment Variables

Set via Railway CLI or Dashboard:

```bash
# Set variable
railway variables set YOTO_CLIENT_ID="your_id" -e production

# Set multiple
railway variables set DEBUG=true LOG_LEVEL=debug -e develop

# List all variables
railway variables list -e staging

# Shared variables (production)
railway variables set YOTO_CLIENT_ID="your_id" -e production --shared
```

**For complete variable management**, see the [railway-service-management skill - Configuration Management](../.github/skills/railway-service-management/reference/configuration_management.md).

## Health Checks

```bash
# Check production
curl https://yoto-smart-stream-production.up.railway.app/health

# Check staging
curl https://yoto-smart-stream-staging.up.railway.app/health

# Check develop
curl https://yoto-smart-stream-develop.up.railway.app/health

# Check PR environment
curl https://yoto-smart-stream-yoto-smart-stream-pr-123.up.railway.app/health
```

## Troubleshooting

### Railway CLI not authenticated

```bash
# Local development
railway login --browserless

# Cloud Agents (should auto-authenticate)
railway login  # Uses RAILWAY_API_TOKEN
```

### Environment not linked

```bash
railway link --project yoto --service yoto-smart-stream --environment <env-name>
railway status --json  # Verify
```

### Deployment issues

```bash
# Check logs for errors
railway logs -e <env> --filter "@level:error"

# Check deployment status
railway deployment list -e <env> --json
```

**For comprehensive troubleshooting**, see the [railway-service-management skill - Troubleshooting](../.github/skills/railway-service-management/reference/deployment_workflows.md#troubleshooting-deployments).

## Key Resources

### Documentation
- [railway-service-management skill](../.github/skills/railway-service-management/SKILL.md) - Complete Railway operations guide
- [Multi-Environment Architecture](../.github/skills/railway-service-management/reference/multi_environment_architecture.md)
- [Deployment Workflows](../.github/skills/railway-service-management/reference/deployment_workflows.md)
- [CLI Scripts Reference](../.github/skills/railway-service-management/reference/cli_scripts.md)
- [Configuration Management](../.github/skills/railway-service-management/reference/configuration_management.md)

### Setup Guides
- [GITHUB_SECRETS_SETUP.md](../GITHUB_SECRETS_SETUP.md) - GitHub secrets configuration
- [RAILWAY_TOKEN_SETUP.md](RAILWAY_TOKEN_SETUP.md) - OAuth authentication setup

### Railway Resources
- [Railway Dashboard](https://railway.app/dashboard)
- [Railway Docs](https://docs.railway.app/)
- [Railway CLI Reference](https://docs.railway.app/reference/cli)

---

**For detailed Railway operations, always refer to the [railway-service-management skill](../.github/skills/railway-service-management/SKILL.md).**
- `docs/RAILWAY_DEPLOYMENT.md` - Full documentation

## Support

- **Full Guide**: [docs/RAILWAY_DEPLOYMENT.md](../docs/RAILWAY_DEPLOYMENT.md)
- **Railway Docs**: https://docs.railway.app/
- **Issues**: https://github.com/earchibald/yoto-smart-stream/issues
