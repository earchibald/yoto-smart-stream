# Deployment Workflows

This document describes the branch-specific deployment workflow for Yoto Smart Stream, particularly for Copilot PR and worktree sessions.

## Overview

The deployment system automatically creates isolated AWS environments based on the git branch, ensuring that:
- Each PR gets its own isolated testing environment
- Multiple developers can work in parallel without conflicts
- Environments are automatically cleaned up when PRs are closed
- Production and development environments remain stable

## Environment Naming Convention

Environments are automatically named based on the git branch:

| Branch Pattern | Environment Name | Example |
|----------------|------------------|---------|
| `aws-main` | `prod` | `prod` |
| `aws-develop` | `dev` | `dev` |
| `copilot/*` | `copilot-<branch>-pr<number>` | `copilot-implement-feature-pr123` |
| `copilot-*` | `copilot-<branch>` | `copilot-worktree-1` |
| Other | `dev` | `dev` |

### PR ID Integration

For `copilot/*` branches (PR sessions), the system automatically:
1. Detects the PR number from environment variables (`PR_NUMBER`, `GITHUB_REF`)
2. Includes it in the environment name for better isolation
3. Ensures each PR has a unique, identifiable environment

## Deployment Process

### Automatic Deployment (Recommended)

Use the deployment script that auto-detects everything:

```bash
./scripts/deploy_branch.sh
```

This script will:
1. Detect the current git branch
2. Determine the appropriate environment name
3. Include PR number if available
4. Deploy to the branch-specific CDK stack
5. Show deployment summary

### Manual Deployment

Navigate to the CDK directory and deploy:

```bash
cd infrastructure/cdk
cdk deploy \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```

The environment is auto-detected from the git branch.

### Explicit Environment Override

If you need to override the auto-detection:

```bash
cdk deploy \
  -c environment=my-custom-env \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false
```

## Cleanup Process

### Automatic Cleanup

When a PR with a `copilot/*` branch is closed, a GitHub Actions workflow automatically:
1. Detects the PR closure event
2. Determines the environment name (including PR number)
3. Destroys the CDK stack
4. Posts a comment on the PR confirming cleanup

**Workflow file:** `.github/workflows/cleanup-pr-environment.yml`

### Manual Cleanup

Use the cleanup script:

```bash
# Auto-detect current branch environment
./scripts/cleanup_environment.sh

# Or specify environment explicitly
./scripts/cleanup_environment.sh copilot-test-pr123
```

Or use CDK directly:

```bash
cd infrastructure/cdk
cdk destroy -c environment=copilot-test-pr123
```

## AWS Resources Created

Each branch-specific environment creates the following AWS resources:

- **Lambda Function:** `yoto-api-<environment>`
- **API Gateway:** `yoto-api-<environment>`
- **DynamoDB Table:** `yoto-smart-stream-<environment>`
- **S3 Buckets:**
  - `yoto-audio-<environment>-<account-id>`
  - `yoto-ui-<environment>-<account-id>`
- **ECS/Fargate Service:** `yoto-mqtt-<environment>` (if MQTT enabled)
- **Cognito User Pool:** `yoto-users-<environment>`
- **CloudWatch Logs:** Various log groups
- **IAM Roles:** Execution and task roles

All resources are prefixed with the environment name to avoid conflicts.

## Environment Detection Script

The core logic is in `scripts/get_deployment_environment.py`:

```python
# Basic usage
from get_deployment_environment import get_deployment_environment

env_name = get_deployment_environment()  # Auto-detects from current branch
print(f"Deploying to: {env_name}")
```

Command-line usage:

```bash
# Print environment name
python3 scripts/get_deployment_environment.py

# Verbose output with debug info
python3 scripts/get_deployment_environment.py --verbose
```

## Best Practices

1. **Always use branch-specific environments for PR testing** - Ensures isolation and prevents conflicts
2. **Clean up environments after testing** - Reduces AWS costs and clutter
3. **Use the automatic deployment scripts** - Less error-prone than manual commands
4. **Verify the environment name before deployment** - Check the deployment script output
5. **Never modify `prod` or `dev` environments from feature branches** - Use branch-specific environments instead

## Troubleshooting

### Environment name doesn't include PR number

The PR number is detected from environment variables:
- `PR_NUMBER` or `PULL_REQUEST_NUMBER`
- `GITHUB_REF` (format: `refs/pull/123/merge`)

If not running in GitHub Actions or without these variables, the PR number won't be included.

### Stack already exists with different configuration

If you need to change configuration, destroy the existing stack first:

```bash
./scripts/cleanup_environment.sh
```

Then redeploy with the new configuration.

### Cannot find environment

Ensure you're on the correct git branch. Check with:

```bash
git branch --show-current
python3 scripts/get_deployment_environment.py --verbose
```

## Cost Management

Branch-specific environments can increase AWS costs if not managed properly:

- **Enable cost alerts** for your AWS account
- **Clean up unused environments** regularly
- **Use smaller instance sizes** for testing (configured automatically)
- **Disable CloudFront** for non-production environments (default)
- **Monitor DynamoDB capacity** - uses on-demand pricing by default
- **Review S3 storage** - audio files can accumulate

The automatic PR cleanup workflow helps minimize costs by destroying environments when they're no longer needed.
