---
name: railway-service-management
description: Specialized knowledge for managing multi-environment Railway deployments. Use when: (1) Setting up Railway projects/environments/services, (2) Configuring deployments and builds (NIXPACKS/Railpack/Dockerfile), (3) Managing Railway CLI operations and logs, (4) Implementing PR environments or branch-based workflows, (5) Troubleshooting deployment failures or health checks, (6) Managing secrets/variables across environments, (7) Optimizing Railway costs and resources, (8) Configuring databases/volumes/networking, (9) Setting up CI/CD with GitHub Actions, (10) Cloud Agent sessions needing Railway CLI access with RAILWAY_API_TOKEN-based authentication.
---

# Railway Service Management

Complete guide for managing Railway.app deployments across multiple environments with automated workflows.

## Quick Start for Cloud Agents

**If you're a Cloud Agent (GitHub Copilot Workspace), use the setup script:**

```bash
# Run the automated setup script
bash .github/skills/railway-service-management/scripts/setup_cloud_agent.sh

# Then use Railway CLI commands
railway status --json
railway logs --lines 50 --filter "@level:error" --json
railway var list --json
railway deployment list --json
```

The script automatically:
- Verifies RAILWAY_API_TOKEN is configured
- Logs in to Railway using `railway login`
- Identifies the correct environment (PR or production)
- Links to project: yoto, service: yoto-smart-stream
- Configures Railway CLI for immediate use

**For detailed instructions**: See [Cloud Agent Authentication](reference/cli_scripts.md#cloud-agent-authentication-railway_api_token-mode)

## Quick Start

### Common CLI Commands

```bash
# Check deployment status
railway status --json

# View filtered logs (prefer filtering for efficiency)
railway logs --filter "@level:error"
railway logs --filter "\"uvicorn\" OR \"startup\""

# Link workspace to environment
railway link --project <project_id>
railway environment --environment develop
```

**For complete CLI reference**: See [cli_scripts.md](reference/cli_scripts.md)

## Essential Workflows

### 1. Deployment Configuration

**Railpack** (preferred build system):
```json
{
  "$schema": "https://schema.railpack.com",
  "provider": "python",
  "packages": {"python": "3.11"},
  "deploy": {"startCommand": "uvicorn app:main --host 0.0.0.0 --port $PORT"}
}
```

**Key principle**: Prefer auto-detection over custom steps. Only configure what needs to differ from defaults.

**For detailed build configuration**: See [configuration_management.md](reference/configuration_management.md)

### 2. Multi-Environment Setup

Typical structure:
- **Production** (main branch) - Customer-facing
- **Staging** (develop branch) - Pre-production testing
- **PR Environments** - Automatic ephemeral environments per PR

**For complete multi-environment architecture**: See [multi_environment_architecture.md](reference/multi_environment_architecture.md)

### 3. Troubleshooting Deployments

Common issues:
- Health check failures → Check `railway logs --filter "@level:error"`
- Package not found → Verify build succeeded, check layering (see configuration_management.md)
- Environment deleted → Re-link with `railway link` and `railway environment`

**For deployment workflows and CI/CD**: See [deployment_workflows.md](reference/deployment_workflows.md)

## Reference Documentation

Load these files as needed for detailed guidance:

- **[cli_scripts.md](reference/cli_scripts.md)** - Complete Railway CLI reference, Cloud Agent authentication, automation scripts
- **[configuration_management.md](reference/configuration_management.md)** - Railpack, NIXPACKS, Dockerfile builds, railway.toml
- **[deployment_workflows.md](reference/deployment_workflows.md)** - GitHub Actions, CI/CD, PR workflows, rollback strategies
- **[multi_environment_architecture.md](reference/multi_environment_architecture.md)** - Environment setup, branch mapping, isolation patterns
- **[secrets_management.md](reference/secrets_management.md)** - Environment variables, GitHub Secrets integration
- **[monitoring_logging.md](reference/monitoring_logging.md)** - Log aggregation, metrics, alerting, debugging
- **[database_services.md](reference/database_services.md)** - PostgreSQL, MySQL, Redis setup and management
- **[pr_environments.md](reference/pr_environments.md)** - Railway's native PR environment feature
- **[cost_optimization.md](reference/cost_optimization.md)** - Resource optimization, billing, usage monitoring
- **[platform_fundamentals.md](reference/platform_fundamentals.md)** - Core Railway concepts, architecture, terminology

## Critical Guidelines

1. **Always filter logs** when using Railway CLI for efficiency
2. **Prefer auto-detection** for build configuration (Railpack)
3. **Verify environment link** before CLI operations: `railway status --json`
4. **Check health checks** are properly configured for all services
