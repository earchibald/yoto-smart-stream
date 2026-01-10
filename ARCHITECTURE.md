# System Architecture and Information Flow

This document illustrates how data flows through the Yoto Smart Stream system and how the web UI interacts with various components.

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Web Browser (Client)                         │
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    React/Vue Frontend                          │  │
│  │                                                                 │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐     │  │
│  │  │Dashboard │  │ Library  │  │  CYOA    │  │ Devices  │     │  │
│  │  │  View    │  │   View   │  │ Builder  │  │  View    │     │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘     │  │
│  │                                                                 │  │
│  │  ┌─────────────────────────────────────────────────────────┐  │  │
│  │  │         State Management (Redux/Vuex/Zustand)           │  │  │
│  │  └─────────────────────────────────────────────────────────┘  │  │
│  │                                                                 │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              ↓ ↑                                     │
└──────────────────────────────┼─┼─────────────────────────────────────┘
                               │ │
                    HTTP/REST  │ │  WebSocket (MQTT over WS)
                               │ │
┌──────────────────────────────┼─┼─────────────────────────────────────┐
│                              ↓ ↑                                     │
│                        Backend Server                                │
│                                                                       │
│  ┌────────────────┐    ┌────────────────┐    ┌─────────────────┐   │
│  │   REST API     │    │  WebSocket     │    │  File Storage   │   │
│  │   Server       │    │  Gateway       │    │  Service        │   │
│  │                │    │                │    │                 │   │
│  │ • Auth         │    │ • MQTT Bridge  │    │ • Audio Files   │   │
│  │ • CRUD Ops     │    │ • Event Stream │    │ • Thumbnails    │   │
│  │ • File Upload  │    │ • Presence     │    │ • Transcripts   │   │
│  └────────────────┘    └────────────────┘    └─────────────────┘   │
│         │                      │                      │              │
│         └──────────────────────┼──────────────────────┘              │
│                                │                                     │
│  ┌─────────────────────────────┼─────────────────────────────────┐  │
│  │                   Database Layer                               │  │
│  │                                                                 │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐│  │
│  │  │  PostgreSQL  │  │    Redis     │  │   Object Storage    ││  │
│  │  │              │  │              │  │   (S3/MinIO)        ││  │
│  │  │ • Users      │  │ • Sessions   │  │                      ││  │
│  │  │ • Scripts    │  │ • Cache      │  │ • Audio Files       ││  │
│  │  │ • Devices    │  │ • Pub/Sub    │  │ • Large Binaries    ││  │
│  │  │ • Metadata   │  │              │  │                      ││  │
│  │  └──────────────┘  └──────────────┘  └──────────────────────┘│  │
│  └─────────────────────────────────────────────────────────────────┘│
│                                                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                     MQTT Message Broker                        │  │
│  │                      (Mosquitto/RabbitMQ)                      │  │
│  │                                                                 │  │
│  │  Topics:                                                        │  │
│  │  • yoto/{device_id}/status                                     │  │
│  │  • yoto/{device_id}/events                                     │  │
│  │  • yoto/{device_id}/commands                                   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                ↓ ↑                                   │
└────────────────────────────────┼─┼───────────────────────────────────┘
                                 │ │
                          MQTT Protocol
                                 │ │
┌────────────────────────────────┼─┼───────────────────────────────────┐
│                                ↓ ↑                                   │
│                          Yoto Devices                                │
│                                                                       │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │ Living Room  │    │ Kids Bedroom │    │   Kitchen    │          │
│  │              │    │              │    │              │          │
│  │ • Playback   │    │ • Playback   │    │ • Playback   │          │
│  │ • Buttons    │    │ • Buttons    │    │ • Buttons    │          │
│  │ • Status     │    │ • Status     │    │ • Status     │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│                                                                       │
└───────────────────────────────────────────────────────────────────────┘
```


---

## Device Capabilities and Limitations

### Yoto Player Models

#### Yoto Player (Original)
- **Display**: None - no screen
- **Microphone**: None
- **Controls**: Physical buttons (play/pause, skip, volume)
- **Connectivity**: Wi-Fi, MQTT
- **Display Icons**: Not applicable (no display)

#### Yoto Mini
- **Display**: 16x16 pixel screen
- **Microphone**: None
- **Controls**: Physical buttons (play/pause, skip, volume)
- **Connectivity**: Wi-Fi, MQTT
- **Display Icons**: Fully supported (16x16 PNG icons)

### Important Limitations

⚠️ **No Voice Control**: Neither Yoto device has a microphone, so voice control and voice-activated features are not possible. All interactions must be through:
- Physical buttons on the device
- MQTT commands from the server
- Web UI controls

✓ **Display Icons**: Only available on Yoto Mini. Icons can be assigned to chapters/tracks and will display during playback on the Mini's 16x16 pixel screen.

### Icon Management

The system supports display icons for Yoto Mini devices:

- **Public Icon Repository**: Browse and use icons from Yoto's public repository via `/media/displayIcons/public` endpoint
- **Custom Icons**: Upload custom 16x16 PNG icons via `/media/displayIcons/upload` endpoint
- **Icon Assignment**: Assign icons to chapters using the `display.icon16x16` field
- **Icon Service**: Use the `yoto_smart_stream.icons` module for icon management

See [Icon Management Documentation](docs/ICON_MANAGEMENT.md) for detailed information.

---

## Data Flow: Uploading Audio and Creating a Card Script

```
┌─────────┐
│  User   │
└────┬────┘
     │
     │ 1. Select audio file
     ↓
