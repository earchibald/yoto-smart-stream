---
name: yoto-smart-stream-new
description: Comprehensive guide for Yoto Smart Stream development - covering both API integration and service operations. Use when developing Yoto applications, integrating with Yoto API/MQTT, or operating the Yoto Smart Stream service.
---

# Yoto Smart Stream - Comprehensive Development & Operations Guide

This unified skill provides comprehensive guidance for both developing Yoto API integrations and operating the Yoto Smart Stream service.

## When to Use This Skill

- **API Development**: Implementing Yoto API integration, MQTT event handling, audio streaming
- **Service Operations**: Accessing, configuring, and managing deployed Yoto Smart Stream instances
- **Testing & Troubleshooting**: Diagnosing issues, running tests, validating functionality

---

# Part 1: API Development

## Overview

Yoto is an audio player system for children that uses physical cards to control content playback. The Yoto API provides:

- **REST API** for managing devices, content (cards), and configuration
- **MQTT** for real-time device control and status monitoring
- **OAuth2** authentication with device flow and refresh tokens
- **Audio Streaming** capabilities to Yoto players
- **Display Icons** for Yoto Mini devices (16x16 pixel custom icons)

### Device Capabilities

**Yoto Player (Original)**:
- No display screen
- No microphone (voice control not possible)
- Physical card slot for content

**Yoto Mini**:
- 16x16 pixel display screen (supports custom icons)
- No microphone (voice control not possible)
- Physical card slot for content

### Base URLs
- REST API: `https://api.yotoplay.com`
- Auth: `https://login.yotoplay.com`
- Developer Portal: https://yoto.dev/

## Reference Documentation

**Load these reference documents as needed:**

- [📋 Yoto API Reference](../yoto-smart-stream/reference/yoto_api_reference.md) - Complete REST API specification with all endpoints, authentication flows, data structures, and code examples
- [🔌 MQTT Deep Dive](../yoto-smart-stream/reference/yoto_mqtt_reference.md) - Real-time communication details including AWS IoT Core setup, topic structure, message formats, and event handling patterns
- [🏗️ Architecture Guide](../yoto-smart-stream/reference/architecture.md) - Implementation recommendations, technology stack suggestions, system design patterns, and project structure
- [🤖 MCP Server Integration](../yoto-smart-stream/reference/mcp_server.md) - Model Context Protocol server for AI agent integration, library queries, and OAuth automation
- [❓ Planning Questions](../yoto-smart-stream/reference/planning_questions.md) - Strategic decisions and considerations for building Yoto applications
- [🎨 Icon Management](../yoto-smart-stream/reference/icon_management.md) - Display icon management for Yoto Mini, including public icon repository access and custom icon uploads
- [📝 Implementation Summary](../yoto-smart-stream/reference/implementation_summary.md) - Summary of recent implementation work including device capabilities and icon management features
- [✅ Testing Guide](../yoto-smart-stream/reference/testing_guide.md) - Comprehensive automated functional testing approach with test-and-fix loop, patterns, and guardrails

## Quick Start: Developer Implementation

### Prerequisites

1. **Register Yoto Application** at https://yoto.dev/get-started/start-here/
   - Application Type: Server-side / CLI Application
   - Grant Type: Device Code (OAuth 2.0 Device Authorization Grant)
   - Allowed Callback URLs: `http://localhost/oauth/callback` (placeholder - not used)
   - Allowed Logout URLs: `http://localhost/logout` (placeholder - not used)
   - Save your Client ID

**Note:** Yoto uses OAuth2 Device Flow which doesn't require callback URLs. If the registration form requires them, use localhost placeholders - they won't be called.

### Authentication Flow (Python Example)

```python
from yoto_api import YotoManager
import time

# Initialize with Client ID
ym = YotoManager(client_id="YOUR_CLIENT_ID")

# Start device code flow
device_code = ym.device_code_flow_start()
print(f"Visit: {device_code['verification_uri']}")
print(f"Code: {device_code['user_code']}")

# Wait for user to authorize
time.sleep(15)

# Complete authentication
ym.device_code_flow_complete()

# Store refresh token for future use
refresh_token = ym.refresh_token
# Save to database or secure storage
```

