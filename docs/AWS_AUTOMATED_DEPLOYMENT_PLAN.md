# AWS Architecture 1: Automated Deployment Plan
# CI/CD for Production, Develop, and PR Environments

**Last Updated:** 2026-01-15  
**Architecture:** Architecture 1 (Minimal Cost - Lambda + Fargate Spot)  
**Purpose:** Automated deployment strategy for multi-environment AWS infrastructure

---

## Table of Contents

1. [Overview](#overview)
2. [Environment Strategy](#environment-strategy)
3. [Infrastructure as Code](#infrastructure-as-code)
4. [GitHub Actions Workflows](#github-actions-workflows)
5. [Environment Configuration](#environment-configuration)
6. [Deployment Process](#deployment-process)
7. [Secrets Management](#secrets-management)
8. [Testing Strategy](#testing-strategy)
9. [Rollback Procedures](#rollback-procedures)
10. [Cost Management](#cost-management)

---

## Overview

### Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Repository                         │
│                    (earchibald/yoto-smart-stream)                │
└────────────┬─────────────────────────────────────────────────────┘
             │
             ├─ main branch      ──► Production Environment
             ├─ develop branch   ──► Develop Environment  
             └─ PR branches      ──► Ephemeral PR Environments
                                     (pr-123, pr-124, etc.)

┌─────────────────────────────────────────────────────────────────┐
│                         AWS Account                              │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │   Production     │  │    Develop       │  │  PR-123       │ │
│  │                  │  │                  │  │  (Ephemeral)  │ │
│  │  Lambda: prod    │  │  Lambda: dev     │  │  Lambda: pr123│ │
│  │  Fargate: prod   │  │  Fargate: dev    │  │  Fargate: pr123│ │
│  │  DynamoDB: prod  │  │  DynamoDB: dev   │  │  DynamoDB:pr123│ │
│  │  S3: prod        │  │  S3: dev         │  │  S3: pr123    │ │
│  └──────────────────┘  └──────────────────┘  └───────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Infrastructure as Code:** All AWS resources defined in code (AWS SAM/CloudFormation)
2. **Immutable Deployments:** Each deployment creates new Lambda versions/Fargate tasks
3. **Automated Testing:** CI runs tests before any deployment
4. **Environment Isolation:** Each environment has separate AWS resources
5. **Cost Optimization:** PR environments auto-deleted after merge/close

---

## Environment Strategy

### Production Environment

**Purpose:** Stable, production-ready application  
**Branch:** `main`  
**Deployment Trigger:** Push to main (after merge)  
**AWS Resources:**
- Lambda Function: `yoto-api-prod`
- API Gateway: `yoto-api-prod`
- DynamoDB Table: `yoto-smart-stream-prod`
- S3 Buckets: `yoto-audio-prod`, `yoto-ui-prod`
- ECS Service: `yoto-mqtt-prod`
- CloudFront Distribution: `d123abc.cloudfront.net`

**Characteristics:**
- Always-on (no auto-deletion)
- Full monitoring and alerting
- Point-in-time recovery enabled
- Multi-AZ deployment for Fargate
- Cost: $6-8/month

### Develop Environment

**Purpose:** Integration testing and staging  
**Branch:** `develop`  
**Deployment Trigger:** Push to develop  
**AWS Resources:**
- Lambda Function: `yoto-api-dev`
- API Gateway: `yoto-api-dev`
- DynamoDB Table: `yoto-smart-stream-dev`
- S3 Buckets: `yoto-audio-dev`, `yoto-ui-dev`
- ECS Service: `yoto-mqtt-dev`
- CloudFront Distribution: `d456def.cloudfront.net`

**Characteristics:**
- Always-on (no auto-deletion)
- Reduced monitoring (cost savings)
- Daily backups only
- Single-AZ for Fargate (cost savings)
- Cost: $6-8/month

### PR Environments (Ephemeral)

**Purpose:** Isolated testing for pull requests  
**Branch:** Any PR branch  
**Deployment Trigger:** PR opened/synchronized  
**Deletion Trigger:** PR closed/merged  
**AWS Resources:**
- Lambda Function: `yoto-api-pr-{number}`
- API Gateway: `yoto-api-pr-{number}`
- DynamoDB Table: `yoto-smart-stream-pr-{number}`
- S3 Buckets: `yoto-audio-pr-{number}`, `yoto-ui-pr-{number}`
- ECS Service: `yoto-mqtt-pr-{number}`
- CloudFront Distribution: `dXXXpr{number}.cloudfront.net`

**Characteristics:**
- Auto-created on PR open
- Auto-deleted on PR close/merge
- Full environment (same as develop)
- Minimal monitoring
- No backups
- Single-AZ for Fargate
- Cost: $6-8/month per PR (prorated by hours active)

**Note:**
- PR environments are full-featured for comprehensive testing
- Include MQTT handler and CloudFront to match production
- Auto-cleanup within 1 hour of PR closure prevents runaway costs

---

## Infrastructure as Code

### AWS SAM Template Structure

```
infrastructure/
├── template.yaml              # Main SAM template
├── parameters/
│   ├── prod.json             # Production parameters
│   ├── dev.json              # Development parameters
│   └── pr-template.json      # PR environment template
├── lambda/
│   ├── handler.py            # Lambda handler
│   ├── requirements.txt      # Lambda dependencies
│   └── layers/               # Lambda layers
└── fargate/
    ├── Dockerfile            # MQTT handler container
    ├── mqtt_standalone.py    # MQTT application
    └── requirements.txt      # Container dependencies
```

### Master SAM Template

Create `infrastructure/template.yaml`:

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31
Description: Yoto Smart Stream - Architecture 1 (Minimal Cost)

Parameters:
  Environment:
    Type: String
    Description: Environment name (prod, dev, pr-123)
    AllowedPattern: ^(prod|dev|pr-\d+)$
  
  YotoClientId:
    Type: String
    Description: Yoto API Client ID
    NoEcho: true
  
  EnableMQTT:
    Type: String
    Description: Enable MQTT handler (Fargate)
    Default: 'true'
    AllowedValues: ['true', 'false']
  
  EnableCloudFront:
    Type: String
    Description: Enable CloudFront CDN
    Default: 'true'
    AllowedValues: ['true', 'false']

Conditions:
  IsProduction: !Equals [!Ref Environment, 'prod']
  IsDevelopment: !Equals [!Ref Environment, 'dev']
  IsPR: !Not [!Or [!Condition IsProduction, !Condition IsDevelopment]]
  EnableMQTTCondition: !Equals [!Ref EnableMQTT, 'true']
  EnableCloudFrontCondition: !Equals [!Ref EnableCloudFront, 'true']

Globals:
  Function:
    Runtime: python3.9
    Timeout: 30
    MemorySize: 1024
    Environment:
      Variables:
        ENVIRONMENT: !Ref Environment
        DYNAMODB_TABLE: !Ref DynamoDBTable
        S3_AUDIO_BUCKET: !Ref AudioBucket
        S3_UI_BUCKET: !Ref UIBucket
        YOTO_CLIENT_ID: !Ref YotoClientId
        AWS_REGION: !Ref AWS::Region

Resources:
  # API Gateway HTTP API
  HttpApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: !Ref Environment
      CorsConfiguration:
        AllowOrigins:
          - '*'
        AllowMethods:
          - GET
          - POST
          - PUT
          - DELETE
          - OPTIONS
        AllowHeaders:
          - '*'
      Tags:
        Environment: !Ref Environment
        Project: yoto-smart-stream

  # Lambda Function (API)
  ApiFunction:
    Type: AWS::Serverless::Function
    Properties:
      FunctionName: !Sub 'yoto-api-${Environment}'
      Handler: handler.handler
      CodeUri: ./lambda/
      Policies:
        - DynamoDBCrudPolicy:
            TableName: !Ref DynamoDBTable
        - S3ReadPolicy:
            BucketName: !Ref AudioBucket
        - S3CrudPolicy:
            BucketName: !Ref AudioBucket
        - S3ReadPolicy:
            BucketName: !Ref UIBucket
      Events:
        ApiEvent:
          Type: HttpApi
          Properties:
            ApiId: !Ref HttpApi
            Path: /{proxy+}
            Method: ANY
      Tags:
        Environment: !Ref Environment
        Project: yoto-smart-stream

  # DynamoDB Table
  DynamoDBTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: !Sub 'yoto-smart-stream-${Environment}'
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: PK
          AttributeType: S
        - AttributeName: SK
          AttributeType: S
      KeySchema:
        - AttributeName: PK
          KeyType: HASH
        - AttributeName: SK
          KeyType: RANGE
      PointInTimeRecoverySpecification:
        PointInTimeRecoveryEnabled: !If [IsProduction, true, false]
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Project
          Value: yoto-smart-stream

  # S3 Bucket for Audio
  AudioBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'yoto-audio-${Environment}-${AWS::AccountId}'
      CorsConfiguration:
        CorsRules:
          - AllowedOrigins: ['*']
            AllowedMethods: [GET, HEAD]
            AllowedHeaders: ['*']
            MaxAge: 3600
      VersioningConfiguration:
        Status: !If [IsProduction, Enabled, Suspended]
      LifecycleConfiguration:
        Rules:
          - Id: DeleteOldVersions
            Status: Enabled
            NoncurrentVersionExpirationInDays: 30
          - Id: DeletePRData
            Status: !If [IsPR, Enabled, Disabled]
            ExpirationInDays: 7
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Project
          Value: yoto-smart-stream

  # S3 Bucket for UI
  UIBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: !Sub 'yoto-ui-${Environment}-${AWS::AccountId}'
      WebsiteConfiguration:
        IndexDocument: index.html
        ErrorDocument: error.html
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Project
          Value: yoto-smart-stream

  # CloudFront Distribution (Optional)
  CloudFrontDistribution:
    Type: AWS::CloudFront::Distribution
    Condition: EnableCloudFrontCondition
    Properties:
      DistributionConfig:
        Enabled: true
        Comment: !Sub 'Yoto Smart Stream ${Environment}'
        Origins:
          - Id: UIBucketOrigin
            DomainName: !GetAtt UIBucket.RegionalDomainName
            S3OriginConfig:
              OriginAccessIdentity: ''
        DefaultCacheBehavior:
          TargetOriginId: UIBucketOrigin
          ViewerProtocolPolicy: redirect-to-https
          AllowedMethods: [GET, HEAD, OPTIONS]
          CachedMethods: [GET, HEAD]
          ForwardedValues:
            QueryString: false
            Cookies:
              Forward: none
          MinTTL: 0
          DefaultTTL: 3600
          MaxTTL: 86400
        PriceClass: PriceClass_100
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Project
          Value: yoto-smart-stream

  # ECS Cluster (MQTT)
  ECSCluster:
    Type: AWS::ECS::Cluster
    Condition: EnableMQTTCondition
    Properties:
      ClusterName: !Sub 'yoto-mqtt-${Environment}'
      CapacityProviders:
        - FARGATE_SPOT
      DefaultCapacityProviderStrategy:
        - CapacityProvider: FARGATE_SPOT
          Weight: 1
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Project
          Value: yoto-smart-stream

  # ECS Task Definition (MQTT)
  MQTTTaskDefinition:
    Type: AWS::ECS::TaskDefinition
    Condition: EnableMQTTCondition
    Properties:
      Family: !Sub 'yoto-mqtt-${Environment}'
      NetworkMode: awsvpc
      RequiresCompatibilities:
        - FARGATE
      Cpu: 256
      Memory: 512
      TaskRoleArn: !GetAtt MQTTTaskRole.Arn
      ExecutionRoleArn: !GetAtt MQTTExecutionRole.Arn
      ContainerDefinitions:
        - Name: mqtt-handler
          Image: !Sub '${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/yoto-mqtt:latest'
          Essential: true
          Environment:
            - Name: ENVIRONMENT
              Value: !Ref Environment
            - Name: YOTO_CLIENT_ID
              Value: !Ref YotoClientId
            - Name: DYNAMODB_TABLE
              Value: !Ref DynamoDBTable
            - Name: AWS_REGION
              Value: !Ref AWS::Region
          LogConfiguration:
            LogDriver: awslogs
            Options:
              awslogs-group: !Ref MQTTLogGroup
              awslogs-region: !Ref AWS::Region
              awslogs-stream-prefix: ecs
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Project
          Value: yoto-smart-stream

  # ECS Service (MQTT)
  MQTTService:
    Type: AWS::ECS::Service
    Condition: EnableMQTTCondition
    Properties:
      ServiceName: !Sub 'yoto-mqtt-${Environment}'
      Cluster: !Ref ECSCluster
      TaskDefinition: !Ref MQTTTaskDefinition
      DesiredCount: 1
      LaunchType: FARGATE
      NetworkConfiguration:
        AwsvpcConfiguration:
          Subnets:
            - !Ref PrivateSubnet
          SecurityGroups:
            - !Ref MQTTSecurityGroup
          AssignPublicIp: ENABLED
      Tags:
        - Key: Environment
          Value: !Ref Environment
        - Key: Project
          Value: yoto-smart-stream

  # IAM Roles
  MQTTTaskRole:
    Type: AWS::IAM::Role
    Condition: EnableMQTTCondition
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - !Ref MQTTTaskPolicy

  MQTTTaskPolicy:
    Type: AWS::IAM::ManagedPolicy
    Condition: EnableMQTTCondition
    Properties:
      PolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Action:
              - dynamodb:GetItem
              - dynamodb:PutItem
              - dynamodb:UpdateItem
              - dynamodb:Query
            Resource: !GetAtt DynamoDBTable.Arn

  MQTTExecutionRole:
    Type: AWS::IAM::Role
    Condition: EnableMQTTCondition
    Properties:
      AssumeRolePolicyDocument:
        Statement:
          - Effect: Allow
            Principal:
              Service: ecs-tasks.amazonaws.com
            Action: sts:AssumeRole
      ManagedPolicyArns:
        - arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy

  # CloudWatch Log Group
  MQTTLogGroup:
    Type: AWS::Logs::LogGroup
    Condition: EnableMQTTCondition
    Properties:
      LogGroupName: !Sub '/ecs/yoto-mqtt-${Environment}'
      RetentionInDays: !If [IsProduction, 30, 7]

  # VPC Resources (Simplified for MQTT)
  VPC:
    Type: AWS::EC2::VPC
    Condition: EnableMQTTCondition
    Properties:
      CidrBlock: 10.0.0.0/16
      EnableDnsHostnames: true
      EnableDnsSupport: true
      Tags:
        - Key: Name
          Value: !Sub 'yoto-vpc-${Environment}'

  PrivateSubnet:
    Type: AWS::EC2::Subnet
    Condition: EnableMQTTCondition
    Properties:
      VpcId: !Ref VPC
      CidrBlock: 10.0.1.0/24
      AvailabilityZone: !Select [0, !GetAZs '']
      Tags:
        - Key: Name
          Value: !Sub 'yoto-private-subnet-${Environment}'

  MQTTSecurityGroup:
    Type: AWS::EC2::SecurityGroup
    Condition: EnableMQTTCondition
    Properties:
      GroupDescription: Security group for MQTT handler
      VpcId: !Ref VPC
      SecurityGroupEgress:
        - IpProtocol: -1
          CidrIp: 0.0.0.0/0

Outputs:
  ApiUrl:
    Description: API Gateway endpoint URL
    Value: !Sub 'https://${HttpApi}.execute-api.${AWS::Region}.amazonaws.com/${Environment}'
    Export:
      Name: !Sub '${AWS::StackName}-ApiUrl'
  
  DynamoDBTableName:
    Description: DynamoDB table name
    Value: !Ref DynamoDBTable
    Export:
      Name: !Sub '${AWS::StackName}-DynamoDBTable'
  
  AudioBucketName:
    Description: S3 audio bucket name
    Value: !Ref AudioBucket
    Export:
      Name: !Sub '${AWS::StackName}-AudioBucket'
  
  UIBucketName:
    Description: S3 UI bucket name
    Value: !Ref UIBucket
    Export:
      Name: !Sub '${AWS::StackName}-UIBucket'
  
  CloudFrontUrl:
    Condition: EnableCloudFrontCondition
    Description: CloudFront distribution URL
    Value: !GetAtt CloudFrontDistribution.DomainName
    Export:
      Name: !Sub '${AWS::StackName}-CloudFrontUrl'
```

### Parameter Files

Create `infrastructure/parameters/prod.json`:
```json
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "prod"
  },
  {
    "ParameterKey": "EnableMQTT",
    "ParameterValue": "true"
  },
  {
    "ParameterKey": "EnableCloudFront",
    "ParameterValue": "true"
  }
]
```

Create `infrastructure/parameters/dev.json`:
```json
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "dev"
  },
  {
    "ParameterKey": "EnableMQTT",
    "ParameterValue": "true"
  },
  {
    "ParameterKey": "EnableCloudFront",
    "ParameterValue": "false"
  }
]
```

Create `infrastructure/parameters/pr-template.json`:
```json
[
  {
    "ParameterKey": "Environment",
    "ParameterValue": "pr-REPLACE_WITH_NUMBER"
  },
  {
    "ParameterKey": "EnableMQTT",
    "ParameterValue": "true"
  },
  {
    "ParameterKey": "EnableCloudFront",
    "ParameterValue": "true"
  }
]
```

---

## GitHub Actions Workflows

### Workflow 1: Deploy to Production

Create `.github/workflows/aws-deploy-production.yml`:

```yaml
name: Deploy to AWS Production

on:
  push:
    branches:
      - main
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ENVIRONMENT: prod

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linter
        run: ruff check .
      
      - name: Run formatter check
        run: black --check .
      
      - name: Run tests
        run: pytest tests/ -v --cov=yoto_smart_stream

  deploy:
    name: Deploy to Production
    runs-on: ubuntu-latest
    needs: test
    environment:
      name: production
      url: ${{ steps.deploy.outputs.api_url }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
      
      - name: Install AWS SAM CLI
        run: |
          pip install aws-sam-cli
      
      - name: Build Lambda package
        run: |
          cd infrastructure/lambda
          pip install -r requirements.txt -t package/
          cp handler.py package/
          cp -r ../../yoto_smart_stream package/
          cd package
          zip -r ../lambda-deployment.zip .
      
      - name: Build and push MQTT Docker image
        run: |
          # Login to ECR
          aws ecr get-login-password --region ${{ env.AWS_REGION }} | \
            docker login --username AWS --password-stdin \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com
          
          # Build and push
          cd infrastructure/fargate
          docker build -t yoto-mqtt:latest .
          docker tag yoto-mqtt:latest \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/yoto-mqtt:latest
          docker push \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/yoto-mqtt:latest
      
      - name: Deploy with SAM
        id: deploy
        run: |
          sam deploy \
            --template-file infrastructure/template.yaml \
            --stack-name yoto-smart-stream-prod \
            --parameter-overrides \
              Environment=prod \
              YotoClientId=${{ secrets.YOTO_CLIENT_ID }} \
              EnableMQTT=true \
              EnableCloudFront=true \
            --capabilities CAPABILITY_IAM \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset
          
          # Get API URL
          API_URL=$(aws cloudformation describe-stacks \
            --stack-name yoto-smart-stream-prod \
            --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
            --output text)
          echo "api_url=$API_URL" >> $GITHUB_OUTPUT
      
      - name: Upload static UI to S3
        run: |
          UI_BUCKET=$(aws cloudformation describe-stacks \
            --stack-name yoto-smart-stream-prod \
            --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
            --output text)
          aws s3 sync ./yoto_smart_stream/static/ s3://$UI_BUCKET/ \
            --cache-control "public, max-age=3600" \
            --delete
      
      - name: Test deployment
        run: |
          API_URL="${{ steps.deploy.outputs.api_url }}"
          echo "Testing $API_URL/api/health"
          curl -f $API_URL/api/health || exit 1
      
      - name: Create deployment summary
        run: |
          echo "## 🚀 Production Deployment Successful" >> $GITHUB_STEP_SUMMARY
          echo "" >> $GITHUB_STEP_SUMMARY
          echo "**API URL:** ${{ steps.deploy.outputs.api_url }}" >> $GITHUB_STEP_SUMMARY
          echo "**Environment:** production" >> $GITHUB_STEP_SUMMARY
          echo "**Region:** ${{ env.AWS_REGION }}" >> $GITHUB_STEP_SUMMARY
          echo "**Commit:** ${{ github.sha }}" >> $GITHUB_STEP_SUMMARY
```

### Workflow 2: Deploy to Develop

Create `.github/workflows/aws-deploy-develop.yml`:

```yaml
name: Deploy to AWS Develop

on:
  push:
    branches:
      - develop
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  ENVIRONMENT: dev

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linter
        run: ruff check .
      
      - name: Run tests
        run: pytest tests/ -v

  deploy:
    name: Deploy to Develop
    runs-on: ubuntu-latest
    needs: test
    environment:
      name: develop
      url: ${{ steps.deploy.outputs.api_url }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Install AWS SAM CLI
        run: pip install aws-sam-cli
      
      - name: Build Lambda package
        run: |
          cd infrastructure/lambda
          pip install -r requirements.txt -t package/
          cp handler.py package/
          cp -r ../../yoto_smart_stream package/
          cd package
          zip -r ../lambda-deployment.zip .
      
      - name: Build and push MQTT Docker image
        run: |
          aws ecr get-login-password --region ${{ env.AWS_REGION }} | \
            docker login --username AWS --password-stdin \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com
          
          cd infrastructure/fargate
          docker build -t yoto-mqtt:dev .
          docker tag yoto-mqtt:dev \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/yoto-mqtt:dev
          docker push \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/yoto-mqtt:dev
      
      - name: Deploy with SAM
        id: deploy
        run: |
          sam deploy \
            --template-file infrastructure/template.yaml \
            --stack-name yoto-smart-stream-dev \
            --parameter-overrides \
              Environment=dev \
              YotoClientId=${{ secrets.YOTO_CLIENT_ID }} \
              EnableMQTT=true \
              EnableCloudFront=false \
            --capabilities CAPABILITY_IAM \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset
          
          API_URL=$(aws cloudformation describe-stacks \
            --stack-name yoto-smart-stream-dev \
            --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
            --output text)
          echo "api_url=$API_URL" >> $GITHUB_OUTPUT
      
      - name: Upload static UI to S3
        run: |
          UI_BUCKET=$(aws cloudformation describe-stacks \
            --stack-name yoto-smart-stream-dev \
            --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
            --output text)
          aws s3 sync ./yoto_smart_stream/static/ s3://$UI_BUCKET/ --delete
```

### Workflow 3: Deploy PR Environments

Create `.github/workflows/aws-deploy-pr.yml`:

```yaml
name: Deploy PR Environment

on:
  pull_request:
    types: [opened, synchronize, reopened]
  workflow_dispatch:
    inputs:
      pr_number:
        description: 'PR number'
        required: true

env:
  AWS_REGION: us-east-1

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.9'
          cache: 'pip'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      
      - name: Run linter
        run: ruff check .
      
      - name: Run tests
        run: pytest tests/ -v

  deploy:
    name: Deploy PR Environment
    runs-on: ubuntu-latest
    needs: test
    environment:
      name: pr-${{ github.event.pull_request.number || github.event.inputs.pr_number }}
      url: ${{ steps.deploy.outputs.api_url }}
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set PR number
        id: pr
        run: |
          if [ "${{ github.event_name }}" == "pull_request" ]; then
            echo "number=${{ github.event.pull_request.number }}" >> $GITHUB_OUTPUT
          else
            echo "number=${{ github.event.inputs.pr_number }}" >> $GITHUB_OUTPUT
          fi
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Install AWS SAM CLI
        run: pip install aws-sam-cli
      
      - name: Build Lambda package
        run: |
          cd infrastructure/lambda
          pip install -r requirements.txt -t package/
          cp handler.py package/
          cp -r ../../yoto_smart_stream package/
          cd package
          zip -r ../lambda-deployment.zip .
      
      - name: Build and push MQTT Docker image
        run: |
          # Login to ECR
          aws ecr get-login-password --region ${{ env.AWS_REGION }} | \
            docker login --username AWS --password-stdin \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com
          
          # Build and push
          PR_NUM=${{ steps.pr.outputs.number }}
          cd infrastructure/fargate
          docker build -t yoto-mqtt:pr-${PR_NUM} .
          docker tag yoto-mqtt:pr-${PR_NUM} \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/yoto-mqtt:pr-${PR_NUM}
          docker push \
            ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com/yoto-mqtt:pr-${PR_NUM}
      
      - name: Deploy with SAM (full environment)
        id: deploy
        run: |
          PR_NUM=${{ steps.pr.outputs.number }}
          
          sam deploy \
            --template-file infrastructure/template.yaml \
            --stack-name yoto-smart-stream-pr-${PR_NUM} \
            --parameter-overrides \
              Environment=pr-${PR_NUM} \
              YotoClientId=${{ secrets.YOTO_CLIENT_ID }} \
              EnableMQTT=true \
              EnableCloudFront=true \
            --capabilities CAPABILITY_IAM \
            --no-confirm-changeset \
            --no-fail-on-empty-changeset \
            --tags \
              Environment=pr-${PR_NUM} \
              PR=${PR_NUM} \
              AutoDelete=true
          
          API_URL=$(aws cloudformation describe-stacks \
            --stack-name yoto-smart-stream-pr-${PR_NUM} \
            --query 'Stacks[0].Outputs[?OutputKey==`ApiUrl`].OutputValue' \
            --output text)
          echo "api_url=$API_URL" >> $GITHUB_OUTPUT
      
      - name: Upload static UI to S3
        run: |
          PR_NUM=${{ steps.pr.outputs.number }}
          UI_BUCKET=$(aws cloudformation describe-stacks \
            --stack-name yoto-smart-stream-pr-${PR_NUM} \
            --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
            --output text)
          aws s3 sync ./yoto_smart_stream/static/ s3://$UI_BUCKET/ --delete
      
      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const prNumber = ${{ steps.pr.outputs.number }};
            const apiUrl = '${{ steps.deploy.outputs.api_url }}';
            
            const body = `## 🚀 PR Environment Deployed
            
            Your changes have been deployed to a full AWS environment:
            
            **API URL:** ${apiUrl}
            **Environment:** pr-${prNumber}
            **Type:** Full environment (Lambda + Fargate + DynamoDB + S3 + CloudFront)
            
            ### Test Your Changes
            \`\`\`bash
            curl ${apiUrl}/api/health
            \`\`\`
            
            ### Features
            - ✅ Full API (Lambda + API Gateway)
            - ✅ MQTT handler (Fargate Spot)
            - ✅ Database (DynamoDB)
            - ✅ Storage (S3 + CloudFront)
            - ✅ Matches production environment
            
            ### Cost Info
            - This environment costs ~$6-8/month (prorated by hours)
            - Full stack for comprehensive testing
            - Environment will be auto-deleted when PR is closed
            
            ### Notes
            - Cold starts expected (2-5 seconds on first request)
            - Subsequent requests fast (<100ms)
            - MQTT events fully functional
            `;
            
            github.rest.issues.createComment({
              issue_number: prNumber,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

### Workflow 4: Cleanup PR Environments

Create `.github/workflows/aws-cleanup-pr.yml`:

```yaml
name: Cleanup PR Environment

on:
  pull_request:
    types: [closed]

env:
  AWS_REGION: us-east-1

jobs:
  cleanup:
    name: Delete PR Environment
    runs-on: ubuntu-latest
    
    steps:
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Delete CloudFormation stack
        run: |
          PR_NUM=${{ github.event.pull_request.number }}
          STACK_NAME="yoto-smart-stream-pr-${PR_NUM}"
          
          echo "Deleting stack: $STACK_NAME"
          
          # Check if stack exists
          if aws cloudformation describe-stacks --stack-name $STACK_NAME 2>/dev/null; then
            # Empty S3 buckets first (required before deletion)
            AUDIO_BUCKET=$(aws cloudformation describe-stacks \
              --stack-name $STACK_NAME \
              --query 'Stacks[0].Outputs[?OutputKey==`AudioBucketName`].OutputValue' \
              --output text)
            
            UI_BUCKET=$(aws cloudformation describe-stacks \
              --stack-name $STACK_NAME \
              --query 'Stacks[0].Outputs[?OutputKey==`UIBucketName`].OutputValue' \
              --output text)
            
            if [ -n "$AUDIO_BUCKET" ]; then
              echo "Emptying audio bucket: $AUDIO_BUCKET"
              aws s3 rm s3://$AUDIO_BUCKET --recursive || true
            fi
            
            if [ -n "$UI_BUCKET" ]; then
              echo "Emptying UI bucket: $UI_BUCKET"
              aws s3 rm s3://$UI_BUCKET --recursive || true
            fi
            
            # Delete stack
            aws cloudformation delete-stack --stack-name $STACK_NAME
            
            # Wait for deletion (max 10 minutes)
            aws cloudformation wait stack-delete-complete \
              --stack-name $STACK_NAME \
              --timeout 600 || echo "Stack deletion timeout or failed"
            
            echo "✓ PR environment cleaned up"
          else
            echo "Stack $STACK_NAME does not exist, nothing to clean up"
          fi
      
      - name: Comment on PR
        uses: actions/github-script@v7
        with:
          script: |
            const prNumber = ${{ github.event.pull_request.number }};
            
            const body = `## 🧹 PR Environment Cleaned Up
            
            The ephemeral AWS environment for PR #${prNumber} has been deleted.
            
            - Lambda function removed
            - DynamoDB table removed
            - S3 buckets emptied and removed
            - API Gateway removed
            
            **Cost saved:** ~$0.10/day
            `;
            
            github.rest.issues.createComment({
              issue_number: prNumber,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: body
            });
```

---

## Environment Configuration

### GitHub Secrets Required

Configure these secrets in GitHub repository settings (`Settings` → `Secrets and variables` → `Actions`):

**AWS Credentials:**
- `AWS_ACCESS_KEY_ID` - AWS access key with deployment permissions
- `AWS_SECRET_ACCESS_KEY` - AWS secret key
- `AWS_ACCOUNT_ID` - Your AWS account ID (12 digits)

**Application Secrets:**
- `YOTO_CLIENT_ID` - Yoto API client ID

### AWS IAM Permissions

Create IAM user with these permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "cloudformation:*",
        "lambda:*",
        "apigateway:*",
        "dynamodb:*",
        "s3:*",
        "ecs:*",
        "ecr:*",
        "ec2:Describe*",
        "ec2:Create*",
        "ec2:Delete*",
        "iam:*",
        "logs:*",
        "cloudfront:*"
      ],
      "Resource": "*"
    }
  ]
}
```

---

## Deployment Process

### Initial Setup (One-Time)

```bash
# 1. Create ECR repository for MQTT container
aws ecr create-repository --repository-name yoto-mqtt

# 2. Create GitHub secrets
# (Done in GitHub UI)

# 3. Push initial commit to trigger deployment
git checkout -b develop
git push origin develop
```

### Production Deployment Flow

```
1. Developer creates feature branch
2. Developer opens PR to develop
3. GitHub Actions:
   ├─ Runs tests
   ├─ Creates ephemeral PR environment
   └─ Comments on PR with test URL

4. PR merged to develop
5. GitHub Actions:
   ├─ Deletes PR environment
   ├─ Deploys to develop environment
   └─ Runs integration tests

6. Create PR from develop to main
7. Review and approve
8. Merge to main
9. GitHub Actions:
   ├─ Runs full test suite
   ├─ Deploys to production
   └─ Runs smoke tests
```

### Manual Deployment

```bash
# Deploy to production manually
sam deploy \
  --template-file infrastructure/template.yaml \
  --stack-name yoto-smart-stream-prod \
  --parameter-overrides \
    Environment=prod \
    YotoClientId=YOUR_CLIENT_ID \
    EnableMQTT=true \
    EnableCloudFront=true \
  --capabilities CAPABILITY_IAM

# Deploy to develop manually
sam deploy \
  --template-file infrastructure/template.yaml \
  --stack-name yoto-smart-stream-dev \
  --parameter-overrides \
    Environment=dev \
    YotoClientId=YOUR_CLIENT_ID \
    EnableMQTT=true \
    EnableCloudFront=false \
  --capabilities CAPABILITY_IAM
```

---

## Secrets Management

### Environment Variables per Environment

**Production:**
- `YOTO_CLIENT_ID` - From GitHub Secrets
- `DEBUG=false`
- `LOG_LEVEL=warning`
- `ENVIRONMENT=prod` (auto-set by SAM)

**Develop:**
- `YOTO_CLIENT_ID` - From GitHub Secrets
- `DEBUG=true`
- `LOG_LEVEL=info`
- `ENVIRONMENT=dev` (auto-set by SAM)

**PR Environments:**
- `YOTO_CLIENT_ID` - From GitHub Secrets
- `DEBUG=true`
- `LOG_LEVEL=debug`
- `ENVIRONMENT=pr-{number}` (auto-set by SAM)

### OAuth Token Storage

OAuth tokens stored in DynamoDB per environment:
- Production: `yoto-smart-stream-prod` table
- Develop: `yoto-smart-stream-dev` table
- PR: `yoto-smart-stream-pr-{number}` table

Each environment has isolated tokens (no cross-contamination).

---

## Testing Strategy

### Pre-Deployment Tests (CI)

```yaml
# Run on every PR and push
- Linting (ruff)
- Formatting (black)
- Unit tests (pytest)
- Coverage report (>70%)
```

### Post-Deployment Tests

```yaml
# After deployment to each environment
1. Health check: curl /api/health
2. Authentication test: Login to admin user
3. Player list test: GET /api/players
4. S3 access test: Generate pre-signed URL
5. DynamoDB test: Read/write user data
```

### Integration Tests

```yaml
# Run on develop environment only
1. Full API test suite
2. Audio streaming test
3. Card creation test
4. Token refresh test
```

---

## Rollback Procedures

### Automatic Rollback

CloudFormation automatically rolls back on deployment failure:
- Failed Lambda deployment → Previous version restored
- Failed DynamoDB creation → Stack creation aborted
- Failed ECS service → Previous task definition used

### Manual Rollback

```bash
# Rollback production to previous deployment
aws cloudformation cancel-update-stack --stack-name yoto-smart-stream-prod

# Or deploy previous version
git checkout <previous-commit>
sam deploy --stack-name yoto-smart-stream-prod ...
```

### Emergency Rollback

```bash
# Delete current stack and redeploy from backup
aws cloudformation delete-stack --stack-name yoto-smart-stream-prod
# Wait for deletion
aws cloudformation wait stack-delete-complete --stack-name yoto-smart-stream-prod

# Restore from backup
sam deploy --stack-name yoto-smart-stream-prod ...
```

---

## Cost Management

### Monthly Cost per Environment

| Environment | Lambda | Fargate | DynamoDB | S3 + CloudFront | Total |
|-------------|--------|---------|----------|-----------------|-------|
| **Production** | $0 | $3 | $1 | $1.50 | **$5.50** |
| **Develop** | $0 | $3 | $0.50 | $0.50 | **$4** |
| **PR (each)** | $0 | $3 | $0.50 | $1 | **$4.50/month** (prorated) |

**Note:** PR environments cost ~$6-8/month if left running continuously, but are prorated by hours active. Examples:
- PR open for 1 day: ~$0.20
- PR open for 3 days: ~$0.60
- PR open for 7 days: ~$1.40
- PR open for 30 days: ~$6.00

### Cost Optimization Strategies

**Strategy 1: Auto-cleanup on PR close**
- Environments automatically deleted within 1 hour of PR closure
- Prevents forgotten PRs from accumulating costs
- Implemented via GitHub Actions workflow

**Strategy 2: Stale PR detection**
- Monitor PRs open for >7 days
- Consider manual cleanup for abandoned PRs
- Add GitHub Action to comment on stale PRs

**Strategy 3: Budget alerts**
- Set CloudWatch billing alarms
- Alert at $50/month threshold (covers ~8 concurrent PR environments)
- Allows proactive management

**Cost Impact:**
- 3 PRs for 2 days each: 6 PR-days × $0.20 = $1.20
- vs. cost-reduced approach: $0.60 (but missing MQTT/CloudFront features)
- **Trade-off:** Full testing capability vs. slightly higher PR costs

### Budget Alerts

```bash
# Create billing alarm for total AWS costs
aws cloudwatch put-metric-alarm \
  --alarm-name TotalAWSCostAlert \
  --alarm-description "Alert when total AWS costs exceed $50" \
  --metric-name EstimatedCharges \
  --namespace AWS/Billing \
  --statistic Maximum \
  --period 21600 \
  --evaluation-periods 1 \
  --threshold 50.0 \
  --comparison-operator GreaterThanThreshold
```

---

## Monitoring & Observability

### CloudWatch Dashboards

Create dashboard per environment:

```bash
# Production dashboard
aws cloudwatch put-dashboard --dashboard-name yoto-prod --dashboard-body file://dashboard-prod.json
```

**Metrics to track:**
- Lambda invocations, errors, duration, cold starts
- API Gateway requests, 4xx/5xx errors, latency
- DynamoDB read/write capacity, throttles
- ECS task count, CPU, memory
- S3 GET requests, bandwidth

### Alarms

**Production alarms:**
- Lambda error rate > 5%
- API Gateway 5xx rate > 1%
- DynamoDB throttling
- ECS task stopped unexpectedly

**Develop alarms:**
- None (cost savings)

**PR alarms:**
- None (ephemeral)

---

## Summary

### Deployment Pipeline

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   Feature   │─────▶│   Develop   │─────▶│ Production  │
│   Branch    │      │ Environment │      │ Environment │
│   + PR Env  │      │             │      │             │
└─────────────┘      └─────────────┘      └─────────────┘
     ↓ PR                  ↓ PR                 ↓ Push
     ↓                     ↓                    ↓
  Test + Deploy        Test + Deploy      Test + Deploy
  (Full Env)           (Always-On)        (Always-On)
  ~$0.20/day           $4/month           $5.50/month
  (prorated)
```

### Key Benefits

1. **Automated:** All deployments via GitHub Actions
2. **Isolated:** Each environment completely separate
3. **Full-Featured:** PR environments match production (MQTT + CloudFront)
4. **Safe:** Automatic rollback on failures
5. **Scalable:** Easy to add more environments
6. **Cost-Controlled:** Auto-cleanup prevents runaway costs

### Next Steps

1. Create infrastructure directory and SAM template
2. Add GitHub Actions workflows
3. Configure GitHub secrets
4. Test deployment to develop environment
5. Create first PR to test ephemeral environment
6. Deploy to production

---

**Document Status:** Complete automated deployment plan  
**Last Updated:** 2026-01-15  
**Related Docs:** 
- [AWS_ARCH1_IMPLEMENTATION_GUIDE.md](AWS_ARCH1_IMPLEMENTATION_GUIDE.md)
- [AWS_COST_OPTIMIZATION_REPORT.md](AWS_COST_OPTIMIZATION_REPORT.md)
