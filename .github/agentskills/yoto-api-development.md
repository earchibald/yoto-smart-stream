# Yoto API Development AgentSkill

This agentskill provides specialized knowledge for developing applications that interact with the Yoto Play API, including audio streaming, MQTT event handling, and device management.

## 📚 Essential Reference Documents

**IMPORTANT**: Before proceeding, review these comprehensive reference documents:

1. **[Yoto API Reference](../../docs/YOTO_API_REFERENCE.md)** - Complete API specification including:
   - All REST API endpoints with request/response examples
   - MQTT topics, message formats, and commands
   - Data structures and models
   - Authentication flows (OAuth2 Device Flow)
   - Code examples in Python and Node.js
   - Official documentation links

2. **[Architecture Guide](../../docs/ARCHITECTURE.md)** - Implementation recommendations and system design

3. **[Planning Questions](../../docs/PLANNING_QUESTIONS.md)** - Strategic decisions and considerations

## Yoto API Overview

### Core Components

1. **REST API**: Main interface for device control, library management, and configuration
2. **MQTT Communication**: Real-time device control and status monitoring
3. **Authentication**: OAuth 2.0 device code flow with refresh tokens
4. **Audio Streaming**: Direct audio URL streaming to Yoto players

### API Base Information

- **Base URLs**:
  - REST API: `https://api.yotoplay.com`
  - Auth: `https://login.yotoplay.com`