### Token Management

```python
# Restore from saved refresh token
ym = YotoManager(
    client_id="YOUR_CLIENT_ID",
    refresh_token=saved_refresh_token
)

# Tokens automatically refresh when needed
# Access tokens expire in 24 hours
# Refresh tokens persist until revoked
```

### Working with Devices

```python
# List connected players
players = ym.list_players()
for player in players:
    print(f"{player['name']} ({player['id']})")

# Get player status
player_id = players[0]['id']
status = ym.get_player_status(player_id)
print(f"Online: {status['online']}")
print(f"Volume: {status['config']['volume']}")
```

### Audio Streaming

```python
# Create a streaming MYO card
card_data = {
    "title": "My Audio Stream",
    "description": "Custom audio content",
    "content": {
        "chapters": [
            {
                "title": "Chapter 1",
                "tracks": [
                    {
                        "title": "Track 1",
                        "url": "https://your-server.com/audio/track1.mp3"
                    }
                ]
            }
        ]
    }
}

card = ym.create_myo_card(card_data)
card_id = card['id']

# Play on device
ym.play_card(player_id, card_id)
```

### MQTT Events

```python
import paho.mqtt.client as mqtt

# Get MQTT credentials
mqtt_creds = ym.get_mqtt_credentials()

# Connect to AWS IoT Core
client = mqtt.Client()
client.username_pw_set(
    mqtt_creds['username'],
    mqtt_creds['password']
)
client.tls_set()
client.connect(mqtt_creds['endpoint'], 8883)

# Subscribe to player events
topic = f"yoto/{player_id}/status"
client.subscribe(topic)

def on_message(client, userdata, msg):
    print(f"Event: {msg.payload}")

client.on_message = on_message
client.loop_start()
```

### Display Icons (Yoto Mini)

```python
# Upload custom 16x16 PNG icon
with open('icon.png', 'rb') as f:
    icon_data = f.read()

icon = ym.upload_icon(icon_data)
icon_id = icon['id']

# Use icon in MYO card
card_data['content']['icon'] = icon_id
card = ym.create_myo_card(card_data)
```

## Common API Patterns

### Error Handling

```python
from yoto_api import YotoAPIError, AuthenticationError

try:
    players = ym.list_players()
except AuthenticationError:
    # Token expired or invalid
    ym.refresh_access_token()
    players = ym.list_players()
except YotoAPIError as e:
    print(f"API Error: {e.status_code} - {e.message}")
```

### Rate Limiting

```python
import time

# Respect rate limits (no official limits documented)
# Recommended: Max 10 requests/second
def rate_limited_call(func, *args, **kwargs):
    result = func(*args, **kwargs)
    time.sleep(0.1)  # 100ms between calls
    return result
```

### Pagination

```python
# Many endpoints support pagination
def get_all_cards():
    cards = []
    page = 1
    while True:
        response = ym.list_cards(page=page, limit=50)
        cards.extend(response['cards'])
        if not response['has_more']:
            break
        page += 1
    return cards
```

---

# Part 2: Service Operations

For complete service operations documentation, see:
- [🔧 Service Operations Reference](./reference/service_operations.md) - Complete guide to accessing, configuring, and troubleshooting the Yoto Smart Stream service

## Quick Start: Service Access

### 1. Determine Service URL

```bash
# Railway CLI (most reliable)
railway domains

# Pattern-based URL
https://yoto-smart-stream-{environment}.up.railway.app

# Environments:
# - production (main branch)
# - develop (develop branch)
# - yoto-smart-stream-pr-{PR_ID} (PR previews)
```

### 2. Login with Default Credentials

- **Username:** `admin`
- **Password:** `yoto`

### 3. Complete Yoto OAuth (One-Time)

1. Navigate to Dashboard
2. Click "🔑 Connect Yoto Account" button
3. Complete Yoto OAuth device flow in browser
4. Authorization complete - tokens persist automatically

**Note:** OAuth authorization is required only once. Tokens automatically refresh in the background and persist across deployments.

## Common Service Operations

### Check Service Health

