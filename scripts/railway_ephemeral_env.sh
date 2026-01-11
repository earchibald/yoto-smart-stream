#!/bin/bash
# Railway Ephemeral Environment Management Script
# This script manages lifecycle of ephemeral Railway environments for PR sessions
# Usage: ./railway_ephemeral_env.sh [create|deploy|test|destroy|status] [env-name]

set -e  # Exit on error

SCRIPT_NAME="Railway Ephemeral Environment Manager"
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

# Check if Railway CLI is installed
check_railway_cli() {
    if ! command -v railway &> /dev/null; then
        log_error "Railway CLI is not installed"
        log_info "Install with: npm i -g @railway/cli"
        exit 1
    fi
    log_success "Railway CLI is available"
}

# Check if authenticated with Railway
check_railway_auth() {
    if [ -z "$RAILWAY_TOKEN" ]; then
        log_warning "RAILWAY_TOKEN not set in environment"
        if ! railway whoami &> /dev/null; then
            log_error "Not authenticated with Railway"
            log_info "Run: railway login OR set RAILWAY_TOKEN environment variable"
            exit 1
        fi
        log_success "Authenticated via Railway CLI"
    else
        log_success "Using RAILWAY_TOKEN from environment"
    fi
}

# Create ephemeral environment
create_environment() {
    local ENV_NAME="$1"
    
    log_info "Creating ephemeral environment: $ENV_NAME"
    
    # Note: Railway CLI doesn't directly support environment creation
    # Environments are typically created via Railway Dashboard or API
    # For automation, we use a naming convention: pr-{number} or copilot-{id}
    
    log_info "Environment name: $ENV_NAME"
    log_info "This environment should be created in Railway Dashboard with:"
    log_info "  - Name: $ENV_NAME"
    log_info "  - Type: Ephemeral"
    log_info "  - Auto-destroy: Enabled"
    
    # Verify the environment exists or can be accessed
    if railway status -e "$ENV_NAME" &> /dev/null; then
        log_success "Environment '$ENV_NAME' is accessible"
        return 0
    else
        log_warning "Environment '$ENV_NAME' may not exist yet"
        log_info "Railway will create it on first deployment"
        return 0
    fi
}

# Deploy to ephemeral environment
deploy_environment() {
    local ENV_NAME="$1"
    
    log_info "Deploying to ephemeral environment: $ENV_NAME"
    
    # Set environment-specific variables
    log_info "Setting environment variables for $ENV_NAME..."
    # Note: ENVIRONMENT is now auto-populated from RAILWAY_ENVIRONMENT_NAME
    railway variables set DEBUG="true" -e "$ENV_NAME" || log_warning "Could not set DEBUG variable"
    railway variables set LOG_LEVEL="debug" -e "$ENV_NAME" || log_warning "Could not set LOG_LEVEL variable"
    
    # Copy secrets from GitHub Actions if available
    if [ -n "$YOTO_CLIENT_ID" ]; then
        log_info "Syncing YOTO_CLIENT_ID to Railway..."
        railway variables set YOTO_CLIENT_ID="$YOTO_CLIENT_ID" -e "$ENV_NAME" || log_warning "Could not sync YOTO_CLIENT_ID"
    fi
    
    # Deploy the application
    log_info "Deploying application..."
    if railway up -e "$ENV_NAME"; then
        log_success "Deployment successful!"
        
        # Get deployment URL
        log_info "Fetching deployment URL..."
        railway status -e "$ENV_NAME" || log_warning "Could not fetch status"
        
        return 0
    else
        log_error "Deployment failed!"
        return 1
    fi
}

# Test ephemeral environment
test_environment() {
    local ENV_NAME="$1"
    
    log_info "Testing ephemeral environment: $ENV_NAME"
    
    # Get the deployment URL
    log_info "Checking deployment status..."
    railway status -e "$ENV_NAME"
    
    # Wait for deployment to be ready
    log_info "Waiting for deployment to be ready..."
    sleep 10
    
    # Get logs to check for errors
    log_info "Checking recent logs for errors..."
    railway logs -e "$ENV_NAME" --tail 50 || log_warning "Could not fetch logs"
    
    log_success "Environment test complete"
    log_info "To test manually, get the URL from Railway dashboard"
    log_info "Or run: railway open -e $ENV_NAME"
}

