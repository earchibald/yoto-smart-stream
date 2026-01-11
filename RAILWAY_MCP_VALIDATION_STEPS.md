# Railway MCP Tool Validation - Manual Steps

This guide provides manual steps to complete the Railway MCP tool validation after the workspace has been restarted with the updated network configuration.

## Prerequisites

1. **Workspace Restart Required**: The network configuration changes require a Copilot Workspace restart to take effect. The current session loaded the old configuration at startup.

2. **Railway API Token**: Ensure `RAILWAY_API_TOKEN` is available in the environment (it should be automatically injected by GitHub secrets).

## Automated Validation

Run the validation script after restarting the workspace:

```bash
cd /home/runner/work/yoto-smart-stream/yoto-smart-stream
./scripts/validate_railway_mcp.sh
```

This script will:
- ✅ Verify Railway CLI installation
- ✅ Test network connectivity to all Railway domains
- ✅ Validate Railway authentication
- ✅ Test basic Railway CLI operations
- ✅ Provide next steps for MCP tool testing

## Manual Validation Steps

If you prefer to validate manually or if the automated script encounters issues, follow these steps:

### Step 1: Verify Railway CLI Installation

```bash
railway --version
# Expected: railway 4.23.0 (or higher)
```

### Step 2: Test Network Connectivity

Test that all Railway domains are accessible:

```bash
# Test railway.app
curl -I https://railway.app
# Expected: HTTP 301 or 200

# Test api.railway.app
curl -I https://api.railway.app
# Expected: HTTP 200

# Test backboard.railway.app
curl -I https://backboard.railway.app
# Expected: HTTP 200

# Test backboard.railway.com (the critical one for CLI v4.x)
getent hosts backboard.railway.com
# Expected: IP addresses returned

curl -I https://backboard.railway.com/graphql/v2
# Expected: Should NOT return DNS resolution error
```

If any of these fail with DNS errors, the workspace may not have loaded the updated configuration yet.

### Step 3: Authenticate with Railway

Verify that the Railway CLI can authenticate:

```bash
railway whoami
# Expected: Your Railway account username/email
# If this fails, the RAILWAY_API_TOKEN may not be set correctly
```

### Step 4: List Railway Projects

Test the Railway CLI's ability to list projects:

```bash
railway list
# Expected: List of Railway projects, including yoto-smart-stream
```

### Step 5: Link to the Railway Service

Use the Railway MCP server to link to the service:

**Via MCP Tool (Preferred):**
```
Use the railway-mcp-server-link-service tool to link this workspace to the yoto-smart-stream service
```

**Via CLI (Alternative):**
```bash
cd /home/runner/work/yoto-smart-stream/yoto-smart-stream
railway link
# Select: yoto-smart-stream project
# Select: yoto-smart-stream service (or the appropriate service name)
```

Verify the link:
```bash
railway status
# Expected: Project and service information displayed
```

### Step 6: Link to PR Environment

Determine the PR environment name and link to it:

**Via MCP Tool (Preferred):**
```
Use the railway-mcp-server-link-environment tool to link to the PR environment for this branch
```

**Via CLI (Alternative):**
```bash
# First, check available environments
railway environment list

# Link to the PR environment (e.g., pr-42, development, etc.)
railway environment pr-42
# or
railway environment development
```

Verify the environment link:
```bash
railway status
# Expected: Should show the linked environment
```

### Step 7: Retrieve Logs

Get logs from the linked environment:

**Via MCP Tool (Preferred):**
```
Use the railway-mcp-server-get-logs tool to retrieve deployment logs from the current environment
```

**Via CLI (Alternative):**
```bash
# Get deployment logs
railway logs

# Get the last 100 lines
railway logs --tail 100

# Filter logs (requires Railway CLI v4.9.0+)
railway logs --filter "error"
railway logs --filter "@level:error"
```

## Validation Checklist

Use this checklist to track validation progress:

- [ ] Workspace restarted after configuration changes
- [ ] Railway CLI version verified (v4.23.0+)
- [ ] Network connectivity tested:
  - [ ] railway.app accessible
  - [ ] api.railway.app accessible
  - [ ] backboard.railway.app accessible
  - [ ] backboard.railway.com accessible (DNS + HTTP)
- [ ] Railway CLI authentication successful (`railway whoami`)
- [ ] Railway projects listed successfully
- [ ] Linked to yoto-smart-stream service
- [ ] Linked to PR environment (or appropriate environment)
- [ ] Retrieved logs from linked environment
- [ ] Tested Railway MCP server tools:
  - [ ] railway-mcp-server-check-railway-status
  - [ ] railway-mcp-server-list-projects
  - [ ] railway-mcp-server-list-services
  - [ ] railway-mcp-server-link-service
  - [ ] railway-mcp-server-link-environment
  - [ ] railway-mcp-server-get-logs

