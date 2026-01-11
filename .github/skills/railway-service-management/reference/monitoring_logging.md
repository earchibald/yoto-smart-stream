# Monitoring & Logging on Railway

## Overview

Effective monitoring and logging are essential for maintaining healthy production services. This guide covers Railway's built-in capabilities and integration with external monitoring tools.

## Railway Built-in Monitoring

### Metrics Dashboard

Railway provides real-time metrics for each service:

**Available Metrics:**
- CPU usage (percentage)
- Memory usage (MB/GB)
- Network bandwidth (in/out)
- Request count
- Deployment status

**Accessing Metrics:**
```bash
# Via Railway Dashboard
# Project → Environment → Service → Metrics tab

# Via Railway CLI
railway status -e production
```

### Resource Usage

```bash
# Check current resource usage
railway status -e production --json | jq '.services[] | {name: .name, cpu: .cpu, memory: .memory}'
```

## Logging

### Railway Logs

Railway captures and aggregates all stdout/stderr output.

**Accessing Logs:**
```bash
# Stream logs in real-time
railway logs -e production

# Filter logs
railway logs -e production --filter "ERROR"
railway logs -e production --filter "request_id"

# Follow logs (continuously)
railway logs -e production --follow

# View specific service
railway logs -s web -e production

# View specific deployment
railway logs --deployment [DEPLOYMENT_ID]

# Limit number of lines
railway logs -e production --tail 100
```

### Structured Logging

```python
# logging_config.py - Structured JSON logging
import logging
import json
import sys
from datetime import datetime
import os

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for better parsing"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": os.getenv("RAILWAY_SERVICE_NAME", "unknown"),
            "environment": os.getenv("RAILWAY_ENVIRONMENT_NAME", "unknown"),
            "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID", "unknown"),
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        
        return json.dumps(log_data)


def setup_logging():
    """Configure application logging"""
    
    # Create logger
    logger = logging.getLogger()
    
    # Set level from environment
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level))
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler with JSON formatter
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger

# Initialize logging
logger = setup_logging()
```

### Application Logging

```python
# main.py - FastAPI with structured logging
from fastapi import FastAPI, Request
import logging
import uuid
import time

app = FastAPI()
logger = logging.getLogger(__name__)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests"""
    
    # Generate request ID
    request_id = str(uuid.uuid4())
    
    # Log request
    logger.info(
        "Incoming request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client": request.client.host,
        }
    )
    
    # Process request
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    # Log response
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "status_code": response.status_code,
            "duration_ms": int(duration * 1000),
        }
    )
    
    return response

@app.get("/")
async def root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello World"}

@app.get("/error")
async def error_endpoint():
    logger.error("Intentional error triggered")
    raise Exception("Test error")
```

## External Monitoring Services

### Sentry (Error Tracking)

**Setup:**
```python
# sentry_config.py
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
import os

def init_sentry():
    """Initialize Sentry error tracking"""
    
    sentry_dsn = os.getenv("SENTRY_DSN")
    if not sentry_dsn:
        return
    
    environment = os.getenv("RAILWAY_ENVIRONMENT_NAME", "development")
    
    sentry_sdk.init(
        dsn=sentry_dsn,
        environment=environment,
        integrations=[FastApiIntegration()],
        
        # Performance monitoring
        traces_sample_rate=1.0 if environment == "development" else 0.1,
        
        # Release tracking
        release=os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown"),
        
        # Additional context
        before_send=add_context,
    )

def add_context(event, hint):
    """Add additional context to Sentry events"""
    
    event["extra"] = {
        **event.get("extra", {}),
        "deployment_id": os.getenv("RAILWAY_DEPLOYMENT_ID"),
        "service_name": os.getenv("RAILWAY_SERVICE_NAME"),
    }
    
    return event

# Initialize on import
init_sentry()
```

**Usage:**
```python
from sentry_sdk import capture_exception, capture_message

try:
    # Risky operation
    result = process_data()
except Exception as e:
    capture_exception(e)
    raise

# Manual error reporting
capture_message("Something unusual happened", level="warning")
```

**Railway Configuration:**
```bash
# Add Sentry DSN to Railway
railway variables set SENTRY_DSN="https://xxx@xxx.ingest.sentry.io/xxx" -e production
```

### Uptime Monitoring

**Using UptimeRobot (Free Tier):**

1. Sign up at https://uptimerobot.com
2. Add HTTP(s) monitor
3. URL: `https://your-app.up.railway.app/health`
4. Interval: 5 minutes
5. Set up alerts (email, Slack, etc.)

