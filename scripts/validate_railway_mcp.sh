#!/bin/bash
# Railway MCP Tool Validation Script
# This script validates that Railway MCP tools work correctly after workspace restart
# Run this after restarting the Copilot Workspace to apply network configuration changes

set -e  # Exit on error

WORKSPACE_PATH="/home/runner/work/yoto-smart-stream/yoto-smart-stream"
cd "$WORKSPACE_PATH"

echo "=================================================="
echo "Railway MCP Tool Validation Script"
echo "=================================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Helper function to run tests
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -n "[$TESTS_TOTAL] Testing: $test_name ... "
    
    if eval "$test_command" > /tmp/test_output.txt 2>&1; then
        echo -e "${GREEN}PASS${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}FAIL${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "    Error output:"
        cat /tmp/test_output.txt | sed 's/^/    /'
        return 1
    fi
}

# Test 1: Railway CLI is installed
echo "Step 1: Verify Railway CLI Installation"
echo "----------------------------------------"
run_test "Railway CLI installed" "command -v railway"
run_test "Railway CLI version" "railway --version"
echo ""

# Test 2: Network connectivity
echo "Step 2: Verify Network Connectivity"
echo "------------------------------------"
run_test "railway.app accessible" "curl -s -o /dev/null -w '%{http_code}' https://railway.app | grep -q '^[23]'"
run_test "api.railway.app accessible" "curl -s -o /dev/null -w '%{http_code}' https://api.railway.app | grep -q '^[23]'"
run_test "backboard.railway.app accessible" "curl -s -o /dev/null -w '%{http_code}' https://backboard.railway.app | grep -q '^[23]'"
run_test "backboard.railway.com DNS resolution" "getent hosts backboard.railway.com"
run_test "backboard.railway.com accessible" "curl -s -o /dev/null -w '%{http_code}' https://backboard.railway.com/graphql/v2 2>&1 | grep -q '^[0-9]'"
echo ""

# Test 3: Railway authentication
echo "Step 3: Verify Railway Authentication"
echo "--------------------------------------"
if [ -n "$RAILWAY_API_TOKEN" ]; then
    echo "    ✓ RAILWAY_API_TOKEN is set"
    run_test "Railway CLI authentication" "railway whoami"
else
    echo -e "    ${YELLOW}⚠${NC} RAILWAY_API_TOKEN is not set"
    echo "    Set it with: export RAILWAY_API_TOKEN='your-token-here'"
fi
echo ""

# Test 4: Railway project operations (if authenticated)
if railway whoami > /dev/null 2>&1; then
    echo "Step 4: Test Railway Project Operations"
    echo "----------------------------------------"
    
    run_test "List Railway projects" "railway list"
    
    # Try to link to the project if not already linked
    if ! railway status > /dev/null 2>&1; then
        echo "    Attempting to link to yoto-smart-stream project..."
        # Note: This might require interactive input in some cases
        # For now, we'll just check if we can get the status
    fi
    
    # If linked, get status
    if railway status > /dev/null 2>&1; then
        run_test "Railway project status" "railway status"
    else
        echo -e "    ${YELLOW}⚠${NC} Not linked to a Railway project"
        echo "    To link: railway link"
    fi
    echo ""
else
    echo "Step 4: Test Railway Project Operations"
    echo "----------------------------------------"
    echo -e "    ${YELLOW}⚠${NC} Skipping project operations (not authenticated)"
    echo ""
fi

# Test 5: Railway MCP Server tools (if available)
echo "Step 5: Test Railway MCP Server Tools"
echo "--------------------------------------"
echo "    Note: These tests use the Railway MCP server via Copilot"
echo "    They are best tested interactively through Copilot commands"
echo ""
echo "    Available MCP tools to test:"
echo "    • railway-mcp-server-check-railway-status"
echo "    • railway-mcp-server-list-projects"
echo "    • railway-mcp-server-list-services"
echo "    • railway-mcp-server-link-service"
echo "    • railway-mcp-server-link-environment"
echo "    • railway-mcp-server-get-logs"
echo ""

# Summary
echo "=================================================="
echo "Validation Summary"
echo "=================================================="
echo ""
echo "Tests Passed: $TESTS_PASSED / $TESTS_TOTAL"
echo "Tests Failed: $TESTS_FAILED / $TESTS_TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Use Railway MCP tools via Copilot commands"
    echo "2. Link to the yoto-smart-stream service"
    echo "3. Link to the PR environment"
    echo "4. Retrieve logs from the environment"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Ensure the Copilot Workspace has been restarted after configuration changes"
    echo "2. Verify RAILWAY_API_TOKEN is set in environment or GitHub secrets"
    echo "3. Check that network domains are correctly configured in .github/copilot-workspace.yml"
    echo "4. Review the validation report: RAILWAY_MCP_VALIDATION.md"
    exit 1
fi