## Railway MCP Server Tools Reference

### check-railway-status
Verifies Railway CLI installation and login status.

**Usage via Copilot:**
```
Check the Railway status to see if I'm logged in
```

### list-projects
Lists all Railway projects for the authenticated account.

**Usage via Copilot:**
```
List all my Railway projects
```

### list-services
Lists all services in the currently linked project.

**Usage via Copilot:**
```
List all services in the Railway project
```

### link-service
Links a service to the current workspace directory.

**Usage via Copilot:**
```
Link the yoto-smart-stream service to this workspace
```

**Parameters:**
- `workspacePath`: `/home/runner/work/yoto-smart-stream/yoto-smart-stream`
- `serviceName`: `yoto-smart-stream` (or appropriate service name)

### link-environment
Links an environment to the current workspace directory.

**Usage via Copilot:**
```
Link to the development environment
```

**Parameters:**
- `workspacePath`: `/home/runner/work/yoto-smart-stream/yoto-smart-stream`
- `environmentName`: `development` (or `pr-42`, `staging`, `production`)

### get-logs
Retrieves build or deployment logs for the linked service.

**Usage via Copilot:**
```
Show me the deployment logs for the current service
```

**Parameters:**
- `workspacePath`: `/home/runner/work/yoto-smart-stream/yoto-smart-stream`
- `logType`: `deploy` or `build`
- `lines`: Optional - number of lines to return (requires CLI v4.9.0+)
- `filter`: Optional - filter logs by search terms (requires CLI v4.9.0+)

**Examples:**
```
Get the last 100 lines of deployment logs
```

```
Show me error logs from the latest deployment
```

```
Filter deployment logs for 'error' messages
```

## Troubleshooting

### DNS Resolution Fails for backboard.railway.com

**Symptoms:**
```
dns error: failed to lookup address information: No address associated with hostname
```

**Solution:**
1. Verify the workspace has been restarted after the configuration changes
2. Check that `.github/copilot-workspace.yml` includes `backboard.railway.com` in `allowed_domains`
3. Confirm the configuration file has no YAML syntax errors

### Railway CLI Not Authenticated

**Symptoms:**
```
Not logged in to Railway CLI. Please run 'railway login' first
```

**Solution:**
1. Check if `RAILWAY_API_TOKEN` is set:
   ```bash
   echo "Token set: $([ -n "$RAILWAY_API_TOKEN" ] && echo "Yes" || echo "No")"
   ```
2. If not set, verify it's configured in GitHub repository secrets
3. Try authenticating manually:
   ```bash
   export RAILWAY_TOKEN="$RAILWAY_API_TOKEN"
   railway whoami
   ```

### MCP Server Tools Not Available

**Symptoms:**
- Railway MCP tools not appearing in Copilot
- "Tool not found" errors

**Solution:**
1. The Railway MCP server is configured at the GitHub Copilot Workspace level
2. It should be automatically available if Railway CLI is installed
3. Try restarting the workspace
4. Verify Railway CLI is installed: `railway --version`

### Project Not Linked

**Symptoms:**
```
No linked project found. Run railway link to connect to a project
```

**Solution:**
Use the MCP tool or manual linking:
```bash
railway link
# Select: yoto-smart-stream
```

Or check if a `.railway` directory exists (legacy linking):
```bash
ls -la .railway/
```

## Success Criteria

The validation is considered successful when:

1. ✅ Railway CLI can connect to all Railway domains
2. ✅ Authentication works (`railway whoami` returns account info)
3. ✅ Projects can be listed
4. ✅ Service is linked to the workspace
5. ✅ Environment is linked to the workspace
6. ✅ Logs can be retrieved from the environment
7. ✅ All Railway MCP server tools function correctly

## Related Documentation

- [Railway MCP Validation Report](../RAILWAY_MCP_VALIDATION.md) - Detailed investigation findings
- [Copilot Workspace Network Config](../docs/COPILOT_WORKSPACE_NETWORK_CONFIG.md) - Network configuration documentation
- [Railway MCP Server Documentation](https://github.com/railwayapp/railway-mcp-server) - Official MCP server docs

## Next Steps After Validation

Once validation is complete:

1. **Document Results**: Update `RAILWAY_MCP_VALIDATION.md` with validation outcomes
2. **Update Skills**: If needed, update Railway skill documentation with any new findings
3. **Close Issue**: Mark the validation task as complete
4. **Share Findings**: The configuration fix benefits future development work

---

**Created:** 2026-01-11  
**For Issue:** Validate MCP tool by using it to link to Railway service and PR environment  
**Branch:** copilot/validate-mcp-link-railway-service