┌─────────────────┐
│  File Uploader  │
│   Component     │
└────┬────────────┘
     │
     │ 2. Chunk file & upload
     ↓
┌─────────────────┐
│  REST API       │
│  /api/upload    │
└────┬────────────┘
     │
     │ 3. Store file
     ↓
┌─────────────────┐
│ Object Storage  │
│ (S3/MinIO)      │
└────┬────────────┘
     │
     │ 4. Extract metadata
     │    (duration, bitrate, etc.)
     ↓
┌─────────────────┐
│  PostgreSQL     │
│  audio_files    │
│  table          │
└────┬────────────┘
     │
     │ 5. Return file ID & metadata
     ↓
┌─────────────────┐
│  Frontend       │
│  Library View   │
└────┬────────────┘
     │
     │ 6. User creates card script
     ↓
┌─────────────────┐
│  Script Editor  │
│  Component      │
└────┬────────────┘
     │
     │ 7. Select audio file
     │    Configure playback
     ↓
┌─────────────────┐
│  REST API       │
│  /api/scripts   │
└────┬────────────┘
     │
     │ 8. Save script definition
     ↓
┌─────────────────┐
│  PostgreSQL     │
│  scripts table  │
└─────────────────┘
```

---

## Data Flow: Real-time Device Monitoring

```
┌───────────────┐
│ Yoto Device   │
└───────┬───────┘
        │
        │ 1. Event occurs (button press, playback start, etc.)
        ↓
┌──────────────────┐
│  MQTT Broker     │
│  Topic: yoto/    │
│  device_123/     │
│  events          │
└───────┬──────────┘
        │
        │ 2. Message published
        ↓
┌──────────────────┐
│  Backend         │
│  MQTT Subscriber │
└───────┬──────────┘
        │
        ├─→ 3a. Log to database
        │   ┌────────────────┐
        │   │  PostgreSQL    │
        │   │  event_log     │
        │   └────────────────┘
        │
        └─→ 3b. Forward to WebSocket clients
            ┌────────────────┐
            │  WebSocket     │
            │  Gateway       │
            └───────┬────────┘
                    │
                    │ 4. Push to connected browsers
                    ↓
            ┌────────────────┐
            │  Frontend      │
            │  WebSocket     │
            │  Connection    │
            └───────┬────────┘
                    │
                    │ 5. Update UI state
                    ↓
            ┌────────────────┐
            │  Device View   │
            │  Component     │
            │                │
            │  • Event log   │
            │  • Status      │
            │  • Playback    │
            └────────────────┘
```

---

## Data Flow: Sending Commands to Device

```
┌─────────────┐
│  User       │
└──────┬──────┘
       │
       │ 1. Click "Pause" button
       ↓
┌─────────────────┐
│  Device Control │
│  Component      │
└──────┬──────────┘
       │
       │ 2. Optimistically update UI
       │    (show loading state)
       ↓
┌─────────────────┐
│  REST API       │
│  /api/devices/  │
│  {id}/command   │
└──────┬──────────┘
       │
       │ 3. Validate & prepare command
       ↓
┌─────────────────┐
│  MQTT Broker    │
│  Publish to:    │
│  yoto/device/   │
│  commands       │
└──────┬──────────┘
       │
       │ 4. Command delivered
       ↓
