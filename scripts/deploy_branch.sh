#!/bin/bash
# Quick deployment script for Yoto Smart Stream
# Automatically detects the appropriate environment based on git branch
#
# Usage:
#   ./scripts/deploy_branch.sh                    # Auto-detect everything
#   ./scripts/deploy_branch.sh --environment prod # Override environment
#
# For copilot/* and copilot-* branches, this automatically creates
# branch-specific isolated CDK environments for testing.

set -e

# Change to repository root
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_debug() { echo -e "${BLUE}[DEBUG]${NC} $1"; }

# Get current branch
CURRENT_BRANCH=$(git branch --show-current)
print_info "Current branch: $CURRENT_BRANCH"

# Auto-detect environment
ENVIRONMENT=$(python3 scripts/get_deployment_environment.py)
print_info "Detected environment: $ENVIRONMENT"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            print_warn "Environment overridden to: $ENVIRONMENT"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  --environment, -e ENV    Override auto-detected environment"
            echo "  --help, -h              Show this help message"
            echo ""
            echo "Environment auto-detection:"
            echo "  copilot/* branches       -> Branch-specific environment"
            echo "  copilot-* branches       -> Branch-specific environment"
            echo "  aws-develop branch       -> dev"
            echo "  aws-main branch          -> prod"
            echo "  Other branches           -> dev"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Set default YOTO_CLIENT_ID if not already set
if [ -z "$YOTO_CLIENT_ID" ]; then
    YOTO_CLIENT_ID="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO"
    print_debug "Using default YOTO_CLIENT_ID"
fi

# Navigate to CDK directory
cd infrastructure/cdk

# Source Python virtual environment if it exists
if [ -d "../../cdk_venv" ]; then
    print_info "Activating Python virtual environment..."
    source ../../cdk_venv/bin/activate
elif [ -d ".venv" ]; then
    print_info "Activating Python virtual environment..."
    source .venv/bin/activate
else
    print_warn "No Python virtual environment found"
fi

# Display deployment information
print_info "=========================================="
print_info "Deployment Configuration"
print_info "=========================================="
print_info "Environment: $ENVIRONMENT"
print_info "Branch: $CURRENT_BRANCH"
print_info "Stack Name: YotoSmartStream-${ENVIRONMENT}"
print_info "YOTO_CLIENT_ID: ${YOTO_CLIENT_ID:0:10}..."
print_info "=========================================="

# Confirm for branch-specific deployments
if [[ "$CURRENT_BRANCH" == copilot/* ]] || [[ "$CURRENT_BRANCH" == copilot-* ]]; then
    print_warn "Creating BRANCH-SPECIFIC environment: $ENVIRONMENT"
    print_info "This will create isolated AWS resources for this branch."
    print_info "Remember to destroy this environment when done testing:"
    echo "  cdk destroy -c environment=$ENVIRONMENT"
    echo ""
    read -p "Continue with deployment? (y/N) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Deployment cancelled"
        exit 0
    fi
fi

# Deploy using CDK
print_info "Starting CDK deployment..."

cdk deploy \
  -c environment="$ENVIRONMENT" \
  -c yoto_client_id="$YOTO_CLIENT_ID" \
  -c enable_mqtt=true \
  -c enable_cloudfront=false \
  --require-approval never

print_info "=========================================="
print_info "Deployment Complete!"
print_info "=========================================="
print_info "Stack: YotoSmartStream-${ENVIRONMENT}"
print_info ""
print_info "To view stack outputs:"
echo "  aws cloudformation describe-stacks --stack-name YotoSmartStream-${ENVIRONMENT} --query 'Stacks[0].Outputs'"
print_info ""
print_info "To destroy this environment when done:"
echo "  cdk destroy -c environment=$ENVIRONMENT"
