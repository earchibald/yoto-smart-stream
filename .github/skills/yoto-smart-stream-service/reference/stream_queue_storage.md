# Stream Queue Storage Architecture

## Overview

The Yoto Smart Stream service manages **dynamic audio playlists** (called "streams") that users can create to customize playback. Stream configurations must be efficiently managed across different deployment environments with varying storage constraints.

## Architecture Decision

### Problem Statement

The service was originally designed to use `/data/streams` for persistent storage, which worked on Railway (which provided a persistent volume at `/data`) but fails on AWS Lambda where:
- The filesystem is **read-only** at deploy time
- `/data` doesn't exist
- `/tmp` is the only writable location (512MB, ephemeral)

### Solution: Environment-Aware Storage

The `StreamManager` class now **auto-detects the environment** and uses the appropriate storage backend:

```python
# Automatic detection based on environment variables
if AWS_LAMBDA_FUNCTION_NAME is set:
    storage_dir = /tmp/streams  # Ephemeral
else:
    storage_dir = ./streams     # Persistent (local development)
```

## Storage Backends

### 1. Lambda / AWS Production

**Location:** `/tmp/streams` (ephemeral)

**Characteristics:**
- In-memory queues (survive within single request)
- Persisted to `/tmp` only for recovery on container restart
- Queues lost on Lambda cold start
- Typical lifetime: minutes to hours per container
- Safe fallback: in-memory only

**Why this works:**
- Streams are **user-session-specific** - created dynamically
- Users don't expect persistence across service deployments
- Even if lost, users can recreate their streams immediately
- In-memory operation is sufficient for streaming use case

**Improvements for Production (Future):**
If persistence is needed across deployments, consider:
- **DynamoDB**: Store stream configurations as items (backup/restore functionality)
- **S3**: Store serialized queue definitions as JSON objects
- **SessionDB**: Store temporary streams in DynamoDB with TTL

### 2. Local Development

**Location:** `./streams` (filesystem)

**Characteristics:**
- Persistent JSON files for each stream
- Format: `./streams/{stream_name}.json`
- Survives service restarts
- Development convenience

**Typical file content:**
```json
{
  "name": "my-playlist",
  "files": ["song1.mp3", "song2.mp3", "song3.mp3"],
  "loop": false
}
```

### 3. Graceful Degradation

If the storage directory cannot be created (permission denied, read-only filesystem), the system:
1. **Logs a warning** (not an error)
2. **Continues with in-memory storage** only
3. **Returns empty list** instead of 500 error
4. Users can still create and manage streams in the session

## Implementation Details

### StreamManager Class

```python
class StreamManager:
    def __init__(self, storage_dir: Optional[Path] = None):
        # Auto-detect environment
        self._is_lambda = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
        
        # Set storage location
        if storage_dir:
            self._storage_dir = storage_dir  # Override (testing)
        elif self._is_lambda:
            self._storage_dir = Path("/tmp/streams")
        else:
            self._storage_dir = Path("./streams")
        
        # Try to initialize storage, but don't fail if it's not writable
        self._storage_enabled = self._init_storage()
    
    def _init_storage(self) -> bool:
        """Returns True if storage is available, False if degraded to in-memory"""
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_queues_from_disk()
            return True
        except (OSError, PermissionError):
            logger.warning(f"Storage unavailable at {self._storage_dir}, using in-memory only")
            return False
    
    def _save_queue_to_disk(self, queue: StreamQueue) -> None:
        """Only saves if storage is enabled"""
        if not self._storage_enabled:
            return
        # ... write to disk ...
```

### API Response Behavior

The `/streams/queues` endpoint **always returns a valid response**:

```python
@router.get("/streams/queues", response_model=QueuesListResponse)
async def list_stream_queues(user: User = Depends(require_auth)):
    """Returns {"queues": [], "count": 0} if no streams or storage unavailable"""
    stream_manager = get_stream_manager()
    queues = await stream_manager.list_queues()  # Returns empty list gracefully
    return {"queues": queues, "count": len(queues)}
```

## Configuration

### Environment Variables

The storage location is determined automatically, but can be overridden:

```bash
# Lambda (auto-detected) - uses /tmp/streams
AWS_LAMBDA_FUNCTION_NAME=yoto-api-dev

# Local development (auto-detected) - uses ./streams
# (no AWS_LAMBDA_FUNCTION_NAME set)

# Override for testing
STREAM_STORAGE_DIR=/custom/path/streams
```

Currently, the environment variable override is **not implemented** (storage_dir parameter is optional in tests only).

## Migration Scenarios

### From Railway to Lambda

If migrating stream definitions from Railway (`/data/streams` JSON files):

1. **Extract streams** from Railway `/data/streams/*.json`
2. **Parse stream definitions** (file lists, loop flags)
3. **Store in DynamoDB** (if persistent storage is needed)
4. **Or:** Users recreate streams in new deployment (simpler for most cases)

### Within Lambda Deployments

Streams created during one Lambda container's lifetime:
- **Lost on new cold start** (expected, acceptable)
- **Persist within warm container** (in-memory)
- **Can recover from /tmp** if container reuses same instance

## Testing

Test the storage behavior:

```python
import os
from yoto_smart_stream.api.stream_manager import StreamManager

# Test 1: Local development mode
manager = StreamManager()
assert str(manager._storage_dir).endswith("streams")
assert manager._storage_enabled is True

# Test 2: Lambda environment
os.environ["AWS_LAMBDA_FUNCTION_NAME"] = "test"
manager = StreamManager()
assert str(manager._storage_dir) == "/tmp/streams"
```

## Monitoring & Observability

The StreamManager logs storage status:

```
INFO: StreamManager in local development - using ./streams directory
INFO: StreamManager running on Lambda - using ephemeral storage at /tmp/streams
WARNING: Failed to create/access storage directory /data/streams: [Errno 30] Read-only file system
INFO: StreamManager storage initialized at /tmp/streams
```

Monitor logs for storage warnings to detect permission issues.

## Future Improvements

1. **DynamoDB Persistence** (Optional)
   - Store stream definitions as DynamoDB items
   - Allow cross-deployment persistence
   - Add backup/restore functionality

2. **S3 Backup** (Optional)
   - Export/import stream definitions to S3
   - Enable sharing between environments

3. **Session-based Storage**
   - Store temporary streams in Cognito user session
   - Auto-cleanup on session expiration

4. **Configuration Options**
   - Allow users to choose persistence level
   - Environment variable for storage backend selection
