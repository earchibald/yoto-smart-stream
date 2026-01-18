> **⚠️ DEPRECATED**: This documentation has been consolidated into the [yoto-smart-stream skill](../.github/skills/yoto-smart-stream/SKILL.md). Please refer to the skill for current information.
>
> **New location:** `.github/skills/yoto-smart-stream/reference/yoto_mqtt_reference.md`

---

# Yoto MQTT Event Service - Deep Dive Reference

## Overview

The Yoto MQTT event service provides real-time communication with Yoto players using the MQTT protocol over WebSockets. This document details the implementation architecture, protocols, and integration patterns for building applications that interact with Yoto devices.

## Architecture

### Core Components

1. **YotoManager** - High-level orchestrator managing authentication, players, and MQTT client
2. **YotoMQTTClient** - MQTT client implementation handling connections, subscriptions, and message processing
3. **YotoAPI** - REST API client for device management and library operations
4. **YotoPlayer** - Data model representing player state and configuration
5. **Token** - Authentication token management

### Communication Flow

```
Application
    ↓
YotoManager
    ↓ (REST API)     ↓ (MQTT)
YotoAPI          YotoMQTTClient
    ↓                   ↓
Yoto Cloud Services   AWS IoT MQTT Broker
    ↓                   ↓
           Yoto Players
```

## Authentication

### Device Code Flow

The Yoto API uses OAuth 2.0 Device Authorization Grant flow for authentication:

```python
# 1. Start device code flow
ym = YotoManager(client_id="your_client_id")
auth_result = ym.device_code_flow_start()

# Present auth_result to user for authorization
# Contains: device_code, user_code, verification_uri, expires_in, interval

# 2. Wait for user to authorize (15-30 seconds)
time.sleep(15)

# 3. Complete flow and obtain tokens
ym.device_code_flow_complete()
```

### Token Management

```python
# Using existing refresh token
ym.set_refresh_token(refresh_token)

# Check and refresh token (auto-refreshes if expired)
ym.check_and_refresh_token()
```

**Token Structure:**
- `access_token` - JWT for API and MQTT authentication
- `refresh_token` - Long-lived token for obtaining new access tokens
- `id_token` - User identity information
- `valid_until` - Token expiration timestamp
- `scope` - Access scope permissions

**Token Lifecycle:**
- Tokens are automatically refreshed 1 hour before expiration
- MQTT connection is re-established after token refresh
- Access tokens are required for both REST API and MQTT authentication

## MQTT Connection

### Connection Details

**AWS IoT Core Configuration:**
```python
CLIENT_ID = "4P2do5RhHDXvCDZDZ6oti27Ft2XdRrzr"
MQTT_AUTH_NAME = "PublicJWTAuthorizer"
MQTT_URL = "aqrphjqbp3u2z-ats.iot.eu-west-2.amazonaws.com"
PORT = 443
TRANSPORT = "websockets"
```

### Connection Setup

```python
# Initialize MQTT client
client = mqtt.Client(
    client_id="YOTOAPI" + player_id.replace("-", ""),
    transport="websockets",
    userdata=(players, callback)
)

# Set JWT authentication
client.username_pw_set(
    username="_?x-amz-customauthorizer-name=PublicJWTAuthorizer",
    password=token.access_token
)

# Configure TLS and connect
client.tls_set()
client.connect(host=MQTT_URL, port=443)
client.loop_start()
```

### Connection Lifecycle

```python
def connect_to_events(self, callback=None):
    """
    Establishes MQTT connection and starts event loop
    
    Args:
        callback: Optional function called when events are processed
    """
    self.callback = callback
    self.mqtt_client = YotoMQTTClient()
    self.mqtt_client.connect_mqtt(self.token, self.players, callback)

def disconnect(self):
    """Gracefully disconnect MQTT client"""
    if self.mqtt_client:
        self.mqtt_client.disconnect_mqtt()
        self.mqtt_client = None
```

