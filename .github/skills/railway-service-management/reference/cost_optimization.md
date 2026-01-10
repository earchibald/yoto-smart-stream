# Cost Optimization for Railway

## Overview

Railway operates on a pay-as-you-go pricing model. This guide covers strategies to optimize costs while maintaining performance and reliability.

## Railway Pricing Model

### Free Tier

**Included:**
- $5 usage credit per month
- All features available
- Community support

**Suitable for:**
- Hobby projects
- Development
- Small personal apps
- Testing and prototyping

### Paid Usage

**Pricing Components:**
- **Compute**: ~$0.000231 per GB-hour of RAM
- **Compute**: ~$0.000463 per vCPU-hour
- **Network**: $0.10 per GB egress (outbound)
- **Storage**: $0.25 per GB/month for volumes

**Example Costs:**

Small app (hobby/development):
```
512 MB RAM × 720 hours = ~$0.17/month
0.5 vCPU × 720 hours = ~$0.17/month
Total: ~$0.34/month (covered by free tier)
```

Medium production app:
```
1 GB RAM × 720 hours × 2 replicas = ~$0.67/month
1 vCPU × 720 hours × 2 replicas = ~$0.67/month
PostgreSQL (1 GB RAM) = ~$0.17/month
Redis (512 MB RAM) = ~$0.08/month
Network (10 GB) = ~$1.00/month
Total: ~$2.59/month
```

Large production app:
```
2 GB RAM × 720 hours × 4 replicas = ~$2.67/month
2 vCPU × 720 hours × 4 replicas = ~$2.67/month
PostgreSQL (4 GB RAM) = ~$0.67/month
Redis (1 GB RAM) = ~$0.17/month
Network (100 GB) = ~$10.00/month
Total: ~$16.18/month
```

## Cost Optimization Strategies

### 1. Right-Size Your Services

**Audit Current Usage:**

```bash
# Check resource usage
railway status -e production --json | jq '.services[] | {
    name: .name,
    cpu: .metrics.cpu,
    memory: .metrics.memory
}'
```

**Optimization Actions:**
- Start with minimal resources (512 MB RAM, 0.5 vCPU)
- Scale up based on actual usage
- Monitor metrics weekly
- Downsize underutilized services

### 2. Environment Management

**Strategy:**

```bash
# Production - Full resources (24/7)
web: 1 GB RAM, 1 vCPU, 2 replicas
postgres: 2 GB RAM
redis: 512 MB RAM
Cost: ~$15-20/month

# Staging - Reduced resources (24/7 or on-demand)
web: 512 MB RAM, 0.5 vCPU, 1 replica
postgres: 1 GB RAM
Cost: ~$3-5/month

# PR Environments - Minimal (ephemeral, auto-destroy)
web: 512 MB RAM, 0.5 vCPU, 1 replica
postgres: 512 MB RAM (ephemeral)
Cost: ~$0.50/month per active PR (auto-destroyed after merge)
```

**Implementation:**

```bash
# Scale staging down during nights/weekends
railway down -e staging  # Stop services

# Restart when needed
railway up -e staging    # Start services
```

### 3. Ephemeral PR Environments

**Configuration:**

Enable automatic PR environment destruction:
```
Railway Dashboard → Project Settings → GitHub
├── PR Deployments: ✓ Enabled
└── Auto-destroy on close: ✓ Enabled
```

**Savings:**
- PR environments only run while PR is open
- Automatically destroyed after merge/close
- Saves ~$5-10/month per active development project

### 4. Database Optimization

**Reduce Storage Costs:**

```sql
-- Remove old data
DELETE FROM logs WHERE created_at < NOW() - INTERVAL '30 days';

-- Vacuum to reclaim space
VACUUM FULL;

-- Archive old data to cheaper storage
-- Move to S3/object storage instead of keeping in PostgreSQL
```

**Connection Pooling:**

```python
# Reduce number of connections
engine = create_engine(
    DATABASE_URL,
    pool_size=5,          # Reduced from 10
    max_overflow=10,      # Reduced from 20
)
```

### 5. Network Optimization

**Reduce Egress:**

```python
# Enable compression
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware

app = FastAPI()
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Cache responses
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(os.getenv("REDIS_URL"))
    FastAPICache.init(RedisBackend(redis), prefix="cache")

@app.get("/api/data")
@cache(expire=300)  # Cache for 5 minutes
async def get_data():
    return expensive_computation()
```

**CDN for Static Assets:**

```python
# Use CDN for static files instead of serving from Railway
STATIC_URL = "https://cdn.example.com/static/"

# Or use Railway for small static files only
# Move large files (images, videos) to S3 + CloudFront
```

### 6. Scheduled Scaling

**Automation Script:**

