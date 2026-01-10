#!/bin/bash
# Railway Deployment Script for Yoto Smart Stream
# This script helps deploy the application to Railway from the devcontainer

set -e  # Exit on error

echo "🚀 Railway Deployment Script"
echo "================================"

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Error: Railway CLI is not installed"
    echo "   Run: npm i -g @railway/cli"
    exit 1
fi

# Check if RAILWAY_TOKEN is set
if [ -z "$RAILWAY_TOKEN" ]; then
    echo "⚠️  RAILWAY_TOKEN not set in environment"
    echo "   You'll need to authenticate with 'railway login'"
    echo "   Or set RAILWAY_TOKEN for CI/CD automation"
    echo ""
fi

# Parse command line arguments
ENVIRONMENT="${1:-staging}"
DRY_RUN="${2:-}"

# Validate environment
if [ "$ENVIRONMENT" == "production" ]; then
    echo "❌ Error: Production deployments are not enabled yet"
    echo "   Only 'staging' and 'development' environments are supported"
    echo ""
    echo "Usage: $0 [staging|development] [--dry-run]"
    exit 1
fi

if [ "$ENVIRONMENT" != "staging" ] && [ "$ENVIRONMENT" != "development" ]; then
    echo "❌ Error: Invalid environment: $ENVIRONMENT"
    echo "   Supported: staging, development"
    echo ""
    echo "Usage: $0 [staging|development] [--dry-run]"
    exit 1
fi

echo "📦 Environment: $ENVIRONMENT"
echo "================================"

# Dry run mode - show what would happen
if [ "$DRY_RUN" == "--dry-run" ]; then
    echo "🔍 DRY RUN MODE - No actual deployment will occur"
    echo ""
    echo "Would execute:"
    echo "  1. Run tests: pytest tests/ -v"
    echo "  2. Check Railway login status"
    echo "  3. Deploy to Railway: railway up -e $ENVIRONMENT"
    echo "  4. Show deployment logs"
    echo ""
    exit 0
fi

# Step 1: Run tests before deploying
echo ""
echo "🧪 Running tests..."
echo "--------------------------------"
if ! pytest tests/ -v --tb=short; then
    echo "❌ Tests failed! Deployment aborted."
    exit 1
fi
echo "✅ Tests passed!"

# Step 2: Check Railway authentication
echo ""
echo "🔐 Checking Railway authentication..."
echo "--------------------------------"
if [ -z "$RAILWAY_TOKEN" ]; then
    # Check if user is logged in via CLI
    if ! railway whoami &> /dev/null; then
        echo "❌ Not authenticated with Railway"
        echo "   Run: railway login"
        exit 1
    fi
    echo "✅ Authenticated via Railway CLI"
else
    echo "✅ Using RAILWAY_TOKEN from environment"
fi

# Step 3: Verify railway.toml exists
if [ ! -f "railway.toml" ]; then
    echo "⚠️  Warning: railway.toml not found"
    echo "   Railway will use default Nixpacks configuration"
fi

# Step 4: Deploy to Railway
echo ""
echo "🚀 Deploying to Railway ($ENVIRONMENT)..."
echo "--------------------------------"
if railway up -e "$ENVIRONMENT"; then
    echo "✅ Deployment successful!"
else
    echo "❌ Deployment failed!"
    exit 1
fi

# Step 5: Show deployment status
echo ""
echo "📊 Deployment Status"
echo "--------------------------------"
railway status -e "$ENVIRONMENT" || echo "⚠️  Could not fetch status"

# Step 6: Show logs
echo ""
echo "📋 Recent Logs (last 50 lines)"
echo "--------------------------------"
echo "To follow logs in real-time, run:"
echo "  railway logs -e $ENVIRONMENT"
echo ""

# Success message
echo ""
echo "✅ Deployment Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "  1. Monitor logs: railway logs -e $ENVIRONMENT"
echo "  2. Check status: railway status -e $ENVIRONMENT"
echo "  3. Open dashboard: railway open -e $ENVIRONMENT"
echo ""
