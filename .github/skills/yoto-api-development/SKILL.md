---
name: yoto-api-development
description: Specialized knowledge for developing applications that interact with the Yoto Play API, including audio streaming, MQTT event handling, and device management. Use this when working with Yoto API integration, audio streaming to Yoto players, or real-time device control.
---

# Yoto API Development

This skill provides comprehensive guidance for developing applications that interact with the Yoto Play API. All detailed reference documentation is included in the `reference/` folder.

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

- [📋 Yoto API Reference](./reference/yoto_api_reference.md) - Complete REST API specification with all endpoints, authentication flows, data structures, and code examples
- [🔌 MQTT Deep Dive](./reference/yoto_mqtt_reference.md) - Real-time communication details including AWS IoT Core setup, topic structure, message formats, and event handling patterns
- [🏗️ Architecture Guide](./reference/architecture.md) - Implementation recommendations, technology stack suggestions, system design patterns, and project structure
- [❓ Planning Questions](./reference/planning_questions.md) - Strategic decisions and considerations for building Yoto applications
- [🎨 Icon Management](./reference/icon_management.md) - Display icon management for Yoto Mini, including public icon repository access and custom icon uploads
- [📝 Implementation Summary](./reference/implementation_summary.md) - Summary of recent implementation work including device capabilities and icon management features
- [✅ Testing Guide](./reference/testing_guide.md) - Comprehensive automated functional testing approach with test-and-fix loop, patterns, and guardrails

## Quick Start

### Authentication Flow (Python)

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
refresh_token = ym.token.refresh_token
```

### Basic Device Control

```python
# Connect to MQTT for real-time events
ym.connect_to_events()

# Update player status
ym.update_player_status()

# Control playback
player_id = next(iter(ym.players))
ym.pause_player(player_id)
ym.play_player(player_id)
ym.set_volume(player_id, 50)
```

## Key Libraries

### Python
- **yoto_api** (https://github.com/cdnninja/yoto_api) - Full Python wrapper with authentication, device control, and MQTT support
- Installation: `pip install yoto-api`

### Node.js/TypeScript
- **yoto-nodejs-client** (https://github.com/bcomnes/yoto-nodejs-client) - Comprehensive client with TypeScript support and automatic token refresh
- Installation: `npm install yoto-nodejs-client`

## Common Patterns

### 1. Token Management
- Always store and reuse refresh tokens
- Implement automatic token refresh (check before API calls)
- Refresh tokens 1 hour before expiration

### 2. MQTT Event Handling
- Use MQTT for real-time device control (lower latency than HTTP)
- Subscribe to all relevant topics: `device/{device_id}/events`, `device/{device_id}/status`
- Implement reconnection logic with exponential backoff
- Process events asynchronously with callbacks

### 3. Audio Streaming
- Yoto players expect direct HTTP/HTTPS URLs to audio files
- Supported formats: MP3, AAC (M4A), OGG, FLAC
- Use MP3 at 128-256 kbps for best compatibility
- Implement byte-range support for seeking

### 4. Display Icons (Yoto Mini)
- Icons must be PNG format, exactly 16x16 pixels
- Maximum file size: 10KB
- Access public icon repository via `/media/displayIcons/public`
- Upload custom icons via `/media/displayIcons/user/me`
- Icons show on Yoto Mini display during playback
- Validate icons before upload (dimensions, format, size)

### 5. Interactive "Choose Your Own Adventure" Cards
- Listen for button press events via MQTT
- Use server-side state persistence for story progress
- Map left/right buttons to binary choices
- Play specific chapters/tracks based on user choices

## Architecture Recommendations

### Technology Stack
- **Backend**: Python 3.9+ with FastAPI (async support)
- **MQTT Client**: Paho MQTT or built into yoto_api
- **Database**: SQLite for development, PostgreSQL for production
- **Audio Processing**: pydub with FFmpeg

### Project Structure
```
yoto_smart_stream/
├── core/
│   ├── yoto_client.py      # API wrapper with caching
│   ├── mqtt_handler.py     # MQTT event processing
│   └── audio_manager.py    # Audio file management
├── api/
│   ├── cards.py            # Card management endpoints
│   ├── players.py          # Player control endpoints
│   └── audio.py            # Audio streaming endpoints
├── models/                  # Data models
├── db/                      # Database models
└── scripts/                 # Interactive card scripts
```

## Best Practices

### ✅ DO:
- Use the `yoto_api` library as foundation
- Implement proper token management and refresh
- Cache API responses (players: 5 min, library: 15 min)
- Use async operations for better performance
- Test with real devices
- Implement error handling and retries
- Log MQTT events for debugging

### ❌ DON'T:
- Commit credentials to version control
- Ignore token expiration
- Skip input validation on uploads
- Hardcode configuration values
- Ignore MQTT connection failures
- Block on synchronous API calls in web server

## Security Considerations

1. **Never commit tokens or credentials** to version control
2. **Use environment variables** for all sensitive configuration
3. **Implement rate limiting** on public endpoints
4. **Validate audio file uploads** for type and size
5. **Secure MQTT credentials** - they provide device access
6. **Use HTTPS** for all audio streaming endpoints

## Development Workflow

1. **Start with authentication** - Test OAuth2 device flow
2. **Write tests first** - Follow TDD approach (see Testing Guide)
3. **Test MQTT connection** - Verify real-time events work
4. **Implement audio upload** - Test streaming to device
5. **Build card management** - Create and manage content
6. **Add interactive features** - Implement CYOA scripts if needed
7. **Polish and deploy** - Add logging, monitoring, documentation

## Testing Best Practices

### Test-Driven Development
- Write failing tests before implementing features
- Aim for >70% code coverage
- Run tests on every commit

### Test Structure
```python
# Unit tests - Fast, isolated
pytest tests/unit