**Health Check Endpoint:**
```python
from fastapi import FastAPI, status
from datetime import datetime
import os

app = FastAPI()

@app.get("/health")
async def health_check():
    """Health check endpoint for uptime monitoring"""
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": os.getenv("RAILWAY_SERVICE_NAME"),
        "version": os.getenv("RAILWAY_GIT_COMMIT_SHA", "unknown")[:7],
    }

@app.get("/health/detailed")
async def detailed_health():
    """Detailed health check with dependencies"""
    
    # Check database
    db_healthy = await check_database()
    
    # Check Redis
    redis_healthy = await check_redis()
    
    # Check external APIs
    yoto_api_healthy = await check_yoto_api()
    
    all_healthy = db_healthy and redis_healthy and yoto_api_healthy
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "checks": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy",
            "yoto_api": "healthy" if yoto_api_healthy else "unhealthy",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
```

### Application Performance Monitoring (APM)

**Using New Relic:**

```python
# newrelic_config.py
import newrelic.agent
import os

def init_newrelic():
    """Initialize New Relic APM"""
    
    license_key = os.getenv("NEW_RELIC_LICENSE_KEY")
    if not license_key:
        return
    
    newrelic.agent.initialize()

# main.py
from newrelic_config import init_newrelic

init_newrelic()

# Railway configuration
# railway variables set NEW_RELIC_LICENSE_KEY="xxx" -e production
# railway variables set NEW_RELIC_APP_NAME="yoto-smart-stream" -e production
```

## Custom Metrics

### Prometheus Metrics

```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import FastAPI, Response
import time

app = FastAPI()

# Define metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

YOTO_API_CALLS = Counter(
    'yoto_api_calls_total',
    'Total Yoto API calls',
    ['endpoint', 'status']
)

@app.middleware("http")
async def track_metrics(request, call_next):
    """Track request metrics"""
    
    ACTIVE_CONNECTIONS.inc()
    
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)
    
    ACTIVE_CONNECTIONS.dec()
    
    return response

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type="text/plain"
    )

# Usage in code
def call_yoto_api(endpoint):
    try:
        response = requests.get(f"https://api.yotoplay.com{endpoint}")
        YOTO_API_CALLS.labels(endpoint=endpoint, status="success").inc()
        return response
    except Exception:
        YOTO_API_CALLS.labels(endpoint=endpoint, status="error").inc()
        raise
```

## Log Aggregation

### Shipping Logs to External Service

**Using Logstash/Fluentd:**

```python
# fluent_logger.py
from fluent import sender
import logging
import os

class FluentHandler(logging.Handler):
    """Send logs to Fluentd"""
    
    def __init__(self):
        super().__init__()
        self.sender = sender.FluentSender(
            'yoto-smart-stream',
            host=os.getenv('FLUENTD_HOST', 'localhost'),
            port=int(os.getenv('FLUENTD_PORT', 24224))
        )
    
    def emit(self, record):
        """Send log record to Fluentd"""
        data = {
            'level': record.levelname,
            'message': record.getMessage(),
            'timestamp': record.created,
            'service': os.getenv('RAILWAY_SERVICE_NAME'),
            'environment': os.getenv('RAILWAY_ENVIRONMENT'),
        }
        
        self.sender.emit(record.levelname.lower(), data)

# Add to logger
logger = logging.getLogger()
logger.addHandler(FluentHandler())
```

**Using Papertrail:**

```bash
# Forward Railway logs to Papertrail
# Via Railway Dashboard: Add log drain
# Settings → Log Drains → Add Drain
# Type: Syslog
# Host: logs.papertrailapp.com
# Port: [your port]
```

## Alerting

### Setting Up Alerts

**Slack Webhook:**

```python
# alerts.py
import requests
import os

SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

def send_alert(message: str, level: str = "warning"):
    """Send alert to Slack"""
    
    if not SLACK_WEBHOOK_URL:
        return
    
    emoji = {
        "info": ":information_source:",
        "warning": ":warning:",
        "error": ":rotating_light:",
        "success": ":white_check_mark:",
    }
    
    payload = {
        "text": f"{emoji.get(level, ':bell:')} {message}",
        "username": "Railway Alert Bot",
    }
    
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except Exception as e:
        print(f"Failed to send alert: {e}")

# Usage
from alerts import send_alert

# Alert on high error rate
error_count = get_error_count_last_hour()
if error_count > 100:
    send_alert(
        f"High error rate detected: {error_count} errors in last hour",
        level="error"
    )
```

### Error Rate Monitoring

