# Yoto Smart Stream Use Cases

## Use Case 1: Authenticate to Yoto Smart Stream and Authorize OAuth

### A. Determine Hostname

Methods to identify the Yoto Smart Stream service hostname:

1. **Railway MCP** (requires Railway CLI underneath)
2. **Railway CLI** directly
3. **Pattern-based URL construction**
   - Format: `https://yoto-smart-stream-{environment}.up.railway.app`
   - Environment options:
     - `production` (main branch)
     - `develop` (develop branch)
     - `yoto-smart-stream-pr-{PR_ID}` (PR preview environments)

### B. Connect and Authenticate to Yoto Smart Stream

Default credentials for initial access:
- Username: `admin`
- Password: `yoto`

### C. Complete Yoto OAuth Authorization

If required by the service, prompt user to complete OAuth authorization with Yoto. 

**Important:** OAuth authorization only needs to be completed once. OAuth tokens and refresh tokens persist across deployments and restarts.