# GitHub Copilot Workspace Instructions

## Project Overview

This is the Yoto Smart Stream project - a service to stream audio to Yoto devices, monitor events via MQTT, and manage interactive audio experiences. The project includes Python/FastAPI backend, web UI components, and Railway deployment infrastructure.

## Guardrails
- **NEVER** write outside of the workspace. use tmp/ in the workspace for temporary files.

## Code Style and Conventions

- **Language**: Python 3.9+
- **Framework**: FastAPI with async/await patterns
- **Testing**: pytest with fixtures, mocks, and comprehensive coverage (target >70%)
- **Linting**: ruff for code quality, black for formatting
- **Type hints**: Use Python typing throughout the codebase

## Design Principles
### Modal Dialogs
- Modal dialogs should close with the Escape key.

## Locally-Maintained Skills

This workspace contains locally-maintained custom skills in `.github/skills/`. These skills are **specialized agents with domain expertise** that should be used whenever relevant work is being done.

### Available Skills

1. **railway-service-management** - Multi-environment Railway deployment management
   - **Use for**: Railway deployments, environment management, CLI operations, configuration
   - **Key tools**: `get_deployment_endpoint.py` script for retrieving deployment URLs
   - **Reference**: `.github/skills/railway-service-management/SKILL.md`

2. **yoto-smart-stream** (formerly yoto-api-development) - Yoto Play API integration, audio streaming, and MQTT handling
   - **Use for**: Yoto API integration, MQTT events, audio streaming, service operations
   - **Reference**: `.github/skills/yoto-smart-stream/SKILL.md`

3. **yoto-smart-stream-testing** - Comprehensive testing for Yoto Smart Stream
   - **Use for**: Writing tests, debugging test failures, authentication testing, Playwright UI automation
   - **Reference**: `.github/skills/yoto-smart-stream-testing/SKILL.md`

### When to Use Skills

**ALWAYS delegate to the appropriate skill when working on:**

- 🚂 **Railway tasks**: Deployments, environment setup, getting endpoint URLs, configuration
  → Use `railway-service-management` skill

- 🎵 **Yoto API tasks**: API integration, MQTT handling, audio streaming, device management
  → Use `yoto-smart-stream` skill

- 🧪 **Testing tasks**: Writing tests, fixing test failures, authentication flows, UI testing
  → Use `yoto-smart-stream-testing` skill

**Examples:**
- Deploying to Railway environment → Invoke `railway-service-management` skill
- Getting a Railway deployment URL → Use `.github/skills/railway-service-management/scripts/get_deployment_endpoint.py`
- Implementing Yoto API endpoint → Invoke `yoto-smart-stream` skill
- Writing integration tests → Invoke `yoto-smart-stream-testing` skill
- Fixing OAuth login flow → Invoke `yoto-smart-stream-testing` skill

### Skill Maintenance Directive

**IMPORTANT**: When you discover, verify, or implement new information related to these skills during development or issue resolution, you MUST update the relevant skill documentation to keep it current and accurate.

**When to Update Skills:**

- When you verify new API endpoints, parameters, or behaviors
- When you discover Railway deployment patterns or configuration options
- When you implement new Yoto API features or MQTT event handling
- When you find corrections to existing documentation
- When you establish new best practices or patterns
- When you resolve issues that reveal gaps in the skill documentation

**How to Update Skills:**

1. **Identify the relevant skill** - Determine which skill (`railway-service-management` or `yoto-smart-stream`) the new information relates to
2. **Locate the appropriate file** - Skills have a main `SKILL.md` and reference docs in `reference/` subdirectories
3. **Update the documentation** - Add or correct information in the relevant file(s)
4. **Be specific** - Include examples, code snippets, or command syntax where applicable
5. **Maintain consistency** - Follow the existing structure and formatting of the skill files
6. **Update related sections** - If the change affects multiple areas, update all relevant sections

**Skill File Structure:**

```
.github/skills/
├── railway-service-management/
│   ├── SKILL.md                    # Main overview and quick start
│   └── reference/                  # Detailed reference docs
│       ├── platform_fundamentals.md
│       ├── deployment_workflows.md
│       ├── configuration_management.md
│       └── ...
├── yoto-smart-stream/
│   ├── SKILL.md                    # Main overview and quick start
│   └── reference/                  # Detailed reference docs
│       ├── yoto_api_reference.md
│       ├── yoto_mqtt_reference.md
│       ├── architecture.md
│       ├── service_operations.md
│       └── ...
└── yoto-smart-stream-testing/
    ├── SKILL.md                    # Main overview and quick start
    └── reference/                  # Detailed reference docs
        ├── testing_guide.md
        └── login_workflows.md
```

**Examples of Updates to Make:**

- ✅ You discover a new Yoto API endpoint → Update `yoto-smart-stream/reference/yoto_api_reference.md`
- ✅ You find a better Railway deployment pattern → Update `railway-service-management/reference/deployment_workflows.md`
- ✅ You implement MQTT reconnection logic → Update `yoto-smart-stream/reference/yoto_mqtt_reference.md` with the pattern
- ✅ You correct an error in documented API behavior → Fix it in the relevant reference file
- ✅ You add a new Railway CLI command pattern → Add it to `railway-service-management/reference/cli_scripts.md`
- ✅ You implement service operation improvements → Update `yoto-smart-stream/reference/service_operations.md`
- ✅ You add new testing patterns → Update `yoto-smart-stream-testing/reference/testing_guide.md`