## MQTT Topics

### Topic Structure

For each player with ID `{device_id}`, the following topics are used:

#### Subscribed Topics (Receive from Player)

1. **Events Topic**: `device/{device_id}/events`
   - Real-time playback state updates
   - Volume changes
   - Card insertion/removal
   - Sleep timer updates

2. **Status Topic**: `device/{device_id}/status`
   - Battery level updates
   - Night light mode changes
   - System status information

3. **Response Topic**: `device/{device_id}/response`
   - Command execution confirmations
   - Error responses

#### Published Topics (Send to Player)

1. **Command Topic Pattern**: `device/{device_id}/command/{command}`

Available commands:
- `events` - Request current status
- `set-volume` - Change volume
- `sleep` - Set sleep timer
- `card-stop` - Stop playback
- `card-pause` - Pause playback
- `card-resume` - Resume playback
- `card-play` - Play a specific card
- `restart` - Restart player
- `bt` - Bluetooth control
- `ambients` - Set ambient lighting

## Message Formats

### Events Message

Received on `device/{device_id}/events`:

```json
{
  "trackLength": 315,
  "position": 0,
  "cardId": "7JtVV",
  "repeatAll": true,
  "source": "remote",
  "cardUpdatedAt": "2021-07-13T14:51:26.576Z",
  "chapterTitle": "Snow and Tell",
  "chapterKey": "03",
  "trackTitle": "Snow and Tell",
  "trackKey": "03",
  "streaming": false,
  "volume": 5,
  "volumeMax": 8,
  "playbackStatus": "playing",
  "playbackWait": false,
  "sleepTimerActive": false,
  "sleepTimerSeconds": 0,
  "eventUtc": 1715133271,
  "online": true
}
```

**Key Fields:**
- `playbackStatus`: "playing" | "paused" | "stopped"
- `source`: "remote" | "nfc" | "local"
- `position`: Current playback position in seconds
- `trackLength`: Total track length in seconds
- `volume`: Current volume level (0-16)
- `volumeMax`: Maximum allowed volume
- `cardId`: Currently playing card ID or "none"
- `sleepTimerActive`: Boolean indicating if sleep timer is active
- `sleepTimerSeconds`: Remaining sleep timer seconds

### Status Message

Received on `device/{device_id}/status`:

```json
{
  "nightlightMode": "0x194a55",
  "batteryLevel": 85,
  "charging": false,
  "online": true
}
```

**Night Light Color Codes:**
- `0x000000`: Off
- `0x194a55`: Blue (On)
- `0x643600`: Day mode
- `0x5a6400`: Night mode
- `0x646464`: White

### Response Message

Received on `device/{device_id}/response`:

```json
{
  "status": {
    "card-play": "OK",
    "req_body": "{\"uri\":\"https://yoto.io/7JtVV\",\"secondsIn\":0,\"requestId\":\"...\"}"
  }
}
```

## Command Reference

### Volume Control

```python
def set_volume(self, player_id: str, volume: int):
    """
    Set player volume
    
    Args:
        player_id: Device ID
        volume: Volume level 0-100 (mapped to 0-16 internally)
    """
    topic = f"device/{player_id}/command/set-volume"
    payload = json.dumps({"volume": closest_volume})
    self.client.publish(topic, str(payload))
```

**Volume Mapping:**
The API accepts 0-100 but Yoto uses 0-16. Mapping table:
```python
VOLUME_MAPPING_INVERTED = [
    0, 7, 13, 19, 25, 32, 38, 44, 50,
    57, 63, 69, 75, 82, 88, 94, 100
]
```

### Playback Control

#### Play Card