```python
# error_monitor.py
from collections import deque
from datetime import datetime, timedelta
import threading

class ErrorRateMonitor:
    """Monitor error rate and alert when threshold exceeded"""
    
    def __init__(self, threshold=10, window_minutes=5):
        self.threshold = threshold
        self.window = timedelta(minutes=window_minutes)
        self.errors = deque()
        self.lock = threading.Lock()
    
    def record_error(self):
        """Record an error occurrence"""
        with self.lock:
            now = datetime.utcnow()
            
            # Remove old errors outside window
            while self.errors and self.errors[0] < now - self.window:
                self.errors.popleft()
            
            # Add new error
            self.errors.append(now)
            
            # Check threshold
            if len(self.errors) >= self.threshold:
                self._alert()
    
    def _alert(self):
        """Send alert when threshold exceeded"""
        from alerts import send_alert
        send_alert(
            f"Error rate threshold exceeded: {len(self.errors)} errors in {self.window.seconds / 60} minutes",
            level="error"
        )

# Global monitor
error_monitor = ErrorRateMonitor(threshold=10, window_minutes=5)

# Usage in exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    error_monitor.record_error()
    # ... handle exception
```

## Performance Monitoring

### Response Time Tracking

```python
# performance.py
import time
from functools import wraps
import logging

logger = logging.getLogger(__name__)

def track_performance(threshold_ms=1000):
    """Decorator to track function performance"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start) * 1000
            
            if duration_ms > threshold_ms:
                logger.warning(
                    f"Slow operation: {func.__name__}",
                    extra={
                        "function": func.__name__,
                        "duration_ms": int(duration_ms),
                    }
                )
            
            return result
        return wrapper
    return decorator

# Usage
@track_performance(threshold_ms=500)
async def get_yoto_players():
    # ... API call
    pass
```

### Database Query Monitoring

```python
# db_monitor.py
from sqlalchemy import event
from sqlalchemy.engine import Engine
import logging
import time

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Track query start time"""
    conn.info.setdefault('query_start_time', []).append(time.time())
    
@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Log slow queries"""
    total = time.time() - conn.info['query_start_time'].pop()
    
    if total > 1.0:  # Queries taking > 1 second
        logger.warning(
            "Slow database query",
            extra={
                "duration_ms": int(total * 1000),
                "query": statement[:200],  # Truncate long queries
            }
        )
```

## Monitoring Checklist

### Production Monitoring Setup

- [ ] Health check endpoint implemented
- [ ] Structured logging configured
- [ ] Log level set appropriately (WARNING or ERROR)
- [ ] Sentry error tracking enabled
- [ ] Uptime monitoring configured (UptimeRobot, Pingdom)
- [ ] Alerts set up (Slack, email)
- [ ] Performance metrics tracked
- [ ] Database query monitoring enabled
- [ ] Resource usage monitored (CPU, memory)
- [ ] Error rate alerting configured

### Monitoring Dashboard

Create a simple monitoring dashboard:

```python
# dashboard.py
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import psutil
import os

app = FastAPI()

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Simple monitoring dashboard"""
    
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    html = f"""
    <html>
        <head><title>Service Dashboard</title></head>
        <body>
            <h1>Yoto Smart Stream - Status Dashboard</h1>
            <h2>Service Info</h2>
            <ul>
                <li>Environment: {os.getenv('RAILWAY_ENVIRONMENT')}</li>
                <li>Service: {os.getenv('RAILWAY_SERVICE_NAME')}</li>
                <li>Deployment: {os.getenv('RAILWAY_DEPLOYMENT_ID')[:8]}</li>
            </ul>
            
            <h2>Resource Usage</h2>
            <ul>
                <li>CPU: {cpu_percent}%</li>
                <li>Memory: {memory.percent}%</li>
                <li>Memory Used: {memory.used / 1024 / 1024:.0f} MB</li>
            </ul>
            
            <h2>Quick Links</h2>
            <ul>
                <li><a href="/health">Health Check</a></li>
                <li><a href="/metrics">Metrics</a></li>
                <li><a href="/docs">API Documentation</a></li>
            </ul>
        </body>
    </html>
    """
    
    return html
```

## Best Practices

### ✅ DO:

1. Use structured (JSON) logging for better parsing
2. Include request IDs for tracing
3. Log at appropriate levels (DEBUG in dev, WARNING+ in prod)
4. Implement comprehensive health checks
5. Set up external error tracking (Sentry)
6. Monitor resource usage regularly
7. Create alerts for critical errors
8. Track performance metrics
9. Keep logs searchable and queryable
10. Regular review of logs and metrics

### ❌ DON'T:

1. Log sensitive information (passwords, tokens)
2. Use verbose logging in production
3. Ignore error alerts
4. Skip health check endpoints
5. Log everything (creates noise)
6. Forget to rotate logs
7. Ignore slow query warnings
8. Skip performance monitoring
9. Use print() instead of logging
10. Ignore monitoring best practices

---

**Next Steps:**
- Review [Cost Optimization](./cost_optimization.md)
- Explore [Railway CLI & Scripts](./cli_scripts.md)
- Implement [Secrets Management](./secrets_management.md)
