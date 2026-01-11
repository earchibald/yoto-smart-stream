> **⚠️ THIS DOCUMENT IS OBSOLETE**
> 
> The deployment process has been simplified. Please see:
> - [GitHub Secrets Setup](GITHUB_SECRETS_SETUP.md) - Configure deployment
> - [Railway Deployment Guide](docs/RAILWAY_DEPLOYMENT.md) - Current deployment process
> - [Railway PR Environments](docs/RAILWAY_PR_ENVIRONMENTS_NATIVE.md) - PR environment usage
> 
> The content below is kept for historical reference only.
> 
> ---
> 
# How to Deploy and Test the YOTO_SERVER_CLIENT_ID Fix

## Quick Start - Deploy to Development

### Step 1: Trigger the Deployment Workflow

Since you have repository access, you can trigger the deployment via GitHub Actions UI:

1. **Navigate to GitHub Actions**
   - Go to: https://github.com/earchibald/yoto-smart-stream/actions
   - Look for the "Railway Development (Shared Environment)" workflow

2. **Run the Workflow**
   - Click on "Railway Development (Shared Environment)"
   - Click the "Run workflow" button (top right)
   - Select branch: `copilot/fix-yoto-client-id-deployment`
   - Enter session ID: `copilot-fix-yoto-client-id-test`
   - Select action: `acquire-and-deploy`
   - Leave force unchecked (unless development is locked)
   - Click "Run workflow"

3. **Monitor the Deployment**
   - The workflow will start running
   - Click on the workflow run to see progress
   - Watch for the "Set Railway Environment Variables" step
   - Verify it shows: "Setting YOTO_SERVER_CLIENT_ID..."

### Step 2: Verify YOTO_SERVER_CLIENT_ID is Set

**Method A: Check Workflow Output**

In the GitHub Actions workflow output:
- Look at the "Set Railway Environment Variables" step
- You should see: `Setting YOTO_SERVER_CLIENT_ID...`
- You should NOT see: `⚠️ Warning: YOTO_SERVER_CLIENT_ID not set in GitHub secrets`

**Method B: Check Railway Dashboard**

1. Go to Railway: https://railway.app
2. Open your Yoto Smart Stream project
3. Select the "development" environment
4. Click on the service
5. Go to "Variables" tab
6. Verify `YOTO_SERVER_CLIENT_ID` is listed with a value

### Step 3: Check Deployment Logs

**Option A: Via Railway Dashboard**

1. In Railway dashboard, go to development service
2. Click "Deployments" tab
3. Select the latest deployment
4. Click "View Logs"
5. Look for these success messages:
   ```
   Starting Yoto Smart Stream v0.2.0
   Environment: development
   ✓ Yoto API connected successfully
   ✓ MQTT connected successfully
   ```

**Option B: Via GitHub Actions**

In the workflow run:
- Look at the "Get deployment status" step
- Look at the "Get recent logs" step
- Verify the service started without errors

### Step 4: Test the Service

**Test Health Endpoint**
```bash
curl https://yoto-smart-stream-development.up.railway.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "0.2.0",
  "environment": "development",
  "yoto_api": "connected",
  "mqtt_enabled": true,
  "audio_files": 0
}
```

**Test Readiness Endpoint**
```bash
curl https://yoto-smart-stream-development.up.railway.app/ready
```

Expected response (if YOTO_SERVER_CLIENT_ID is set correctly):
```json
{
  "ready": true
}
```

**Test API Documentation**
Open in browser:
```
https://yoto-smart-stream-development.up.railway.app/docs
```

You should see the FastAPI Swagger UI with all endpoints.

## Troubleshooting

### If YOTO_SERVER_CLIENT_ID is still not working

1. **Verify the GitHub Secret exists:**
   - Go to repository Settings → Secrets and variables → Actions
   - Verify `YOTO_SERVER_CLIENT_ID` is listed under "Repository secrets"
   - If missing, add it with your Yoto API client ID
   - **Security Note**: Only repository administrators should have access to secrets. Never expose secrets in logs or commit them to the repository. The workflows use environment variables to pass secrets securely to Railway.

2. **Check Railway Token:**
   - Verify `RAILWAY_TOKEN_DEV` secret exists in GitHub
   - This token must have access to the development environment

3. **Check Logs for Specific Errors:**
   - Look for authentication errors
   - Look for "Could not initialize Yoto API" messages
   - These will tell you if there's an issue with the client ID value

### If Deployment Fails

1. **Check for lock conflicts:**
   - Someone else might have the development environment locked
   - Run the workflow with action: `status` to check
   - Use action: `release` with the session ID to release
   - Or use `force: true` to override (use with caution)

2. **Check Railway service status:**
   - Ensure the Railway project and environment exist
   - Verify the service is not in a failed state

## Alternative: Deploy via Railway CLI

If you have the Railway CLI installed and a token:

```bash
# Set the Railway token
export RAILWAY_TOKEN="your_railway_token_for_dev"

# Set Yoto client ID before deploying
railway variables set YOTO_SERVER_CLIENT_ID="your_yoto_client_id" -e development

# Deploy
railway up -e development

# Check logs
railway logs -e development --tail 50
```

## Success Indicators

✅ Workflow completes without errors
✅ "Setting YOTO_SERVER_CLIENT_ID..." appears in logs
✅ No warning about missing YOTO_SERVER_CLIENT_ID
✅ Railway shows YOTO_SERVER_CLIENT_ID in environment variables
✅ Service starts successfully
✅ Logs show "✓ Yoto API connected successfully"
✅ Health endpoint returns healthy status
✅ Ready endpoint returns ready: true
✅ API documentation is accessible

## Next Steps After Successful Deployment

1. **Test with actual Yoto devices** (if available)
2. **Verify MQTT events** are being received
3. **Test audio streaming** functionality
4. **Check all API endpoints** work as expected
5. **Monitor for any runtime issues** over the next few hours

## Cleanup

When done testing, release the development environment lock:

1. Go to GitHub Actions
2. Run "Railway Development (Shared Environment)" workflow
3. Select action: `release`
4. Enter your session ID: `copilot-fix-yoto-client-id-test`
5. Run workflow

This allows others to use the development environment.
