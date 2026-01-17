# GitHub Copilot Workspace Instructions

## RULES
- Follow the instructions in this file when generating code or suggestions.
- If there are conflicting instructions between this file and any other documentation, prioritize the instructions in this file.
- If you are unsure about any instruction, ask for clarification before proceeding.
- ALWAYS and ONLY test against AWS services and never against local mocks or emulators.
- ALWAYS use Playwright MCP for web UI interactions.
- ALWAYS deploy fixes to AWS before testing.
- NEVER deploy to Railway. Railway is retired.

## Shell initialization
- ALWAYS source the python virtual environment before running any commands:
```bash
source cdk_venv/bin/activate
```
- ONLY source the python virtual environment ONCE per session.

## Standard Workflow
1. Understand the issue or feature request.
1. Check for existing skills in `.github/skills/` that relate to the task.
1. If a relevant skill exists, follow its guidance closely.
1. If no relevant skill exists, follow the general project guidelines below.
1. Implement the solution following best practices.
1. Write agent-focused tests to verify the solution using the guidelines provided.
1. Update the version shown in the web UI footer if applicable.
  1. Use semver format: MAJOR.MINOR.PATCH
  1. Increment:
     - MAJOR for incompatible API changes
     - MINOR for backward-compatible functionality
     - PATCH for backward-compatible bug fixes
1. Perform a **targeted** commit with a descriptive message.
1. Push changes to the appropriate branch.
1. Deploy to AWS using the established deployment process and the `cdk` commands below.
    a. If `cdk` is not installed, install it via `npm install -g aws-cdk`.
1. Test thoroughly in the AWS environment. Ensure that we are seeing the current deployed version from step 7 in the web UI footer.
1. If there are errors, return to step 1. Otherwise, proceed to step 13.
1. Once tests pass, report with a one-line summary of the fix or feature added and the deployed endpoint details (if applicable).
1. Once the task is successfully completed, proceed to the "Locally-Maintained Skills" section.

## Deployment Configuration

### Environment Selection
- **aws-develop branch or copilot/* branches**: Deploy to CDK environment `dev`
- **aws-main branch**: Deploy to CDK environment `prod`

### Deployment Flags by Environment

**Development (dev)**
```bash
cdk deploy \
  -c environment=dev \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```
- MQTT enabled: Required for testing real-time device events
- CloudFront disabled: Not needed in dev; reduces deployment time

**Production (prod)**
```bash
cdk deploy \
  -c environment=prod \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=true
```
- MQTT enabled: Required for production device control and events
- CloudFront enabled: Improves performance and reduces Lambda invocation costs

## Credentials
### AWS
- In the local environment, we don't need AWS credentials or region in the environment. Simply use the `default` profile.
- In a copilot environment, use the provided AWS environment variable credentials.

### Yoto API
- YOTO_CLIENT_ID=Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO

### yoto-smart-stream server auth
- Use the default user: `admin` / `yoto`

## Project Overview

This is the Yoto Smart Stream project - a service to stream audio to Yoto devices, monitor events via MQTT, and manage interactive audio experiences. The project includes Python/FastAPI backend, web UI components, and AWS infrastructure.

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

This workspace contains locally-maintained custom skills in `.github/skills/`:

1. **aws-service-management** - Multi-environment AWS deployment management
2. **yoto-api-development** - Yoto Play API integration, audio streaming, and MQTT handling

### Skill and copilot-instructions.md Maintenance Directive

**IMPORTANT**: When you discover, verify, or implement new information related to these skills or the top-level copilot-instructions.md during development or issue resolution, you MUST update the relevant file or skill documentation to keep it current and accurate.

** When to Update copilot-instructions.md:**
- When there are changes to the standard workflow, deployment process, or project conventions
- When new environment variables or credentials are introduced
- When there are updates to design principles or coding standards
- When new tools or frameworks are adopted in the project
- When existing instructions are found to be unclear or incomplete

**When to Update Skills:**

- When you verify new API endpoints, parameters, or behaviors
- When you discover AWS deployment patterns or configuration options
- When you implement new Yoto API features or MQTT event handling
- When you find corrections to existing documentation
- When you establish new best practices or patterns
- When you resolve issues that reveal gaps in the skill documentation

**How to Update Skills:**

1. **Identify the relevant skill** - Determine which skill (`aws-service-management` or `yoto-api-development`) the new information relates to
2. **Locate the appropriate file** - Skills have a main `SKILL.md` and reference docs in `reference/` subdirectories
3. **Update the documentation** - Add or correct information in the relevant file(s)
4. **Be specific** - Include examples, code snippets, or command syntax where applicable
5. **Maintain consistency** - Follow the existing structure and formatting of the skill files
6. **Update related sections** - If the change affects multiple areas, update all relevant sections

**Skill File Structure:**

```
.github/skills/
├── aws-service-management/
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
- ✅ You find a better AWS deployment pattern → Update `aws-service-management/reference/deployment_workflows.md`
- ✅ You implement MQTT reconnection logic → Update `yoto-api-development/reference/yoto_mqtt_reference.md` with the pattern
- ✅ You correct an error in documented API behavior → Fix it in the relevant reference file
- ✅ You add a new AWS CLI command pattern → Add it to `aws-service-management/reference/cli_scripts.md`

## failure to maintain skills
Neglecting to update these skills when new information is discovered can lead to outdated or incorrect documentation, which may cause confusion and errors in future development. Always ensure that the skills reflect the most current and accurate information.
