# AWS Service Management

Minimal skill for managing multi-environment AWS deployments for the yoto-smart-stream project.

## Quick Start
- Ensure CDK is installed: `npm install -g aws-cdk`
- Source the Python venv once per session: `source cdk_venv/bin/activate`
- Use the default AWS profile; test only against AWS services.
- Deployment commands are in `reference/cli_scripts.md`.
- For branch-specific deployments, see `reference/deployment_workflows.md`.

## Scope
- CDK deploy to `dev`, `prod`, or **branch-specific** environments
- Branch-specific environments for Copilot PR and worktree sessions
- Automatic environment detection based on git branch
- PR ID incorporation for better environment isolation
- Automatic cleanup of PR environments when PRs are closed
- MQTT/CloudFront toggles per environment
- Adheres to project conventions defined in copilot-instructions.md

## Branch-Specific Deployments

### Environment Detection
The system automatically detects the appropriate environment:
- `aws-main` → `prod`
- `aws-develop` → `dev`
- `copilot/*` → Branch-specific with PR ID (e.g., `copilot-feature-pr123`)
- `copilot-*` → Branch-specific (e.g., `copilot-worktree-1`)
- Other branches → `dev` (default)

### Quick Deploy
```bash
# Auto-detect and deploy
./scripts/deploy_branch.sh

# Or use CDK directly (auto-detects from branch)
cd infrastructure/cdk
cdk deploy -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" -c enable_mqtt=true -c enable_cloudfront=false
```

### Cleanup
```bash
# Auto-cleanup current branch environment
./scripts/cleanup_environment.sh

# Specify environment to cleanup
./scripts/cleanup_environment.sh copilot-test-pr123
```

**Note**: PR environments are automatically destroyed when the PR is closed via GitHub Actions.

## CDK Usage
- Navigate to the CDK app if needed: `infrastructure/cdk`
- Common commands:
	- Install: `npm install -g aws-cdk`
	- Synthesize: `cdk synth`
	- Diff: `cdk diff`
	- Deploy (see env flags in cli_scripts.md): `cdk deploy ...`
- Optional first-time setup: `cdk bootstrap` (per account/region)

## Architecture Documentation
- AWS infrastructure diagram and documentation maintained in `docs/` directory
- When CDK stack changes, update corresponding documentation
- See `reference/architecture_documentation.md` for complete update process
- Files to maintain:
  - `docs/AWS_ARCHITECTURE_DIAGRAM.svg` - Generated graphical diagram
  - `docs/AWS_ARCHITECTURE_OVERVIEW.md` - Detailed technical documentation
  - `docs/README_ARCHITECTURE.md` - Quick reference guide

## Railway legacy migration notes
- Export audio files from Railway persistent volume if needed (legacy):
  `railway run tar -czf /tmp/audio.tar.gz /data/audio_files/ && railway cp /tmp/audio.tar.gz ./audio.tar.gz`.
- Persistent data on Railway lived under `/data` (examples: `/data/.yoto_refresh_token`, `/data/audio_files`). When migrating to AWS, copy audio files to S3 and move tokens to AWS Secrets Manager.
- Rollback strategy: keep Railway running as a warm backup for 1-2 weeks after cutover; update DNS to point back to Railway URL to revert quickly.
- CI token mapping: Railway used `RAILWAY_TOKEN[_PROD|_STAGING|_DEV]`. Ensure equivalent deployment credentials are created and stored as GitHub Secrets for CI/CD during migration.
