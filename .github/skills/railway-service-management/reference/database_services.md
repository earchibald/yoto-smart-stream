# Database & Services Management on Railway

## Overview

This guide covers managing databases, caching services, and other infrastructure components on Railway, including PostgreSQL, Redis, and service-to-service communication.

## PostgreSQL on Railway

### Adding PostgreSQL

```bash
# Via Railway CLI
railway add --plugin postgresql -e production

# Via Railway Dashboard
# Project → Environment → New → PostgreSQL Plugin
```

### PostgreSQL Variables

Railway automatically creates these variables when you add PostgreSQL:

```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
PGHOST=postgres.railway.internal
PGPORT=5432
PGUSER=postgres
PGPASSWORD=randomly_generated
PGDATABASE=railway
```

### Connecting to PostgreSQL

```python
# Using DATABASE_URL (recommended)
import os
from sqlalchemy import create_engine

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# Or with psycopg2
import psycopg2

conn = psycopg2.connect(os.getenv("DATABASE_URL"))
```

### Direct Database Access

```bash
# Connect via Railway CLI
railway connect postgres -e production

# Or use connection string
psql $DATABASE_URL
```

### Database Migrations

```bash
# Using Alembic
railway run -e production alembic upgrade head

# Using Django
railway run -e production python manage.py migrate

# Using custom script
railway run -e production python scripts/migrate.py
```

## Redis on Railway

### Adding Redis

```bash
# Via Railway CLI
railway add --plugin redis -e production

# Via Railway Dashboard
# Project → Environment → New → Redis Plugin
```

### Redis Variables

```bash
REDIS_URL=redis://default:password@host:port
REDIS_HOST=redis.railway.internal
REDIS_PORT=6379
REDIS_PASSWORD=randomly_generated
```

### Connecting to Redis

```python
# Using redis-py
import os
import redis

REDIS_URL = os.getenv("REDIS_URL")
redis_client = redis.from_url(REDIS_URL)

# Test connection
redis_client.ping()

# Set/Get values
redis_client.set("key", "value")
value = redis_client.get("key")
```

### Redis Use Cases

**Caching:**
```python
# cache.py
import redis
import json
import os
from functools import wraps

redis_client = redis.from_url(os.getenv("REDIS_URL"))

def cache_result(ttl=300):
    """Decorator to cache function results"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = f"{func.__name__}:{args}:{kwargs}"
            
            # Check cache
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Call function
            result = func(*args, **kwargs)
            
            # Store in cache
            redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result)
            )
            
            return result
        return wrapper
    return decorator

# Usage
@cache_result(ttl=600)
def get_yoto_players():
    # Expensive API call
    return yoto_manager.get_players()
```

**Session Storage:**
```python
# sessions.py
from fastapi import FastAPI, Depends, Cookie
import redis
import json
import uuid

app = FastAPI()
redis_client = redis.from_url(os.getenv("REDIS_URL"))

def get_session(session_id: str = Cookie(None)):
    """Get session data from Redis"""
    if not session_id:
        return {}
    
    data = redis_client.get(f"session:{session_id}")
    return json.loads(data) if data else {}

def set_session(session_id: str, data: dict, ttl=3600):
    """Store session data in Redis"""
    redis_client.setex(
        f"session:{session_id}",
        ttl,
        json.dumps(data)
    )

@app.post("/login")
async def login(username: str, password: str):
    # Authenticate user
    # ...
    
    # Create session
    session_id = str(uuid.uuid4())
    set_session(session_id, {"username": username})
    
    return {"session_id": session_id}
```

**Task Queues:**
```python
# Using RQ (Redis Queue)
from redis import Redis
from rq import Queue
import os

redis_conn = Redis.from_url(os.getenv("REDIS_URL"))
queue = Queue(connection=redis_conn)

# Enqueue task
job = queue.enqueue('tasks.process_audio', audio_file_id)

# Worker (separate process)
# railway run -e production rq worker
```

## Service-to-Service Communication

### Internal Networking

```python
# Services in same environment can communicate via internal URLs
# Example: web service calling API service

import os
import httpx

# Use Railway's private domain for internal communication
INTERNAL_API_URL = os.getenv("INTERNAL_API_URL")  # ${{API.RAILWAY_PRIVATE_DOMAIN}}

async def call_internal_api():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://{INTERNAL_API_URL}/internal/data")
        return response.json()
```

