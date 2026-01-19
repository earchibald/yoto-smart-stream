#!/bin/bash
# Railway CLI Setup for Cloud Agent Sessions
# Automatically detects and configures Railway CLI for this project

set -e

echo "🚀 Railway CLI Cloud Agent Setup"
echo ""

# 1. Verify RAILWAY_API_TOKEN is set
if [ -z "$RAILWAY_API_TOKEN" ]; then
  echo "❌ Error: RAILWAY_API_TOKEN not set"
  echo "Cloud Agent environment must have RAILWAY_API_TOKEN configured"
  echo ""
  echo "Expected: RAILWAY_API_TOKEN environment variable"
  exit 1
fi

echo "✅ RAILWAY_API_TOKEN is set"

# 2. Login to Railway (automatically uses RAILWAY_API_TOKEN)
echo ""
echo "🔐 Logging in to Railway..."
railway login
echo "✅ Logged in to Railway"

# 3. Auto-detect environment from GitHub context
if [[ "$GITHUB_REF" =~ refs/pull/([0-9]+)/merge ]]; then
  PR_NUMBER="${BASH_REMATCH[1]}"
  ENV_NAME="yoto-smart-stream-pr-${PR_NUMBER}"
  echo "📋 Detected PR #${PR_NUMBER} → Environment: ${ENV_NAME}"
elif [[ "$GITHUB_REF_NAME" =~ pr-([0-9]+) ]]; then
  PR_NUMBER="${BASH_REMATCH[1]}"
  ENV_NAME="yoto-smart-stream-pr-${PR_NUMBER}"
  echo "📋 Detected PR #${PR_NUMBER} from branch → Environment: ${ENV_NAME}"
elif [ "$GITHUB_REF" == "refs/heads/main" ]; then
  ENV_NAME="production"
  echo "📋 Detected main branch → Environment: ${ENV_NAME}"
else
  ENV_NAME="production"
  echo "📋 Using default → Environment: ${ENV_NAME}"
fi

# 4. Link project, service, and environment
echo ""
echo "🔗 Linking to project: yoto, service: yoto-smart-stream, environment: ${ENV_NAME}"
railway link --project yoto --service yoto-smart-stream --environment "$ENV_NAME"

# 5. Verify setup
echo ""
echo "✅ Railway CLI configured for Cloud Agent"
echo ""
echo "Available commands:"
echo "  railway status --json"
echo "  railway logs --lines 50 --filter \"@level:error\" --json"
echo "  railway var list --json"
echo "  railway deployment list --json"
