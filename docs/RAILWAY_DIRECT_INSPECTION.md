# Railway Service Inspection Guide

## Overview

This guide provides a process for **directly inspecting Railway services** using the GraphQL API, bypassing the Railway CLI which has authentication limitations in the current environment.

## Problem Statement

The Railway CLI (`railway` command) does **NOT** work with `RAILWAY_API_TOKEN` in the current environment, despite documentation suggesting otherwise. However, direct GraphQL API calls work perfectly.

## Solution: Direct API Inspection

We've created `scripts/railway_inspect.py` - a Python script that provides comprehensive Railway service inspection capabilities using the GraphQL API directly.

## Prerequisites

```bash
# Ensure requests library is installed
pip install requests

# Set your Railway API token
export RAILWAY_API_TOKEN="your-token-here"
```

## Usage

### Quick Start: Interactive Mode

The easiest way to inspect the yoto-smart-stream service:

```bash
python scripts/railway_inspect.py interactive
```

This automatically:
- Finds the yoto-smart-stream service
- Shows project and environment details
- Displays recent production deployments
- Shows latest deployment logs

**Example Output:**
```
🔍 Finding yoto-smart-stream service...

✅ Found service!

Project: zippy-encouragement (f92d5fa2-484e-4d93-9b1f-91c33cc33d0e)
Service: yoto-smart-stream (e63186e3-4ff7-4d6f-b448-a5b5e1590e79)

Environments:
  • production (c4477d57-96c3-49b5-961d-a456819dedf2)
  • yoto-smart-stream-pr-49 (159c71a2-74ce-4bca-ac71-c8ab2a13d829)
  • yoto-smart-stream-pr-50 (72f83a58-1146-453b-8b3d-5a1a5d3c03b2)

📦 Recent Production Deployments:
  ✅ SUCCESS: 2026-01-11 16:16:49 UTC
     URL: https://yoto-smart-stream-production.up.railway.app

📋 Recent Logs (latest 20 lines):
  INFO: Application startup complete.
  INFO: Uvicorn running on http://0.0.0.0:8080
  ...
```

### List All Projects

```bash
python scripts/railway_inspect.py list-projects
```

### List Services in a Project

```bash
python scripts/railway_inspect.py list-services \
    --project-id f92d5fa2-484e-4d93-9b1f-91c33cc33d0e
```

### Get Recent Deployments

```bash
# All deployments in a project
python scripts/railway_inspect.py deployments \
    --project-id f92d5fa2-484e-4d93-9b1f-91c33cc33d0e \
    --limit 10

# Deployments for a specific environment
python scripts/railway_inspect.py deployments \
    --project-id f92d5fa2-484e-4d93-9b1f-91c33cc33d0e \
    --environment production \
    --limit 5
```

### Retrieve Deployment Logs

```bash
# Get logs from a specific deployment
python scripts/railway_inspect.py logs \
    --deployment-id 45bbeb97-238c-480d-ba0b-c2a13e7d72f6 \
    --limit 100

# Raw logs (no timestamp formatting)
python scripts/railway_inspect.py logs \
    --deployment-id 45bbeb97-238c-480d-ba0b-c2a13e7d72f6 \
    --limit 50 \
    --raw
```

### Check Service Health

```bash
python scripts/railway_inspect.py health \
    --project-id f92d5fa2-484e-4d93-9b1f-91c33cc33d0e \
    --service-id e63186e3-4ff7-4d6f-b448-a5b5e1590e79
```

This checks:
- Latest deployment status
- Service URL accessibility
- `/api/health` endpoint response
- Recent deployment history

## Common Workflows

### Troubleshooting a Deployment Failure

1. **Find the failed deployment:**
   ```bash
   python scripts/railway_inspect.py deployments \
       --project-id <PROJECT_ID> \
       --environment production \
       --limit 10
   ```

2. **Get the deployment logs:**
   ```bash
   python scripts/railway_inspect.py logs \
       --deployment-id <DEPLOYMENT_ID> \
       --limit 200
   ```

3. **Check service health:**
   ```bash
   python scripts/railway_inspect.py health \
       --project-id <PROJECT_ID> \
       --service-id <SERVICE_ID>
   ```

### Monitoring Production

```bash
# Quick production check
python scripts/railway_inspect.py interactive

# Detailed production deployments
python scripts/railway_inspect.py deployments \
    --project-id f92d5fa2-484e-4d93-9b1f-91c33cc33d0e \
    --environment production \
    --limit 5

# Get latest production logs
# (first get latest deployment ID from above, then:)
python scripts/railway_inspect.py logs \
    --deployment-id <LATEST_DEPLOYMENT_ID> \
    --limit 100
```

### Checking PR Environment

```bash
# List all environments
python scripts/railway_inspect.py list-services \
    --project-id f92d5fa2-484e-4d93-9b1f-91c33cc33d0e

# Check PR-50 deployments
python scripts/railway_inspect.py deployments \
    --project-id f92d5fa2-484e-4d93-9b1f-91c33cc33d0e \
    --environment yoto-smart-stream-pr-50 \
    --limit 3
```

## Using in Agent Scripts

The script can be easily integrated into automated agent workflows:

### Example: Python Integration

