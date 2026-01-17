# AWS Architecture Overview

This document provides a comprehensive overview of the Yoto Smart Stream AWS infrastructure architecture.

## Architecture Diagram

See the graphical diagram: [`AWS_ARCHITECTURE_DIAGRAM.svg`](AWS_ARCHITECTURE_DIAGRAM.svg)

The diagram illustrates all AWS services, components, and their relationships in the production environment.

## Component Overview

### Client Layer
- **Web Browser (React Frontend)**: The client-side application running in users' browsers
  - Communicates via REST API for data operations
  - Communicates via WebSocket for real-time device events
  - Receives cached UI resources from CloudFront CDN

### Content Delivery
- **CloudFront CDN**: Distributed content delivery network
  - Caches static UI assets (HTML, CSS, JavaScript, images)
  - Origin: S3 UI Bucket
  - Reduces latency and improves performance globally

### Network & API Layer
- **API Gateway (HTTP API)**: AWS API Gateway configured for HTTP/REST API
  - Routes requests to Lambda function
  - CORS enabled for cross-origin requests
  - Integrates with Cognito for authorization
  - Protocol: HTTPS (encrypted)

### Security & Authentication
- **AWS Cognito User Pool**: Manages user authentication and authorization
  - User registration and sign-in
  - Email-based account verification
  - Password policies and account recovery
  - Admin user management via Lambda
  - Provides JWT tokens for API access

- **AWS Secrets Manager**: Secure credential storage
  - Stores Yoto OAuth tokens for API integration
  - Stores third-party API credentials
  - Automatic credential rotation support

### Compute Services

#### Lambda (REST API)
- **Function**: `yoto-api-{environment}`
- **Runtime**: Python 3.12 with Mangum ASGI adapter
- **Responsibilities**:
  - RESTful API endpoint handling
  - User management and authentication
  - Audio file processing and metadata extraction
  - Device registration and management
  - Yoto API integration (OAuth, device discovery)
  - Secrets Manager access for credentials
  - Cognito user administration

- **Integrations**:
  - DynamoDB for data persistence
  - S3 for audio and UI file storage
  - Cognito for user management
  - AWS Polly for text-to-speech
  - Secrets Manager for credential retrieval
  - CloudWatch for logging and metrics

#### ECS + Fargate (MQTT Handler)
- **Cluster**: `yoto-mqtt-{environment}`
- **Service**: Fargate service with Spot pricing
- **Container**: Custom Docker image from `mqtt_handler/` directory
- **Infrastructure**:
  - VPC with public subnets across multiple AZs (HA)
  - Security groups for network isolation
  - Spot instances for cost optimization
  - Auto-scaling based on demand

- **Responsibilities**:
  - MQTT message broker subscription
  - Device event processing
  - Device command delivery
  - Device state synchronization
  - Real-time telemetry collection

### Storage Services

#### S3 Audio Bucket
- **Name**: `yoto-audio-{environment}-{account}`
- **Purpose**: Persistent storage for audio files
- **Features**:
  - CORS enabled for direct download access
  - Versioning (production only)
  - Lifecycle policies for old versions (production only)
  - Read/write access from Lambda and Fargate

#### S3 UI Bucket
- **Name**: `yoto-ui-{environment}-{account}`
- **Purpose**: Static website assets
- **Features**:
  - CORS enabled
  - Origin for CloudFront distribution
  - Read access from Lambda
  - Write access only from deployment pipeline

### Database & Persistence

#### DynamoDB
- **Table Name**: `yoto-smart-stream-{environment}`
- **Schema**:
  - Partition Key: `PK` (String)
  - Sort Key: `SK` (String)
  - Pay-per-request billing mode
  - Point-in-time recovery (production only)

- **Data Stored**:
  - User profiles and authentication data
  - Device registrations and status
  - Script definitions and CYOA stories
  - Audio file metadata
  - Event logs and telemetry
  - Playback history

### Messaging & Real-time Communication

#### MQTT Message Broker
- **Protocol**: MQTT over TCP (TLS encrypted)
- **Communication Pattern**: Pub/Sub
- **Connections**:
  - Yoto devices publish events and telemetry
  - Fargate service subscribes to events and publishes commands
  - Frontend receives events via WebSocket bridge

- **Topic Structure**:
  ```
  yoto/{device_id}/
    ├── status/          # Device online/offline, battery level
    ├── events/          # Button presses, playback events
    ├── commands/        # Commands from server
    ├── playback/        # Current playback state
    └── telemetry/       # Diagnostics and metrics
  ```

### External Services

#### Yoto Public API
- **Purpose**: Integration with Yoto device ecosystem
- **Capabilities**:
  - Device discovery and registration
  - OAuth authentication for Yoto services
  - Device metadata and capabilities
  - Firmware updates

#### AWS Polly
- **Purpose**: Text-to-speech synthesis
- **Use Cases**:
  - Converting text content to speech
  - Creating audio-only interactive experiences
  - Dynamic audio content generation

### Monitoring & Alerting

#### CloudWatch
- **Logs**: Centralized logging from all services
  - Lambda function logs
  - Fargate container logs
  - API requests and responses
  - Log retention: 1 week (dev), 1 month (prod)

- **Metrics**: Performance and operational metrics
  - Lambda invocations, duration, errors
  - DynamoDB read/write capacity and throttling
  - S3 access patterns
  - Fargate CPU and memory utilization

#### CloudWatch Alarms
- Monitors CloudWatch metrics against thresholds
- Integrated with SNS for notifications
- Common alarms:
  - API error rates
  - Lambda duration
  - DynamoDB throttling
  - Fargate service health