```python
def card_play(
    self,
    player_id: str,
    card_id: str,
    secondsIn: int = None,      # Start position in seconds
    cutoff: int = None,          # Stop position in seconds
    chapterKey: str = None,      # Specific chapter
    trackKey: str = None         # Specific track
):
    topic = f"device/{player_id}/command/card-play"
    payload = {
        "uri": f"https://yoto.io/{card_id}"
    }
    if secondsIn is not None:
        payload["secondsIn"] = int(secondsIn)
    if cutoff is not None:
        payload["cutOff"] = int(cutoff)
    if chapterKey is not None:
        payload["chapterKey"] = str(chapterKey)
    if trackKey is not None:
        payload["trackKey"] = str(trackKey)
    
    self.client.publish(topic, json.dumps(payload))
```

**Example Payloads:**

Play from beginning:
```json
{"uri": "https://yoto.io/7JtVV"}
```

Play specific chapter/track:
```json
{
  "uri": "https://yoto.io/7JtVV",
  "chapterKey": "03",
  "trackKey": "01"
}
```

Resume from position:
```json
{
  "uri": "https://yoto.io/7JtVV",
  "secondsIn": 120
}
```

Play segment:
```json
{
  "uri": "https://yoto.io/7JtVV",
  "secondsIn": 60,
  "cutOff": 180
}
```

#### Pause/Resume/Stop

```python
def card_pause(self, player_id: str):
    topic = f"device/{player_id}/command/card-pause"
    self.client.publish(topic)

def card_resume(self, player_id: str):
    topic = f"device/{player_id}/command/card-resume"
    self.client.publish(topic)

def card_stop(self, player_id: str):
    topic = f"device/{player_id}/command/card-stop"
    self.client.publish(topic)
```

### Sleep Timer

```python
def set_sleep(self, player_id: str, seconds: int):
    """
    Set sleep timer
    
    Args:
        player_id: Device ID
        seconds: Timer duration (0 to disable)
    """
    topic = f"device/{player_id}/command/sleep"
    payload = json.dumps({"seconds": seconds})
    self.client.publish(topic, str(payload))
```

### Ambient Lighting

```python
def set_ambients(self, player_id: str, r: int, g: int, b: int):
    """
    Set ambient light color
    
    Args:
        player_id: Device ID
        r, g, b: RGB values 0-255
    """
    topic = f"device/{player_id}/command/ambients"
    payload = json.dumps({"r": r, "g": g, "b": b})
    self.client.publish(topic, str(payload))
```

**Predefined Colors:**
```python
HEX_COLORS = {
    "#40bfd9": "Sky Blue",
    "#9eff00": "Apple Green",
    "#f57399": "Lilac",
    "#ff0000": "Tambourine Red",
    "#ff3900": "Orange Peel",
    "#ff8500": "Bumblebee Yellow",
    "#ffffff": "White",
    "#0": "Off"
}
```

### Bluetooth Control

```python
def bluetooth(
    self,
    player_id: str,
    action: str,     # "on", "off", or "is-on"
    name: str = None,
    mac: str = None
):
    topic = f"device/{player_id}/command/bt"
    payload = json.dumps({
        "action": action,
        "name": name,
        "mac": mac
    })
    self.client.publish(topic, str(payload))
```

### Restart Player

```python
def restart(self, player_id: str):
    topic = f"device/{player_id}/command/restart"
    self.client.publish(topic)
```

### Request Status Update

```python
def update_status(self, player_id: str):
    """Force player to send current status"""
    topic = f"device/{player_id}/command/events"
    self.client.publish(topic)
```

## Event Handling

### Message Processing

```python
def _on_message(self, client, userdata, message):
    players = userdata[0]
    callback = userdata[1]
    
    base, device, topic = message.topic.split("/")
    player = players[device]
    
    if topic == "status":
        self._parse_status_message(
            json.loads(message.payload.decode("utf-8")),
            player
        )
        if callback:
            callback()
            
    elif topic == "events":
        self._parse_events_message(
            json.loads(message.payload.decode("utf-8")),
            player
        )
        if callback:
            callback()
```

### Status Message Parser

Updates player state from status messages:

