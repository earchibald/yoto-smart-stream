# Migration Guide: From Examples to Production Server

This guide helps you migrate from using `examples/basic_server.py` to the production server in the `yoto_smart_stream` package.

## Quick Comparison

| Feature | Examples | Production |
|---------|----------|-----------|
| **Import** | `from examples.basic_server import app` | `from yoto_smart_stream.api import app` |
| **Run** | `python examples/basic_server.py` | `python -m yoto_smart_stream` |
| **Uvicorn** | `uvicorn examples.basic_server:app` | `uvicorn yoto_smart_stream.api:app` |

## Step-by-Step Migration

### Step 1: Update Environment Variables

The production server uses the same environment variables, so no changes needed:

```bash
# .env file (same for both)
YOTO_CLIENT_ID=your_client_id
PUBLIC_URL=https://your-server.com
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### Step 2: Update Import Statements

**Before (Examples)**:
```python
from examples.basic_server import app
```

**After (Production)**:
```python
from yoto_smart_stream.api import app
```

### Step 3: Update Run Commands

**Before (Examples)**:
```bash
# Direct execution
python examples/basic_server.py

# Uvicorn
uvicorn examples.basic_server:app --reload
```

**After (Production)**:
```bash
# Direct execution (recommended)
python -m yoto_smart_stream

# Uvicorn
uvicorn yoto_smart_stream.api:app --reload
```

### Step 4: Update Railway/Docker Configuration

**Before (Examples)**:
```toml
# railway.toml
[deploy]
startCommand = "uvicorn examples.basic_server:app --host 0.0.0.0 --port $PORT"
```

**After (Production)**:
```toml
# railway.toml  
[deploy]
startCommand = "uvicorn yoto_smart_stream.api:app --host 0.0.0.0 --port $PORT"
```

**Before (Examples)**:
```dockerfile
# Dockerfile
CMD ["uvicorn", "examples.basic_server:app", "--host", "0.0.0.0", "--port", "8080"]
```

**After (Production)**:
```dockerfile
# Dockerfile
CMD ["uvicorn", "yoto_smart_stream.api:app", "--host", "0.0.0.0", "--port", "8080"]
```

### Step 5: Update Tests (if applicable)

**Before (Examples)**:
```python
from examples.basic_server import app
from fastapi.testclient import TestClient

client = TestClient(app)
```

**After (Production)**:
```python
from yoto_smart_stream.api import app
from fastapi.testclient import TestClient

client = TestClient(app)
```

## API Compatibility

The production server maintains **100% API compatibility** with the examples. All endpoints work exactly the same:

- `GET /` - Web UI dashboard
- `GET /api/status` - API information
- `GET /api/health` - Health check
- `GET /api/players` - List players
- `POST /api/players/{id}/control` - Control player
- `GET /api/audio/{filename}` - Stream audio
- `POST /api/cards/create-streaming` - Create card

**No code changes needed in client applications!**

## What You Get with Production Server

### Better Structure
- Modular code organization
- Clear separation of concerns
- Easy to extend and maintain

### Enhanced Error Handling
- Detailed error messages
- Proper HTTP status codes
- Exception chaining for debugging

### Configuration Management
- Centralized settings with validation
- Environment-specific configs
- Type-safe configuration

### Dependency Injection
- Testable code
- Better isolation
- Easier mocking

### Logging
- Structured logging
- Configurable log levels
- Better debugging

## Backward Compatibility

### Examples Still Work

The `examples/` directory is still functional for learning and reference:
- `examples/simple_client.py` - Authentication
- `examples/basic_server.py` - Sample server (deprecated, use production)
- `examples/mqtt_listener.py` - MQTT monitoring
- `examples/icon_management.py` - Icon API usage

### When to Use Examples vs Production

**Use Examples For**:
- Learning the Yoto API
- Quick prototyping
- Understanding specific features
- Testing authentication flow

**Use Production Server For**:
- Deployed applications
- Long-running services
- Production environments
- Team projects
- Applications requiring maintenance

## Troubleshooting Migration

### Issue: Import Errors

**Problem**: `ModuleNotFoundError: No module named 'yoto_smart_stream'`

**Solution**:
```bash
# Install in development mode
pip install -e .

# Or reinstall
pip install -r requirements.txt
```

### Issue: Configuration Not Loading

**Problem**: `ValidationError: 1 validation error for Settings`

**Solution**:
```bash
# Check environment variables
echo $YOTO_CLIENT_ID

# Or use .env file
cp .env.example .env
# Edit .env with your values
```

### Issue: Authentication Failing

**Problem**: `FileNotFoundError: Refresh token file not found`

**Solution**:
```bash
# Run authentication first
python examples/simple_client.py

# This creates .yoto_refresh_token file
ls -la .yoto_refresh_token
```

### Issue: Different Behavior

**Problem**: Production server behaves differently than examples

**Solution**:
1. Check configuration in `yoto_smart_stream/config.py`
2. Verify environment variables match
3. Check logs for detailed error messages
4. Review API documentation at `/docs` endpoint

## Need Help?

### Resources
- **Production Server Docs**: See `PRODUCTION_SERVER_COMPLETE.md`
- **API Documentation**: Visit `/docs` endpoint
- **Configuration**: See `yoto_smart_stream/config.py`
- **Issues**: Open GitHub issue with details

### Common Questions

**Q: Do I need to change my database or data?**
A: No, the production server uses the same data structures.

**Q: Will my existing audio files work?**
A: Yes, same `audio_files/` directory structure.

**Q: Do I need to re-authenticate?**
A: No, same `.yoto_refresh_token` file is used.

**Q: Are the API endpoints the same?**
A: Yes, 100% compatible. No client changes needed.

**Q: Can I use both examples and production?**
A: Yes, but don't run both servers simultaneously (port conflict).

## Summary

✅ **Simple Migration** - Mostly just changing import and run commands
✅ **API Compatible** - No client-side changes needed
✅ **Better Code** - More maintainable and testable
✅ **Production Ready** - Proper error handling and logging
✅ **Backward Compatible** - Examples still work for learning

**Estimated Migration Time**: 5-10 minutes

---

**Next Steps After Migration**:
1. Test locally: `python -m yoto_smart_stream`
2. Verify health: `curl http://localhost:8080/health`
3. Check docs: Visit `http://localhost:8080/docs`
4. Deploy to Railway: See `PRODUCTION_SERVER_COMPLETE.md`