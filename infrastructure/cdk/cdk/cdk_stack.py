"""
Yoto Smart Stream AWS CDK Stack
Architecture 1: Lambda + Fargate Spot + DynamoDB + S3 + Cognito
"""
from aws_cdk import (
    Stack,
    Duration,
    CfnOutput,
    BundlingOptions,
    aws_lambda as lambda_,
    aws_apigatewayv2 as apigw,
    aws_apigatewayv2_integrations as apigw_integrations,
    aws_apigatewayv2_authorizers as apigw_authorizers,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
    aws_logs as logs,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr_assets as ecr_assets,
    aws_cloudfront as cloudfront,
    aws_cloudfront_origins as origins,
    aws_cognito as cognito,
    aws_sns as sns,
    aws_sns_subscriptions as sns_subscriptions,
    aws_cloudwatch as cloudwatch,
    aws_cloudwatch_actions as cloudwatch_actions,
    RemovalPolicy,
)
from constructs import Construct


class YotoSmartStreamStack(Stack):
    """Main stack for Yoto Smart Stream application"""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str = "dev",
        yoto_client_id: str = None,
        enable_mqtt: bool = True,
        enable_cloudfront: bool = False,
        billing_alert_email: str = None,
        billing_alert_threshold: float = 10.0,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.env_name = environment  # Renamed from self.environment to avoid conflict
        self.is_production = environment == "prod"
        
        # Create billing alerts if email provided
        if billing_alert_email:
            self.billing_alert_topic = self._create_billing_alerts(
                billing_alert_email, billing_alert_threshold
            )
        
        # Create resources
        self.cognito_user_pool = self._create_cognito_user_pool()
        self.dynamodb_table = self._create_dynamodb_table()
        self.audio_bucket = self._create_audio_bucket()
        self.ui_bucket = self._create_ui_bucket()
        self.lambda_function = self._create_lambda_function(yoto_client_id)
        self.api_gateway = self._create_api_gateway()
        
        # Update Lambda PUBLIC_URL now that API Gateway is created
        self.lambda_function.add_environment(
            "PUBLIC_URL",
            f"https://{self.api_gateway.api_id}.execute-api.{self.region}.amazonaws.com"
        )
        
        if enable_mqtt:
            self.mqtt_service = self._create_mqtt_handler()
        
        if enable_cloudfront:
            self.cloudfront_dist = self._create_cloudfront_distribution()

    def _create_billing_alerts(
        self, email: str, threshold: float
    ) -> sns.Topic:
        """
        Create billing alerts with CloudWatch alarm and SNS topic.
        
        Args:
            email: Email address for billing alerts
            threshold: Dollar amount threshold for alerts
            
        Returns:
            SNS topic for billing alerts
        """
        # Create SNS topic for billing alerts
        topic = sns.Topic(
            self,
            "BillingAlertTopic",
            topic_name=f"yoto-billing-alerts-{self.env_name}",
            display_name=f"Yoto Smart Stream Billing Alerts ({self.env_name})",
        )
        
        # Subscribe email to topic
        topic.add_subscription(
            sns_subscriptions.EmailSubscription(email)
        )
        
        # Create CloudWatch alarm for billing
        # Note: Billing metrics are only available in us-east-1
        alarm = cloudwatch.Alarm(
            self,
            "BillingAlarm",
            alarm_name=f"yoto-billing-{self.env_name}-threshold",
            alarm_description=f"Alert when estimated charges exceed ${threshold} for {self.env_name}",
            metric=cloudwatch.Metric(
                namespace="AWS/Billing",
                metric_name="EstimatedCharges",
                dimensions_map={
                    "Currency": "USD",
                },
                statistic="Maximum",
                period=Duration.hours(6),
            ),
            threshold=threshold,
            evaluation_periods=1,
            comparison_operator=cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
        )
        
        # Add SNS action to alarm
        alarm.add_alarm_action(
            cloudwatch_actions.SnsAction(topic)
        )
        
        CfnOutput(
            self,
            "BillingAlertTopicArn",
            value=topic.topic_arn,
            description="SNS Topic ARN for billing alerts",
        )
        CfnOutput(
            self,
            "BillingAlertEmail",
            value=email,
            description="Email address receiving billing alerts",
        )
        CfnOutput(
            self,
            "BillingAlertThreshold",
            value=str(threshold),
            description="Billing alert threshold in USD",
        )
        
        return topic

    def _create_cognito_user_pool(self) -> cognito.UserPool:
        """Create Cognito User Pool for authentication"""
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            user_pool_name=f"yoto-users-{self.env_name}",
            self_sign_up_enabled=False,  # Only admin can create users
            sign_in_aliases=cognito.SignInAliases(
                username=True,
                email=True,
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=True),
            ),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=False,
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY,
        )

        # Create app client for the web application
        user_pool_client = user_pool.add_client(
            "WebAppClient",
            user_pool_client_name=f"yoto-webapp-{self.env_name}",
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=False,
                    implicit_code_grant=True,
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE,
                ],
            ),
            prevent_user_existence_errors=True,
        )
        
        # Store client as instance variable for use in Lambda environment
        self.cognito_user_pool_client = user_pool_client

        # Create a domain for hosted UI (optional)
        user_pool.add_domain(
            "CognitoDomain",
            cognito_domain=cognito.CognitoDomainOptions(
                domain_prefix=f"yoto-smart-stream-{self.env_name}",
            ),
        )

        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
        CfnOutput(
            self,
            "CognitoLoginUrl",
            value=f"https://yoto-smart-stream-{self.env_name}.auth.{self.region}.amazoncognito.com/login",
            description="Cognito Hosted UI Login URL",
        )

        return user_pool

    def _create_dynamodb_table(self) -> dynamodb.Table:
        """Create DynamoDB table for application data"""
        table = dynamodb.Table(
            self,
            "YotoTable",
            table_name=f"yoto-smart-stream-{self.env_name}",
            partition_key=dynamodb.Attribute(
                name="PK", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="SK", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery=self.is_production,
            removal_policy=RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY,
        )

        CfnOutput(self, "DynamoDBTableName", value=table.table_name)
        return table

    def _create_audio_bucket(self) -> s3.Bucket:
        """Create S3 bucket for audio files"""
        bucket = s3.Bucket(
            self,
            "AudioBucket",
            bucket_name=f"yoto-audio-{self.env_name}-{self.account}",
            versioned=self.is_production,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3600,
                )
            ],
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    enabled=True,
                    noncurrent_version_expiration=Duration.days(30),
                ),
            ] if self.is_production else [],
            removal_policy=RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY,
            auto_delete_objects=not self.is_production,
        )

        CfnOutput(self, "AudioBucketName", value=bucket.bucket_name)
        return bucket

    def _create_ui_bucket(self) -> s3.Bucket:
        """Create S3 bucket for static UI files"""
        bucket = s3.Bucket(
            self,
            "UIBucket",
            bucket_name=f"yoto-ui-{self.env_name}-{self.account}",
            # Removed public_read_access and website hosting to comply with Block Public Access
            # UI files will be served through Lambda/API Gateway or CloudFront
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.GET, s3.HttpMethods.HEAD],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3600,
                )
            ],
            removal_policy=RemovalPolicy.RETAIN if self.is_production else RemovalPolicy.DESTROY,
            auto_delete_objects=not self.is_production,
        )

        CfnOutput(self, "UIBucketName", value=bucket.bucket_name)
        return bucket

    def _create_lambda_function(self, yoto_client_id: str) -> lambda_.Function:
        """Create Lambda function for API"""
        # Lambda execution role
        role = iam.Role(
            self,
            "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
            ],
        )

        # Grant permissions
        self.dynamodb_table.grant_read_write_data(role)
        self.audio_bucket.grant_read_write(role)
        self.ui_bucket.grant_read(role)
        
        # Grant Secrets Manager permissions for OAuth tokens
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:PutSecretValue",
                    "secretsmanager:CreateSecret",
                    "secretsmanager:DeleteSecret",
                ],
                resources=[
                    f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:yoto-smart-stream-{self.env_name}/*"
                ],
            )
        )
        
        # Grant Polly permissions for TTS
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["polly:SynthesizeSpeech"],
                resources=["*"],
            )
        )
        
        # Grant Cognito permissions
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "cognito-idp:AdminInitiateAuth",
                    "cognito-idp:AdminCreateUser",
                    "cognito-idp:AdminSetUserPassword",
                    "cognito-idp:AdminGetUser",
                    "cognito-idp:ListUsers",
                ],
                resources=[self.cognito_user_pool.user_pool_arn],
            )
        )
        
        # Grant Secrets Manager permissions for Yoto OAuth tokens
        role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "secretsmanager:GetSecretValue",
                    "secretsmanager:CreateSecret",
                    "secretsmanager:UpdateSecret",
                    "secretsmanager:DeleteSecret",
                ],
                resources=[f"arn:aws:secretsmanager:{self.region}:{self.account}:secret:yoto-smart-stream-{self.env_name}/yoto-token/*"],
            )
        )

        # Create Lambda function
        function = lambda_.Function(
            self,
            "ApiFunction",
            function_name=f"yoto-api-{self.env_name}",
            runtime=lambda_.Runtime.PYTHON_3_12,  # Updated to Python 3.12
            handler="handler.handler",
            code=lambda_.Code.from_asset("../lambda/package"),  # Use pre-packaged directory
            timeout=Duration.seconds(30),
            memory_size=1024,
            role=role,
            environment={
                "ENVIRONMENT": self.env_name,
                "DYNAMODB_TABLE": self.dynamodb_table.table_name,
                "S3_AUDIO_BUCKET": self.audio_bucket.bucket_name,
                "S3_UI_BUCKET": self.ui_bucket.bucket_name,
                "YOTO_CLIENT_ID": yoto_client_id or "",
                "YOTO_SECRET_PREFIX": f"yoto-smart-stream-{self.env_name}",
                "SECRETS_EXTENSION_HTTP_POLL": "1000",  # Extension polling interval in ms
                "SECRETS_EXTENSION_HTTP_PORT": "2773",  # Extension port
                "COGNITO_USER_POOL_ID": self.cognito_user_pool.user_pool_id,
                "COGNITO_CLIENT_ID": self.cognito_user_pool_client.user_pool_client_id,  # Fixed: use client ID not provider name
                "AUDIO_FILES_DIR": "/tmp/audio_files",  # Lambda writable directory
                "DATABASE_URL": "sqlite:////tmp/yoto_smart_stream.db",  # Lambda writable location
                "PUBLIC_URL": f"https://{{api_id}}.execute-api.{self.region}.amazonaws.com",  # For audio streaming (will be populated after API creation)
                # AWS_REGION is automatically set by Lambda runtime
            },
            log_retention=logs.RetentionDays.ONE_WEEK if not self.is_production else logs.RetentionDays.ONE_MONTH,
        )
        
        # Add AWS Secrets Manager Lambda Extension Layer
        # This layer provides automatic caching and refresh of secrets
        # Using the underlying CDK construct to add the layer directly to CloudFormation
        from aws_cdk.aws_lambda import CfnFunction
        
        cfn_function = function.node.default_child
        extension_layer_arn = f"arn:aws:lambda:{self.region}:976759262368:layer:AWS-Parameters-and-Secrets-Lambda-Extension:12"
        
        if not hasattr(cfn_function, "layers"):
            cfn_function.layers = []
        cfn_function.layers.append(extension_layer_arn)
        
        # FFmpeg Lambda layer removed - exceeds Lambda size limit (250MB)
        # Audio recording/conversion features will not work
        # Workaround: Upload pre-recorded MP3 files directly

        CfnOutput(self, "LambdaFunctionArn", value=function.function_arn)
        return function

    def _create_api_gateway(self) -> apigw.HttpApi:
        """Create API Gateway HTTP API"""
        api = apigw.HttpApi(
            self,
            "HttpApi",
            api_name=f"yoto-api-{self.env_name}",
            cors_preflight=apigw.CorsPreflightOptions(
                allow_origins=["*"],
                allow_methods=[apigw.CorsHttpMethod.ANY],
                allow_headers=["*"],
            ),
            default_integration=apigw_integrations.HttpLambdaIntegration(
                "DefaultIntegration",
                self.lambda_function,
            ),
        )

        CfnOutput(self, "ApiUrl", value=api.url, description="API Gateway URL")
        return api

    def _create_mqtt_handler(self) -> ecs.FargateService:
        """Create ECS Fargate service for MQTT handler"""
        # Create VPC
        vpc = ec2.Vpc(
            self,
            "VPC",
            max_azs=2,
            nat_gateways=0,  # Use public subnets to save costs
        )

        # Create ECS cluster
        cluster = ecs.Cluster(
            self,
            "MQTTCluster",
            cluster_name=f"yoto-mqtt-{self.env_name}",
            vpc=vpc,
            enable_fargate_capacity_providers=True,
        )

        # Task execution role
        execution_role = iam.Role(
            self,
            "MQTTExecutionRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                ),
            ],
        )

        # Task role
        task_role = iam.Role(
            self,
            "MQTTTaskRole",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )
        self.dynamodb_table.grant_read_write_data(task_role)

        # Create task definition
        task_definition = ecs.FargateTaskDefinition(
            self,
            "MQTTTaskDef",
            family=f"yoto-mqtt-{self.env_name}",
            cpu=256,
            memory_limit_mib=512,
            execution_role=execution_role,
            task_role=task_role,
        )

        # Add container
        container = task_definition.add_container(
            "mqtt-handler",
            image=ecs.ContainerImage.from_asset("../mqtt_handler"),  # Fixed path: relative to cdk directory
            logging=ecs.LogDriver.aws_logs(
                stream_prefix="ecs",
                log_retention=logs.RetentionDays.ONE_WEEK if not self.is_production else logs.RetentionDays.ONE_MONTH,
            ),
            environment={
                "ENVIRONMENT": self.env_name,
                "DYNAMODB_TABLE": self.dynamodb_table.table_name,
                "AWS_REGION": self.region,
            },
        )

        # Create security group
        security_group = ec2.SecurityGroup(
            self,
            "MQTTSecurityGroup",
            vpc=vpc,
            description="Security group for MQTT handler",
            allow_all_outbound=True,
        )

        # Create Fargate service with Spot
        service = ecs.FargateService(
            self,
            "MQTTService",
            service_name=f"yoto-mqtt-{self.env_name}",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=1,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT",
                    weight=1,
                )
            ],
            security_groups=[security_group],
            assign_public_ip=True,  # Required for public subnets
        )

        CfnOutput(self, "MQTTServiceArn", value=service.service_arn)
        return service

    def _create_cloudfront_distribution(self) -> cloudfront.Distribution:
        """Create CloudFront distribution for UI"""
        distribution = cloudfront.Distribution(
            self,
            "CloudFrontDistribution",
            comment=f"Yoto Smart Stream {self.env_name}",
            default_behavior=cloudfront.BehaviorOptions(
                origin=origins.S3Origin(self.ui_bucket),
                viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
                allowed_methods=cloudfront.AllowedMethods.ALLOW_GET_HEAD_OPTIONS,
                cached_methods=cloudfront.CachedMethods.CACHE_GET_HEAD_OPTIONS,
            ),
            default_root_object="index.html",
            price_class=cloudfront.PriceClass.PRICE_CLASS_100,
        )

        CfnOutput(
            self,
            "CloudFrontDomainName",
            value=distribution.distribution_domain_name,
            description="CloudFront Distribution Domain Name",
        )
        return distribution