```python
def _parse_status_message(self, message, player):
    player.night_light_mode = (
        get_child_value(message, "nightlightMode") 
        or player.night_light_mode
    )
    player.battery_level_percentage = (
        get_child_value(message, "batteryLevel")
        or player.battery_level_percentage
    )
    player.last_updated_at = datetime.datetime.now(pytz.utc)
```

### Events Message Parser

Updates player playback state from events:

```python
def _parse_events_message(self, message, player):
    if player.online is False:
        player.online = True
        
    # Update all fields with new values or keep existing
    player.repeat_all = get_child_value(message, "repeatAll") or player.repeat_all
    player.volume = get_child_value(message, "volume") or player.volume
    player.volume_max = get_child_value(message, "volumeMax") or player.volume_max
    player.online = get_child_value(message, "online") or player.online
    player.chapter_title = get_child_value(message, "chapterTitle") or player.chapter_title
    player.track_title = get_child_value(message, "trackTitle") or player.track_title
    player.track_length = get_child_value(message, "trackLength") or player.track_length
    player.track_position = get_child_value(message, "position") or player.track_position
    player.source = get_child_value(message, "source") or player.source
    player.playback_status = get_child_value(message, "playbackStatus") or player.playback_status
    
    # Sleep timer handling
    if get_child_value(message, "sleepTimerActive") is not None:
        player.sleep_timer_active = get_child_value(message, "sleepTimerActive")
    player.sleep_timer_seconds_remaining = (
        get_child_value(message, "sleepTimerSeconds")
        or player.sleep_timer_seconds_remaining
    )
    if not player.sleep_timer_active:
        player.sleep_timer_seconds_remaining = 0
        
    # Card info
    player.card_id = get_child_value(message, "cardId") or player.card_id
    if player.card_id == "none":
        player.card_id = None
        
    player.track_key = get_child_value(message, "trackKey") or player.track_key
    player.chapter_key = get_child_value(message, "chapterKey") or player.chapter_key
    player.last_updated_at = datetime.datetime.now(pytz.utc)
```

## Player State Model

### YotoPlayer Data Class

```python
@dataclass
class YotoPlayer:
    # Device Information
    id: str = None
    name: str = None
    device_type: str = None
    online: bool = None
    last_updated_at: datetime.datetime = None
    
    # Status (from REST API)
    active_card: str = None
    is_playing: bool = None
    playing_source: str = None
    ambient_light_sensor_reading: int = None
    battery_level_percentage: int = None
    day_mode_on: bool = None
    night_light_mode: str = None
    user_volume: int = None
    system_volume: int = None
    temperature_celcius: int = None
    bluetooth_audio_connected: bool = None
    charging: bool = None
    audio_device_connected: bool = None
    firmware_version: str = None
    wifi_strength: int = None
    power_source: str = None
    
    # MQTT State
    card_id: str = None
    repeat_all: bool = None
    volume_max: int = None
    volume: int = None
    chapter_title: str = None
    chapter_key: str = None
    source: str = None
    track_title: str = None
    track_length: int = None
    track_position: int = None
    track_key: str = None
    playback_status: str = None
    sleep_timer_active: bool = False
    sleep_timer_seconds_remaining: int = 0
    
    # Configuration
    config: YotoPlayerConfig = None
```

### Player Configuration

```python
@dataclass
class YotoPlayerConfig:
    # Day Mode Settings
    day_mode_time: datetime.time = None
    day_display_brightness: str = None  # "Auto" or specific value
    day_ambient_colour: str = None      # HEX color
    day_max_volume_limit: int = None
    
    # Night Mode Settings
    night_mode_time: datetime.time = None
    night_display_brightness: str = None
    night_ambient_colour: str = None
    night_max_volume_limit: int = None
    
    # Alarms
    alarms: list = None
```

## Integration Patterns

### Basic Integration Example

