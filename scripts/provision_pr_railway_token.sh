#!/bin/bash
# Provision Railway Token for PR Environment
# This script assists users in setting up Railway tokens for PR environments
# to enable Cloud Agent access to Railway services

set -e

SCRIPT_NAME="Provision PR Railway Token"
VERSION="1.0.0"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_step() {
    echo -e "${CYAN}$1${NC}"
}

# Show banner
show_banner() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  $SCRIPT_NAME v$VERSION"
    echo "  Enable Cloud Agent Railway Access for PRs"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Check prerequisites
check_prerequisites() {
    log_step "Step 1/5: Checking prerequisites..."
    echo ""

    # Check Railway CLI
    if ! command -v railway &> /dev/null; then
        log_error "Railway CLI is not installed"
        log_info "Install with: npm install -g @railway/cli"
        exit 1
    fi
    log_success "Railway CLI is installed: $(railway --version)"

    # Check gh CLI (optional but helpful)
    if ! command -v gh &> /dev/null; then
        log_warning "GitHub CLI (gh) is not installed - some features limited"
        log_info "Install with: https://cli.github.com/"
    else
        log_success "GitHub CLI is installed: $(gh --version | head -1)"
    fi

    # Check Railway authentication
    if ! railway whoami &> /dev/null; then
        log_error "Not authenticated with Railway"
        log_info "Run: railway login"
        exit 1
    fi
    log_success "Authenticated to Railway as: $(railway whoami)"

    echo ""
    log_success "All prerequisites met"
    echo ""
}

# Get PR number
get_pr_number() {
    log_step "Step 2/5: Determining PR number..."
    echo ""

    # Try to auto-detect from current branch if gh CLI is available
    if command -v gh &> /dev/null; then
        PR_NUMBER=$(gh pr view --json number -q .number 2>/dev/null || echo "")
        if [ -n "$PR_NUMBER" ]; then
            log_success "Auto-detected PR number: $PR_NUMBER"
            echo ""

            # Show PR details
            log_info "PR Details:"
            gh pr view --json number,title,headRefName -q '"  • PR #\(.number): \(.title)\n  • Branch: \(.headRefName)"' 2>/dev/null || true
            echo ""

            # Confirm with user
            read -p "$(echo -e ${CYAN}Is this the correct PR? [Y/n]: ${NC})" confirm
            if [[ "$confirm" =~ ^[Nn] ]]; then
                PR_NUMBER=""
            fi
        fi
    fi

    # If not auto-detected or user said no, ask for PR number
    if [ -z "$PR_NUMBER" ]; then
        echo ""
        log_info "Available PRs:"
        if command -v gh &> /dev/null; then
            gh pr list --json number,title,headRefName -q '.[] | "  • PR #\(.number): \(.title) (\(.headRefName))"' || log_warning "Could not list PRs"
        else
            log_warning "Install 'gh' CLI to see PR list"
            log_info "Visit: https://github.com/earchibald/yoto-smart-stream/pulls"
        fi
        echo ""

        read -p "$(echo -e ${CYAN}Enter PR number: ${NC})" PR_NUMBER

        if ! [[ "$PR_NUMBER" =~ ^[0-9]+$ ]]; then
            log_error "Invalid PR number: $PR_NUMBER"
            exit 1
        fi
    fi

    PR_ENV_NAME="pr-${PR_NUMBER}"
    TOKEN_NAME="pr-${PR_NUMBER}-token"

    echo ""
    log_success "PR Number: $PR_NUMBER"
    log_info "PR Environment: $PR_ENV_NAME"
    log_info "Token Name: $TOKEN_NAME"
    echo ""
}

# Check if PR environment exists
check_pr_environment() {
    log_step "Step 3/5: Checking PR environment in Railway..."
    echo ""

    if railway status -e "$PR_ENV_NAME" &> /dev/null; then
        log_success "PR environment '$PR_ENV_NAME' exists in Railway"

        # Show environment info
        log_info "Environment status:"
        railway status -e "$PR_ENV_NAME" | head -10 || log_warning "Could not fetch full status"
    else
        log_error "PR environment '$PR_ENV_NAME' does not exist in Railway"
        log_info ""
        log_info "Possible reasons:"
        log_info "  1. PR was just opened - Railway may still be creating the environment"
        log_info "  2. Railway PR Environments feature is not enabled"
        log_info "  3. PR does not target a branch with Railway integration"
        log_info ""
        log_info "Solutions:"
        log_info "  • Wait a few minutes and try again"
        log_info "  • Check Railway dashboard: https://railway.app/dashboard"
        log_info "  • Verify PR Environments is enabled in Railway settings"
        exit 1
    fi
    echo ""
}