```bash
#!/bin/bash
# scripts/scheduled-scaling.sh - Scale services based on schedule

set -e

ENVIRONMENT="staging"
HOUR=$(date +%H)

# Scale down during off-hours (11 PM - 7 AM)
if [ $HOUR -ge 23 ] || [ $HOUR -lt 7 ]; then
    echo "Off-hours: Scaling down $ENVIRONMENT"
    railway down -e "$ENVIRONMENT"
else
    echo "Business hours: Ensuring $ENVIRONMENT is running"
    railway up -e "$ENVIRONMENT"
fi
```

**GitHub Actions Scheduled Scaling:**

```yaml
# .github/workflows/scheduled-scaling.yml
name: Scheduled Scaling

on:
  schedule:
    # Scale down at 11 PM UTC (Mon-Fri)
    - cron: '0 23 * * 1-5'
    # Scale up at 7 AM UTC (Mon-Fri)
    - cron: '0 7 * * 1-5'

jobs:
  scale:
    runs-on: ubuntu-latest
    steps:
      - name: Install Railway CLI
        run: npm i -g @railway/cli
      
      - name: Determine action
        id: action
        run: |
          HOUR=$(date +%H)
          if [ $HOUR -eq 23 ]; then
            echo "action=down" >> $GITHUB_OUTPUT
          else
            echo "action=up" >> $GITHUB_OUTPUT
          fi
      
      - name: Scale staging
        run: railway ${{ steps.action.outputs.action }} -e staging
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

### 7. Monitoring and Alerts

**Set Up Billing Alerts:**

```python
# billing_monitor.py
import os
import requests
from datetime import datetime

def check_railway_usage():
    """Check Railway usage and alert if threshold exceeded"""
    
    # Railway doesn't have direct billing API yet
    # Monitor via dashboard and set manual alerts
    
    # Alternative: Track deployment metrics
    deployments_today = count_deployments_today()
    
    if deployments_today > 50:
        send_alert(
            f"High deployment count today: {deployments_today}",
            level="warning"
        )
```

**Cost Dashboard:**

```python
# cost_dashboard.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/costs", response_class=HTMLResponse)
async def cost_dashboard():
    """Display estimated costs"""
    
    # Calculate based on resource allocation
    web_cost = 1.0 * 720 * 0.000231 * 2  # 1GB RAM, 2 replicas
    cpu_cost = 1.0 * 720 * 0.000463 * 2  # 1 vCPU, 2 replicas
    db_cost = 2.0 * 720 * 0.000231      # 2GB PostgreSQL
    redis_cost = 0.5 * 720 * 0.000231   # 512MB Redis
    
    total = web_cost + cpu_cost + db_cost + redis_cost
    
    html = f"""
    <html>
        <body>
            <h1>Estimated Monthly Costs</h1>
            <ul>
                <li>Web Service (RAM): ${web_cost:.2f}</li>
                <li>Web Service (CPU): ${cpu_cost:.2f}</li>
                <li>PostgreSQL: ${db_cost:.2f}</li>
                <li>Redis: ${redis_cost:.2f}</li>
                <li><strong>Total: ${total:.2f}</strong></li>
            </ul>
            <p>Note: Excludes network egress</p>
        </body>
    </html>
    """
    
    return html
```

### 8. Resource Limits

**Set Appropriate Limits:**

```toml
# railway.toml
[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"

# Limit resources via Railway dashboard
# Settings → Resources:
# - Memory: 512 MB (for non-production)
# - Memory: 1 GB (for production)
# - CPU: Shared (default) or Dedicated (if needed)
```

### 9. Efficient Worker Configuration

**Optimize Worker Count:**

```python
# config.py
import os

# Calculate optimal workers based on available resources
MEMORY_GB = int(os.getenv("MEMORY_MB", 512)) / 1024
WORKERS = max(2, min(int(MEMORY_GB * 2), 4))

# uvicorn startup
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        workers=WORKERS
    )
```

### 10. Caching Strategy

**Implement Aggressive Caching:**

```python
# caching.py
from functools import lru_cache
import redis
import json

redis_client = redis.from_url(os.getenv("REDIS_URL"))