```python
import time
from yoto_api import YotoManager

# Initialize manager
ym = YotoManager(client_id="your_client_id")

# Authenticate
auth_result = ym.device_code_flow_start()
print(f"Go to {auth_result['verification_uri']} and enter code: {auth_result['user_code']}")
time.sleep(15)
ym.device_code_flow_complete()

# Connect to MQTT events
def on_player_update():
    for player_id, player in ym.players.items():
        print(f"Player {player.name}: {player.playback_status}")
        print(f"  Track: {player.track_title}")
        print(f"  Position: {player.track_position}/{player.track_length}")

ym.connect_to_events(callback=on_player_update)

# Control player
player_id = next(iter(ym.players))
ym.play_card(player_id, "7JtVV")
time.sleep(5)
ym.pause_player(player_id)
time.sleep(2)
ym.resume_player(player_id)

# Keep running to receive events
time.sleep(60)

# Cleanup
ym.disconnect()
```

### Advanced: Interactive Skill Pattern

```python
class YotoSkill:
    def __init__(self, manager: YotoManager):
        self.manager = manager
        self.player_id = None
        self.current_state = "idle"
        
    def on_event(self):
        """Called when player state changes"""
        player = self.manager.players[self.player_id]
        
        # Detect end of track
        if (player.playback_status == "stopped" and 
            self.current_state == "playing"):
            self.on_track_completed()
            
        # Detect card insertion
        if player.source == "nfc" and player.card_id:
            self.on_card_inserted(player.card_id)
    
    def on_track_completed(self):
        """Handle track completion - e.g., for Choose Your Own Adventure"""
        # Play next track based on user choice
        next_track = self.determine_next_track()
        self.manager.play_card(
            self.player_id,
            self.current_card,
            chapterKey=next_track["chapter"],
            trackKey=next_track["track"]
        )
    
    def on_card_inserted(self, card_id: str):
        """Handle card insertion"""
        if card_id == self.skill_card_id:
            self.start_skill()
    
    def start_skill(self):
        """Initialize skill execution"""
        self.current_state = "playing"
        # Play welcome message
        self.manager.play_card(
            self.player_id,
            self.current_card,
            chapterKey="01",
            trackKey="01"
        )
```

### Choose Your Own Adventure Implementation

```python
class AdventureSkill(YotoSkill):
    def __init__(self, manager: YotoManager, player_id: str):
        super().__init__(manager)
        self.player_id = player_id
        self.story_graph = self.load_story_graph()
        self.current_node = "start"
        self.choices = {}
    
    def load_story_graph(self):
        """Define story branching structure"""
        return {
            "start": {
                "track": "01",
                "choices": {
                    "left": "forest_path",
                    "right": "mountain_path"
                }
            },
            "forest_path": {
                "track": "02",
                "choices": {
                    "fight": "battle",
                    "flee": "escape"
                }
            },
            # ... more nodes
        }
    
    def on_track_completed(self):
        """Wait for user choice via button press or NFC"""
        node = self.story_graph[self.current_node]
        
        # Could use volume buttons as choice selectors
        # Or wait for specific NFC card placements
        # For now, trigger next based on timer or default
        
        next_choice = list(node["choices"].values())[0]
        self.play_node(next_choice)
    
    def play_node(self, node_id: str):
        """Play story node"""
        self.current_node = node_id
        node = self.story_graph[node_id]
        
        self.manager.play_card(
            self.player_id,
            self.current_card,
            trackKey=node["track"]
        )
```

### Volume-Based Input Detection