```bash
# Basic health check
curl https://SERVICE_URL/api/health

# Check authentication status
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://SERVICE_URL/api/auth/status

# Check player connectivity
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://SERVICE_URL/api/players
```

### Create Additional Users

```bash
# Login as admin first, get token
TOKEN=$(curl -X POST https://SERVICE_URL/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yoto"}' \
  | jq -r '.access_token')

# Create new user
curl -X POST https://SERVICE_URL/api/admin/users \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"user1","password":"secret123","role":"user"}'
```

### View Yoto Devices

```bash
# Get list of connected players
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/players | jq
```

### Audio Library Management

```bash
# List audio files
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/audio/list | jq

# Upload audio file
curl -X POST https://SERVICE_URL/api/audio/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@audio.mp3"

# Delete audio file
curl -X DELETE https://SERVICE_URL/api/audio/delete/filename.mp3 \
  -H "Authorization: Bearer $TOKEN"
```

## Key Service Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `GET /api/health` | Health check | None |
| `GET /` | Dashboard UI | Required |
| `POST /api/user/login` | Admin/user login | None |
| `GET /api/players` | List Yoto devices | Required |
| `GET /api/auth/status` | Yoto OAuth status | Required |
| `GET /api/admin/users` | List users | Admin only |
| `POST /api/admin/users` | Create user | Admin only |
| `GET /audio-library` | Audio Library page | Required |
| `GET /admin` | Admin panel | Admin only |
| `POST /api/audio/upload` | Upload audio | Required |
| `DELETE /api/audio/delete/{filename}` | Delete audio | Required |
| `GET /api/audio/list` | List audio files | Required |

## Troubleshooting Quick Reference

### Cannot Access Service

```bash
# Check service is running
railway status

# Check logs
railway logs

# Verify domain
railway domains
```

### Login Failures

```bash
# Test health endpoint (no auth)
curl https://SERVICE_URL/api/health

# Verify credentials (default: admin/yoto)
curl -v -X POST https://SERVICE_URL/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"yoto"}'
```

### OAuth Not Working

```bash
# Check OAuth status
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/auth/status

# Check logs for OAuth errors
railway logs --tail 100 | grep -i oauth

# Verify Yoto Client ID is set
railway variables | grep YOTO_CLIENT_ID
```

### No Devices Showing

```bash
# Verify OAuth completed
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/auth/status

# Check player API
curl -H "Authorization: Bearer $TOKEN" \
  https://SERVICE_URL/api/players | jq

# Check logs for MQTT connection
railway logs --tail 100 | grep -i mqtt
```

## Environment Variables

**Required:**
- `YOTO_CLIENT_ID` - Yoto OAuth Client ID from https://yoto.dev/

**Optional:**
- `DATABASE_URL` - SQLite database path (default: `/data/yoto_smart_stream.db`)
- `TOKEN_REFRESH_INTERVAL_HOURS` - OAuth token refresh interval (default: 12, range: 1-23)
- `TRANSCRIPTION_ENABLED` - Enable audio transcription (default: `false`)
- `TRANSCRIPTION_MODEL` - Whisper model (default: `base`, options: `tiny|base|small|medium|large`)
- `JWT_SECRET_KEY` - Secret for JWT tokens (auto-generated if not set)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Best Practices

### Development Workflow

1. **Local Development**: Use `.env` file for environment variables
2. **Testing**: Run tests before deploying (`pytest`)
3. **Deployment**: Use Railway environments for isolation
4. **Monitoring**: Check Railway logs regularly
5. **Security**: Never commit secrets to git

### Token Management

- OAuth tokens automatically refresh every 12 hours (configurable)
- Tokens persist in database across deployments
- Refresh tokens valid until manually revoked
- No manual intervention needed after initial OAuth setup

### Audio File Management

- Use MP3 format (128-256 kbps) for best compatibility
- Keep files under 50MB for faster uploads
- Use descriptive filenames (no special characters)
- Organize files with prefixes (e.g., `story_`, `music_`)

### Icon Management (Yoto Mini)

- Icons must be exactly 16x16 pixels
- PNG format only
- Use public icon repository when possible
- Upload custom icons for unique content

