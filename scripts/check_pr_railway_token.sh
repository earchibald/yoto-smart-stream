#!/bin/bash
# Check if Railway Token is Provisioned for PR Environment
# This script verifies if a PR environment has the required Railway tokens
# for Cloud Agent access

set -e

SCRIPT_NAME="Check PR Railway Token"
VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Show usage
show_usage() {
    cat << EOF
$SCRIPT_NAME v$VERSION

Check if Railway tokens are provisioned for a PR environment.

USAGE:
    $0 [PR_NUMBER]

ARGUMENTS:
    PR_NUMBER       PR number to check (optional, will auto-detect if not provided)

DESCRIPTION:
    This script checks if the required Railway tokens (RAILWAY_TOKEN and
    RAILWAY_API_TOKEN) are configured in the PR's Railway environment.

EXAMPLES:
    # Auto-detect PR from current branch
    $0

    # Check specific PR
    $0 123

EXIT CODES:
    0   Tokens are properly configured
    1   Tokens are missing or configuration error
    2   Script usage error

EOF
}

# Get PR number
get_pr_number() {
    local pr_num="$1"

    if [ -n "$pr_num" ]; then
        echo "$pr_num"
        return 0
    fi

    # Try to auto-detect from current branch if gh CLI is available
    if command -v gh &> /dev/null; then
        pr_num=$(gh pr view --json number -q .number 2>/dev/null || echo "")
        if [ -n "$pr_num" ]; then
            echo "$pr_num"
            return 0
        fi
    fi

    # Check if we're in GitHub Actions PR context
    if [[ "$GITHUB_REF" =~ refs/pull/([0-9]+)/merge ]]; then
        pr_num="${BASH_REMATCH[1]}"
        echo "$pr_num"
        return 0
    fi

    # Could not detect
    return 1
}

# Main check function
check_pr_tokens() {
    local pr_number="$1"

    if [ -z "$pr_number" ]; then
        log_error "PR number is required"
        echo ""
        show_usage
        exit 2
    fi

    local pr_env="pr-${pr_number}"

    echo ""
    log_info "Checking Railway tokens for PR #${pr_number}"
    log_info "Environment: $pr_env"
    echo ""

    # Check Railway CLI
    if ! command -v railway &> /dev/null; then
        log_error "Railway CLI is not installed"
        log_info "Install with: npm install -g @railway/cli"
        exit 1
    fi

    # Check Railway authentication
    if ! railway whoami &> /dev/null; then
        log_error "Not authenticated with Railway"
        log_info "Run: railway login"
        exit 1
    fi

    # Check if environment exists
    if ! railway status -e "$pr_env" &> /dev/null; then
        log_error "PR environment '$pr_env' does not exist in Railway"
        log_info "The PR may not have been deployed yet, or Railway PR Environments may not be enabled"
        exit 1
    fi

    log_success "PR environment exists: $pr_env"
    echo ""

    # Check for RAILWAY_TOKEN
    log_info "Checking RAILWAY_TOKEN..."
    if railway variables get RAILWAY_TOKEN -e "$pr_env" &> /dev/null; then
        local token_value=$(railway variables get RAILWAY_TOKEN -e "$pr_env" 2>/dev/null || echo "")
        if [ -n "$token_value" ] && [ "$token_value" != "null" ]; then
            log_success "RAILWAY_TOKEN is set"
        else
            log_warning "RAILWAY_TOKEN exists but is empty or null"
        fi
    else
        log_error "RAILWAY_TOKEN is not set"
        echo ""
        log_info "To provision Railway token for this PR:"
        log_info "  scripts/provision_pr_railway_token.sh --pr $pr_number"
        log_info ""
        log_info "Or see: docs/CLOUD_AGENT_RAILWAY_TOKENS.md"
        exit 1
    fi

    # Check for RAILWAY_API_TOKEN
    log_info "Checking RAILWAY_API_TOKEN..."
    if railway variables get RAILWAY_API_TOKEN -e "$pr_env" &> /dev/null; then
        local api_token_value=$(railway variables get RAILWAY_API_TOKEN -e "$pr_env" 2>/dev/null || echo "")
        if [ -n "$api_token_value" ] && [ "$api_token_value" != "null" ]; then
            log_success "RAILWAY_API_TOKEN is set"
        else
            log_warning "RAILWAY_API_TOKEN exists but is empty or null"
        fi
    else
        log_error "RAILWAY_API_TOKEN is not set"
        echo ""
        log_info "To provision Railway token for this PR:"
        log_info "  scripts/provision_pr_railway_token.sh --pr $pr_number"
        log_info ""
        log_info "Or see: docs/CLOUD_AGENT_RAILWAY_TOKENS.md"
        exit 1
    fi

    echo ""
    log_success "All required Railway tokens are configured for PR #${pr_number}"
    echo ""
    log_info "Cloud Agents can now:"
    log_info "  ✓ Deploy to the PR environment"
    log_info "  ✓ View environment-specific logs"
    log_info "  ✓ Manage environment variables"
    log_info "  ✓ Perform all Railway operations"
    echo ""

    exit 0
}

# Parse arguments
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_usage
    exit 0
fi

# Get PR number from argument or auto-detect
PR_NUMBER=$(get_pr_number "$1")

if [ -z "$PR_NUMBER" ]; then
    log_error "Could not determine PR number"
    echo ""
    log_info "Please provide PR number as argument:"
    log_info "  $0 <PR_NUMBER>"
    echo ""
    log_info "Or run from a PR branch with 'gh' CLI installed"
    echo ""
    exit 2
fi

# Run the check
check_pr_tokens "$PR_NUMBER"
