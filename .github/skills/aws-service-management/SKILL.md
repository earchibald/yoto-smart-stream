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