---

# Part 3: MCP Server Integration

The yoto-smart-stream repository includes an MCP (Model Context Protocol) server for AI agents to query the Yoto library using natural language and manage OAuth authentication.

## Overview

The MCP server (`mcp-server/` directory) provides:
- Natural language queries of your Yoto library
- Multi-deployment support (query different environments)
- Lazy initialization and lazy authentication
- In-memory auth cookie caching per host
- Search cards by title, author, or metadata
- List playlists and their contents
- Yoto OAuth activation/deactivation with structured Status responses
- Direct integration with VS Code, Claude Desktop, and other MCP clients

**Status Field** (v0.1.4+): All oauth responses include a Status field (success, pending, error, expired) for programmatic handling

## Quick Reference

**Version**: 0.1.4 (Stable)  
**Package**: `yoto-library-mcp`  
**Location**: `mcp-server/` directory  
**Framework**: FastMCP (mcp.server.fastmcp)
**Entry Point**: `server:sync_main`

### Available Tools

1. **`oauth(service_url, action)`** - Manage Yoto authentication
   - `action = "activate"` to log in with Yoto credentials
   - `action = "deactivate"` to log out
   - Requires `YOTO_USERNAME` and `YOTO_PASSWORD` environment variables
   - Supports automated browser-based OAuth with Playwright

2. **`query_library(service_url, query)`** - Natural language library queries
   - Examples: "how many cards?", "find cards with princess", "what metadata keys?"
   - Returns library statistics, search results, or metadata information
   - Multi-deployment support via `service_url` parameter

## Key Features

- **Lazy Initialization**: No startup requirements for YOTO_SERVICE_URL
- **Per-Tool Deployment**: Each tool call can target different yoto-smart-stream deployments
- **Single Auth per Host**: First query authenticates, subsequent queries reuse cached cookies
- **Environment Variables**:
  - `ADMIN_USERNAME` (required): Admin account username
  - `ADMIN_PASSWORD` (required): Admin account password
  - `YOTO_USERNAME` (optional): Yoto account email for OAuth activation
  - `YOTO_PASSWORD` (optional): Yoto account password for OAuth activation
  - `YOTO_SERVICE_URL` (optional): Default service URL for CLI invocation

## Setup for VS Code

```json
{
  "mcpServers": {
    "yoto-library": {
      "command": "python",
      "args": ["/path/to/yoto-smart-stream/mcp-server/server.py"],
      "env": {
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "your-admin-password",
        "YOTO_USERNAME": "your-email@example.com",
        "YOTO_PASSWORD": "your-yoto-password"
      }
    }
  }
}
```

## Usage Examples

### Query Production Library
```
User: "Query the production library - how many cards are there?"
→ Tool call: query_library(
    service_url="https://yoto-smart-stream-production.up.railway.app",
    query="how many cards are there?"
  )
```

### Compare Across Deployments
```
User: "Compare card counts between production and staging"
→ Two tool calls:
  1. query_library(prod_url, "how many cards?")
  2. query_library(staging_url, "how many cards?")
```

### Activate Yoto OAuth
```
User: "Activate Yoto OAuth on production"
→ Tool call: oauth(
    service_url="https://yoto-smart-stream-production.up.railway.app",
    action="activate"
  )
```

## Installation & Testing

### Run Tests
```bash
# Test MCP server structure and tools
python test_mcp_structure.py

# Test API integration
python test_api_integration.py
```

### Direct Python Execution
```bash
cd mcp-server
python server.py --username admin --password secret
```

## Detailed Documentation

See: [🤖 MCP Server Reference](./reference/mcp_server.md)

---

## Additional Resources

- **Project Documentation**: See `docs/` folder for detailed guides
- **Testing Guide**: See [yoto-smart-stream-testing skill](../yoto-smart-stream-testing/SKILL.md)
- **Railway Management**: See [railway-service-management skill](../railway-service-management/SKILL.md)
- **Example Code**: See `examples/` folder for working implementations
- **API Tests**: See `tests/` folder for test examples
- **MCP Server**: See `mcp-server/` folder for server implementation
