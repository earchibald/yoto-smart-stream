> **⚠️ DEPRECATED**: This documentation has been consolidated into the [yoto-smart-stream skill](../.github/skills/yoto-smart-stream/SKILL.md). Please refer to the skill for current information.
>
> **New location:** `.github/skills/yoto-smart-stream/reference/architecture.md`

---

# Yoto Smart Stream - Architecture & Implementation Plan

## Executive Summary

This document provides architectural recommendations for implementing **Yoto Smart Stream**, a service to stream audio to Yoto devices with MQTT event monitoring, web UI for configuration, and support for interactive "Choose Your Own Adventure" style experiences.

## Technology Stack Recommendations

### Backend: Python with FastAPI

**Rationale for Python**:
- Excellent `yoto_api` library already exists (mature, well-maintained)
- Strong async support for concurrent MQTT + HTTP operations
- Rich ecosystem for audio processing (pydub, mutagen)
- FastAPI provides modern, high-performance async web framework

**Core Stack**:
```
- Python 3.9+
- FastAPI (async web framework)
- Uvicorn (ASGI server)
- SQLAlchemy 2.0 (database ORM)
- Paho MQTT (MQTT client)
- yoto_api (Yoto API wrapper)
```

### Frontend: Modern Web UI

**Recommended Options**:

1. **Simple/MVP**: Vanilla JS + Tailwind CSS
   - Quick to develop
   - No build process needed
   - Sufficient for CRUD operations

2. **Full-Featured**: React/Vue + Vite
   - Better for complex interactive features
   - Component reusability
   - Rich ecosystem

3. **Hybrid**: HTMX + Alpine.js
   - Minimal JavaScript
   - Server-side rendering
   - Progressive enhancement

**Recommendation**: Start with HTMX + Alpine.js for rapid development, migrate to React if complexity increases.

### Database

**SQLite for Development/Single User**:
- Zero configuration
- File-based, easy backup
- Sufficient for card scripts and metadata

**PostgreSQL for Production/Multi-User**:
- Better concurrency
- JSON field support
- Scalability

## System Architecture

```
┌─────────────────┐
│   Web Browser   │
│   (React/HTMX)  │
└────────┬────────┘
         │ HTTP/WebSocket
         │
┌────────▼────────────────────────────────────┐
│         FastAPI Application                  │
│  ┌──────────────────────────────────────┐  │
│  │         API Routes                    │  │
│  │  /api/cards    /api/players           │  │
│  │  /api/audio    /api/scripts           │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │      Business Logic Layer            │  │
│  │  - Audio Manager                      │  │
│  │  - Card Script Engine                 │  │
│  │  - Event Processor                    │  │
│  └──────────────────────────────────────┘  │
│  ┌──────────────────────────────────────┐  │
│  │      Yoto Integration Layer          │  │
│  │  - YotoManager (yoto_api)            │  │
│  │  - MQTT Event Handler                │  │
│  └──────────────────────────────────────┘  │
└────────┬────────────────────┬──────────────┘
         │                    │
         │                    │ MQTT (TLS)
         │                    │
    ┌────▼─────┐         ┌───▼─────────┐
    │ Database │         │ Yoto Cloud  │
    │ (SQLite) │         │   & MQTT    │
    └──────────┘         └─────┬───────┘
                               │
                         ┌─────▼──────┐
                         │   Yoto     │
                         │  Players   │
                         └────────────┘
```

## Core Components

### 1. Yoto API Client Wrapper

**Purpose**: Abstraction layer over `yoto_api` with additional features

```python
# yoto_smart_stream/core/yoto_client.py
class YotoClient:
    """Enhanced Yoto API client with caching and error handling"""

    def __init__(self, config: Settings):
        self.manager = YotoManager(client_id=config.yoto_client_id)
        self._player_cache = {}
        self._library_cache = {}
        self._cache_ttl = 300  # 5 minutes

    async def authenticate(self, refresh_token: Optional[str] = None):
        """Authenticate with Yoto API"""

    async def get_players(self, force_refresh: bool = False):
        """Get all players with caching"""

    async def control_player(self, player_id: str, action: PlayerAction):
        """Control player (play, pause, skip, volume)"""
```

### 2. MQTT Event Handler

**Purpose**: Process real-time events from Yoto devices

```python
# yoto_smart_stream/core/mqtt_handler.py
class MQTTEventHandler:
    """Handle MQTT events from Yoto players"""

    def __init__(self, yoto_client: YotoClient):
        self.client = yoto_client
        self.event_callbacks = []

    async def connect(self):
        """Connect to MQTT broker"""

    async def on_event(self, topic: str, payload: dict):
        """Process incoming MQTT events"""
        # Parse event type
        # Update local state
        # Trigger callbacks (webhooks, scripts)

    def register_callback(self, event_type: str, callback: Callable):
        """Register callback for specific event types"""
```