#### SNS (Simple Notification Service)
- **Purpose**: Alert delivery and notifications
- **Subscriptions**: Email, SMS, webhook endpoints
- **Use Cases**:
  - Billing alerts (when costs exceed threshold)
  - System health alerts
  - Critical error notifications

## Data Flow Patterns

### User Authentication Flow
```
Browser → API Gateway → Lambda → Cognito → DynamoDB
                                    ↑
                                 JWT Token
```

### REST API Request Flow
```
Browser → API Gateway → Lambda → (Various Services)
                            ↓
                    S3/DynamoDB/Secrets Manager
                            ↓
                        Response → Browser
```

### Device Event Flow
```
Yoto Device → MQTT Broker → Fargate (Subscribe) → DynamoDB
                                      ↓
                          WebSocket Bridge → Browser
```

### Command Delivery Flow
```
Browser → API Gateway → Lambda → MQTT Broker → Yoto Device
                            ↓
                        DynamoDB (Command Log)
```

## Environment Configuration

### Development (`dev`)
- Lambda: 1024 MB memory, 30s timeout
- Fargate: 256 CPU, 512 MB memory
- DynamoDB: Pay-per-request billing
- MQTT: Enabled
- CloudFront: Disabled (faster deployments)
- Database: Point-in-time recovery disabled
- Log retention: 1 week

### Production (`prod`)
- Lambda: 1024 MB memory, 30s timeout
- Fargate: 256 CPU, 512 MB memory (Spot instances)
- DynamoDB: Pay-per-request billing
- MQTT: Enabled
- CloudFront: Enabled (global distribution)
- Database: Point-in-time recovery enabled
- S3 versioning: Enabled
- Log retention: 1 month

## Security Architecture

### Authentication & Authorization
- **Cognito User Pool**: Primary authentication mechanism
- **JWT Tokens**: Used for API access
- **Role-based Access**: Users can only access their own resources

### Network Security
- **VPC Isolation**: Fargate runs within VPC with public subnets
- **Security Groups**: Control inbound/outbound traffic
- **HTTPS/TLS**: All external communications encrypted
- **MQTT over TLS**: Device communications encrypted

### Data Protection
- **Encryption in Transit**: All connections use TLS/HTTPS
- **Encryption at Rest**: S3 server-side encryption, DynamoDB encryption
- **Secrets Management**: AWS Secrets Manager for credentials
- **Audit Logging**: CloudWatch logs track all API calls

## Deployment Architecture

### Deployment Process
1. Code committed to repository
2. GitHub Actions triggers deployment pipeline
3. Lambda function packaged and deployed
4. Fargate task definition updated and rolled out
5. API Gateway configuration updated
6. CloudFront cache invalidation (if enabled)

### Rollback Strategy
- Previous Lambda versions retained for quick rollback
- CloudFormation stack templates stored in version control
- Database restoration points available (production)

## High Availability & Disaster Recovery

### Multi-AZ Redundancy
- **Fargate**: Deployed across multiple availability zones
- **DynamoDB**: Automatically replicated across AZs
- **S3**: Cross-region replication available
- **CloudFront**: Global edge locations for failover

### Backup & Recovery
- **DynamoDB**: Point-in-time recovery (production)
- **S3**: Versioning and lifecycle policies
- **Infrastructure**: CloudFormation templates in Git

### Failover Mechanisms
- Lambda scales automatically on demand
- Fargate service auto-recovery on failure
- DynamoDB automatic failover
- CloudFront edge caches for offline resilience

## Cost Optimization

### Compute
- **Lambda**: Pay-per-use, scales to zero when idle
- **Fargate Spot**: Discounted pricing (80% savings vs on-demand)
- **Multi-AZ**: Balanced across zones for cost distribution

### Storage
- **S3 Lifecycle Policies**: Archive old versions, delete expired data
- **DynamoDB**: Pay-per-request eliminates reserved capacity cost
- **CloudFront**: Reduces bandwidth costs for global users

### Monitoring
- **CloudWatch Alarms**: Alert on unusual usage patterns
- **Billing Alerts**: SNS notifications when costs spike
- **Reserved Capacity**: Can be added for predictable workloads

## Scaling Considerations

### Horizontal Scaling
- **Lambda**: Automatic scaling (concurrent executions)
- **Fargate**: Can increase task count or CPU/memory
- **DynamoDB**: Automatic scaling with pay-per-request mode

### Vertical Scaling
- **Lambda**: Increase memory (and CPU) as needed
- **Fargate**: Modify task CPU and memory
- **S3/CloudFront**: No scaling needed (managed service)

## Future Enhancements

Potential improvements to the architecture:

1. **Lambda Layers**: Move shared dependencies to Lambda layers
2. **CloudFront Functions**: Add request filtering at edge
3. **DynamoDB Global Tables**: Multi-region active-active setup
4. **API Caching**: Implement caching layer with API Gateway
5. **Batch Operations**: Async job processing for large uploads
6. **WebSocket Gateway**: Native WebSocket support instead of bridge
7. **Cognito Identity Pool**: For unauthenticated device access
8. **Aurora RDS**: Consider for complex relational queries
9. **ElastiCache**: Redis cache layer for session/data caching
10. **Step Functions**: Orchestrate complex asynchronous workflows

## References

- [AWS Architecture Best Practices](https://docs.aws.amazon.com/architecture/)
- [Lambda Design Patterns](https://docs.aws.amazon.com/lambda/)
- [DynamoDB Best Practices](https://docs.aws.amazon.com/amazondynamodb/)
- [Cognito Security](https://docs.aws.amazon.com/cognito/)
- [ECS/Fargate Best Practices](https://docs.aws.amazon.com/AmazonECS/)