### Service Dependencies

```toml
# railway.toml
[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"

# Service depends on PostgreSQL and Redis
# Configure via reference variables in Railway dashboard:
# DATABASE_URL=${{Postgres.DATABASE_URL}}
# REDIS_URL=${{Redis.REDIS_URL}}
```

## Database Backups

### Automatic Backups

Railway provides automatic daily backups for all database plugins.

**Features:**
- Daily automatic backups
- Retained for 7 days (free tier) or longer (paid plans)
- Point-in-time recovery available

### Manual Backups

```bash
# Create manual backup before critical operations
railway run -e production pg_dump > backup_$(date +%Y%m%d_%H%M%S).sql

# Backup with compression
railway run -e production pg_dump | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup specific tables
railway run -e production pg_dump -t users -t cards > partial_backup.sql
```

### Restore from Backup

```bash
# Restore from backup file
cat backup_20240110_120000.sql | railway run -e staging psql

# Restore compressed backup
gunzip -c backup.sql.gz | railway run -e staging psql
```

### Backup Automation Script

```bash
#!/bin/bash
# scripts/backup-database.sh - Automated database backup

set -e

ENVIRONMENT=${1:-production}
BACKUP_DIR="backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_${ENVIRONMENT}_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Creating backup for $ENVIRONMENT..."

# Create backup
railway run -e "$ENVIRONMENT" pg_dump | gzip > "$BACKUP_FILE"

echo "✅ Backup created: $BACKUP_FILE"

# Optional: Upload to S3 or other storage
# aws s3 cp "$BACKUP_FILE" s3://my-backups/

# Optional: Clean old backups (keep last 30 days)
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +30 -delete

echo "✅ Backup complete"
```

## Database Migrations

### Migration Strategy

1. **Backward Compatible** - New code works with old and new schema
2. **Forward Compatible** - Old code works with new schema
3. **Multi-Step** - For breaking changes, deploy in phases

### Using Alembic (SQLAlchemy)

```bash
# Initialize Alembic
alembic init alembic

# Create migration
alembic revision --autogenerate -m "Add user_preferences table"

# Apply migrations (staging)
railway run -e staging alembic upgrade head

# Verify in staging
railway run -e staging python scripts/verify_schema.py

# Apply migrations (production)
railway run -e production alembic upgrade head

# Rollback if needed
railway run -e production alembic downgrade -1
```

### Migration Script Template

```python
# migrations/001_add_feature.py
"""
Migration: Add new feature table

Backward compatible: Yes
Forward compatible: Yes
"""

def upgrade(connection):
    """Apply migration"""
    connection.execute("""
        CREATE TABLE IF NOT EXISTS feature_flags (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) UNIQUE NOT NULL,
            enabled BOOLEAN DEFAULT false,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    # Add initial data
    connection.execute("""
        INSERT INTO feature_flags (name, enabled)
        VALUES ('mqtt_enabled', true);
    """)

def downgrade(connection):
    """Rollback migration"""
    connection.execute("DROP TABLE IF EXISTS feature_flags;")
```

### Safe Migration Workflow

```bash
#!/bin/bash
# scripts/safe-migrate.sh - Safe migration deployment

set -e

ENVIRONMENT=${1:-staging}

echo "🔍 Checking migrations for $ENVIRONMENT..."

# 1. Backup database
echo "Creating backup..."
./scripts/backup-database.sh "$ENVIRONMENT"

# 2. Check pending migrations
echo "Checking pending migrations..."
railway run -e "$ENVIRONMENT" alembic current
railway run -e "$ENVIRONMENT" alembic history

# 3. Confirm
read -p "Apply migrations to $ENVIRONMENT? (yes/no): " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted"
    exit 0
fi

# 4. Apply migrations
echo "Applying migrations..."
railway run -e "$ENVIRONMENT" alembic upgrade head

# 5. Verify
echo "Verifying database schema..."
railway run -e "$ENVIRONMENT" python scripts/verify_schema.py

echo "✅ Migrations completed successfully"
```

## Connection Pooling

### PostgreSQL Connection Pooling

```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool
import os

DATABASE_URL = os.getenv("DATABASE_URL")

# Configure connection pool
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # Number of connections to keep open
    max_overflow=20,       # Max additional connections when pool is full
    pool_timeout=30,       # Timeout waiting for connection
    pool_recycle=3600,     # Recycle connections after 1 hour
    pool_pre_ping=True,    # Verify connections before using
)
```

