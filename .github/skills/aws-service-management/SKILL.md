# AWS Service Management

Minimal skill for managing multi-environment AWS deployments for the yoto-smart-stream project.

## Quick Start
- Ensure CDK is installed: `npm install -g aws-cdk`
- Source the Python venv once per session: `source cdk_venv/bin/activate`
- Use the default AWS profile; test only against AWS services.
- Deployment commands are in `reference/cli_scripts.md`.

## Scope
- CDK deploy to `dev` or `prod` with required context flags
- MQTT/CloudFront toggles per environment
- Adheres to project conventions defined in copilot-instructions.md

## CDK Usage
- Navigate to the CDK app if needed: `infrastructure/cdk`
- Common commands:
	- Install: `npm install -g aws-cdk`
	- Synthesize: `cdk synth`
	- Diff: `cdk diff`
	- Deploy (see env flags in cli_scripts.md): `cdk deploy ...`
- Optional first-time setup: `cdk bootstrap` (per account/region)

## Railway legacy migration notes
- Export audio files from Railway persistent volume if needed (legacy):
  `railway run tar -czf /tmp/audio.tar.gz /data/audio_files/ && railway cp /tmp/audio.tar.gz ./audio.tar.gz`.
- Persistent data on Railway lived under `/data` (examples: `/data/.yoto_refresh_token`, `/data/audio_files`). When migrating to AWS, copy audio files to S3 and move tokens to AWS Secrets Manager.
- Rollback strategy: keep Railway running as a warm backup for 1-2 weeks after cutover; update DNS to point back to Railway URL to revert quickly.
- CI token mapping: Railway used `RAILWAY_TOKEN[_PROD|_STAGING|_DEV]`. Ensure equivalent deployment credentials are created and stored as GitHub Secrets for CI/CD during migration.
