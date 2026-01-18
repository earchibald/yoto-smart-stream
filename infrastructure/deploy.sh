#!/bin/bash
# Deploy Yoto Smart Stream to AWS using CDK
# Architecture 1: Lambda + Fargate Spot + DynamoDB + S3 + Cognito + Billing Alerts

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Function to auto-detect environment based on git branch
get_branch_environment() {
    local script_dir="$(cd "$(dirname "$0")/.." && pwd)"
    local env_script="$script_dir/scripts/get_deployment_environment.py"

    if [ -f "$env_script" ]; then
        python3 "$env_script"
    else
        echo "dev"
    fi
}

# Parse arguments
# If no environment is specified, auto-detect based on git branch
if [ -z "$1" ]; then
    ENVIRONMENT=$(get_branch_environment)
    print_info "Auto-detected environment from git branch: $ENVIRONMENT"
else
    ENVIRONMENT="$1"
fi

YOTO_CLIENT_ID="${2:-$YOTO_CLIENT_ID}"
BILLING_EMAIL="${3:-$BILLING_ALERT_EMAIL}"

if [ -z "$YOTO_CLIENT_ID" ]; then
    print_error "YOTO_CLIENT_ID is required"
    echo "Usage: $0 [environment] <yoto_client_id> [billing_email]"
    echo "  environment: dev, staging, prod, or omit to auto-detect from git branch"
    echo "  yoto_client_id: Your Yoto API client ID (or set YOTO_CLIENT_ID env var)"
    echo "  billing_email: Email for billing alerts (optional, or set BILLING_ALERT_EMAIL env var)"
    exit 1
fi

print_info "Deploying to environment: $ENVIRONMENT"

# Check AWS credentials
if [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
    print_error "AWS credentials not found"
    print_info "Please set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables"
    exit 1
fi

AWS_REGION="${AWS_REGION:-us-east-1}"
print_info "Using AWS region: $AWS_REGION"

# Billing alert configuration
if [ -n "$BILLING_EMAIL" ]; then
    print_info "Billing alerts will be sent to: $BILLING_EMAIL"
    BILLING_THRESHOLD="${BILLING_ALERT_THRESHOLD:-10.0}"
    print_info "Billing alert threshold: \$$BILLING_THRESHOLD"
else
    print_warn "No billing email provided. Billing alerts will not be configured."
    print_info "To enable billing alerts, set BILLING_ALERT_EMAIL environment variable or pass as 3rd argument"
fi

# Navigate to CDK directory
cd "$(dirname "$0")/cdk"

# Install CDK dependencies
print_info "Installing CDK dependencies..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install -q -r requirements.txt

# Bootstrap CDK (only needed once per account/region)
print_info "Checking CDK bootstrap status..."
if ! cdk bootstrap aws://unknown-account/$AWS_REGION 2>/dev/null; then
    print_info "Bootstrapping CDK..."
    cdk bootstrap
fi

# Package Lambda function
print_info "Packaging Lambda function..."
cd ../lambda
if [ -d "package" ]; then
    rm -rf package
fi
mkdir -p package

# Install Lambda dependencies
pip install -q -r requirements.txt -t package/

# Copy application code
cp -r ../../yoto_smart_stream package/
cp handler.py package/

# Return to CDK directory
cd ../cdk

# Synthesize CloudFormation template
print_info "Synthesizing CloudFormation template..."
SYNTH_ARGS="-c environment=\"$ENVIRONMENT\" -c yoto_client_id=\"$YOTO_CLIENT_ID\" -c enable_mqtt=\"true\" -c enable_cloudfront=\"false\""
if [ -n "$BILLING_EMAIL" ]; then
    SYNTH_ARGS="$SYNTH_ARGS -c billing_alert_email=\"$BILLING_EMAIL\" -c billing_alert_threshold=\"${BILLING_THRESHOLD:-10.0}\""
fi
eval "cdk synth $SYNTH_ARGS"

# Deploy stack
print_info "Deploying stack..."
DEPLOY_ARGS="-c environment=\"$ENVIRONMENT\" -c yoto_client_id=\"$YOTO_CLIENT_ID\" -c enable_mqtt=\"true\" -c enable_cloudfront=\"false\" --require-approval never"
if [ -n "$BILLING_EMAIL" ]; then
    DEPLOY_ARGS="$DEPLOY_ARGS -c billing_alert_email=\"$BILLING_EMAIL\" -c billing_alert_threshold=\"${BILLING_THRESHOLD:-10.0}\""
fi
eval "cdk deploy $DEPLOY_ARGS"

# Get outputs
print_info "Deployment complete!"
print_info "Getting stack outputs..."

STACK_NAME="YotoSmartStream-${ENVIRONMENT}"
API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='ApiUrl'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

DYNAMODB_TABLE=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='DynamoDBTableName'].OutputValue" \
    --output text \
    --region "$AWS_REGION")

print_info ""
print_info "==================================="
print_info "Deployment Summary"
print_info "==================================="
print_info "Environment: $ENVIRONMENT"
print_info "API URL: $API_URL"
print_info "DynamoDB Table: $DYNAMODB_TABLE"
print_info ""
print_info "Testing API endpoint..."
curl -f "$API_URL/api/health" && print_info "✓ API is responding" || print_warn "✗ API health check failed"

print_info ""
print_info "Next steps:"
print_info "1. Upload static UI files to S3"
print_info "2. Migrate data from existing database to DynamoDB"
print_info "3. Test all endpoints"
print_info "4. Update DNS to point to API URL"