def redis_cache(ttl=300):
    """Cache decorator using Redis"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create cache key
            key = f"{func.__name__}:{args}:{kwargs}"
            
            # Check cache
            cached = redis_client.get(key)
            if cached:
                return json.loads(cached)
            
            # Call function
            result = func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(key, ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# Cache expensive Yoto API calls
@redis_cache(ttl=600)  # 10 minutes
def get_yoto_players():
    return yoto_manager.get_players()

@lru_cache(maxsize=100)  # In-memory cache
def get_static_config():
    return load_config()
```

## Cost Monitoring Checklist

### Weekly Review

- [ ] Check resource usage in Railway dashboard
- [ ] Review deployment frequency
- [ ] Check active environments
- [ ] Verify PR environments are destroyed
- [ ] Review database size growth
- [ ] Check network egress
- [ ] Identify unused services
- [ ] Review error rates (may indicate inefficiencies)

### Monthly Optimization

- [ ] Analyze billing report
- [ ] Right-size all services
- [ ] Clean up old data from database
- [ ] Review caching effectiveness
- [ ] Optimize slow queries
- [ ] Update resource allocations
- [ ] Remove unused environments
- [ ] Document cost trends

## Cost Estimation Tool

```python
#!/usr/bin/env python3
# scripts/estimate-costs.py - Estimate Railway costs

import sys

def estimate_monthly_cost(
    web_ram_gb=1.0,
    web_replicas=2,
    web_cpu=1.0,
    postgres_ram_gb=2.0,
    redis_ram_gb=0.5,
    network_gb=10,
):
    """Estimate monthly Railway costs"""
    
    hours_per_month = 720
    
    # Compute costs
    ram_cost_per_gb_hour = 0.000231
    cpu_cost_per_vcpu_hour = 0.000463
    
    web_ram_cost = web_ram_gb * hours_per_month * ram_cost_per_gb_hour * web_replicas
    web_cpu_cost = web_cpu * hours_per_month * cpu_cost_per_vcpu_hour * web_replicas
    postgres_cost = postgres_ram_gb * hours_per_month * ram_cost_per_gb_hour
    redis_cost = redis_ram_gb * hours_per_month * ram_cost_per_gb_hour
    
    # Network costs
    network_cost = network_gb * 0.10
    
    # Total
    total = web_ram_cost + web_cpu_cost + postgres_cost + redis_cost + network_cost
    
    print("Estimated Monthly Costs:")
    print(f"  Web RAM ({web_ram_gb}GB × {web_replicas} replicas): ${web_ram_cost:.2f}")
    print(f"  Web CPU ({web_cpu} vCPU × {web_replicas} replicas): ${web_cpu_cost:.2f}")
    print(f"  PostgreSQL ({postgres_ram_gb}GB): ${postgres_cost:.2f}")
    print(f"  Redis ({redis_ram_gb}GB): ${redis_cost:.2f}")
    print(f"  Network ({network_gb}GB egress): ${network_cost:.2f}")
    print(f"  ---")
    print(f"  Total: ${total:.2f}/month")
    
    if total <= 5.0:
        print(f"  ✅ Covered by free tier ($5/month credit)")
    else:
        print(f"  💰 Cost above free tier: ${total - 5:.2f}/month")
    
    return total

if __name__ == "__main__":
    # Default: Production configuration
    estimate_monthly_cost(
        web_ram_gb=1.0,
        web_replicas=2,
        web_cpu=1.0,
        postgres_ram_gb=2.0,
        redis_ram_gb=0.5,
        network_gb=10,
    )
    
    print("\n" + "=" * 50 + "\n")
    
    # Staging configuration
    print("Staging Configuration:")
    estimate_monthly_cost(
        web_ram_gb=0.5,
        web_replicas=1,
        web_cpu=0.5,
        postgres_ram_gb=1.0,
        redis_ram_gb=0.5,
        network_gb=5,
    )
```

## Best Practices

### ✅ DO:

1. Start with minimal resources and scale up
2. Monitor resource usage weekly
3. Use ephemeral PR environments
4. Enable auto-destroy for PR environments
5. Implement aggressive caching
6. Optimize database queries
7. Use compression for API responses
8. Right-size all services based on metrics
9. Clean up old data regularly
10. Review billing monthly

### ❌ DON'T:

1. Over-provision resources "just in case"
2. Leave unused environments running
3. Keep PR environments after merge
4. Ignore slow queries
5. Serve large static files from Railway
6. Run staging 24/7 if not needed
7. Skip database optimization
8. Forget to enable compression
9. Keep all historical data forever
10. Ignore cost alerts

## Quick Wins

**Immediate cost savings:**

1. **Enable PR auto-destroy**: Save $5-10/month
   ```bash
   # Railway Dashboard → Settings → GitHub → PR Deployments
   # Enable "Auto-destroy on close"
   ```

2. **Scale down staging nights/weekends**: Save $2-3/month
   ```bash
   railway down -e staging  # When not in use
   ```

3. **Optimize database size**: Save $0.25/GB/month
   ```sql
   DELETE FROM logs WHERE created_at < NOW() - INTERVAL '90 days';
   VACUUM FULL;
   ```

4. **Enable response compression**: Reduce network costs by 60-80%
   ```python
   app.add_middleware(GZipMiddleware)
   ```

5. **Implement caching**: Reduce compute and external API costs
   ```python
   @cache(expire=300)
   async def expensive_function():
       pass
   ```

---

**Next Steps:**
- Implement [Monitoring & Logging](./monitoring_logging.md)
- Review [Railway CLI & Scripts](./cli_scripts.md)
- Set up [Configuration Management](./configuration_management.md)