## Development Workflow

### Branch and Environment Strategy

- **`develop` branch**: Primary development branch
  - All feature work branches from `develop`
  - Integration tested at: https://yoto-smart-stream-develop.up.railway.app
  
- **Feature branches**: Two patterns based on agent type:
  - **Cloud Agents / @copilot issues**: Create `copilot/TOPIC` branches from `develop`
    - Open PR to `develop`
    - Automatic PR environment: https://yoto-smart-stream-yoto-smart-stream-pr-${PR_ID}.up.railway.app
    - Normal PR review and merge lifecycle
  - **VS Code Background Agents**: Create `copilot-worktree-TIMESTAMP` worktree branches from `develop`
    - For work that doesn't require deployment to test
    - Merge directly back to `develop` when complete
    - No automatic Railway environment

- **`staging` branch**: Pre-production testing
  - `develop` merges into `staging` for integration testing
  - Integration tested at: https://yoto-smart-stream-staging.up.railway.app
  
- **`production` branch**: Production deployment
  - `staging` merges into `production` after successful integration testing
  - Live at: https://yoto-smart-stream-production.up.railway.app

### Development Best Practices

1. **Testing First**: Write tests before implementing features (TDD approach)
2. **Use Skills First**: ALWAYS check if a custom skill is available for your task before doing it yourself
   - Railway work? → Use `railway-service-management` skill
   - Yoto API work? → Use `yoto-smart-stream` skill
   - Testing work? → Use `yoto-smart-stream-testing` skill
3. **Update Documentation**: Keep skills and docs synchronized with verified implementation
4. **Code Quality**: Run linting and tests before committing
5. **Security**: Never commit secrets; use environment variables and GitHub Secrets

## Custom Skill Usage Examples

### Railway Deployment Management

```bash
# Get deployment endpoint URL
python .github/skills/railway-service-management/scripts/get_deployment_endpoint.py \
  --environment production --url-only

# Health check all environments
bash .github/skills/railway-service-management/scripts/check_railway_deployments.sh
```

**For complex Railway tasks**, invoke the skill:
```
Use the railway-service-management skill to deploy to staging environment
```

### Yoto API Integration

**For Yoto API work**, invoke the skill:
```
Use the yoto-smart-stream skill to implement MQTT reconnection logic
Use the yoto-smart-stream skill to add support for new Yoto API endpoint
```

### Testing

**For testing tasks**, invoke the skill:
```
Use the yoto-smart-stream-testing skill to write integration tests for the new endpoint
Use the yoto-smart-stream-testing skill to fix the failing authentication test
```

## Deployment

- **Platform**: Railway.app with multi-environment setup
- **Environments**: 
  - **Production** (`production` branch): https://yoto-smart-stream-production.up.railway.app
  - **Staging** (`staging` branch): https://yoto-smart-stream-staging.up.railway.app
  - **Develop** (`develop` branch): https://yoto-smart-stream-develop.up.railway.app
  - **PR Environments** (feature branches): https://yoto-smart-stream-yoto-smart-stream-pr-${PR_ID}.up.railway.app
- **Secrets**: Managed via GitHub Secrets and Railway environment variables
- **Tokens**: Separate Railway tokens for each environment (RAILWAY_TOKEN_PROD, RAILWAY_TOKEN_STAGING, RAILWAY_TOKEN_DEV)
- **Monitoring**: Use Railway CLI and dashboard for logs and metrics

## Key Resources

- **Yoto API**: https://yoto.dev/
- **Railway Docs**: https://docs.railway.app/
- **Railway MCP Server**: https://github.com/railwayapp/railway-mcp-server
- **Testing Guide**: `docs/TESTING_GUIDE.md`
- **Architecture**: `docs/ARCHITECTURE.md`
- **Copilot Workspace Network Config**: `docs/COPILOT_WORKSPACE_NETWORK_CONFIG.md` (Railway URL access configuration)

## Important Notes

- Yoto devices use OAuth2 Device Flow (no callback URLs required)
- Audio files should be MP3 format (128-256 kbps) for compatibility
- MQTT is used for real-time device events and control
- Railway environments use separate tokens for security (RAILWAY_TOKEN_PROD, RAILWAY_TOKEN_STAGING, RAILWAY_TOKEN_DEV)
- Display icons for Yoto Mini must be exactly 16x16 pixels in PNG format
- **Network Access**: Copilot Workspace is configured to access Railway deployment URLs (*.up.railway.app) and Railway APIs (railway.app) via `.github/copilot-workspace.yml`
- **Railway MCP Server**: Provides Railway management tools directly in Copilot Workspace (project/service/environment management, deployments, logs, variables)
- **Railway CLI Auto-Install**: The Railway CLI is automatically installed on workspace startup via `.github/copilot-workspace.yml` setup commands
- **Railway API Access**: The railway.app domain is whitelisted in the Copilot firewall, enabling full Railway CLI functionality
