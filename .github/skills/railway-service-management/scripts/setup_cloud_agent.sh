#!/bin/bash
# Railway CLI Setup for Cloud Agent Sessions
# Automatically detects and configures Railway CLI for this project

set -e

echo "🚀 Railway CLI Cloud Agent Setup"
echo ""

# 1. Auto-detect and set RAILWAY_TOKEN from RAILWAY_TOKEN_XX variables
if [ -z "$RAILWAY_TOKEN" ]; then
  echo "🔍 RAILWAY_TOKEN not set, checking for PR-specific tokens..."
  for var in $(env | grep '^RAILWAY_TOKEN_' | cut -d= -f1 2>/dev/null); do
    export RAILWAY_TOKEN="${!var}"
    echo "✅ Using $var as RAILWAY_TOKEN"
    break
  done
fi

if [ -z "$RAILWAY_TOKEN" ]; then
  echo "❌ Error: No Railway token found"
  echo "Expected RAILWAY_TOKEN or RAILWAY_TOKEN_XX environment variable"
  exit 1
fi

# 2. Auto-detect environment from GitHub context
if [[ "$GITHUB_REF" =~ refs/pull/([0-9]+)/merge ]]; then
  PR_NUMBER="${BASH_REMATCH[1]}"
  ENV_NAME="pr-${PR_NUMBER}"
  echo "📋 Detected PR #${PR_NUMBER} → Environment: ${ENV_NAME}"
elif [[ "$GITHUB_REF_NAME" =~ pr-([0-9]+) ]]; then
  PR_NUMBER="${BASH_REMATCH[1]}"
  ENV_NAME="pr-${PR_NUMBER}"
  echo "📋 Detected PR #${PR_NUMBER} from branch → Environment: ${ENV_NAME}"
elif [ "$GITHUB_REF" == "refs/heads/main" ]; then
  ENV_NAME="production"
  echo "📋 Detected main branch → Environment: ${ENV_NAME}"
else
  # Try to extract from token variable name
  for var in $(env | grep '^RAILWAY_TOKEN_' | cut -d= -f1 2>/dev/null); do
    if [[ "$var" =~ RAILWAY_TOKEN_([0-9]+) ]]; then
      PR_NUMBER="${BASH_REMATCH[1]}"
      ENV_NAME="pr-${PR_NUMBER}"
      echo "📋 Detected PR #${PR_NUMBER} from token → Environment: ${ENV_NAME}"
      break
    fi
  done

  if [ -z "$ENV_NAME" ]; then
    ENV_NAME="production"
    echo "📋 Using default → Environment: ${ENV_NAME}"
  fi
fi

# 3. Link service
echo ""
echo "🔗 Linking to service: yoto-smart-stream"
railway service link yoto-smart-stream 2>&1 | head -3 || echo "⚠️  May already be linked"

# 4. Link environment
echo ""
echo "🔗 Linking to environment: ${ENV_NAME}"
railway environment link "$ENV_NAME" 2>&1 | head -3 || echo "⚠️  May already be linked"

# 5. Verify setup
echo ""
echo "✅ Railway CLI configured for Cloud Agent"
echo ""
echo "Available commands:"
echo "  railway status --json"
echo "  railway logs --lines 50 --filter \"@level:error\" --json"
echo "  railway var list --json"
echo "  railway deployment list --json"
