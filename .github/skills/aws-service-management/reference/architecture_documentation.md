# AWS Architecture Documentation Update Guide

This guide covers maintaining and updating the AWS architecture diagram and documentation for the Yoto Smart Stream project.

## Overview

The project maintains comprehensive AWS infrastructure documentation in three formats:

1. **AWS_ARCHITECTURE_DIAGRAM.svg** - Graphical diagram with 21 AWS components
2. **AWS_ARCHITECTURE_OVERVIEW.md** - Detailed technical documentation
3. **README_ARCHITECTURE.md** - Quick reference guide

These files are located in the `docs/` directory and are version-controlled in Git.

## File Locations & Purposes

### docs/AWS_ARCHITECTURE_DIAGRAM.svg
- **Type:** Scalable Vector Graphics (SVG)
- **Size:** ~27 KB
- **Purpose:** Visual representation of all AWS services and their relationships
- **Usage:** Embedded in presentations, wikis, PR descriptions
- **Generated:** Programmatically using Graphviz Python library

### docs/AWS_ARCHITECTURE_OVERVIEW.md
- **Type:** Markdown documentation
- **Size:** ~11 KB
- **Purpose:** Comprehensive technical reference
- **Contents:**
  - Component descriptions and responsibilities
  - Data flow patterns for key operations
  - Security architecture and best practices
  - High availability and disaster recovery strategies
  - Cost optimization and scaling considerations
  - Deployment architecture and processes
  - Future enhancement recommendations

### docs/README_ARCHITECTURE.md
- **Type:** Markdown quick reference
- **Size:** ~4.5 KB
- **Purpose:** User-friendly guide to the documentation
- **Contents:**
  - Quick navigation instructions
  - Component summary table
  - Architecture highlights
  - Instructions for regenerating the diagram

## When to Update Architecture Documentation

Update the architecture documentation when:

1. **Infrastructure Changes:**
   - New AWS services added (Lambda, RDS, ElastiCache, etc.)
   - Service configuration changes (memory, instance type, scaling)
   - Network topology changes (VPC, subnets, security groups)
   - Database schema or storage changes

2. **Integration Changes:**
   - New external service integrations
   - API or protocol changes
   - Authentication mechanism updates

3. **Data Flow Changes:**
   - New request/response patterns
   - MQTT topic structure updates
   - Event handling changes
   - Communication protocol changes

4. **Operational Changes:**
   - Deployment process updates
   - Monitoring or alerting changes
   - Cost optimization strategy updates
   - Backup and recovery procedure changes

## Regenerating the Architecture Diagram

The diagram is generated from Python code using Graphviz. This ensures it stays synchronized with the actual infrastructure design.

### Prerequisites

- Python 3.9+
- Graphviz system package (not the Python wrapper)
- Git access to the repository

### Step-by-Step Process

#### 1. Review Infrastructure Changes

Before regenerating, review what changed:

```bash
# Check CDK stack definition
cd infrastructure/cdk
cat cdk/cdk_stack.py | grep -E "(lambda_|s3\.|dynamodb|ecs\.|apigw)"
```

#### 2. Update the Diagram Generation Script

Edit `.agent-tmp/generate_architecture_diagram.py` to reflect infrastructure changes:

**Common Changes:**

a) **Adding a new AWS service:**
```python
# In the _create_aws_architecture_diagram() function

# 1. Add node definition
dot.node('service_id', 'Service Name\nDescription', 
         color=colors['category'], shape='box')

# 2. Add edges (connections) to/from this service
dot.edge('source_service', 'service_id', label='Connection description')
dot.edge('service_id', 'target_service', label='Connection description')
```

b) **Changing service category color:**
```python
# Modify the colors dictionary
colors = {
    'compute': '#E8F8E8',        # Green for compute
    'storage': '#F0E8F8',        # Purple for storage
    'database': '#E8E8F8',       # Light blue for databases
    'network': '#F8F0E8',        # Light orange for networking
    'messaging': '#F8E8E8',      # Red for messaging
    'security': '#F8F8E0',       # Yellow for security
    'monitoring': '#F0F8E8',     # Light green for monitoring
    'external': '#FFE8E8',       # Pink for external services
}
```

c) **Modifying connections/relationships:**
```python
# Update edge definitions to show new or changed data flows
dot.edge('source', 'destination', 
         label='Updated description',
         style='dashed')  # Use dashed for optional connections
```

#### 3. Regenerate the Diagram

From the repository root:

```bash
# Navigate to the agent-tmp directory
cd .agent-tmp

# Create or activate the virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install graphviz

# Generate the diagram
python3 generate_architecture_diagram.py
```

