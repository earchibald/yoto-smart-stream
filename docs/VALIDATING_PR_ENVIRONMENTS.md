# Validating Railway PR Environments

This document describes how to validate that Railway PR Environments are working correctly with this project.

## What Gets Validated

Railway PR Environments validation ensures that:

1. **Health Endpoint** - The `/health` endpoint is accessible and returns correct status
2. **Root Endpoint** - The root endpoint returns proper API information
3. **API Documentation** - OpenAPI documentation is accessible at `/docs`
4. **Railway Configuration** - The `railway.toml` file is properly configured
5. **GitHub Workflow** - The PR checks workflow is set up correctly

## Automatic Validation

### On Every Pull Request

When you open or update a pull request, the GitHub Actions workflow automatically:

1. **Deploys** - Railway automatically creates and deploys a PR environment
2. **Waits** - The workflow waits for the deployment to be ready
3. **Validates** - Runs the validation script against the PR environment
4. **Reports** - Posts a comment to the PR with validation results

### Workflow File

The validation is configured in `.github/workflows/railway-pr-checks.yml`:

```yaml
- name: Validate PR Environment
  env:
    PR_NUMBER: ${{ github.event.pull_request.number }}
  run: |
    python scripts/validate_pr_environment.py "${{ steps.env-url.outputs.url }}" --wait --skip-config
```

## Manual Validation

You can manually validate a PR environment using the validation script.

### Prerequisites

- Python 3.9 or higher
- Access to the internet (to reach Railway deployments)

### Validate a Specific PR Environment

```bash
# Validate PR #42
python scripts/validate_pr_environment.py https://yoto-smart-stream-pr-42.up.railway.app

# Validate with automatic wait for deployment
python scripts/validate_pr_environment.py https://yoto-smart-stream-pr-42.up.railway.app --wait

# Validate local development server
python scripts/validate_pr_environment.py http://localhost:8000
```

### Auto-Detect PR URL from Environment

If you're running in a CI environment or have set environment variables, the script can auto-detect the PR URL:

```bash
# Set PR number
export PR_NUMBER=42

# Run validation (auto-detects URL)
python scripts/validate_pr_environment.py --wait
```

### Validation Script Options

```bash
python scripts/validate_pr_environment.py --help

usage: validate_pr_environment.py [-h] [--wait] [--skip-config] [base_url]

Validate Railway PR Environment

positional arguments:
  base_url       Base URL of the service (auto-detected if not provided)

optional arguments:
  -h, --help     show this help message and exit
  --wait         Wait for deployment to be ready before testing
  --skip-config  Skip local configuration validation
```

## Validation Results

### Successful Validation

When all checks pass, you'll see output like:

```
Railway PR Environment Validation
Target: https://yoto-smart-stream-pr-42.up.railway.app

1. Testing Health Endpoint
✓ Health check passed: healthy
  Version: 1.0.0
  Environment: pr-42
  MQTT Enabled: True
  Audio Files: 3

2. Testing Root Endpoint
✓ Root endpoint passed: running
  Name: Yoto Smart Stream
  Version: 1.0.0
  Environment: pr-42
  Features:
    ✓ player_control: True
    ✓ audio_streaming: True
    ✓ myo_card_creation: True
    ✓ mqtt_events: True

3. Testing API Documentation
✓ API documentation is accessible
  Docs URL: https://yoto-smart-stream-pr-42.up.railway.app/docs

4. Validating Railway Configuration
✓ Railway config file exists
  ✓ Found: [build]
  ✓ Found: [deploy]
  ✓ Found: startCommand
  ✓ Found: healthcheckPath
  ✓ Health check path configured

5. Validating GitHub Workflow
✓ PR checks workflow exists
  ✓ pull_request trigger
  ✓ health check test
  ✓ PR comment

Validation Summary
✓ Health Endpoint
✓ Root Endpoint
✓ API Documentation
✓ Railway Config
✓ GitHub Workflow

Results: 5/5 checks passed
✓ All validations passed! ✨
```

### Failed Validation

If validation fails, the output will show which checks failed:

```
Railway PR Environment Validation
Target: https://yoto-smart-stream-pr-42.up.railway.app

1. Testing Health Endpoint
✗ Health check failed with status 503

2. Testing Root Endpoint
✗ Root endpoint failed with status 503

...

Validation Summary
✗ Health Endpoint
✗ Root Endpoint
✓ API Documentation
✓ Railway Config
✓ GitHub Workflow

Results: 3/5 checks passed
⚠ 2 validation(s) failed
```