```python
class VolumeInputDetector:
    """Use volume changes as user input"""
    
    def __init__(self, manager: YotoManager):
        self.manager = manager
        self.last_volumes = {}
        self.input_callback = None
    
    def on_event(self):
        for player_id, player in self.manager.players.items():
            last_vol = self.last_volumes.get(player_id, player.volume)
            
            if player.volume > last_vol:
                self.on_volume_up(player_id)
            elif player.volume < last_vol:
                self.on_volume_down(player_id)
                
            self.last_volumes[player_id] = player.volume
    
    def on_volume_up(self, player_id: str):
        """Volume increase detected"""
        if self.input_callback:
            self.input_callback(player_id, "up")
    
    def on_volume_down(self, player_id: str):
        """Volume decrease detected"""
        if self.input_callback:
            self.input_callback(player_id, "down")
```

## Error Handling

### Connection Errors

```python
def _on_disconnect(self, client, userdata, rc):
    _LOGGER.debug(f"MQTT Disconnected: {rc}")
    # rc codes:
    # 0: Clean disconnect
    # 1-6: Connection errors
    # Handle reconnection logic here
```

### Token Expiration

```python
def check_and_refresh_token(self) -> Token:
    if self.token is None:
        raise ValueError("No token available, please authenticate first")
        
    if self.token.access_token is None:
        self.token = self.api.refresh_token(self.token)
    
    # Refresh 1 hour before expiration
    if self.token.valid_until - timedelta(hours=1) <= datetime.now(pytz.utc):
        self.token = self.api.refresh_token(self.token)
        
        # Reconnect MQTT with new token
        if self.mqtt_client:
            self.disconnect()
            self.connect_to_events(self.callback)
            
    return self.token
```

### Message Parsing Errors

```python
try:
    payload = json.loads(message.payload.decode("utf-8"))
    self._parse_events_message(payload, player)
except json.JSONDecodeError as e:
    _LOGGER.error(f"Failed to parse MQTT message: {e}")
except Exception as e:
    _LOGGER.error(f"Error processing MQTT message: {e}")
```

## Best Practices

### 1. Token Management
- Store refresh tokens securely
- Implement automatic token refresh
- Handle token refresh failures gracefully
- Re-establish MQTT connection after token refresh

### 2. MQTT Connection
- Use persistent connections with automatic reconnection
- Subscribe to all relevant topics on connect
- Implement exponential backoff for reconnection attempts
- Handle disconnections gracefully

### 3. Message Processing
- Use callbacks for asynchronous event handling
- Update local player state from MQTT messages
- Request status updates periodically for long-running connections
- Log all received messages for debugging

### 4. Command Execution
- Wait for status updates after sending commands
- Implement timeouts for command responses
- Handle command failures and retries
- Throttle command sending to avoid overwhelming the player

### 5. State Management
- Maintain local player state synchronized with MQTT events
- Use the `last_updated_at` timestamp to track state freshness
- Implement state change notifications for UI updates
- Cache player configuration to minimize API calls

### 6. Resource Management
- Always disconnect MQTT client on shutdown
- Stop MQTT loop before disconnecting
- Clean up player state on disconnect
- Handle multiple players efficiently

## Debugging

### Enable Logging

```python
import logging
import sys

logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s %(name)s %(levelname)s:%(message)s'
)
```

### Common Debug Patterns

```python
# Log all MQTT messages
def _on_message(self, client, userdata, message):
    _LOGGER.debug(f"MQTT Topic: {message.topic}")
    _LOGGER.debug(f"MQTT Payload: {message.payload}")
    # ... rest of processing

# Log connection status
def _on_connect(self, client, userdata, flags, rc):
    _LOGGER.debug(f"Connected with result code: {rc}")
    
# Log all player state changes
def on_player_update():
    for player_id, player in ym.players.items():
        _LOGGER.debug(f"Player {player_id} updated:")
        _LOGGER.debug(f"  Status: {player.playback_status}")
        _LOGGER.debug(f"  Position: {player.track_position}")
        _LOGGER.debug(f"  Volume: {player.volume}")
```

## Security Considerations

### 1. Token Storage
- Never commit tokens to version control
- Store refresh tokens in secure storage (keychain, encrypted file)
- Use environment variables for sensitive configuration
- Implement token rotation policies

