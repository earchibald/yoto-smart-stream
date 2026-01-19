# Railway Deployment Endpoint Script

This script provides a simple interface to retrieve Railway deployment endpoint URLs using the Railway CLI.

## Features

- Get endpoint URL for the currently linked Railway service
- Query specific environments (production, staging, etc.)
- List all deployments with metadata
- Multiple output formats (human-readable, JSON, URL-only)
- Full type checking and comprehensive test coverage

## Installation

### Prerequisites

1. **Railway CLI**: The script requires the Railway CLI to be installed:
   ```bash
   npm i -g @railway/cli
   ```

2. **Authentication**: Authenticate with Railway:
   ```bash
   railway login
   ```
   Or set the `RAILWAY_TOKEN` environment variable for CI/CD environments.

3. **Link to Project**: Link to your Railway project:
   ```bash
   railway link --project <project-name>
   ```

## Usage

### Basic Usage

Get the endpoint URL for the currently linked service:

```bash
python scripts/get_deployment_endpoint.py
```

Output:
```
Endpoint URL: https://yoto-smart-stream-production.up.railway.app
```

### Get URL Only (for scripting)

Perfect for use in shell scripts:

```bash
URL=$(python scripts/get_deployment_endpoint.py --url-only)
echo "Deployment URL: $URL"
```

### Query Specific Environment

Get endpoint for a specific environment:

```bash
python scripts/get_deployment_endpoint.py --environment production
python scripts/get_deployment_endpoint.py --environment staging
python scripts/get_deployment_endpoint.py --environment develop
```

### JSON Output

Get structured JSON output:

```bash
python scripts/get_deployment_endpoint.py --json
```

Output:
```json
{
  "url": "https://yoto-smart-stream-production.up.railway.app",
  "service": null,
  "environment": null
}
```

### List Deployments

List recent deployments:

```bash
python scripts/get_deployment_endpoint.py --list
python scripts/get_deployment_endpoint.py --list --limit 5
python scripts/get_deployment_endpoint.py --list --environment production
```

Output:
```
=== Deployments (3) ===

1. Deployment ID: 7e0a8079-26f5-466a-b8ba-e8b348b3aab8
   Status: SUCCESS
   Created: 2026-01-19T01:12:54.190Z

2. Deployment ID: ce1eddf5-80ea-4564-a113-d0c9b152da9e
   Status: REMOVED
   Created: 2026-01-19T00:37:05.938Z
```

### Combined with Other Tools

Check if deployment is live:

```bash
URL=$(python scripts/get_deployment_endpoint.py --url-only)
curl -s "$URL/api/health" | jq
```

Run tests against deployment:

```bash
DEPLOYMENT_URL=$(python scripts/get_deployment_endpoint.py --environment staging --url-only)
pytest tests/ --base-url="$DEPLOYMENT_URL"
```

## Command-Line Options

```
usage: get_deployment_endpoint.py [-h] [-s SERVICE] [-e ENVIRONMENT]
                                  [--deployment-id DEPLOYMENT_ID] [--list]
                                  [--limit LIMIT] [--json] [--url-only]

Get Railway deployment endpoint URL

options:
  -h, --help            show this help message and exit
  -s SERVICE, --service SERVICE
                        Service name or ID (defaults to linked service)
  -e ENVIRONMENT, --environment ENVIRONMENT
                        Environment name (defaults to linked environment)
  --deployment-id DEPLOYMENT_ID
                        Get specific deployment by ID (not implemented yet)
  --list                List all deployments instead of getting endpoint
  --limit LIMIT         Maximum number of deployments to list (default: 20)
  --json                Output in JSON format
  --url-only            Output only the URL (useful for scripts)
```

## Use Cases

### CI/CD Integration

In GitHub Actions workflows:

```yaml
- name: Get deployment URL
  id: deployment
  run: |
    URL=$(python scripts/get_deployment_endpoint.py --environment production --url-only)
    echo "url=$URL" >> $GITHUB_OUTPUT

- name: Run smoke tests
  run: |
    curl -f ${{ steps.deployment.outputs.url }}/api/health
```

### Environment Verification

Verify all environments are deployed:

```bash
for env in production staging develop; do
  echo "Checking $env..."
  python scripts/get_deployment_endpoint.py --environment $env
done
```

### Deployment Monitoring

Monitor deployment status:

```bash
python scripts/get_deployment_endpoint.py --list --limit 5 --json | \
  jq -r '.[] | "\(.status): \(.createdAt)"'
```

## Testing

The script includes comprehensive unit tests:

```bash
python -m pytest tests/test_get_deployment_endpoint.py -v
```

## Troubleshooting

### "Railway CLI is not installed"

Install the Railway CLI:
```bash
npm i -g @railway/cli
```

### "Not authenticated with Railway"

Authenticate with Railway:
```bash
railway login
```

Or set the `RAILWAY_TOKEN` environment variable.

### "No linked project found"

Link to your Railway project:
```bash
railway link --project <project-name>
```

### "No endpoint URL found"

Possible causes:
1. Service doesn't have an active deployment
2. Service doesn't have a domain configured
3. Wrong environment specified

Check the service status:
```bash
railway status
railway deployment list
```

## Implementation Details

The script uses the Railway CLI's JSON output format to:
1. Query `railway status --json` to get service and domain information
2. Parse the nested JSON structure to extract domain configuration
3. Handle multiple environment configurations
4. Provide clean, typed interfaces for programmatic use

The script handles Railway's complex nested JSON structure:
- `environments.edges[].node.serviceInstances.edges[].node.domains.serviceDomains[]`

And provides a simple interface:
- `get_endpoint_url(service=None, environment=None) -> Optional[str]`

## License

This script is part of the Yoto Smart Stream project.
