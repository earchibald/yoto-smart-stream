#!/bin/bash
# Example: Health check all Railway environments
# This script demonstrates using get_deployment_endpoint.py to verify deployments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GET_ENDPOINT_SCRIPT="$SCRIPT_DIR/get_deployment_endpoint.py"

echo "🚀 Railway Deployment Health Check"
echo "===================================="
echo ""

# List of environments to check
ENVIRONMENTS=("production" "develop")

for ENV in "${ENVIRONMENTS[@]}"; do
    echo "Checking $ENV environment..."

    # Get the endpoint URL
    URL=$(python "$GET_ENDPOINT_SCRIPT" --environment "$ENV" --url-only 2>&1)

    if [ $? -eq 0 ]; then
        echo "  ✓ URL: $URL"

        # Try to hit the health endpoint
        if curl -s -f -m 10 "$URL/api/health" > /dev/null 2>&1; then
            echo "  ✓ Health check: PASSED"
        else
            echo "  ✗ Health check: FAILED"
        fi
    else
        echo "  ✗ Failed to get endpoint URL"
        echo "    Error: $URL"
    fi

    echo ""
done

echo "===================================="
echo "Health check complete!"