**Expected Output:**
```
✓ AWS Architecture Diagram generated successfully!
  Output file: /path/to/docs/AWS_ARCHITECTURE_DIAGRAM.svg
  Size: 27636 bytes
```

#### 4. Verify the Output

```bash
# Check the generated file
ls -lh docs/AWS_ARCHITECTURE_DIAGRAM.svg

# View the diagram (optional, opens in browser)
open docs/AWS_ARCHITECTURE_DIAGRAM.svg
```

## Updating Documentation Files

### AWS_ARCHITECTURE_OVERVIEW.md

Update this file with detailed information about infrastructure changes:

```markdown
## Sections to Update

### Component Overview
- Add new AWS service description
- Update responsibility descriptions
- Add service integration details

### Data Flow Patterns
- Add new data flow diagrams
- Update existing flow descriptions
- Include code examples if applicable

### Environment Configuration
- Update dev vs prod settings
- Modify resource allocations
- Change feature toggles (MQTT, CloudFront)

### Security Architecture
- Document new security measures
- Update encryption mechanisms
- Add compliance considerations

### Scaling Considerations
- Update horizontal scaling strategies
- Modify vertical scaling recommendations
- Include new auto-scaling triggers

### Cost Optimization
- Document new cost savings
- Update pricing analysis
- Add Reserved Instance recommendations
```

**Example Edit:**

When adding a new service (e.g., ElastiCache):

```markdown
#### ElastiCache (Redis)
- **Name**: `yoto-cache-{environment}`
- **Purpose**: High-performance in-memory cache
- **Use Cases**:
  - Session caching
  - Rate limiting
  - Real-time leaderboards
  
- **Configuration**:
  - Node type: cache.t3.micro
  - Engine: Redis 7.0
  - Multi-AZ: Enabled in production

- **Integrations**:
  - Lambda: Cache reads/writes
  - Fargate: Session store
  - CloudWatch: Monitoring
```

### README_ARCHITECTURE.md

Update the quick reference section:

```markdown
## Key Components

| Component | Purpose | Key Features |
|-----------|---------|--------------|
| **New Service** | Brief description | Feature 1, Feature 2 |
```

## Git Workflow for Architecture Updates

### 1. Create Feature Branch

```bash
git checkout -b docs/update-architecture-{service-name}
```

### 2. Make Changes

Edit the following files as needed:
- `.agent-tmp/generate_architecture_diagram.py` (if infrastructure changed)
- `docs/AWS_ARCHITECTURE_OVERVIEW.md` (details)
- `docs/README_ARCHITECTURE.md` (quick reference)

### 3. Regenerate Diagram

```bash
cd .agent-tmp
source venv/bin/activate
python3 generate_architecture_diagram.py
```

### 4. Stage Changes

```bash
git add docs/AWS_ARCHITECTURE_DIAGRAM.svg
git add docs/AWS_ARCHITECTURE_OVERVIEW.md
git add docs/README_ARCHITECTURE.md
# Don't commit .agent-tmp/ files (already in .gitignore)
```

### 5. Commit with Descriptive Message

```bash
git commit -m "Update AWS architecture documentation: {change description}

- Add new service/Update service configuration/Modify data flow
- Generated new architecture diagram with {number} components
- Updated AWS_ARCHITECTURE_OVERVIEW.md with detailed information
- Updated README_ARCHITECTURE.md quick reference

Diagram changes:
- Added: {service names if added}
- Modified: {service connections if changed}
- Removed: {service names if removed}"
```

### 6. Push and Create PR

```bash
git push origin docs/update-architecture-{service-name}
# Create PR through GitHub
```

### 7. PR Checklist

Before merging, verify:

- [ ] Diagram SVG is valid and displays correctly
- [ ] All documentation is accurate and complete
- [ ] All AWS services shown in diagram are documented
- [ ] Data flow descriptions match the diagram
- [ ] No sensitive data (credentials, tokens) in files
- [ ] Links to referenced documentation are correct
- [ ] Formatting is consistent with existing docs

## Maintenance Schedule

Recommended review cadence:

| Frequency | Activity |
|-----------|----------|
| Monthly | Review for infrastructure drift |
| Per CDK change | Update after infrastructure modifications |
| Per deployment | Verify environment-specific config |
| Quarterly | Full audit and refresh |

## Common Update Scenarios

### Scenario 1: Adding a New Compute Service

Example: Adding Step Functions for workflow orchestration