### 2. MQTT Security
- Always use TLS for MQTT connections
- Validate JWT tokens before use
- Don't log access tokens
- Implement proper authentication error handling

### 3. API Rate Limiting
- Respect API rate limits
- Implement exponential backoff for failed requests
- Cache data when possible to reduce API calls
- Use MQTT for real-time updates instead of polling

## Performance Optimization

### 1. Connection Management
- Use single MQTT connection per application instance
- Reuse connections across multiple operations
- Implement connection pooling for multiple players
- Use async/await patterns for non-blocking operations

### 2. Message Processing
- Process messages asynchronously
- Use message queues for high-volume scenarios
- Batch status updates when possible
- Implement efficient state diffing

### 3. Memory Management
- Clean up old player states
- Limit message history retention
- Use generators for large data sets
- Implement proper resource cleanup

## Testing

### Unit Testing

```python
import unittest
from unittest.mock import Mock, patch
from yoto_api import YotoMQTTClient

class TestYotoMQTT(unittest.TestCase):
    def setUp(self):
        self.mqtt_client = YotoMQTTClient()
        self.mock_player = Mock()
        
    def test_parse_events_message(self):
        message = {
            "playbackStatus": "playing",
            "volume": 5,
            "cardId": "test123"
        }
        self.mqtt_client._parse_events_message(message, self.mock_player)
        self.assertEqual(self.mock_player.playback_status, "playing")
        self.assertEqual(self.mock_player.volume, 5)
        self.assertEqual(self.mock_player.card_id, "test123")
```

### Integration Testing

```python
def test_full_playback_flow():
    ym = YotoManager(client_id=TEST_CLIENT_ID)
    ym.set_refresh_token(TEST_REFRESH_TOKEN)
    ym.check_and_refresh_token()
    
    # Connect and wait for initial status
    event_received = False
    def callback():
        nonlocal event_received
        event_received = True
    
    ym.connect_to_events(callback=callback)
    time.sleep(5)
    assert event_received, "Should receive initial status"
    
    # Test playback control
    player_id = next(iter(ym.players))
    ym.play_card(player_id, TEST_CARD_ID)
    time.sleep(2)
    
    player = ym.players[player_id]
    assert player.playback_status == "playing"
    assert player.card_id == TEST_CARD_ID
    
    ym.disconnect()
```

## References

### Official Resources
- Yoto Developer Portal: https://yoto.dev/
- AWS IoT Core Documentation: https://docs.aws.amazon.com/iot/
- MQTT Protocol Specification: https://mqtt.org/

### Community Resources
- yoto_api Python Library: https://github.com/cdnninja/yoto_api
- Home Assistant Yoto Integration: Based on yoto_api

### Related Protocols
- MQTT over WebSockets: RFC 6455
- JWT Authentication: RFC 7519
- OAuth 2.0 Device Flow: RFC 8628

## Changelog

### Version 1.0 (2026-01-10)
- Initial comprehensive reference document
- Detailed MQTT protocol documentation
- Integration patterns and examples
- Security and performance best practices
- Choose Your Own Adventure implementation pattern

## Future Enhancements

### Planned Features
1. **WebSocket Direct Connection** - Alternative to MQTT client library
2. **Offline Caching** - Cache player state for offline access
3. **Multi-Player Orchestration** - Synchronized playback across multiple players
4. **Voice Input Integration** - Use microphone for interactive skills
5. **Analytics and Telemetry** - Track usage patterns and performance metrics

### Research Areas
1. **Player Discovery** - Automatic discovery of players on local network
2. **Direct Player Communication** - Bypass cloud for local control
3. **Custom Card Formats** - Support for user-generated content
4. **Advanced Audio Routing** - Multi-source audio mixing
5. **Energy Management** - Battery optimization strategies

---

**Document Maintained By**: Yoto Smart Stream Project  
**Last Updated**: 2026-01-10  
**Version**: 1.0