┌─────────────────┐
│  Yoto Device    │
│                 │
│  Executes       │
│  command        │
└──────┬──────────┘
       │
       │ 5. Acknowledge execution
       ↓
┌─────────────────┐
│  MQTT Broker    │
│  Publish to:    │
│  yoto/device/   │
│  status         │
└──────┬──────────┘
       │
       │ 6. Status update
       ↓
┌─────────────────┐
│  Backend        │
│  MQTT Sub       │
└──────┬──────────┘
       │
       │ 7. Forward to WebSocket
       ↓
┌─────────────────┐
│  Frontend       │
│                 │
│  ✓ Confirm UI   │
│    update       │
└─────────────────┘
```

---

## Data Flow: Building and Deploying CYOA Story

```
┌─────────┐
│  User   │
└────┬────┘
     │
     │ 1. Create story in CYOA Builder
     ↓
┌─────────────────┐
│  Flow Canvas    │
│  Component      │
│                 │
│  • Drag nodes   │
│  • Connect      │
│  • Configure    │
└────┬────────────┘
     │
     │ 2. Save story structure
     │    (nodes + connections)
     ↓
┌─────────────────┐
│  REST API       │
│  /api/stories   │
└────┬────────────┘
     │
     │ 3. Store story definition
     ↓
┌─────────────────┐
│  PostgreSQL     │
│                 │
│ stories table:  │
│ • metadata      │
│ • nodes (JSON)  │
│ • connections   │
└────┬────────────┘
     │
     │ 4. User clicks "Deploy to Device"
     ↓
┌─────────────────┐
│  REST API       │
│  /api/stories/  │
│  {id}/deploy    │
└────┬────────────┘
     │
     │ 5. Compile story into
     │    executable format
     ↓
┌─────────────────┐
│  Story Engine   │
│                 │
│  • Validate     │
│  • Optimize     │
│  • Package      │
└────┬────────────┘
     │
     │ 6. Send to device
     ↓
┌─────────────────┐
│  MQTT Broker    │
│  yoto/device/   │
│  commands       │
└────┬────────────┘
     │
     │ 7. Device receives story
     ↓
