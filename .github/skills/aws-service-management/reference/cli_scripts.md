# AWS CLI/CDK Scripts

Minimal, copy-paste friendly commands per copilot-instructions.md.

Install CDK if missing:

```bash
npm install -g aws-cdk
```

Source the Python virtual environment (once per session):

```bash
source cdk_venv/bin/activate
```

## Branch-Specific Deployment (Recommended for Copilot Sessions)

Auto-detect environment from current branch and deploy:

```bash
# Quick deployment with auto-detection
./scripts/deploy_branch.sh

# Or use CDK directly (auto-detects branch)
cd infrastructure/cdk
cdk deploy \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```

**How it works:**
- `copilot/*` branches → Creates `copilot-<branch>-pr<number>` environment
- `copilot-*` branches → Creates `copilot-<branch>` environment
- `aws-develop` → Uses `dev` environment
- `aws-main` → Uses `prod` environment
- Other branches → Uses `dev` environment

## Cleanup Branch-Specific Environments

Auto-cleanup current branch:

```bash
./scripts/cleanup_environment.sh
```

Cleanup specific environment:

```bash
./scripts/cleanup_environment.sh copilot-feature-pr123

# Or use CDK directly
cd infrastructure/cdk
cdk destroy -c environment=copilot-feature-pr123
```

**Note:** PR environments are automatically cleaned up when PRs are closed.

## Manual Environment Specification

Useful CDK helpers:

```bash
# From the CDK app directory (if applicable):
cd infrastructure/cdk

# Synthesize CloudFormation
cdk synth

# Show stack differences
cdk diff

# Bootstrap (first-time per account/region)
cdk bootstrap
```

Development (dev):

```bash
cdk deploy \
  -c environment=dev \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```

Production (prod):

```bash
cdk deploy \
  -c environment=prod \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=true
```

Notes:
- Use the default AWS profile locally.
- Always test against AWS; never deploy to Railway.
- Branch-specific environments provide isolation for testing.