```python
#!/usr/bin/env python3
import subprocess
import json
import os

# Set token
os.environ["RAILWAY_API_TOKEN"] = "your-token-here"

# Get deployment info
result = subprocess.run(
    ["python", "scripts/railway_inspect.py", "deployments",
     "--project-id", "f92d5fa2-484e-4d93-9b1f-91c33cc33d0e",
     "--environment", "production",
     "--limit", "1"],
    capture_output=True,
    text=True
)

print(result.stdout)

# Get logs
result = subprocess.run(
    ["python", "scripts/railway_inspect.py", "logs",
     "--deployment-id", "45bbeb97-238c-480d-ba0b-c2a13e7d72f6",
     "--limit", "50"],
    capture_output=True,
    text=True
)

print(result.stdout)
```

### Example: Bash Integration

```bash
#!/bin/bash

# Set token
export RAILWAY_API_TOKEN="your-token-here"

# Quick health check
python scripts/railway_inspect.py interactive

# Get recent logs and filter for errors
python scripts/railway_inspect.py logs \
    --deployment-id "45bbeb97-238c-480d-ba0b-c2a13e7d72f6" \
    --limit 200 \
    --raw | grep -i error
```

## API Reference

### RailwayInspector Class

The script provides a `RailwayInspector` class that can be imported and used directly:

```python
from scripts.railway_inspect import RailwayInspector

# Initialize
inspector = RailwayInspector(api_token="your-token")

# Or use environment variable
inspector = RailwayInspector()  # Uses RAILWAY_API_TOKEN

# List projects
projects = inspector.list_projects()

# Get services
project_details = inspector.get_project_services(project_id)

# Get deployments
deployments = inspector.get_deployments(
    project_id,
    environment_id="...",
    limit=10
)

# Get logs
logs = inspector.get_deployment_logs(deployment_id, limit=100)

# Find yoto-smart-stream automatically
result = inspector.find_yoto_project()
```

## GraphQL Queries Used

The script uses these Railway GraphQL queries:

### List Projects
```graphql
query {
    projects {
        edges {
            node {
                id
                name
                description
                createdAt
            }
        }
    }
}
```

### Get Project Services
```graphql
query($projectId: String!) {
    project(id: $projectId) {
        id
        name
        services {
            edges {
                node {
                    id
                    name
                    createdAt
                }
            }
        }
        environments {
            edges {
                node {
                    id
                    name
                }
            }
        }
    }
}
```

### Get Deployments
```graphql
query($input: DeploymentListInput!, $limit: Int!) {
    deployments(first: $limit, input: $input) {
        edges {
            node {
                id
                status
                createdAt
                staticUrl
                meta
            }
        }
    }
}
```

### Get Deployment Logs
```graphql
query($deploymentId: String!, $limit: Int!) {
    deploymentLogs(deploymentId: $deploymentId, limit: $limit) {
        message
        timestamp
        severity
    }
}
```

## Known IDs (for reference)

### Projects
- **zippy-encouragement**: `f92d5fa2-484e-4d93-9b1f-91c33cc33d0e`
  - Contains yoto-smart-stream service

### Services
- **yoto-smart-stream**: `e63186e3-4ff7-4d6f-b448-a5b5e1590e79`

### Environments
- **production**: `c4477d57-96c3-49b5-961d-a456819dedf2`
- **yoto-smart-stream-pr-49**: `159c71a2-74ce-4bca-ac71-c8ab2a13d829`
- **yoto-smart-stream-pr-50**: `72f83a58-1146-453b-8b3d-5a1a5d3c03b2`

## Troubleshooting

### "RAILWAY_API_TOKEN not found"

Set the environment variable:
```bash
export RAILWAY_API_TOKEN="your-token-here"
```

Or create a `.env` file in the project root (make sure it's in `.gitignore`):
```
RAILWAY_API_TOKEN=your-token-here
```

### "requests library not installed"

Install the required dependency:
```bash
pip install requests
```

### "GraphQL errors: Unauthorized"

Your Railway API token may be invalid or expired. Generate a new one at:
https://railway.app/account/tokens

### Connection Timeout

The Railway API may be temporarily unavailable. Try again in a few moments.

## Advantages Over Railway CLI

1. **Works with API Tokens**: Direct API access works with `RAILWAY_API_TOKEN`
2. **No Authentication Issues**: Bypasses CLI login problems
3. **Programmatic Access**: Easy to integrate into scripts and automation
4. **Flexible Querying**: Direct GraphQL access for custom queries
5. **Agent-Friendly**: Perfect for autonomous agent workflows

## Security Notes

- Never commit your `RAILWAY_API_TOKEN` to version control
- Use environment variables or secret management systems
- Rotate tokens periodically
- Use project-specific tokens when possible (scope limitation)

## Related Documentation

- [Railway GraphQL API](https://docs.railway.com/reference/public-api)
- [Railway MCP Validation Success](../RAILWAY_MCP_VALIDATION_SUCCESS.md)
- [Railway Deployment Guide](./RAILWAY_DEPLOYMENT.md)

---

**Created:** 2026-01-11  
**Purpose:** Direct Railway service inspection for development and troubleshooting  
**Method:** Railway GraphQL API (bypasses CLI authentication issues)