**Step 1: Update diagram script**
```python
# Add node
dot.node('step_functions', 'AWS Step Functions\n(Workflows)', 
         color=colors['compute'], shape='box')

# Add edges
dot.edge('lambda', 'step_functions', label='Trigger workflows')
dot.edge('step_functions', 'dynamodb', label='Update state')
dot.edge('step_functions', 'sns', label='Send notifications')
```

**Step 2: Regenerate**
```bash
cd .agent-tmp && source venv/bin/activate && python3 generate_architecture_diagram.py
```

**Step 3: Update overview**
```markdown
#### AWS Step Functions
- **Purpose**: Orchestrate complex workflows
- **Workflows**: Audio processing pipeline, error handling
- **Integration**: Lambda, SNS notifications
```

**Step 4: Commit**
```bash
git add -A && git commit -m "Add Step Functions for workflow orchestration"
```

### Scenario 2: Modifying Environment Configuration

Example: Enabling CloudFront caching in development

**Step 1: No diagram change needed (logic change only)**

**Step 2: Update documentation**
```markdown
### Development (`dev`)
- Lambda: 1024 MB memory, 30s timeout
- Fargate: 256 CPU, 512 MB memory
- DynamoDB: Pay-per-request billing
- MQTT: Enabled
- CloudFront: **Enabled** (caching enabled for dev testing)  ← Changed
- Log retention: 1 week
```

**Step 3: Update CDK context flags**
- Update `reference/cli_scripts.md` with new flag

**Step 4: Commit**
```bash
git add docs/AWS_ARCHITECTURE_OVERVIEW.md
git add reference/cli_scripts.md
git commit -m "Enable CloudFront caching in dev environment"
```

### Scenario 3: Updating Data Flow

Example: Adding WebSocket connection for real-time updates

**Step 1: Update diagram script**
```python
# Add or modify edge
dot.edge('client', 'apigw', 
         label='WebSocket\n(Real-time events)', 
         style='dashed')
```

**Step 2: Update documentation**
```markdown
### Real-time Communication Flow
Browser → API Gateway → WebSocket Gateway → Lambda → Events
                                                ↓
                                            CloudWatch
```

**Step 3: Regenerate and commit**

## Troubleshooting

### Diagram Generation Fails

```bash
# Check Graphviz is installed
which dot

# If missing, install:
brew install graphviz  # macOS
apt-get install graphviz  # Ubuntu/Debian

# Verify Python environment
source .agent-tmp/venv/bin/activate
python3 -m pip list | grep graphviz

# Reinstall if needed
pip install --upgrade graphviz
```

### SVG File Doesn't Display

```bash
# Verify SVG is valid
file docs/AWS_ARCHITECTURE_DIAGRAM.svg

# Check file size
ls -lh docs/AWS_ARCHITECTURE_DIAGRAM.svg

# Ensure no corrupted characters
head -20 docs/AWS_ARCHITECTURE_DIAGRAM.svg
```

### Documentation Sync Issues

```bash
# Compare diagram script with documentation
grep "dot.node" .agent-tmp/generate_architecture_diagram.py | wc -l
# Should match number of components documented in README_ARCHITECTURE.md

# Check all services documented
grep "^##" docs/AWS_ARCHITECTURE_OVERVIEW.md | wc -l
```

## Best Practices

1. **Keep Documentation DRY**
   - Single source of truth (the CDK stack)
   - Generate diagram from code, not manually
   - Reference architecture docs from related files

2. **Version Control**
   - Commit diagram SVG with documentation changes
   - Include clear commit messages explaining changes
   - Link to CDK changes in commit message

3. **Review Process**
   - Have team member verify accuracy
   - Test diagram renders correctly in multiple viewers
   - Validate all components are properly connected

4. **Automation**
   - Consider CI/CD hook to validate diagrams
   - Auto-generate on main branch commits
   - Alert on missing documentation

5. **Documentation Standards**
   - Use consistent formatting and structure
   - Include examples and code snippets
   - Provide links to AWS documentation
   - Keep sections organized by component category

## References

- **AWS Architecture Best Practices**: https://docs.aws.amazon.com/architecture/
- **Graphviz Documentation**: https://graphviz.org/documentation/
- **Project CDK Stack**: `infrastructure/cdk/cdk/cdk_stack.py`
- **AWS Architecture Overview**: `docs/AWS_ARCHITECTURE_OVERVIEW.md`
- **Quick Reference**: `docs/README_ARCHITECTURE.md`

## Related Skills

- [aws-service-management/SKILL.md](../SKILL.md) - Deployment and CDK management
- [aws-service-management/reference/cli_scripts.md](./cli_scripts.md) - CDK deployment commands
