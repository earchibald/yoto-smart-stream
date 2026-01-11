# GitHub Copilot Workspace Instructions

## Project Overview

This is the Yoto Smart Stream project - a service to stream audio to Yoto devices, monitor events via MQTT, and manage interactive audio experiences. The project includes Python/FastAPI backend, web UI components, and Railway deployment infrastructure.

## Code Style and Conventions

- **Language**: Python 3.9+
- **Framework**: FastAPI with async/await patterns
- **Testing**: pytest with fixtures, mocks, and comprehensive coverage (target >70%)
- **Linting**: ruff for code quality, black for formatting
- **Type hints**: Use Python typing throughout the codebase

## Locally-Maintained Skills

This workspace contains locally-maintained custom skills in `.github/skills/`:

1. **railway-service-management** - Multi-environment Railway deployment management
2. **yoto-api-development** - Yoto Play API integration, audio streaming, and MQTT handling

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

1. **Identify the relevant skill** - Determine which skill (`railway-service-management` or `yoto-api-development`) the new information relates to
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
└── yoto-api-development/
    ├── SKILL.md                    # Main overview and quick start
    └── reference/                  # Detailed reference docs
        ├── yoto_api_reference.md
        ├── yoto_mqtt_reference.md
        ├── architecture.md
        └── ...
```

**Examples of Updates to Make:**

- ✅ You discover a new Yoto API endpoint → Update `yoto-api-development/reference/yoto_api_reference.md`
- ✅ You find a better Railway deployment pattern → Update `railway-service-management/reference/deployment_workflows.md`
- ✅ You implement MQTT reconnection logic → Update `yoto-api-development/reference/yoto_mqtt_reference.md` with the pattern
- ✅ You correct an error in documented API behavior → Fix it in the relevant reference file
- ✅ You add a new Railway CLI command pattern → Add it to `railway-service-management/reference/cli_scripts.md`

## Development Workflow

1. **Testing First**: Write tests before implementing features (TDD approach)
2. **Use Skills**: Delegate to custom skills when available (railway-service-management, yoto-api-development)
3. **Update Documentation**: Keep skills and docs synchronized with verified implementation
4. **Code Quality**: Run linting and tests before committing
5. **Security**: Never commit secrets; use environment variables and GitHub Secrets

## Deployment

- **Platform**: Railway.app with multi-environment setup
- **Environments**: Production (main), Staging (develop), Development (shared)
- **Secrets**: Managed via GitHub Secrets and Railway environment variables
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
