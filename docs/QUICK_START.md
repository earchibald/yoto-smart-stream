# Quick Start Guide - Getting Yoto Smart Stream Running

This guide will get you from zero to a running Yoto Smart Stream system in minutes.

## 🎯 Goal

By the end of this guide, you'll have:
- ✅ Installed Yoto Smart Stream
- ✅ Authenticated with the Yoto API
- ✅ Started the API server
- ✅ Connected your Yoto players
- ✅ Verified everything is working

## ⏱️ Time Required

- **Without Yoto Account**: 5 minutes (setup + testing)
- **With Yoto Account**: 10-15 minutes (full authentication + testing)

## 📋 Prerequisites Check

Before starting, ensure you have:

- [ ] Python 3.9 or higher installed
- [ ] pip package manager
- [ ] Git (for cloning the repository)
- [ ] A Yoto account (optional for initial testing)
- [ ] A Yoto Client ID from [yoto.dev](https://yoto.dev/get-started/start-here/) (optional initially)

### Check Your Python Version

```bash
python --version
# Should show: Python 3.9.x or higher
```

## 🚀 Installation Steps

### Step 1: Clone the Repository

```bash
# Clone the repository
git clone https://github.com/earchibald/yoto-smart-stream.git
cd yoto-smart-stream
```

**Expected output:**
```
Cloning into 'yoto-smart-stream'...
```

### Step 2: Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

**Expected output:**
You'll see `(venv)` prefix in your terminal.

### Step 3: Install Dependencies

```bash
# Install main dependencies
pip install -r requirements.txt

# Install development dependencies (for testing)
pip install -r requirements-dev.txt

# Or install everything at once:
pip install -e ".[dev]"
```

**Expected output:**
```
Successfully installed yoto-smart-stream-0.1.0 ...
```

### Step 4: Verify Installation

```bash
# Run tests to verify everything is working
pytest

# Expected output: All tests pass
# ====== 48 passed in X.XXs ======
```

**✅ Checkpoint:** If tests pass, installation is successful!

## 🔑 Authentication Setup

### Option A: Quick Test (No Yoto Account Needed)

You can test the system without Yoto credentials:

```bash
# Start the API server
python examples/basic_server.py
```

Visit http://localhost:8000/docs to explore the API.

**Note:** Most endpoints will return errors without authentication, but you can see the API structure.

### Option B: Full Setup (With Yoto Account)

For full functionality with real Yoto devices:

#### 1. Get Your Yoto Client ID

1. Visit [yoto.dev](https://yoto.dev/get-started/start-here/)
2. Sign up for a developer account
3. Create an application
4. Copy your Client ID

#### 2. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file and add your client ID
# YOTO_CLIENT_ID=your_client_id_here
```

Or set it directly:
```bash
export YOTO_CLIENT_ID=your_client_id_here
```

#### 3. Authenticate

```bash
# Run authentication flow
python examples/simple_client.py
```

**What will happen:**

1. The script will display a URL and code:
   ```
   ============================================================
   AUTHENTICATION REQUIRED
   ============================================================
   
   1. Go to: https://yoto.auth0.com/activate
   2. Enter code: ABCD-EFGH
   
   Waiting for authorization...
   ```

2. Visit the URL in your browser
3. Enter the code shown
4. Log in with your Yoto account
5. Approve the application

6. Wait 20-30 seconds. The script will:
   - Complete authentication
   - Save your refresh token to `.yoto_refresh_token`
   - Display your Yoto players
   - Connect to MQTT
   - Test basic controls

**Expected output:**
```
✓ Authentication successful!
✓ Refresh token saved to .yoto_refresh_token

============================================================
YOTO PLAYERS
============================================================

Player: Living Room
  ID: abc123
  Online: True
  Volume: 8/16
  Status: Not playing

✓ Connected to MQTT successfully!
```

**✅ Checkpoint:** If you see your players listed, authentication works!

## 🌐 Starting the API Server

### Start the Server

```bash
# Start the API server
python examples/basic_server.py

# Or using uvicorn directly:
uvicorn examples.basic_server:app --reload
```

**Expected output:**
```
✓ Yoto API connected successfully
✓ MQTT connected successfully
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Test the Server

Open your browser and visit:

1. **API Documentation**: http://localhost:8000/docs
   - Interactive Swagger UI
   - Try all endpoints
   - See request/response schemas

2. **Health Check**: http://localhost:8000/health
   ```json
   {
     "status": "healthy",
     "yoto_api": "connected"
   }
   ```

3. **List Players**: http://localhost:8000/api/players
   ```json
   [
     {
       "id": "abc123",
       "name": "Living Room",
       "online": true,
       "volume": 8,
       "playing": false,
       "battery_level": 85
     }
   ]
   ```

### Test Player Control (Using curl)

```bash
# Get player list
curl http://localhost:8000/api/players

# Pause a player
curl -X POST http://localhost:8000/api/players/YOUR_PLAYER_ID/control \
  -H "Content-Type: application/json" \
  -d '{"action": "pause"}'

# Set volume
curl -X POST http://localhost:8000/api/players/YOUR_PLAYER_ID/control \
  -H "Content-Type: application/json" \
  -d '{"action": "pause", "volume": 10}'
```

**✅ Checkpoint:** If you can control your player via the API, it's working!

## 📡 Testing MQTT Events

Open a second terminal and start the MQTT listener:

```bash
# Activate virtual environment in new terminal
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start MQTT listener
python examples/mqtt_listener.py
```

**What to do:**

1. Interact with your Yoto player:
   - Press play/pause
   - Change volume
   - Insert/remove a card
   - Press navigation buttons

2. Watch events appear in the terminal:
   ```
   ================================================================================
   Event #1 at 2026-01-10T10:30:45.123456
   Topic: yoto/players/abc123/playback/status
   Payload:
   {
     "state": "paused",
     "position": 120.5,
     "chapter": 1
   }
   ================================================================================
   ```

**✅ Checkpoint:** If you see events when interacting with your player, MQTT is working!

## 🎨 Testing Icon Management

The icon management module is fully implemented and tested. Here's how to explore it:

### View Available Icons

```python
# Create a test script: test_icons.py
import asyncio
from yoto_smart_stream.icons import IconClient, IconService

async def list_icons():
    # You'll need an access token (get from YotoManager after auth)
    async with IconClient(access_token="your_token") as client:
        service = IconService(client)
        
        # List public icons
        icons = await service.get_public_icons(per_page=10)
        
        for icon in icons.icons:
            print(f"- {icon.name}: {icon.url}")

# Run it
# asyncio.run(list_icons())
```

### Icon Module Tests

All icon functionality is tested:

```bash
# Run icon tests
pytest tests/icons/ -v

# Expected: 39 tests pass, 96% coverage
```

**✅ Checkpoint:** Icon module is fully implemented and tested!

## ✅ Verification Checklist

After completing this guide, verify:

- [ ] Python environment is set up
- [ ] Dependencies are installed
- [ ] All tests pass (`pytest`)
- [ ] Code quality checks pass (`ruff check .`)
- [ ] Authentication works (if using Yoto account)
- [ ] API server starts without errors
- [ ] Can access API documentation at http://localhost:8000/docs
- [ ] Can list Yoto players via API
- [ ] Can control players via API
- [ ] MQTT events are received
- [ ] Icon module tests pass

## 🎓 What You've Achieved

You now have:

✅ **A working API server** that can control Yoto players
✅ **Real-time event monitoring** via MQTT
✅ **Complete icon management** for Yoto Mini displays
✅ **Full test coverage** for all implemented features
✅ **Interactive API documentation** for exploration

## 📚 Next Steps

Now that everything is working, explore:

1. **[Testing Guide](TESTING_GUIDE.md)** - Comprehensive testing instructions
2. **[Icon Management Guide](ICON_MANAGEMENT.md)** - Working with display icons
3. **[API Documentation](http://localhost:8000/docs)** - Interactive API reference
4. **[Example Scripts](../examples/)** - More usage examples

## 🔧 Troubleshooting

### Server Won't Start

```bash
# Check if port 8000 is in use
# Linux/Mac:
lsof -i :8000

# Windows:
netstat -ano | findstr :8000

# Use a different port:
uvicorn examples.basic_server:app --port 8001
```

### Authentication Fails

```bash
# Verify client ID is set
echo $YOTO_CLIENT_ID

# Check if .env file exists and is configured
cat .env

# Try authentication again
python examples/simple_client.py
```

### Tests Fail

```bash
# Reinstall dependencies
pip install -e ".[dev]" --force-reinstall

# Clear Python cache
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Run tests again
pytest -v
```

### Can't See MQTT Events

```bash
# Verify MQTT connection in server logs
# Should see: "✓ MQTT connected successfully"

# Check if player is online
curl http://localhost:8000/api/players

# Ensure you're using the authenticated token
# (The simple_client.py saves it to .yoto_refresh_token)
```

## 💡 Tips for Success

1. **Keep the server running** in one terminal while testing
2. **Use the MQTT listener** to understand event flow
3. **Explore the API docs** at /docs to see all capabilities
4. **Check the examples/** directory for usage patterns
5. **Run tests frequently** to catch issues early

## 🎉 You're Ready!

Everything is set up and tested. You can now:

- Control Yoto players programmatically
- Monitor real-time events
- Manage display icons for Yoto Mini
- Build custom integrations
- Create interactive audio experiences

**Happy streaming! 🎵**

---

**Need Help?**

- Documentation: Check the `docs/` directory
- Examples: Review `examples/` for working code
- Tests: Look at `tests/` for usage patterns
- Issues: Open a GitHub issue with details

**Remember:** This is a working, tested implementation ready for human testing with real Yoto devices!