### 3. Audio Manager

**Purpose**: Handle audio file storage, conversion, and streaming

```python
# yoto_smart_stream/core/audio_manager.py
class AudioManager:
    """Manage audio files and streaming"""

    async def upload_audio(self, file: UploadFile) -> str:
        """Upload and process audio file"""
        # Validate format
        # Convert if needed (to MP3)
        # Extract metadata
        # Store file
        # Return file ID

    async def get_audio_url(self, file_id: str) -> str:
        """Get streamable URL for audio file"""

    async def convert_audio(self, input_path: Path, output_format: str):
        """Convert audio to compatible format"""
```

### 4. Card Script Engine

**Purpose**: Execute interactive card scripts (Choose Your Own Adventure)

```python
# yoto_smart_stream/core/script_engine.py
class CardScript:
    """Interactive card script definition"""
    card_id: str
    chapters: Dict[int, Chapter]
    variables: Dict[str, Any]

class ScriptEngine:
    """Execute card scripts based on events"""

    async def load_script(self, card_id: str) -> CardScript:
        """Load script from database"""

    async def handle_button_press(
        self,
        card_id: str,
        player_id: str,
        button: str
    ):
        """Process button press in script context"""
        # Get current chapter
        # Evaluate condition
        # Determine next chapter
        # Update player

    async def evaluate_condition(
        self,
        script: CardScript,
        condition: str
    ) -> bool:
        """Evaluate script condition"""
```

## Database Schema

```sql
-- Cards and audio content
CREATE TABLE cards (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    cover_image_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tracks (
    id TEXT PRIMARY KEY,
    card_id TEXT REFERENCES cards(id),
    track_number INTEGER,
    title TEXT,
    audio_file_id TEXT NOT NULL,
    duration_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Interactive scripts
CREATE TABLE card_scripts (
    id TEXT PRIMARY KEY,
    card_id TEXT REFERENCES cards(id),
    script_type TEXT NOT NULL, -- 'linear', 'interactive', 'cyoa'
    script_data JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Script execution state (for multi-session CYOA)
CREATE TABLE player_script_state (
    id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    card_id TEXT REFERENCES cards(id),
    current_chapter INTEGER DEFAULT 1,
    variables JSON,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Audio files
CREATE TABLE audio_files (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    format TEXT NOT NULL,
    size_bytes INTEGER,
    duration_seconds INTEGER,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Event log (for debugging and analytics)
CREATE TABLE events (
    id TEXT PRIMARY KEY,
    player_id TEXT,
    event_type TEXT NOT NULL,
    event_data JSON,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## API Endpoints

### Player Management

```
GET    /api/players                    - List all players
GET    /api/players/{id}              - Get player details
POST   /api/players/{id}/control      - Control player
  Body: { "action": "play|pause|skip", "parameters": {...} }
```

### Card Management

```
GET    /api/cards                     - List all cards
GET    /api/cards/{id}                - Get card details
POST   /api/cards                     - Create new card
PUT    /api/cards/{id}                - Update card
DELETE /api/cards/{id}                - Delete card
POST   /api/cards/{id}/upload-audio   - Upload audio track
```

### Audio Streaming

```
GET    /api/audio/{file_id}           - Stream audio file
  Headers: Range support for seeking
```

### Script Management

```
GET    /api/scripts/{card_id}         - Get card script
PUT    /api/scripts/{card_id}         - Update card script
POST   /api/scripts/{card_id}/test    - Test script execution
```

### WebSocket for Real-time Events

```
WS     /ws/events                     - Real-time player events
```

## Choose Your Own Adventure Implementation

### Script Format (JSON)

```json
{
  "version": "1.0",
  "card_id": "adventure-001",
  "title": "Forest Adventure",
  "chapters": {
    "1": {
      "audio_file_id": "intro.mp3",
      "description": "You enter the forest...",
      "choices": {
        "left": {
          "label": "Go left",
          "next_chapter": 2
        },
        "right": {
          "label": "Go right",
          "next_chapter": 3
        }
      }
    },
    "2": {
      "audio_file_id": "left-path.mp3",
      "description": "You find a cave...",
      "choices": {
        "left": {
          "label": "Enter cave",
          "next_chapter": 4
        },
        "right": {
          "label": "Keep walking",
          "next_chapter": 5
        }
      }
    }
  }
}
```

### Button Mapping

Yoto players have physical buttons:
- **Left/Right arrows**: Chapter navigation / choices
- **Pause button**: Pause/resume
- **Shake**: Special action

### Event Flow

```
1. User plays interactive card
2. MQTT event: card inserted
3. Server loads script, chapter 1
4. Audio plays on device
5. User presses left button
6. MQTT event: button.press {"button": "left"}
7. Server evaluates script, moves to chapter 2
8. Server sends command to play next chapter
9. Cycle continues
```

## Audio Streaming Strategy

### Option 1: Local Network Streaming (Recommended for Home Use)

**Pros**:
- Low latency
- No external dependencies
- Works without internet

**Implementation**:
```python
@app.get("/audio/{file_id}")
async def stream_audio(file_id: str):
    file_path = audio_manager.get_file_path(file_id)
    return FileResponse(
        file_path,
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Content-Disposition": f"inline; filename={file_id}.mp3"
        }
    )