# Integration tests - API/MQTT mocks
pytest tests/integration

# Functional tests - End-to-end flows
pytest tests/functional -m "not slow"
```

### Key Testing Patterns
1. **Mock External APIs** - Use `unittest.mock` for Yoto API calls
2. **Use Fixtures** - Share common setup with pytest fixtures
3. **Test Error Cases** - Network failures, invalid data, timeouts
4. **Clean Up Resources** - Always cleanup test data (cards, audio)

### Test-and-Fix Loop
```bash
# 1. Write failing test
pytest tests/unit/test_feature.py::test_new_feature -v

# 2. Implement feature
# ... code ...

# 3. Run test again (should pass)
pytest tests/unit/test_feature.py::test_new_feature -v

# 4. Run full suite
pytest -v --cov=yoto_smart_stream
```

See [Testing Guide](./reference/testing_guide.md) for comprehensive testing approach with examples and guardrails.

## Troubleshooting

### Token Issues
- Problem: Access tokens expire
- Solution: Call `check_and_refresh_token()` before API operations

### MQTT Connection Drops
- Problem: MQTT connections can drop
- Solution: Implement reconnection logic with exponential backoff

### Audio Not Playing
- Problem: Some formats may not play
- Solution: Convert to MP3 (128-256 kbps) for maximum compatibility

### Rate Limiting
- Problem: API has undocumented rate limits
- Solution: Implement request queuing and caching strategies

## Resources

- **Yoto Developer Portal**: https://yoto.dev/
- **API Documentation**: https://yoto.dev/api/
- **MQTT Documentation**: https://yoto.dev/players-mqtt/mqtt-docs/
- **Python Library**: https://github.com/cdnninja/yoto_api
- **Node.js Library**: https://github.com/bcomnes/yoto-nodejs-client
- **Home Assistant Integration**: https://github.com/cdnninja/yoto_ha (reference implementation)

---

**When building Yoto applications:**
1. Review the relevant reference documentation in the `reference/` folder
2. Follow the patterns and best practices outlined above
3. Use the recommended libraries and technology stack
4. Test thoroughly with real Yoto devices
5. Implement proper error handling and security measures
