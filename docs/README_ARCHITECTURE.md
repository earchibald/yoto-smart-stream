# AWS Architecture Documentation

This directory contains comprehensive documentation and diagrams of the Yoto Smart Stream AWS infrastructure.

## Files

### AWS_ARCHITECTURE_DIAGRAM.svg
**Interactive graphical diagram** of the complete AWS infrastructure showing:
- All AWS services (Lambda, ECS/Fargate, DynamoDB, S3, Cognito, API Gateway, CloudFront)
- Component relationships and connections
- Data flow between services
- Color-coded by service category for easy navigation

**How to view:**
- Open directly in any web browser
- Click on nodes/edges for interaction
- Zoom and pan for detailed exploration
- Embed in documentation or presentations

### AWS_ARCHITECTURE_OVERVIEW.md
**Comprehensive documentation** covering:
- Detailed component descriptions
- Service responsibilities and capabilities
- Data flow patterns for key operations
- Security architecture
- High availability and disaster recovery
- Cost optimization strategies
- Scaling considerations
- Deployment architecture

## Architecture at a Glance

```

              Web Browser (Client)                   │

              │              │
    ┌─────────▼───────┬──────▼─────────┐
    │  CloudFront     │  API Gateway   │
    │  (CDN)          │  (HTTP API)    │
    └────────┬────────┴──────┬─────────┘
             │               │
- Add 'Select All' toggle convenience
         │  AWS Lambda (REST API)   │
         │  + ECS/Fargate (MQTT)    │
         └───┬──────────┬──────────
             │          │          │
      ┌──────▼──┐  ┌────▼────┐  ┌─▼──────┐
      │DynamoDB │  │S3 Audio │  │Cognito │
      │(Primary)│  │+ S3 UI  │  │(Auth)  │
      └─────────┘  └─────────┘  └────────┘
             │
      ┌──────▼─────────┐
      │ MQTT Broker    │◄─────► Yoto Devices
      │ (Real-time)    │
      └────────────────┘
```

## Key Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **Lambda** | REST API execution | Serverless, auto-scaling, pay-per-use |
| **ECS/Fargate** | MQTT handler | Real-time device communication, multi-AZ |
| **DynamoDB** | Primary database | NoSQL, pay-per-request, point-in-time recovery |
| **S3 (Audio)** | Audio storage | Versioning, lifecycle policies, CORS |
| **S3 (UI)** | Static assets | CloudFront origin, CORS enabled |
| **Cognito** | User authentication | User pools, OAuth, JWT tokens |
| **API Gateway** | API management | HTTPS, CORS, rate limiting |
| **CloudFront** | CDN | Global distribution, caching, edge locations |
| **CloudWatch** | Monitoring | Logs, metrics, alarms |
| **Secrets Manager** | Credentials | OAuth tokens, API keys |

## Related Documentation

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design and information flows
- [AWS_QUICK_REFERENCE.md](../AWS_QUICK_REFERENCE.md) - Quick AWS deployment guide
- [AWS_DEPLOYMENT_COMPLETE.md](../AWS_DEPLOYMENT_COMPLETE.md) - Deployment status

## How to Update the Diagram

The diagram is generated from Python code using Graphviz. To regenerate:

```bash
# Navigate to the repo
cd /path/to/repo

# Run the generation script (requires graphviz and python3)
python3 .agent-tmp/generate_architecture_diagram.py
```

The script:
1. Creates a Python virtual environment in `.agent-tmp/`
2. Installs dependencies (graphviz library)
3. Generates the diagram in SVG format
4. Saves to `docs/AWS_ARCHITECTURE_DIAGRAM.svg`

## Architecture Highlights

 **Multi-AZ High Availability**
- Fargate deployed across multiple availability zones
- DynamoDB automatic replication
- CloudFront global edge caching

 **Security**
- Cognito-based authentication
- All communications encrypted (HTTPS/TLS)
- Secrets Manager for credentials
- VPC isolation for compute

 **Scalability**
- Lambda auto-scales on demand
- Fargate horizontal scaling
- DynamoDB pay-per-request
- CloudFront global distribution

 **Cost Optimization**
- Lambda pay-per-use
- Fargate Spot instances
- DynamoDB on-demand billing
- S3 lifecycle policies

## Support

For questions about the architecture, refer to:
- Component documentation in AWS_ARCHITECTURE_OVERVIEW.md
- AWS service documentation links in the overview
- Infrastructure code in `infrastructure/cdk/`
