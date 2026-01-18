#!/usr/bin/env python3
"""
Yoto Smart Stream AWS CDK Application
Architecture 1: Lambda + Fargate Spot + DynamoDB + S3 + Cognito + Billing Alerts
"""
import os
import sys

import aws_cdk as cdk
from cdk.cdk_stack import YotoSmartStreamStack


def get_branch_based_environment() -> str:
    """
    Auto-detect the appropriate environment based on the current git branch.

    Returns:
        Environment name for CDK deployment
    """
    # Import the helper module from scripts
    scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "scripts")
    sys.path.insert(0, scripts_dir)

    try:
        from get_deployment_environment import get_deployment_environment

        return get_deployment_environment()
    except Exception as e:
        print(f"Warning: Could not auto-detect branch environment: {e}", file=sys.stderr)
        return "dev"


app = cdk.App()

# Get configuration from context or environment
# If no explicit environment is provided, auto-detect based on git branch
environment = (
    app.node.try_get_context("environment")
    or os.getenv("ENVIRONMENT")
    or get_branch_based_environment()
)
yoto_client_id = app.node.try_get_context("yoto_client_id") or os.getenv("YOTO_CLIENT_ID")
enable_mqtt = app.node.try_get_context("enable_mqtt") != "false"
enable_cloudfront = app.node.try_get_context("enable_cloudfront") == "true"

# Billing alert configuration
billing_alert_email = app.node.try_get_context("billing_alert_email") or os.getenv(
    "BILLING_ALERT_EMAIL"
)
billing_alert_threshold = float(
    app.node.try_get_context("billing_alert_threshold")
    or os.getenv("BILLING_ALERT_THRESHOLD", "10.0")
)

# AWS account and region from environment or default
aws_account = os.getenv("CDK_DEFAULT_ACCOUNT") or os.getenv("AWS_ACCOUNT_ID")
aws_region = os.getenv("CDK_DEFAULT_REGION") or os.getenv("AWS_REGION", "us-east-1")

# Create environment configuration
env = cdk.Environment(account=aws_account, region=aws_region) if aws_account else None

# Create stack
YotoSmartStreamStack(
    app,
    f"YotoSmartStream-{environment}",
    environment=environment,
    yoto_client_id=yoto_client_id,
    enable_mqtt=enable_mqtt,
    enable_cloudfront=enable_cloudfront,
    billing_alert_email=billing_alert_email,
    billing_alert_threshold=billing_alert_threshold,
    env=env,
    description=f"Yoto Smart Stream {environment} environment - Architecture 1 (Lambda + Fargate Spot + Cognito)",
    tags={
        "Project": "yoto-smart-stream",
        "Environment": environment,
        "ManagedBy": "CDK",
    },
)

app.synth()
