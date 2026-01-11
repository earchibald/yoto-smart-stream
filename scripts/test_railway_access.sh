#!/bin/bash
# Test script to verify Copilot Workspace can access Railway URLs
# Run this after the copilot-workspace.yml configuration is deployed

echo "Testing Railway URL Access Configuration"
echo "=========================================="
echo ""

# Test function
test_url() {
    local url=$1
    local description=$2
    
    echo -n "Testing $description... "
    
    # Try to connect with a short timeout
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 --max-time 10 "$url" > /tmp/test_result 2>&1; then
        code=$(cat /tmp/test_result)
        if [ "$code" = "000" ]; then
            echo "❌ Cannot connect (blocked or unreachable)"
            return 1
        elif [ "$code" = "404" ] || [ "$code" = "200" ] || [ "$code" = "301" ] || [ "$code" = "302" ]; then
            echo "✅ Accessible (HTTP $code)"
            return 0
        else
            echo "⚠️  Got response (HTTP $code)"
            return 0
        fi
    else
        echo "❌ Connection failed"
        return 1
    fi
}

echo "Railway Platform URLs:"
test_url "https://railway.app" "Railway main site"
test_url "https://backboard.railway.app/graphql" "Railway GraphQL API"

echo ""
echo "Railway Deployment URLs (if deployed):"
test_url "https://yoto-smart-stream-production.up.railway.app/api/health" "Production health"
test_url "https://yoto-smart-stream-staging.up.railway.app/api/health" "Staging health"
test_url "https://yoto-smart-stream-development.up.railway.app/api/health" "Development health"

echo ""
echo "Yoto API URLs:"
test_url "https://yoto.dev" "Yoto Developer Portal"
test_url "https://api.yoto.io" "Yoto REST API"

echo ""
echo "=========================================="
echo "Test complete!"
echo ""
echo "Notes:"
echo "- HTTP 000: Domain might be blocked by network policy"
echo "- HTTP 404: URL accessible but endpoint not found (OK)"
echo "- HTTP 200/301/302: URL accessible and responding (OK)"
echo "- Connection failed: Network issue or service down"
echo ""
echo "If you see '000' or 'Connection failed' for Railway domains,"
echo "the copilot-workspace.yml configuration may not be active yet."
echo "Try restarting the Copilot Workspace session."
