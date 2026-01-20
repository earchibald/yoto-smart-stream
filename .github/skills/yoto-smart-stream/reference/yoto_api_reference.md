# Yoto API Reference Documentation

This document provides comprehensive reference information about the Yoto API for use in developing Yoto smart streaming skills and applications.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [REST API Endpoints](#rest-api-endpoints)
4. [MQTT Communication](#mqtt-communication)
5. [Device Models and Data Structures](#device-models-and-data-structures)
6. [Code Examples](#code-examples)
7. [Useful Libraries](#useful-libraries)
8. [Official Resources](#official-resources)

---

## Overview

Yoto is an audio player system for children that uses physical cards to control content playback. The Yoto API provides:

- **REST API** for managing devices, content (cards), and configuration
- **MQTT** for real-time device control and status monitoring
- **OAuth2** authentication with device flow and refresh tokens

### Base URLs

```
REST API: https://api.yotoplay.com
Auth: https://login.yotoplay.com
```

### Getting Started

1. Obtain a Client ID from: https://yoto.dev/get-started/start-here/
2. Authenticate using OAuth2 Device Flow
3. Use REST API for device management and content
4. Connect via MQTT for real-time control

---

### Smart Stream Service Proxy Endpoints

The FastAPI service in this repository exposes helper endpoints that proxy to the Yoto API using the server's authenticated session. This allows tooling to manage library content without embedding Yoto credentials locally.

- `DELETE /api/library/{contentId}`: Remove a card or MYO playlist from the authenticated user's library. Requires a valid session cookie obtained via `POST /api/user/login`. Returns `200`/`204` with `{ success, contentId }` on success or `404` if the item is missing.
- Library listing includes stable identifiers (`id`, `cardId`, `contentId`, `type`, `source`) so clients can safely target items for deletion.

Refresh and cache control:

- `GET /api/library?fresh=1` forces a hard refresh and prunes stale MYO-backed cards whose `contentId` no longer exists in `/content/mine`. Use this after bulk deletions to avoid cached titles lingering.

The automation script [scripts/delete_llm_test_cards.py](scripts/delete_llm_test_cards.py) consumes these endpoints to delete matched items without calling Yoto APIs directly.

#### Audio Editing (Stitch + Preview)

The Smart Stream service provides endpoints to stitch multiple audio files together with per-file delays, including a resumable background task with WebSocket progress and temporary previews.

- `GET /api/audio/stitch/status`: Returns the current user's active stitch task if any. Response: `{ active, task_id?, status?, progress?, current_file?, output_filename?, error? }`.
- `POST /api/audio/stitch`: Starts a stitching task.
  - Body: `{ files: string[], delays: number[], output_filename: string }`
  - Constraints: `len(files) == len(delays)`, each delay in `0.1–10.0` seconds. `output_filename` is sanitized and saved as `.mp3`.
  - Response: `{ task_id, status: 'pending', output_filename }`
- `POST /api/audio/stitch/{task_id}/cancel`: Requests cancellation of the active task. Response: `{ success, message }`.
- `POST /api/audio/preview-stitch`: Generates a temporary preview combining the selected files with delays, trimming each segment to a configurable per-file duration.
  - Body: `{ files: string[], delays: number[], preview_duration_seconds: number (1–30) }`
  - Response: `{ preview_id, url }` where `url` serves from `/api/audio-preview/{preview_id}`.
- `DELETE /api/audio/preview-stitch/{preview_id}`: Deletes the temporary preview.
- `GET /api/audio-preview/{preview_id}`: Serves the preview MP3 stored in `/tmp`.
- `WS /ws/stitch/{task_id}`: WebSocket streaming task progress. Emits events: `snapshot`, `heartbeat`, `loading`, `progress`, `finalizing`, `completed`, `cancelled`, `error`.

Export parameters: MP3 mono, 44.1 kHz, 192 kbps. Single active task per user is enforced in single-instance deployments. Completed tasks auto-clean after 10 minutes.

## Authentication

### OAuth2 Device Flow

The recommended authentication method for CLI/server applications.

#### Step 1: Request Device Code

```
POST https://login.yotoplay.com/oauth/device/code
Content-Type: application/x-www-form-urlencoded

audience=https://api.yotoplay.com
client_id=YOUR_CLIENT_ID
scope=offline_access
```

**Response:**
```json
{
  "device_code": "CODE_FOR_POLLING",
  "user_code": "XXXX-XXXX",
  "verification_uri": "https://login.yotoplay.com/activate",
  "verification_uri_complete": "https://login.yotoplay.com/activate?user_code=XXXX-XXXX",
  "expires_in": 300,
  "interval": 5
}
```

#### Step 2: Poll for Token

```
POST https://login.yotoplay.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=urn:ietf:params:oauth:grant-type:device_code
device_code=CODE_FROM_STEP_1
client_id=YOUR_CLIENT_ID
audience=https://api.yotoplay.com
```

**Success Response:**
```json
{
  "access_token": "JWT_TOKEN",
  "refresh_token": "REFRESH_TOKEN",
  "token_type": "Bearer",
  "expires_in": 86400,
  "scope": "openid profile offline_access"
}
```

**Pending Response (403):**
```json
{
  "error": "authorization_pending"
}
```

#### Step 3: Refresh Token

```
POST https://login.yotoplay.com/oauth/token
Content-Type: application/x-www-form-urlencoded

grant_type=refresh_token
refresh_token=YOUR_REFRESH_TOKEN
client_id=YOUR_CLIENT_ID
audience=https://api.yotoplay.com
```

### Authentication Headers

All API requests require:

```
Authorization: Bearer ACCESS_TOKEN
Content-Type: application/json
User-Agent: Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4
```

---

## REST API Endpoints

### Devices

#### Get All Devices

```
GET /device-v2/devices/mine
```

**Response:**
```json
{
  "devices": [
    {
      "deviceId": "string",
      "name": "string",
      "deviceType": "v3",
      "online": true
    }
  ]
}
```

#### Get Device Status

```
GET /device-v2/{deviceId}/status
```

**Response:**
```json
{
  "device": {
    "deviceId": "string",
    "status": {
      "activeCard": "cardId or 'none'",
      "batteryLevelPercentage": 100,
      "isCharging": true,
      "userVolumePercentage": 50,
      "systemVolumePercentage": 50,
      "temperatureCelsius": 24,
      "isBluetoothAudioConnected": false,
      "isAudioDeviceConnected": false,
      "firmwareVersion": "v2.17.5-5",
      "wifiStrength": -54,
      "playingSource": "card",
      "nightlightMode": "0x194a55",
      "dayMode": true,
      "ambientLightSensorReading": 100,
      "powerSource": "battery"
    }
  }
}
```

**Power Source Values:**
- `0`: Unknown
- `1`: AC Power
- `2`: Battery
- `3`: Wireless Charging

#### Get Device Config

```
GET /device-v2/{deviceId}/config
```

**Response:**
```json
{
  "device": {
    "deviceId": "string",
    "name": "string",
    "config": {
      "dayTime": "06:30",
      "nightTime": "18:20",
      "maxVolumeLimit": "16",
      "nightMaxVolumeLimit": "8",
      "dayDisplayBrightness": "auto",
      "nightDisplayBrightness": "100",
      "ambientColour": "#40bfd9",
      "nightAmbientColour": "#f57399",
      "timezone": "",
      "hourFormat": "12",
      "alarms": []
    }
  }
}
```

#### Update Device Config

```
PUT /device-v2/{deviceId}/config
Content-Type: application/json

{
  "deviceId": "string",
  "config": {
    "name": "Bedroom Player",
    "dayTime": "07:00",
    "nightTime": "19:00",
    "maxVolumeLimit": "80"
  }
}
```

#### Send Device Command (via HTTP)

```
POST /device-v2/{deviceId}/command
Content-Type: application/json

{
  "volume": 50
}
```

### Content (Cards)

#### Get User's MYO Content

```
GET /card/mine
```

**Response:**
```json
{
  "cards": [
    {
      "cardId": "string",
      "metadata": {
        "title": "string",
        "description": "string",
        "author": "string",
        "cover": {
          "imageL": "https://url"
        }
      }
    }
  ]
}
```

#### Get Family Library

```
GET /card/family/library
```

#### Get Card Details

```
GET /card/{cardId}
```

**Response:**
```json
{
  "card": {
    "cardId": "string",
    "title": "string",
    "content": {
      "chapters": [
        {
          "key": "01-INT",
          "title": "Chapter Title",
          "duration": 349,
          "display": {
            "icon16x16": "https://url"
          },
          "tracks": [
            {
              "key": "01-INT",
              "title": "Track Title",
              "duration": 349,
              "format": "aac",
              "channels": "mono",
              "trackUrl": "https://signed-url"
            }
          ]
        }
      ]
    }
  }
}
```

### Family

#### Get Family Info

```
GET /user/family
```

### Groups (Family Library Groups)

#### Get All Groups

```
GET /groups
```

#### Create Group

```
POST /groups
Content-Type: application/json

{
  "name": "Bedtime Stories",
  "imageId": "fp-cards",
  "items": [
    { "contentId": "cardId1" },
    { "contentId": "cardId2" }
  ]
}
```

### Media

#### Get Audio Upload URL

```
POST /media/audio/upload-url
Content-Type: application/json

{
  "sha256": "hash",
  "filename": "story.mp3"
}
```

#### Upload Cover Image

```
POST /media/cover-image
Content-Type: multipart/form-data

image: [binary data]
coverType: default
autoConvert: true
```

---

## MQTT Communication

### Connection

MQTT provides real-time device control and status monitoring.

**Getting MQTT Credentials:**

```
GET /device-v2/{deviceId}/mqtt-credentials
```

**Response:**
```json
{
  "host": "mqtt.broker.url",
  "port": 8883,
  "username": "string",
  "password": "string",
  "clientId": "string"
}
```

### Topics

#### Subscribe Topics

**Status Updates:**
```
yoto/{deviceId}/status
```

**Playback Events:**
```
yoto/{deviceId}/events
```

**Command Responses:**
```
yoto/{deviceId}/response
```

#### Publish Topics

**Send Commands:**
```
yoto/{deviceId}/command
```

### MQTT Messages

#### Status Message

```json
{
  "volume": 50,
  "batteryLevel": 100,
  "charging": false,
  "online": true,
  "temperature": 24
}
```

#### Events Message (Playback)

```json
{
  "trackTitle": "Story Title",
  "cardTitle": "Card Name",
  "playbackStatus": "playing",
  "position": 120,
  "trackLength": 300
}
```

#### Command Message

**Set Volume:**
```json
{
  "volume": 50
}
```

**Set Ambient Color:**
```json
{
  "ambient": "#FF0000"
}
```

**Set Sleep Timer:**
```json
{
  "sleepTimer": 30
}
```

**Play Card:**
```json
{
  "card": {
    "cardId": "5WsQg",
    "chapterKey": "01",
    "trackKey": "01"
  }
}
```

**Pause/Resume/Stop:**
```json
{ "pause": true }
{ "resume": true }
{ "stop": true }
```

---

## Device Models and Data Structures

### YotoPlayer

The `YotoPlayer` class from the `yoto_api` library contains data from both the REST API and MQTT. When extracting player data, be aware that MQTT data (real-time) is preferred over API data (snapshot).

```python
class YotoPlayer:
    # Device identification (from REST API)
    id: str  # Device ID
    name: str  # Device name
    device_type: str  # "v3", "v2", etc.
    online: bool
    
    # Status from REST API (snapshot at last update)
    is_playing: bool  # Boolean playing state from API
    active_card: str  # Card ID or "none"
    battery_level_percentage: int  # Battery percentage (0-100)
    charging: bool
    user_volume: int  # User-configured volume from API (0-100, mapped to 0-16 hardware)
    system_volume: int  # System volume
    temperature_celcius: int
    wifi_strength: int
    firmware_version: str
    
    # Real-time status from MQTT (preferred for current state)
    volume: int  # Current volume from MQTT (0-100 in API, mapped to 0-16 hardware)
    volume_max: int  # Maximum volume
    playback_status: str  # "playing", "paused", "stopped" - MQTT string
    card_id: str  # Current card ID from MQTT
    chapter_title: str
    chapter_key: str
    track_title: str
    track_key: str
    track_length: int  # seconds
    track_position: int  # seconds
    source: str  # "card" or other sources
    repeat_all: bool
    sleep_timer_active: bool
    sleep_timer_seconds_remaining: int
    
    # Configuration
    config: YotoPlayerConfig
    
    # Timestamps
    last_updated_api: datetime
    last_updated_at: datetime
```

#### Important: Extracting Player Data

When building API responses or UI displays, prefer MQTT data over API data for real-time accuracy:

**Volume**: Use `player.volume` (MQTT) with fallback to `player.user_volume` (API). **CRITICAL**: Volume values are in the range 0-100 (API representation), not 0-16 (hardware representation). Pydantic models must accept 0-100 to avoid ValidationErrors.
```python
volume = player.volume if player.volume is not None else (
    player.user_volume if player.user_volume is not None else 8
)
# volume will be in range 0-100
```

**Playing Status**: Parse `player.playback_status` (MQTT string) with fallback to `player.is_playing` (API boolean)
```python
playing = False
if player.playback_status is not None:
    playing = player.playback_status == "playing"
elif player.is_playing is not None:
    playing = player.is_playing
```

**Battery Level**: Use `player.battery_level_percentage` directly (can be None)
```python
battery_level = player.battery_level_percentage
```

**Note**: The `player.playing` attribute does NOT exist - use `playback_status` or `is_playing` instead.

### YotoPlayerConfig

```python
class YotoPlayerConfig:
    day_mode_time: time  # "07:00"
    day_display_brightness: int
    day_ambient_colour: str  # "#40bfd9"
    day_max_volume_limit: int
    
    night_mode_time: time  # "19:00"
    night_display_brightness: int
    night_ambient_colour: str  # "#f57399"
    night_max_volume_limit: int
    
    alarms: list[Alarm]
```

### Card

```python
class Card:
    id: str  # Card ID
    title: str
    description: str
    author: str
    category: str
    cover_image_large: str  # URL
    chapters: dict[str, Chapter]
```

### Chapter

```python
class Chapter:
    key: str  # "01-INT"
    title: str
    icon: str  # URL
    duration: int  # seconds
    tracks: dict[str, Track]
```

### Track

```python
class Track:
    key: str
    title: str
    duration: int
    format: str  # "aac", "mp3"
    channels: str  # "mono", "stereo"
    type: str  # "audio"
    trackUrl: str  # Signed URL
```

---

## Code Examples

### Python (using yoto_api library)

#### Basic Setup and Authentication

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

# Update player status
ym.update_player_status()
print(ym.players)
```

#### Using Saved Refresh Token

```python
# Save refresh token after first auth
refresh_token = ym.token.refresh_token

# Later, restore session
ym = YotoManager(client_id="YOUR_CLIENT_ID")
ym.set_refresh_token(refresh_token)
ym.check_and_refresh_token()
```

#### Device Control

```python
# Connect to MQTT for real-time control
ym.connect_to_events()

# Get first player ID
player_id = next(iter(ym.players))

# Control playback
ym.pause_player(player_id)
ym.resume_player(player_id)

# Update library
ym.update_cards()
print(ym.library)

# Access player properties
for player_id, player in ym.players.items():
    print(f"{player.name}: {player.battery_level_percentage}%")
```

### Node.js (using yoto-nodejs-client)

#### Authentication and Setup

```javascript
import { YotoClient } from 'yoto-nodejs-client'

// Start device flow
const deviceCode = await YotoClient.requestDeviceCode({
  clientId: 'YOUR_CLIENT_ID'
})

console.log(`Visit: ${deviceCode.verification_uri_complete}`)
console.log(`Code: ${deviceCode.user_code}`)

// Wait for authorization (simple approach)
const tokens = await YotoClient.waitForDeviceAuthorization({
  deviceCode: deviceCode.device_code,
  clientId: 'YOUR_CLIENT_ID',
  initialInterval: deviceCode.interval * 1000,
  expiresIn: deviceCode.expires_in,
  onPoll: (result) => {
    if (result.status === 'pending') process.stdout.write('.')
  }
})

// Create client with auto-refresh
const client = new YotoClient({
  clientId: 'YOUR_CLIENT_ID',
  refreshToken: tokens.refresh_token,
  accessToken: tokens.access_token,
  onTokenRefresh: async (event) => {
    // MUST save tokens
    await saveTokens(event)
  }
})
```

#### Device Management

```javascript
// Get devices
const { devices } = await client.getDevices()
console.log('Devices:', devices)

// Get device status
const status = await client.getDeviceStatus({ 
  deviceId: devices[0].deviceId 
})
console.log('Battery:', status.batteryLevelPercentage, '%')

// Update config
await client.updateDeviceConfig({
  deviceId: devices[0].deviceId,
  configUpdate: {
    config: {
      maxVolumeLimit: '80'
    }
  }
})
```

#### MQTT Real-time Control

```javascript
// Create MQTT client
const mqtt = await client.createMqttClient({
  deviceId: devices[0].deviceId
})

// Listen for events
mqtt.on('events', (message) => {
  console.log('Playing:', message.trackTitle)
})

mqtt.on('status', (message) => {
  console.log('Volume:', message.volume)
  console.log('Battery:', message.batteryLevel)
})

// Connect and control
await mqtt.connect()
await mqtt.setVolume(50)
await mqtt.setAmbientHex('#FF0000')
await mqtt.startCard({ cardId: '5WsQg' })
```

#### Stateful Device Model

```javascript
import { YotoDeviceModel } from 'yoto-nodejs-client'

// Create stateful device client
const deviceClient = new YotoDeviceModel(client, devices[0], {
  httpPollIntervalMs: 600000  // Poll every 10 minutes
})

// Listen for updates
deviceClient.on('statusUpdate', (status, source, changedFields) => {
  console.log(`Battery: ${status.batteryLevelPercentage}% (${source})`)
})

deviceClient.on('online', (metadata) => {
  console.log('Device online:', metadata.reason)
})

deviceClient.on('playbackUpdate', (playback) => {
  console.log('Playing:', playback.trackTitle)
})

// Start managing device
await deviceClient.start()

// Access current state
console.log('Status:', deviceClient.status)
console.log('Config:', deviceClient.config)

// Control device
await deviceClient.updateConfig({ maxVolumeLimit: 14 })

// Stop when done
await deviceClient.stop()
```

#### Account Manager (Multiple Devices)

```javascript
import { YotoAccount } from 'yoto-nodejs-client'

const account = new YotoAccount({
  clientOptions: {
    clientId: 'YOUR_CLIENT_ID',
    refreshToken: 'YOUR_REFRESH_TOKEN',
    accessToken: 'YOUR_ACCESS_TOKEN',
    onTokenRefresh: async (event) => {
      await saveTokens(event)
    }
  }
})

// Unified event handling for all devices
account.on('statusUpdate', ({ deviceId, status, source }) => {
  console.log(`${deviceId}: ${status.batteryLevelPercentage}%`)
})

account.on('online', ({ deviceId }) => {
  console.log(`${deviceId} online`)
})

// Start managing all devices
await account.start()

// Access individual device
const device = account.getDevice('abc123')
console.log('Battery:', device.status.batteryLevelPercentage)

// Stop all
await account.stop()
```

---

## Useful Libraries

### Python

**cdnninja/yoto_api**
- Repository: https://github.com/cdnninja/yoto_api
- Full Python wrapper for Yoto API
- Includes authentication, device control, MQTT support
- Used by Home Assistant integration

**Installation:**
```bash
pip install yoto-api
```

### Node.js/TypeScript

**bcomnes/yoto-nodejs-client**
- Repository: https://github.com/bcomnes/yoto-nodejs-client
- NPM: https://www.npmjs.com/package/yoto-nodejs-client
- Comprehensive Node.js client
- Automatic token refresh
- Full TypeScript support
- Stateful device management
- CLI tools included

**Installation:**
```bash
npm install yoto-nodejs-client
```

**libraryfm/yoto-js**
- Repository: https://github.com/libraryfm/yoto-js
- Unofficial Node SDK
- TypeScript support

### Other Tools

**cdnninja/yoto_ha**
- Repository: https://github.com/cdnninja/yoto_ha
- Home Assistant Integration
- 175+ stars
- Production-ready implementation

**yotoplay/examples**
- Repository: https://github.com/yotoplay/examples
- Official examples from Yoto
- React, Next.js, Node.js, Vanilla JS examples
- MQTT examples

---

## Official Resources

### Documentation

- **Yoto API Documentation**: https://yoto.dev/api/
- **Get Started**: https://yoto.dev/get-started/start-here/
- **MQTT Documentation**: https://yoto.dev/players-mqtt/mqtt-docs/
- **Developer Portal**: https://yoto.dev/

### Key API Sections

1. **Authentication**
   - POST /oauth/device/code - Start device flow
   - POST /oauth/token - Exchange tokens
   - GET /authorize - Browser-based flow

2. **Devices**
   - GET /device-v2/devices/mine - List devices
   - GET /device-v2/{id}/status - Device status
   - GET /device-v2/{id}/config - Device config
   - PUT /device-v2/{id}/config - Update config
   - POST /device-v2/{id}/command - Send command

3. **Content**
   - GET /card/{cardId} - Get card details
   - GET /card/mine - User's MYO content
   - GET /card/family/library - Family library
   - POST /card - Create/update content (**IMPORTANT**: Use this endpoint for BOTH creating AND updating MYO cards. Include `cardId` in the payload for updates. Do NOT use `/content` endpoint for updates.)
   - DELETE /card/{cardId} - Delete content

4. **Groups**
   - GET /groups - List groups
   - POST /groups - Create group
   - GET /groups/{id} - Get group
   - PUT /groups/{id} - Update group
   - DELETE /groups/{id} - Delete group

5. **Media**
   - POST /media/audio/upload-url - Get upload URL
   - POST /media/cover-image - Upload cover
   - GET /media/displayIcons/public - Public icons
   - GET /media/displayIcons/user/me - User icons

---

## Common Use Cases

### Stream Custom Audio

1. Get audio upload URL with SHA256 hash
2. Upload audio file to signed URL (if not already uploaded)
3. Create card content with upload ID
4. Play card on device via MQTT

### Monitor Device Status

1. Authenticate and get devices
2. Connect to MQTT for real-time updates
3. Subscribe to status and events topics
4. Process battery, temperature, playback events

### Create Interactive Card

1. Upload audio tracks
2. Upload cover image
3. Create card with chapters and tracks
4. Assign icons to chapters
5. Test playback

### Control Multiple Devices

1. Use YotoAccount (Node.js) or iterate devices (Python)
2. Listen to unified events
3. Send commands to specific devices
4. Handle online/offline states

---

## Tips for Development

### Authentication

- **Always persist refresh tokens** - Access tokens expire, refresh tokens are long-lived
- **Implement token refresh callback** - Save new tokens immediately
- **Handle authorization_pending** - Poll with proper intervals (usually 5 seconds)
- **Respect slow_down responses** - Increase polling interval when requested

### API Best Practices

- **Use MQTT for real-time control** - Lower latency than HTTP
- **Poll HTTP API periodically** - For config sync (every 10 minutes is common)
- **Cache device state** - Reduce API calls
- **Handle offline devices** - Check online status before commands

### MQTT Tips

- **Maintain persistent connection** - Automatic reconnection is important
- **Subscribe to all relevant topics** - status, events, response
- **Handle connection drops** - Devices may go offline/online
- **Use QoS appropriately** - QoS 1 for important commands

### Error Handling

- **Token expiration** - Implement automatic refresh
- **Network failures** - Retry with exponential backoff
- **Device offline** - Queue commands or notify user
- **Rate limiting** - Respect API limits

---

## Version History

**Document Version 1.0** (January 2026)
- Initial comprehensive reference
- Based on Yoto API as of January 2026
- Includes Python and Node.js examples
- MQTT documentation
- REST API endpoints

---

## Contributing

This document will be updated as the Yoto API evolves and new features are added. Contributions and updates are welcome to keep this reference current and useful for Copilot skill development.

---

## License Note

This documentation is for educational and development purposes. Yoto, Yoto Player, and related trademarks are property of Yoto Ltd. This is unofficial documentation compiled from public sources and community projects.