# Get environment status
status_environment() {
    local ENV_NAME="$1"
    
    log_info "Getting status for environment: $ENV_NAME"
    
    railway status -e "$ENV_NAME" || log_error "Could not get status"
    
    log_info "Recent logs:"
    railway logs -e "$ENV_NAME" --tail 20 || log_warning "Could not fetch logs"
}

# Destroy ephemeral environment
destroy_environment() {
    local ENV_NAME="$1"
    
    log_info "Destroying ephemeral environment: $ENV_NAME"
    
    # Stop the environment
    log_info "Stopping services in $ENV_NAME..."
    if railway down -e "$ENV_NAME"; then
        log_success "Environment '$ENV_NAME' stopped successfully"
    else
        log_warning "Could not stop environment (it may not exist or already be stopped)"
    fi
    
    log_info "Note: Complete environment deletion must be done via Railway Dashboard"
    log_info "Railway Dashboard → Project → Environments → $ENV_NAME → Delete"
    
    log_success "Ephemeral environment cleanup initiated"
}

# Show usage
show_usage() {
    cat << EOF
$SCRIPT_NAME v$VERSION

Manage ephemeral Railway environments for PR and Copilot sessions

USAGE:
    $0 [COMMAND] [ENVIRONMENT_NAME]

COMMANDS:
    create ENV_NAME    Create a new ephemeral environment
    deploy ENV_NAME    Deploy application to environment
    test ENV_NAME      Test the deployed environment
    status ENV_NAME    Get environment status and logs
    destroy ENV_NAME   Destroy the ephemeral environment
    help               Show this help message

ENVIRONMENT_NAME:
    Naming convention:
    - PR environments: pr-{number} (e.g., pr-123)
    - Copilot sessions: copilot-{session-id} (e.g., copilot-abc123)

EXAMPLES:
    # Create and deploy for PR #123
    $0 create pr-123
    $0 deploy pr-123
    $0 test pr-123
    
    # Create and deploy for Copilot session
    $0 create copilot-session-abc123
    $0 deploy copilot-session-abc123
    
    # Check status
    $0 status pr-123
    
    # Cleanup when done
    $0 destroy pr-123

ENVIRONMENT VARIABLES:
    RAILWAY_TOKEN      Railway API token (required for CI/CD)
    YOTO_CLIENT_ID     Yoto API client ID (synced to Railway)

AUTHENTICATION:
    - For local use: Run 'railway login' first
    - For CI/CD: Set RAILWAY_TOKEN environment variable
    - For GitHub Codespaces: RAILWAY_TOKEN should be set as a Codespace secret

EOF
}

# Main script logic
main() {
    local COMMAND="${1:-help}"
    local ENV_NAME="$2"
    
    case "$COMMAND" in
        create)
            if [ -z "$ENV_NAME" ]; then
                log_error "Environment name is required"
                show_usage
                exit 1
            fi
            check_railway_cli
            check_railway_auth
            create_environment "$ENV_NAME"
            ;;
        deploy)
            if [ -z "$ENV_NAME" ]; then
                log_error "Environment name is required"
                show_usage
                exit 1
            fi
            check_railway_cli
            check_railway_auth
            deploy_environment "$ENV_NAME"
            ;;
        test)
            if [ -z "$ENV_NAME" ]; then
                log_error "Environment name is required"
                show_usage
                exit 1
            fi
            check_railway_cli
            check_railway_auth
            test_environment "$ENV_NAME"
            ;;
        status)
            if [ -z "$ENV_NAME" ]; then
                log_error "Environment name is required"
                show_usage
                exit 1
            fi
            check_railway_cli
            check_railway_auth
            status_environment "$ENV_NAME"
            ;;
        destroy)
            if [ -z "$ENV_NAME" ]; then
                log_error "Environment name is required"
                show_usage
                exit 1
            fi
            check_railway_cli
            check_railway_auth
            destroy_environment "$ENV_NAME"
            ;;
        help|--help|-h)
            show_usage
            exit 0
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