## Troubleshooting

### Deployment Not Ready

**Problem:** Validation fails with connection errors

**Solution:**
```bash
# Wait for deployment to be ready
python scripts/validate_pr_environment.py https://yoto-smart-stream-pr-42.up.railway.app --wait
```

The `--wait` flag will retry for up to 5 minutes (30 attempts with 10-second delays).

### Health Check Fails

**Problem:** Health endpoint returns 503 or other error

**Check:**
1. View Railway deployment logs:
   ```bash
   railway logs -e pr-42 --tail 100
   ```

2. Check for startup errors:
   ```bash
   railway logs -e pr-42 --filter "ERROR"
   ```

3. Verify environment variables:
   ```bash
   railway variables -e pr-42
   ```

**Common Causes:**
- Missing environment variables
- Database connection issues
- Python dependencies not installed
- Port binding issues

### API Documentation Not Accessible

**Problem:** `/docs` endpoint returns 404

**Check:**
1. Verify FastAPI is configured correctly
2. Check if docs are disabled in production
3. Review application startup logs

### Railway Config Invalid

**Problem:** Railway configuration validation fails

**Check:**
1. Verify `railway.toml` exists in repository root
2. Ensure required sections are present:
   - `[build]`
   - `[deploy]`
   - `startCommand`
   - `healthcheckPath`

**Fix:**
```toml
# railway.toml
[build]
builder = "NIXPACKS"
buildCommand = "pip install -r requirements.txt"

[deploy]
startCommand = "uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 100
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

## Testing in CI/CD

### GitHub Actions

The validation script is integrated into the PR checks workflow:

```yaml
# .github/workflows/railway-pr-checks.yml
- name: Validate PR Environment
  run: |
    python scripts/validate_pr_environment.py "${{ steps.env-url.outputs.url }}" --wait --skip-config
```

### Other CI Systems

For other CI systems, set the `PR_NUMBER` environment variable:

```bash
export PR_NUMBER="${CI_PR_NUMBER}"
python scripts/validate_pr_environment.py --wait --skip-config
```

## Advanced Usage

### Validate Specific Endpoints

You can extend the validation script to test specific endpoints:

```python
# Add custom validation function
def validate_custom_endpoint(base_url: str) -> bool:
    """Validate custom endpoint."""
    status, data = make_request(f"{base_url}/api/players")
    return status == 200

# Add to main validation
results.append(("Custom Endpoint", validate_custom_endpoint(base_url)))
```

### Integration with Tests

Use the validation script as part of integration tests:

```python
# tests/integration/test_pr_environment.py
import subprocess
import os

def test_pr_environment_validation():
    """Test that PR environment passes validation."""
    pr_number = os.environ.get("PR_NUMBER")
    if not pr_number:
        pytest.skip("Not running in PR environment")
    
    url = f"https://yoto-smart-stream-pr-{pr_number}.up.railway.app"
    result = subprocess.run(
        ["python", "scripts/validate_pr_environment.py", url, "--skip-config"],
        capture_output=True
    )
    
    assert result.returncode == 0, "PR environment validation failed"
```

## Best Practices

### For Developers

1. **Always validate locally first** before pushing to PR
   ```bash
   python scripts/validate_pr_environment.py http://localhost:8000
   ```

2. **Check PR comments** for automated validation results

3. **Fix failures immediately** - don't let PRs sit with failing validations

4. **Test OAuth-free features** in PR environments (OAuth requires static URLs)

### For CI/CD

1. **Use `--wait` flag** in CI to handle deployment delays

2. **Use `--skip-config` flag** when running remotely (config files aren't available)

3. **Set appropriate timeouts** - deployments can take 1-3 minutes

4. **Post results to PR comments** for visibility

## Related Documentation

- [Railway PR Environments Quick Start](RAILWAY_PR_ENVIRONMENTS_NATIVE.md)
- [Railway PR Environments Comparison](RAILWAY_PR_ENVIRONMENTS_COMPARISON.md)
- [Railway Service Management Skill](../.github/skills/railway-service-management/SKILL.md)
- [PR Environments Reference](../.github/skills/railway-service-management/reference/pr_environments.md)

## Summary

Railway PR Environment validation ensures that:

✅ PR environments deploy successfully  
✅ Health checks pass  
✅ API endpoints are accessible  
✅ Configuration is correct  
✅ Deployments are ready for testing  

By following this guide, you can confidently validate that Railway PR Environments are working correctly for every pull request.

---

**Last Updated:** 2026-01-11  
**Version:** 1.0.0  
**Status:** Active