```

### Option 2: Cloud Storage + CDN

**Pros**:
- Works from anywhere
- Scalable
- Professional

**Implementation**:
- Upload to S3/Cloudflare R2
- Generate signed URLs
- Return URL to Yoto API

## Development Workflow

### Phase 1: Core API Client (Week 1)
1. Set up FastAPI project structure
2. Implement YotoClient wrapper
3. Add authentication flow
4. Test player listing and control

### Phase 2: MQTT Integration (Week 1-2)
1. Implement MQTT event handler
2. Add event logging
3. Test real-time event processing
4. Build simple event viewer UI

### Phase 3: Audio Management (Week 2-3)
1. Implement audio upload
2. Add format conversion
3. Set up streaming endpoint
4. Test with real device

### Phase 4: Card Management (Week 3-4)
1. Build card CRUD API
2. Add database models
3. Create card editor UI
4. Test card creation and playback

### Phase 5: Interactive Scripts (Week 4-6)
1. Design script format
2. Implement script engine
3. Add button event handling
4. Build script editor UI
5. Test CYOA experience

### Phase 6: Polish & Production (Week 6+)
1. Add user authentication
2. Implement multi-user support
3. Add logging and monitoring
4. Write documentation
5. Deploy to production

## Security Considerations

1. **API Authentication**: Use OAuth 2.0 or JWT for API access
2. **Yoto Credentials**: Store in environment variables, never in code
3. **File Upload Validation**: Check file types, sizes, and scan for malware
4. **Rate Limiting**: Prevent API abuse
5. **HTTPS**: All audio streaming over HTTPS
6. **Access Control**: Users can only access their own cards and players

## Performance Optimization

1. **Caching**:
   - Cache player status (5 min TTL)
   - Cache library data (15 min TTL)
   - Cache audio file metadata

2. **Async Operations**:
   - Use async/await throughout
   - Non-blocking MQTT handling
   - Concurrent API requests

3. **Database Indexing**:
   - Index card_id, player_id
   - Index timestamps for event queries

4. **Audio Optimization**:
   - Convert to 128kbps MP3 for streaming
   - Use byte-range requests for seeking
   - Implement CDN for high traffic

## Testing Strategy

### Unit Tests
```python
# Test audio processing
def test_audio_conversion():
    manager = AudioManager()
    result = manager.convert_audio("test.wav", "mp3")
    assert result.format == "mp3"

# Test script engine
def test_chapter_navigation():
    engine = ScriptEngine()
    script = load_test_script()
    next_chapter = engine.handle_button_press(script, 1, "left")
    assert next_chapter == 2
```

### Integration Tests
```python
# Test API endpoints
async def test_card_creation(client: TestClient):
    response = await client.post("/api/cards", json={
        "title": "Test Card",
        "description": "Test"
    })
    assert response.status_code == 201

# Test Yoto API integration
async def test_player_control():
    # Requires test Yoto account
    pass
```

### End-to-End Tests
- Test complete CYOA flow
- Test audio upload and playback
- Test MQTT event handling

## Deployment Options

### 1. Self-Hosted (Raspberry Pi / Home Server)
- Run on local network
- Perfect for home use
- Low cost

### 2. Cloud (Heroku / Railway / Fly.io)
- Accessible from anywhere
- Scalable
- Managed infrastructure

### 3. Hybrid
- Server in cloud
- Audio files on local NAS
- VPN for audio access

## Monitoring and Logging

```python
# Use structlog for structured logging
import structlog

logger = structlog.get_logger()

logger.info(
    "player_control",
    player_id=player_id,
    action=action,
    success=True
)

# Track metrics
from prometheus_client import Counter, Histogram

audio_plays = Counter('audio_plays_total', 'Total audio plays')
api_latency = Histogram('api_latency_seconds', 'API latency')
```

## Cost Estimate

**Development**: ~40-60 hours
**Self-hosted**: $0-50/month (hardware)
**Cloud hosted**: $10-50/month (depending on traffic)

---

## Next Steps

1. Review and approve architecture
2. Set up development environment
3. Begin Phase 1 implementation
4. Iterate based on testing feedback