# Guide user through token creation
create_token() {
    log_step "Step 4/5: Creating Railway environment token..."
    echo ""

    log_warning "Token creation must be done via Railway UI (API limitation)"
    echo ""

    log_info "Follow these steps:"
    echo ""
    echo "  1. Open Railway token page:"
    echo -e "     ${BLUE}https://railway.app/account/tokens${NC}"
    echo ""
    echo "  2. Click 'Create Token'"
    echo ""
    echo "  3. Configure token:"
    echo -e "     • Name: ${GREEN}${TOKEN_NAME}${NC}"
    echo -e "     • Project: ${GREEN}yoto-smart-stream${NC}"
    echo -e "     • Environment: ${GREEN}${PR_ENV_NAME}${NC}"
    echo ""
    echo "  4. Click 'Create'"
    echo ""
    echo "  5. Copy the token (you'll only see it once!)"
    echo ""

    # Open browser if possible
    if command -v open &> /dev/null; then
        read -p "$(echo -e ${CYAN}Open Railway tokens page in browser? [Y/n]: ${NC})" open_browser
        if [[ ! "$open_browser" =~ ^[Nn] ]]; then
            open "https://railway.app/account/tokens" 2>/dev/null || log_warning "Could not open browser"
            log_info "Browser opened to Railway tokens page"
        fi
    elif command -v xdg-open &> /dev/null; then
        read -p "$(echo -e ${CYAN}Open Railway tokens page in browser? [Y/n]: ${NC})" open_browser
        if [[ ! "$open_browser" =~ ^[Nn] ]]; then
            xdg-open "https://railway.app/account/tokens" 2>/dev/null || log_warning "Could not open browser"
            log_info "Browser opened to Railway tokens page"
        fi
    fi

    echo ""
    read -p "$(echo -e ${CYAN}Press Enter when you have created and copied the token...${NC})"
    echo ""
}

# Set token in Railway environment
set_token() {
    log_step "Step 5/5: Setting token in Railway environment..."
    echo ""

    # Prompt for token (hidden input)
    log_info "Paste the Railway token you just created:"
    echo ""
    read -s -p "Token: " RAILWAY_TOKEN
    echo ""
    echo ""

    if [ -z "$RAILWAY_TOKEN" ]; then
        log_error "Token cannot be empty"
        exit 1
    fi

    # Validate token format (basic check)
    if [ ${#RAILWAY_TOKEN} -lt 20 ]; then
        log_error "Token seems too short - did you paste it correctly?"
        exit 1
    fi

    log_info "Setting RAILWAY_TOKEN in environment $PR_ENV_NAME..."
    if railway variables set RAILWAY_TOKEN="$RAILWAY_TOKEN" -e "$PR_ENV_NAME"; then
        log_success "RAILWAY_TOKEN set successfully"
    else
        log_error "Failed to set RAILWAY_TOKEN"
        exit 1
    fi

    log_info "Setting RAILWAY_API_TOKEN in environment $PR_ENV_NAME..."
    if railway variables set RAILWAY_API_TOKEN="$RAILWAY_TOKEN" -e "$PR_ENV_NAME"; then
        log_success "RAILWAY_API_TOKEN set successfully"
    else
        log_error "Failed to set RAILWAY_API_TOKEN"
        exit 1
    fi

    echo ""
    log_success "Token provisioned successfully!"
    echo ""
}

# Show completion message
show_completion() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_success "Railway Token Provisioned for PR #${PR_NUMBER}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    log_info "Summary:"
    echo "  • PR Number: $PR_NUMBER"
    echo "  • Environment: $PR_ENV_NAME"
    echo "  • Token Name: $TOKEN_NAME"
    echo "  • Variables Set: RAILWAY_TOKEN, RAILWAY_API_TOKEN"
    echo ""

    log_info "Next Steps:"
    echo "  1. Cloud Agent can now access Railway for this PR"
    echo "  2. Agent can deploy, view logs, manage variables"
    echo "  3. When PR is closed, remember to revoke the token:"
    echo "     https://railway.app/account/tokens"
    echo ""

    log_info "Verification:"
    echo "  # Check variables are set"
    echo "  railway variables -e $PR_ENV_NAME | grep RAILWAY"
    echo ""
    echo "  # Test authentication"
    echo "  RAILWAY_TOKEN=\"\$(railway variables get RAILWAY_TOKEN -e $PR_ENV_NAME)\" railway whoami"
    echo ""

    log_info "Documentation:"
    echo "  • Full guide: docs/CLOUD_AGENT_RAILWAY_TOKENS.md"
    echo "  • Railway setup: docs/RAILWAY_TOKEN_SETUP.md"
    echo ""

    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Show usage
show_usage() {
    cat << EOF
$SCRIPT_NAME v$VERSION

Provision Railway environment tokens for PR environments to enable Cloud Agent access.

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -p, --pr NUMBER     PR number (if not provided, will auto-detect or prompt)
    -h, --help          Show this help message

DESCRIPTION:
    This script helps you provision Railway tokens for PR environments. Railway
    tokens enable Cloud Agents (GitHub Copilot Workspace in Actions) to perform
    full Railway operations (deploy, logs, variables) for specific PRs.

WORKFLOW:
    1. Detects or prompts for PR number
    2. Verifies PR environment exists in Railway
    3. Guides you through creating a Railway token via UI
    4. Sets RAILWAY_TOKEN and RAILWAY_API_TOKEN in the PR environment

PREREQUISITES:
    • Railway CLI installed (npm install -g @railway/cli)
    • Authenticated to Railway (railway login)
    • GitHub CLI (optional, for PR auto-detection)

EXAMPLES:
    # Auto-detect PR from current branch
    $0

    # Specify PR number
    $0 --pr 123

TOKEN NAMING:
    Tokens should be named: pr-{NUMBER}-token
    Example: pr-123-token

CLEANUP:
    When PR is closed, revoke the token:
    https://railway.app/account/tokens

SEE ALSO:
    • docs/CLOUD_AGENT_RAILWAY_TOKENS.md
    • docs/RAILWAY_TOKEN_SETUP.md

EOF
}

# Main script
main() {
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -p|--pr)
                PR_NUMBER="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    show_banner
    check_prerequisites
    get_pr_number
    check_pr_environment
    create_token
    set_token
    show_completion
}

# Run main function
main "$@"