### Redis Connection Pooling

```python
# redis_client.py
import redis
import os

# Connection pool is automatic with redis-py
redis_client = redis.from_url(
    os.getenv("REDIS_URL"),
    max_connections=50,
    socket_timeout=5,
    socket_connect_timeout=5,
    decode_responses=True
)
```

## Database Performance

### Indexing

```sql
-- Add indexes for frequently queried columns
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_cards_user_id ON cards(user_id);
CREATE INDEX idx_events_created_at ON events(created_at DESC);

-- Composite indexes
CREATE INDEX idx_cards_user_status ON cards(user_id, status);
```

### Query Optimization

```python
# Use select_related for foreign keys (Django)
users = User.objects.select_related('profile').all()

# Use prefetch_related for many-to-many
users = User.objects.prefetch_related('cards').all()

# Limit results
cards = Card.objects.all()[:100]

# Use database aggregation
from django.db.models import Count
user_counts = User.objects.annotate(card_count=Count('cards'))
```

### Monitoring Queries

```python
# Log slow queries
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

@event.listens_for(Engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info.setdefault('query_start_time', []).append(time.time())

@event.listens_for(Engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - conn.info['query_start_time'].pop()
    if total > 1.0:  # Log queries taking > 1 second
        logger.warning(f"Slow query ({total:.2f}s): {statement}")
```

## Service Health Checks

### Database Health Check

```python
# health.py
from fastapi import FastAPI, status
from sqlalchemy import text
import redis

app = FastAPI()

@app.get("/health/database")
async def database_health():
    """Check database connectivity"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "healthy", "service": "database"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "database",
            "error": str(e)
        }

@app.get("/health/redis")
async def redis_health():
    """Check Redis connectivity"""
    try:
        redis_client.ping()
        return {"status": "healthy", "service": "redis"}
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "redis",
            "error": str(e)
        }

@app.get("/health")
async def overall_health():
    """Overall health check"""
    db_healthy = await database_health()
    redis_healthy = await redis_health()
    
    all_healthy = (
        db_healthy["status"] == "healthy" and
        redis_healthy["status"] == "healthy"
    )
    
    return {
        "status": "healthy" if all_healthy else "degraded",
        "services": {
            "database": db_healthy["status"],
            "redis": redis_healthy["status"],
        }
    }
```

## Resource Limits

### PostgreSQL

```bash
# Monitor database size
railway run -e production psql -c "
    SELECT
        pg_size_pretty(pg_database_size(current_database())) as size;
"

# Monitor connection count
railway run -e production psql -c "
    SELECT count(*) FROM pg_stat_activity;
"

# Monitor table sizes
railway run -e production psql -c "
    SELECT
        relname as table_name,
        pg_size_pretty(pg_total_relation_size(relid)) as total_size
    FROM pg_catalog.pg_statio_user_tables
    ORDER BY pg_total_relation_size(relid) DESC
    LIMIT 10;
"
```

### Redis

```bash
# Check Redis memory usage
railway run -e production redis-cli INFO memory

# Check key count
railway run -e production redis-cli DBSIZE

# Monitor commands
railway run -e production redis-cli MONITOR
```

## Best Practices

### ✅ DO:

1. Use Railway's reference variables for service URLs
2. Implement connection pooling
3. Create database backups before migrations
4. Use indexes on frequently queried columns
5. Monitor database and Redis performance
6. Implement health checks for all services
7. Use transactions for multi-step operations
8. Clean up old data regularly
9. Test migrations in staging first
10. Use read replicas for heavy read workloads (paid plans)

### ❌ DON'T:

1. Hardcode database credentials
2. Skip database backups
3. Run migrations without testing
4. Store large files in database (use object storage)
5. Use SELECT * in production code
6. Skip indexing on large tables
7. Keep all data forever (implement retention policies)
8. Use database for session storage (use Redis)
9. Ignore slow query logs
10. Share databases between environments

---

**Next Steps:**
- Set up [Monitoring & Logging](./monitoring_logging.md)
- Review [Cost Optimization](./cost_optimization.md)
- Explore [Railway CLI & Scripts](./cli_scripts.md)