┌─────────────────┐
│  Yoto Device    │
│                 │
│  • Load story   │
│  • Ready to play│
└─────────────────┘
```

---

## Database Schema (Simplified)

### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    password_hash VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### devices
```sql
CREATE TABLE devices (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    device_id VARCHAR(255) UNIQUE NOT NULL,
    mqtt_topic VARCHAR(255),
    status VARCHAR(50), -- 'connected', 'disconnected', 'idle'
    last_seen TIMESTAMP,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### audio_files
```sql
CREATE TABLE audio_files (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    file_path VARCHAR(512) NOT NULL,
    file_size BIGINT,
    duration_seconds INTEGER,
    format VARCHAR(50), -- 'mp3', 'wav', 'ogg'
    bitrate INTEGER,
    sample_rate INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### scripts
```sql
CREATE TABLE scripts (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50), -- 'simple', 'playlist', 'cyoa'
    definition JSONB NOT NULL, -- script structure
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### cyoa_stories
```sql
CREATE TABLE cyoa_stories (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    nodes JSONB NOT NULL, -- array of nodes
    connections JSONB NOT NULL, -- array of connections
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### events
```sql
CREATE TABLE events (
    id UUID PRIMARY KEY,
    device_id UUID REFERENCES devices(id),
    event_type VARCHAR(100), -- 'button_press', 'playback_start', etc.
    event_data JSONB,
    timestamp TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_events_device_timestamp 
    ON events(device_id, timestamp DESC);
```

### playback_history
```sql
CREATE TABLE playback_history (
    id UUID PRIMARY KEY,
    device_id UUID REFERENCES devices(id),
    script_id UUID REFERENCES scripts(id),
    audio_file_id UUID REFERENCES audio_files(id),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    duration_played INTEGER,
    metadata JSONB
);
```

---

## MQTT Topic Structure

```
yoto/
├── {device_id}/
│   ├── status              # Device online/offline, battery, etc.
│   ├── events              # User interactions, state changes
│   ├── commands            # Commands from server to device
│   ├── playback            # Current playback state
│   └── telemetry           # System metrics, diagnostics
│
├── broadcast/
│   └── announcements       # System-wide messages
│
└── admin/
    ├── discovery           # Device discovery
    └── management          # Admin commands
```

### Example Messages

**Status Update:**
```json
Topic: yoto/device_abc123/status
Payload: {
    "status": "connected",
    "battery": 85,
    "firmware": "2.4.1",
    "ip": "192.168.1.105",
    "timestamp": "2026-01-10T08:15:32Z"
}
```

**Button Press Event:**
```json
Topic: yoto/device_abc123/events
Payload: {
    "type": "button_press",
    "button": 1,
    "timestamp": "2026-01-10T08:15:32Z"
}
```

**Play Command:**
```json
Topic: yoto/device_abc123/commands
Payload: {
    "command": "play",
    "script_id": "script-uuid-here",
    "audio_file": "https://your-server.com/audio/story.mp3",
    "timestamp": "2026-01-10T08:15:30Z"
}
```

**Note on Audio Streaming:** Yoto MYO cards can stream audio from your own server by using the `url` field in track definitions instead of `uploadId`. This enables:
- Dynamic content that changes based on time, user, or context
- No upload size limits
- Complete control over audio content
- Ability to update content without recreating cards

See [Streaming from Your Own Service](docs/STREAMING_FROM_OWN_SERVICE.md) for details.

**Playback Status:**
```json
Topic: yoto/device_abc123/playback
Payload: {
    "state": "playing",
    "script_id": "script-uuid-here",
    "current_track": 3,
    "total_tracks": 12,
    "position": 512,
    "duration": 900,
    "volume": 60,
    "timestamp": "2026-01-10T08:15:32Z"
}
```

---

## API Endpoints Summary

### Authentication
```
POST   /api/auth/login
POST   /api/auth/logout
POST   /api/auth/register
GET    /api/auth/me
```

### Audio Files
```
GET    /api/audio                    # List audio files
POST   /api/audio                    # Upload audio
GET    /api/audio/{id}              # Get audio details
PUT    /api/audio/{id}              # Update metadata
DELETE /api/audio/{id}              # Delete audio
GET    /api/audio/{id}/download     # Download file
GET    /api/audio/{id}/stream       # Stream audio
```

### Scripts
```
GET    /api/scripts                 # List scripts
POST   /api/scripts                 # Create script
GET    /api/scripts/{id}           # Get script
PUT    /api/scripts/{id}           # Update script
DELETE /api/scripts/{id}           # Delete script
POST   /api/scripts/{id}/deploy    # Deploy to device
```

### CYOA Stories
```
GET    /api/stories                 # List stories
POST   /api/stories                 # Create story
GET    /api/stories/{id}           # Get story
PUT    /api/stories/{id}           # Update story
DELETE /api/stories/{id}           # Delete story
POST   /api/stories/{id}/deploy    # Deploy to device
POST   /api/stories/{id}/test      # Test in simulator
```

### Devices
```
GET    /api/devices                 # List devices
POST   /api/devices                 # Register device
GET    /api/devices/{id}           # Get device
PUT    /api/devices/{id}           # Update device
DELETE /api/devices/{id}           # Remove device
POST   /api/devices/{id}/command   # Send command
GET    /api/devices/{id}/events    # Get event history
GET    /api/devices/{id}/status    # Get current status
```

### Analytics
```
GET    /api/analytics/overview      # Dashboard stats
GET    /api/analytics/devices       # Device usage stats
GET    /api/analytics/content       # Content popularity
GET    /api/analytics/playback      # Playback history
```

### System
```
GET    /api/system/health           # System health check
GET    /api/system/config           # Get configuration
PUT    /api/system/config           # Update configuration
```

---

## WebSocket Events

### Client → Server
```javascript
// Subscribe to device updates
{
    type: "subscribe",
    topic: "device.abc123"
}

// Unsubscribe
{
    type: "unsubscribe",
    topic: "device.abc123"
}

// Heartbeat
{
    type: "ping"
}
```

### Server → Client
```javascript
// Device status update
{
    type: "device.status",
    deviceId: "abc123",
    data: {
        status: "connected",
        battery: 85
    }
}

// Device event
{
    type: "device.event",
    deviceId: "abc123",
    event: {
        type: "button_press",
        button: 1,
        timestamp: "2026-01-10T08:15:32Z"
    }
}

// Playback update
{
    type: "device.playback",
    deviceId: "abc123",
    data: {
        state: "playing",
        position: 512,
        duration: 900
    }
}

// Heartbeat response
{
    type: "pong"
}
```

---

## Security Considerations

### Authentication
- JWT tokens for API authentication
- Refresh token mechanism
- Session management in Redis

### Authorization
- Role-based access control (RBAC)
- User can only access their own devices/content
- Admin role for system management

### MQTT Security
- Username/password authentication
- TLS encryption for connections
- Access Control Lists (ACLs) per device
- Topic-level permissions

### File Upload Security
- File type validation (whitelist)
- File size limits
- Virus scanning
- Content-Type verification
- Sanitized filenames

### API Security
- Rate limiting (per user, per IP)
- CORS configuration
- Input validation
- SQL injection prevention (parameterized queries)
- XSS prevention (output encoding)

---

## Performance Optimization

### Frontend
- Code splitting by route
- Lazy loading for heavy components
- Virtual scrolling for large lists
- Debounced search inputs
- Memoized computed values
- Service Worker for offline support

### Backend
- Database indexing on frequently queried fields
- Redis caching for hot data
- CDN for audio file delivery
- Connection pooling
- Query optimization

### Real-time
- WebSocket connection pooling
- Message batching for high-frequency events
- MQTT QoS levels appropriately set
- Backpressure handling

---

## Scalability Considerations

### Horizontal Scaling
- Stateless API servers (can scale horizontally)
- Load balancer for API requests
- Redis for shared session state
- MQTT broker clustering

### Data Partitioning
- Shard audio files by user ID
- Partition events table by date
- Separate read replicas for analytics

### Async Processing
- Queue for file processing (encoding, thumbnail generation)
- Background workers for heavy tasks
- Event-driven architecture for loose coupling

---

## Monitoring and Observability

### Metrics to Track
- API response times
- WebSocket connection count
- MQTT message throughput
- Device online/offline events
- Error rates
- File upload success rate
- Database query performance

### Logging
- Structured logging (JSON)
- Log levels (debug, info, warn, error)
- Correlation IDs for request tracing
- MQTT message logging (sample)

### Alerting
- Device offline for > 1 hour
- API error rate > 5%
- Database connection pool exhausted
- Disk space low
- High memory usage

---

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer (nginx)                  │
│                                                             │
│  • SSL termination                                          │
│  • Request routing                                          │
│  • Rate limiting                                            │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  API Server  │ │  API Server  │ │  API Server  │
│  Instance 1  │ │  Instance 2  │ │  Instance 3  │
└──────────────┘ └──────────────┘ └──────────────┘
        │               │               │
        └───────────────┼───────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ↓               ↓               ↓
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  PostgreSQL  │ │    Redis     │ │ MQTT Broker  │
│  (Primary)   │ │  (Cache)     │ │ (Clustered)  │
│              │ │              │ │              │
│  Replica →   │ └──────────────┘ └──────────────┘
└──────────────┘

┌──────────────────────────────────────────────────────────────┐
│                     Object Storage (S3/MinIO)                │
│                                                              │
│  • Audio files                                               │
│  • Thumbnails                                                │
│  • Backups                                                   │
└──────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Recommendation

### Frontend
- **Framework**: React 18 with TypeScript
- **State Management**: Zustand or Redux Toolkit
- **Routing**: React Router v6
- **UI Components**: Material-UI or custom with Tailwind CSS
- **WebSocket**: Socket.io-client or native WebSocket
- **Audio**: Web Audio API, Howler.js
- **Canvas**: Konva.js or React Flow for CYOA editor
- **Build Tool**: Vite
- **Testing**: Jest, React Testing Library

### Backend
- **Runtime**: Node.js 18+ with TypeScript or Python 3.11+
- **Framework**: Express.js / Fastify or FastAPI (Python)
- **MQTT**: Mosquitto (broker), mqtt.js or paho-mqtt (client)
- **WebSocket**: Socket.io or ws
- **Database**: PostgreSQL 15+
- **Cache**: Redis 7+
- **ORM**: Prisma (Node.js) or SQLAlchemy (Python)
- **File Storage**: MinIO or AWS S3
- **Queue**: Bull or BullMQ (Redis-based)

### DevOps
- **Containerization**: Docker
- **Orchestration**: Kubernetes or Docker Compose
- **CI/CD**: GitHub Actions
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or Loki
- **Reverse Proxy**: nginx or Traefik

---

This architecture supports:
✅ Real-time bidirectional communication
✅ Scalable file storage
✅ Efficient device monitoring
✅ Complex interactive story flows
✅ High availability
✅ Horizontal scaling
