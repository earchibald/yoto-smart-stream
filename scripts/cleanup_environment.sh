#!/bin/bash
# Cleanup script to destroy branch-specific CDK environments
# Usage:
#   ./scripts/cleanup_environment.sh                    # Auto-detect environment from current branch
#   ./scripts/cleanup_environment.sh copilot-test-pr123 # Destroy specific environment

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

# Parse command line arguments
if [ -z "$1" ]; then
    # Auto-detect environment
    CURRENT_BRANCH=$(git branch --show-current)
    ENVIRONMENT=$(python3 scripts/get_deployment_environment.py)
    print_info "Auto-detected environment from git branch: $ENVIRONMENT"
else
    ENVIRONMENT="$1"
    print_info "Using specified environment: $ENVIRONMENT"
fi

STACK_NAME="YotoSmartStream-${ENVIRONMENT}"

# Display cleanup information
print_warn "=========================================="
print_warn "Environment Cleanup"
print_warn "=========================================="
print_warn "Environment: $ENVIRONMENT"
print_warn "Stack Name: $STACK_NAME"
print_warn "=========================================="
print_warn ""
print_warn "This will PERMANENTLY DELETE all AWS resources for this environment:"
print_warn "  - Lambda functions"
print_warn "  - API Gateway"
print_warn "  - DynamoDB tables and data"
print_warn "  - S3 buckets (if empty)"
print_warn "  - ECS/Fargate services"
print_warn "  - Cognito user pools"
print_warn "  - All associated resources"
print_warn ""

# Confirm deletion
read -p "Are you sure you want to destroy this environment? Type 'yes' to confirm: " -r
echo ""
if [[ ! $REPLY == "yes" ]]; then
    print_info "Cleanup cancelled"
    exit 0
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

# Check if stack exists
print_info "Checking if stack exists..."
if ! aws cloudformation describe-stacks --stack-name "$STACK_NAME" 2>/dev/null >/dev/null; then
    print_warn "Stack $STACK_NAME does not exist"
    print_info "Nothing to destroy"
    exit 0
fi

# Destroy the stack
print_info "Starting CDK stack destruction..."
print_info "This may take several minutes..."

cdk destroy \
  -c environment="$ENVIRONMENT" \
  -c yoto_client_id="Pcht77vFlFIWF9xro2oPUBEtCYJr8zuO" \
  --force

print_info "=========================================="
print_info "Cleanup Complete!"
print_info "=========================================="
print_info "Stack $STACK_NAME has been destroyed"
print_info ""
print_info "All AWS resources for environment '$ENVIRONMENT' have been removed."
