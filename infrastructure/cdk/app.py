#!/usr/bin/env python3
"""
Yoto Smart Stream AWS CDK Application
Architecture 1: Lambda + Fargate Spot + DynamoDB + S3
"""
import os
import aws_cdk as cdk
from cdk.cdk_stack import YotoSmartStreamStack


app = cdk.App()

# Get configuration from context or environment
environment = app.node.try_get_context("environment") or os.getenv("ENVIRONMENT", "dev")
yoto_client_id = app.node.try_get_context("yoto_client_id") or os.getenv("YOTO_CLIENT_ID")
enable_mqtt = app.node.try_get_context("enable_mqtt") != "false"
enable_cloudfront = app.node.try_get_context("enable_cloudfront") == "true"

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
    env=env,
    description=f"Yoto Smart Stream {environment} environment - Architecture 1 (Lambda + Fargate Spot)",
    tags={
        "Project": "yoto-smart-stream",
        "Environment": environment,
        "ManagedBy": "CDK",
    },
)

app.synth()