- **Developer Portal**: https://yoto.dev/
- **Authentication**: Device Code Flow (OAuth 2.0)
- **Primary Python Library**: `yoto_api` by cdnninja (https://github.com/cdnninja/yoto_api)
- **Node.js Library**: `yoto-nodejs-client` (https://github.com/bcomnes/yoto-nodejs-client)

## Key Patterns and Best Practices

### 1. Authentication Flow

```python
from yoto_api import YotoManager

# Initialize manager with client ID
ym = YotoManager(client_id="your_client_id")

# Start device code flow
device_info = ym.device_code_flow_start()
# Present device_info['user_code'] and device_info['verification_uri'] to user

# Wait for user to complete authorization (typically 15-30 seconds)
time.sleep(15)

# Complete the flow to get tokens
ym.device_code_flow_complete()

# Store refresh token for future use
refresh_token = ym.token.refresh_token

# On subsequent runs, use the refresh token
ym.set_refresh_token(refresh_token)
ym.check_and_refresh_token()
```

### 2. MQTT Event Handling

The Yoto API uses MQTT for real-time device events. Key patterns:

```python
# Connect to MQTT broker (credentials obtained from API)
ym.connect_to_events()

# MQTT topics follow pattern: yoto/{family_id}/player/{player_id}/event
# Common events:
# - playback.status: Track position, play/pause state
# - config.nightLight: Night light color changes
# - config.volume: Volume changes
# - player.status: Battery, online status
```

**Event Structure**:
- Events are JSON payloads
- Players are identified by unique player_id
- Family_id groups devices under one account
- Events include timestamps and state changes

### 3. Player Control Operations

```python
# Get all players
players = ym.players  # Dict of player objects keyed by player_id

# Common operations
ym.pause_player(player_id)
ym.play_player(player_id)
ym.skip_chapter(player_id, direction="forward")  # or "backward"
ym.set_volume(player_id, volume)  # volume: 0-16
ym.set_night_light(player_id, color_hex)

# Update player data
ym.update_player_status()  # Fetch latest state from API
```

### 4. Library and Card Management

```python
# Get user's card library
ym.update_cards()
library = ym.library  # Dict of Card objects

# Card object properties:
# - card_id: Unique identifier
# - title: Card title
# - description: Card description
# - content: List of audio tracks
# - image_url: Cover image URL
```

### 5. Audio Streaming Architecture

**Key Considerations**:
- Yoto players expect direct HTTP/HTTPS URLs to audio files
- Supported formats: MP3, AAC (M4A), OGG, FLAC
- Implement audio file hosting with accessible URLs
- Use content delivery or local network streaming
- Audio files should have proper metadata (title, artist, duration)

**Recommended Pattern**:
```python
# FastAPI endpoint for audio streaming
from fastapi import FastAPI
from fastapi.responses import FileResponse

@app.get("/audio/{card_id}/{track_id}")
async def stream_audio(card_id: str, track_id: str):
    # Retrieve audio file path
    audio_path = get_audio_file_path(card_id, track_id)
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"}
    )
```

## Project Structure Recommendations

```
yoto_smart_stream/
├── yoto_smart_stream/
│   ├── __init__.py
│   ├── api/              # FastAPI routes
│   │   ├── __init__.py
│   │   ├── cards.py      # Card management endpoints
│   │   ├── players.py    # Player control endpoints
│   │   └── audio.py      # Audio streaming endpoints
│   ├── core/             # Core business logic
│   │   ├── __init__.py
│   │   ├── yoto_client.py    # Yoto API wrapper
│   │   ├── mqtt_handler.py   # MQTT event processing
│   │   └── audio_manager.py  # Audio file management
│   ├── models/           # Data models
│   │   ├── __init__.py
│   │   ├── card.py
│   │   └── player.py
│   ├── db/              # Database models and migrations
│   │   ├── __init__.py
│   │   └── models.py
│   └── config.py        # Configuration management
├── tests/
│   ├── test_api/
│   ├── test_core/
│   └── conftest.py
├── examples/            # Example scripts
│   ├── simple_client.py
│   ├── mqtt_listener.py
│   └── audio_upload.py
└── web_ui/             # Web interface (optional)
    ├── index.html
    └── static/
```

## Common Pitfalls and Solutions

### 1. Token Expiration
**Problem**: Access tokens expire after a period
**Solution**: Always call `check_and_refresh_token()` before API operations

### 2. MQTT Connection Stability
**Problem**: MQTT connections can drop
**Solution**: Implement reconnection logic with exponential backoff

### 3. Audio Format Compatibility
**Problem**: Some audio formats may not play on all Yoto devices
**Solution**: Convert to MP3 (128-256 kbps) for maximum compatibility

### 4. Large Audio Files
**Problem**: Large files can cause memory issues
**Solution**: Use streaming responses with `FileResponse` or chunk-based transfer

### 5. Rate Limiting
**Problem**: API has rate limits (not publicly documented)
**Solution**: Implement request queuing and caching strategies

## Testing Strategy

### Unit Tests
```python
import pytest
from yoto_smart_stream.core.yoto_client import YotoClient

@pytest.fixture
def mock_yoto_manager(mocker):
    """Mock YotoManager for testing without API calls"""
    return mocker.patch('yoto_api.YotoManager')

def test_player_control(mock_yoto_manager):
    # Test player control logic without hitting real API
    pass
```

### Integration Tests
```python
# Use real API in controlled test environment
# Store test credentials in .env.test
@pytest.mark.integration
def test_real_api_connection():
    # Test with real Yoto API
    pass
```

## Security Considerations

1. **Never commit tokens or credentials** to version control
2. **Use environment variables** for all sensitive configuration
3. **Implement rate limiting** on public endpoints
4. **Validate audio file uploads** for type and size
5. **Secure MQTT credentials** - they provide device access
6. **Use HTTPS** for all audio streaming endpoints

## Choose Your Own Adventure Architecture

For interactive audio experiences:

```python
class AdventureCard:
    def __init__(self, card_id: str):
        self.card_id = card_id
        self.chapters = {}  # chapter_num -> ChapterNode
        self.current_chapter = 1

    def handle_button_press(self, button: str):
        """Handle physical button presses on Yoto player"""
        current = self.chapters[self.current_chapter]
        if button == "left":
            self.current_chapter = current.left_choice
        elif button == "right":
            self.current_chapter = current.right_choice
        # Update player to play new chapter
```

**MQTT Integration**:
Listen for button press events on MQTT:
- Topic: `yoto/{family_id}/player/{player_id}/event`
- Event type: `button.press`
- Payload: `{"button": "left|right|pause|skip"}`

## Performance Optimization

1. **Cache API responses**: Player and library data don't change frequently
2. **Use async operations**: FastAPI + async Yoto API calls
3. **Database for card metadata**: Store card configurations locally
4. **CDN for audio files**: Use CDN or local caching for audio delivery
5. **Connection pooling**: Maintain persistent MQTT connections

## Useful Resources

- **Yoto API Python Library**: https://github.com/cdnninja/yoto_api
- **Home Assistant Integration**: https://github.com/cdnninja/yoto_ha (reference implementation)
- **Yoto Developer Portal**: https://yoto.dev/
- **MQTT Documentation**: https://mqtt.org/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/

## Example Implementation Snippets

### Complete Working Example
```python
#!/usr/bin/env python3
import time
import logging
from yoto_api import YotoManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize Yoto Manager
    client_id = "your_client_id"
    ym = YotoManager(client_id=client_id)

    # Authenticate
    logger.info("Starting authentication...")
    device_info = ym.device_code_flow_start()
    logger.info(f"Go to {device_info['verification_uri']}")
    logger.info(f"Enter code: {device_info['user_code']}")

    time.sleep(20)
    ym.device_code_flow_complete()
    logger.info("Authentication complete!")

    # Connect to events
    ym.connect_to_events()

    # Get player status
    ym.update_player_status()
    for player_id, player in ym.players.items():
        logger.info(f"Player: {player.name} - Online: {player.online}")

    # Keep alive to receive events
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")

if __name__ == "__main__":
    main()
```

## Development Workflow

1. **Start with examples**: Use the simple examples to understand API behavior
2. **Test with real device**: Development requires a physical Yoto player or account
3. **Monitor MQTT events**: Use MQTT listener to understand event patterns
4. **Iterate on audio**: Test different audio formats and streaming approaches
5. **Build incrementally**: Start with basic control, add features gradually

## Best Practices Summary

✅ **DO**:
- Use the `yoto_api` library as foundation
- Implement proper token management and refresh
- Cache API responses appropriately
- Use async operations for better performance
- Test with real devices
- Implement error handling and retries
- Log MQTT events for debugging

❌ **DON'T**:
- Commit credentials to version control
- Ignore token expiration
- Skip input validation on uploads
- Hardcode configuration values
- Ignore MQTT connection failures
- Block on synchronous API calls in web server

---

*This agentskill is based on research of the yoto_api library (v2.1.2) and community implementations. Always refer to official Yoto documentation for the most current information.*
