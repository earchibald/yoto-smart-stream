"""Player control endpoints."""

import logging
import time
from typing import Dict, Optional, Tuple

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import User
from ..dependencies import get_yoto_client
from .user_auth import require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

# Volume change cache: {player_id: (volume, timestamp)}
# This prevents volume changes from being overridden by stale MQTT/API data
_volume_cache: Dict[str, Tuple[int, float]] = {}
VOLUME_CACHE_TTL = 5.0  # seconds


# Request/Response models
class PlayerInfo(BaseModel):
    """Player information response model."""

    id: str
    name: str
    online: bool
    volume: int = Field(..., ge=0, le=100)
    playing: bool = False
    battery_level: Optional[int] = None

    # Charging status
    is_charging: Optional[bool] = None

    # Temperature
    temperature: Optional[float] = None

    # Sleep timer
    sleep_timer_active: Optional[bool] = None
    sleep_timer_seconds_remaining: Optional[int] = None

    # Audio connections
    bluetooth_audio_connected: Optional[bool] = None

    # Active playback
    active_card: Optional[str] = None
    chapter_title: Optional[str] = None
    track_title: Optional[str] = None

    # Card/Album Info (from library)
    card_title: Optional[str] = None  # Album name
    card_author: Optional[str] = None  # Artist name
    card_cover_url: Optional[str] = None  # Album art


class PlayerDetailInfo(BaseModel):
    """Detailed player information response model."""

    id: str
    name: str
    online: bool
    volume: int = Field(..., ge=0, le=100)
    playing: bool = False

    # Battery & Power
    battery_level: Optional[int] = None
    is_charging: Optional[bool] = None
    power_source: Optional[str] = None

    # Device Info
    firmware_version: Optional[str] = None
    device_type: Optional[str] = None

    # Network & Environment
    wifi_strength: Optional[int] = None
    temperature: Optional[float] = None
    ambient_light: Optional[int] = None

    # Playback
    active_card: Optional[str] = None
    playback_status: Optional[str] = None
    playback_position: Optional[int] = None
    track_length: Optional[int] = None
    current_chapter: Optional[str] = None
    current_track: Optional[str] = None
    chapter_title: Optional[str] = None
    track_title: Optional[str] = None

    # Card/Album Info (from library)
    card_title: Optional[str] = None  # Album name
    card_author: Optional[str] = None  # Artist name
    card_cover_url: Optional[str] = None  # Album art

    # Modes & Settings
    nightlight_mode: Optional[str] = None
    day_mode: Optional[bool] = None

    # Audio Connections
    bluetooth_audio_connected: Optional[bool] = None
    audio_device_connected: Optional[bool] = None

    # Sleep Timer
    sleep_timer_active: Optional[bool] = None
    sleep_timer_seconds_remaining: Optional[int] = None

    # Timestamps
    last_updated_at: Optional[str] = None


class PlayerControl(BaseModel):
    """Player control request model."""

    action: str = Field(
        ..., description="Action to perform: play, pause, stop, skip_forward, skip_backward, volume"
    )
    volume: Optional[int] = Field(None, ge=0, le=16, description="Volume level (0-16 bins)")


def extract_player_info(player_id: str, player, manager=None) -> PlayerInfo:
    """
    Extract PlayerInfo from a YotoPlayer object.

    This helper function handles the extraction of player data from the yoto_api
    library's YotoPlayer object, with proper fallbacks for missing data.

    Args:
        player_id: The player's unique identifier
        player: YotoPlayer object from yoto_api library
        manager: YotoManager object (optional, for library access)

    Returns:
        PlayerInfo with extracted data
    """
    # Check volume cache first (recent volume changes take priority)
    volume = None
    current_time = time.time()
    if player_id in _volume_cache:
        cached_volume, timestamp = _volume_cache[player_id]
        if current_time - timestamp < VOLUME_CACHE_TTL:
            # Cache is still fresh, use cached volume
            volume = cached_volume
            logger.debug(f"Using cached volume {volume}% for player {player_id}")
        else:
            # Cache expired, remove it
            del _volume_cache[player_id]
    
    # If no valid cached volume, get from player object
    if volume is None:
        # Get volume - prioritize MQTT data (real-time) over REST API (slow to update):
        # Strategy:
        # 1. Try MQTT volume first (player.volume, 0-16 scale) - real-time from device
        # 2. Fall back to REST API (player.user_volume, 0-100 scale) - slow (30-60s lag)
        # 3. Fall back to system volume (player.system_volume, 0-100 scale)
        # 
        # Hardware supports 0-16 (17 levels total)
        mqtt_volume = getattr(player, 'volume', None)
        if mqtt_volume is not None:
            # Use MQTT volume directly (0-16 scale)
            volume = mqtt_volume
            logger.debug(f"Using MQTT volume {volume}/16 for player {player_id}")
        else:
            # No MQTT data yet, use REST API data (convert from percentage to bins)
            api_volume = getattr(player, 'user_volume', None)
            if api_volume is None:
                # Fallback to system_volume if user_volume not available
                api_volume = getattr(player, 'system_volume', None)
            if api_volume is not None:
                # Convert from 0-100 percentage to 0-16 bins
                volume = round((api_volume / 100) * 16)
            else:
                volume = 8  # Default to 8/16 (mid-range) if no volume available

    # Ensure volume is within valid range (0-16)
    if volume is not None:
        volume = max(0, min(16, int(volume)))
    else:
        volume = 8  # Default to 8/16

    # Get playing status: check playback_status string or is_playing boolean
    playing = False
    playback_status = getattr(player, 'playback_status', None)
    if playback_status is not None:
        playing = playback_status == "playing"
    else:
        is_playing = getattr(player, 'is_playing', None)
        if is_playing is not None:
            playing = is_playing

    # Get battery level from battery_level_percentage attribute
    battery_level = getattr(player, 'battery_level_percentage', None)

    # Charging status
    is_charging = getattr(player, 'charging', None)

    # Temperature
    temperature = getattr(player, 'temperature_celcius', None)

    # Sleep timer
    sleep_timer_active = getattr(player, 'sleep_timer_active', None)
    sleep_timer_seconds_remaining = getattr(player, 'sleep_timer_seconds_remaining', None)

    # Audio connections
    bluetooth_audio_connected = getattr(player, 'bluetooth_audio_connected', None)

    # Active playback
    active_card = getattr(player, 'card_id', None)
    chapter_title = getattr(player, 'chapter_title', None)
    track_title = getattr(player, 'track_title', None)

    # Card/Album info from library (like yoto_ha media_album_name, media_artist, media_image_url)
    card_title = None
    card_author = None
    card_cover_url = None

    # Look up card metadata from library if we have an active card
    if active_card and active_card != 'none' and manager and hasattr(manager, 'library'):
        try:
            logger.debug(f"Looking up card {active_card} in library with {len(manager.library)} cards")
            # Use dictionary access like yoto_ha does
            if active_card in manager.library:
                card = manager.library[active_card]
                card_title = getattr(card, 'title', None)
                card_author = getattr(card, 'author', None)
                # yoto_ha uses cover_image_large
                card_cover_url = getattr(card, 'cover_image_large', None)
                logger.debug(f"Found card info: title={card_title}, author={card_author}")
            else:
                logger.warning(f"Card {active_card} not found in library")
        except Exception as e:
            logger.warning(f"Failed to get card info for {active_card}: {e}")

    return PlayerInfo(
        id=player_id,
        name=player.name,
        online=player.online,
        volume=volume,
        playing=playing,
        battery_level=battery_level,
        is_charging=is_charging,
        temperature=temperature,
        sleep_timer_active=sleep_timer_active,
        sleep_timer_seconds_remaining=sleep_timer_seconds_remaining,
        bluetooth_audio_connected=bluetooth_audio_connected,
        active_card=active_card,
        chapter_title=chapter_title,
        track_title=track_title,
        card_title=card_title,
        card_author=card_author,
        card_cover_url=card_cover_url,
    )


def extract_player_detail_info(player_id: str, player, manager=None) -> PlayerDetailInfo:
    """
    Extract comprehensive PlayerDetailInfo from a YotoPlayer object.

    Based on yoto_ha Home Assistant integration attribute mapping.
    The yoto_api library uses snake_case for attributes populated from status/config.

    Args:
        player_id: The player's unique identifier
        player: YotoPlayer object from yoto_api library
        manager: YotoManager object (optional, for library access)

    Returns:
        PlayerDetailInfo with all available data
    """
    # Volume - yoto_api normalizes to 0-16 scale
    volume = getattr(player, 'volume', 8)

    # Convert volume from 0-16 scale to 0-100 percentage
    if volume is not None:
        volume = int((volume / 16) * 100)
    else:
        volume = 50  # Default to 50%

    # Get playing status from playback_status
    playback_status = getattr(player, 'playback_status', None)
    playing = playback_status == "playing" if playback_status is not None else False

    # Charging status - yoto_ha uses player.charging (boolean)
    is_charging = getattr(player, 'charging', None)

    # Battery level - yoto_ha uses player.battery_level_percentage
    battery_level = getattr(player, 'battery_level_percentage', None)

    # Firmware version - yoto_ha uses player.firmware_version
    firmware_version = getattr(player, 'firmware_version', None)

    # WiFi strength - yoto_ha uses player.wifi_strength
    wifi_strength = getattr(player, 'wifi_strength', None)

    # Temperature - yoto_ha uses player.temperature_celcius (note the typo in API)
    temperature = getattr(player, 'temperature_celcius', None)

    # Ambient light - yoto_ha uses player.ambient_light_sensor_reading
    ambient_light = getattr(player, 'ambient_light_sensor_reading', None)

    # Card and playback info - yoto_ha uses these exact names
    active_card = getattr(player, 'card_id', None)
    playback_position = getattr(player, 'track_position', None)
    track_length = getattr(player, 'track_length', None)
    current_chapter = getattr(player, 'chapter_key', None)
    current_track = getattr(player, 'track_key', None)
    chapter_title = getattr(player, 'chapter_title', None)
    track_title = getattr(player, 'track_title', None)

    # Nightlight mode - yoto_ha uses player.night_light_mode
    nightlight_mode = getattr(player, 'night_light_mode', None)

    # Day mode - yoto_ha uses player.day_mode_on (boolean)
    day_mode = getattr(player, 'day_mode_on', None)

    # Device type - yoto_ha uses player.device_type
    device_type = getattr(player, 'device_type', None)

    # Audio connections
    bluetooth_audio_connected = getattr(player, 'bluetooth_audio_connected', None)
    audio_device_connected = getattr(player, 'audio_device_connected', None)

    # Sleep timer
    sleep_timer_active = getattr(player, 'sleep_timer_active', None)
    sleep_timer_seconds_remaining = getattr(player, 'sleep_timer_seconds_remaining', None)

    # Timestamps
    last_updated_at = getattr(player, 'last_updated_at', None)
    if last_updated_at and hasattr(last_updated_at, 'isoformat'):
        last_updated_at = last_updated_at.isoformat()
    elif last_updated_at:
        last_updated_at = str(last_updated_at)

    # Power source - not directly exposed as attribute, would need config parsing
    power_source = None

    # Card/Album info from library (like yoto_ha media_album_name, media_artist, media_image_url)
    card_title = None
    card_author = None
    card_cover_url = None

    # Look up card metadata from library if we have an active card
    if active_card and active_card != 'none' and manager and hasattr(manager, 'library'):
        try:
            logger.debug(f"[Detail] Looking up card {active_card} in library with {len(manager.library)} cards")
            card = manager.library.get(active_card)
            if card:
                card_title = getattr(card, 'title', None)
                card_author = getattr(card, 'author', None)
                # yoto_ha uses cover_image_large
                card_cover_url = getattr(card, 'cover_image_large', None)
                logger.debug(f"[Detail] Found card info: title={card_title}, author={card_author}")
            else:
                logger.warning(f"[Detail] Card {active_card} not found in library")
        except Exception as e:
            logger.warning(f"Failed to get card info for {active_card}: {e}")

    return PlayerDetailInfo(
        id=player_id,
        name=player.name,
        online=player.online,
        volume=volume,
        playing=playing,
        battery_level=battery_level,
        is_charging=is_charging,
        power_source=power_source,
        firmware_version=firmware_version,
        device_type=device_type,
        wifi_strength=wifi_strength,
        temperature=temperature,
        ambient_light=ambient_light,
        active_card=active_card,
        playback_status=playback_status,
        playback_position=playback_position,
        track_length=track_length,
        current_chapter=current_chapter,
        current_track=current_track,
        chapter_title=chapter_title,
        track_title=track_title,
        card_title=card_title,
        card_author=card_author,
        card_cover_url=card_cover_url,
        nightlight_mode=nightlight_mode,
        day_mode=day_mode,
        bluetooth_audio_connected=bluetooth_audio_connected,
        audio_device_connected=audio_device_connected,
        sleep_timer_active=sleep_timer_active,
        sleep_timer_seconds_remaining=sleep_timer_seconds_remaining,
        last_updated_at=last_updated_at,
    )


@router.get("/players", response_model=list[PlayerInfo])
async def list_players(user: User = Depends(require_auth)):
    """
    List all Yoto players on the account.

    Returns a list of players with their current status, including:
    - Player ID and name
    - Online status
    - Current volume
    - Playing status
    - Battery level (if available)
    """
    try:
         client = get_yoto_client()
     except RuntimeError as e:
         logger.error(f"Failed to get Yoto client: {e}")
         raise HTTPException(
             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
             detail=f"Yoto client not initialized. Please authenticate first: {str(e)}",
         ) from e

     # Ensure we have a fresh, authenticated client before making API calls
     try:
         client.ensure_authenticated()
     except Exception as e:
         error_str = str(e).lower()
         logger.info(f"Client authentication check failed: {e}")
         raise HTTPException(
             status_code=status.HTTP_401_UNAUTHORIZED,
             detail="Not authenticated with Yoto API. Please connect your Yoto account."
         )

     try:
         # Refresh player status
         try:
             client.update_player_status()
         except FileNotFoundError as e:
             logger.info(f"Players requested without Yoto auth: {e}")
             raise HTTPException(
                 status_code=status.HTTP_401_UNAUTHORIZED,
                 detail="Not authenticated with Yoto API. Please connect your Yoto account."
             )
         except Exception as e:
             # Catch AuthenticationError and other auth-related exceptions
             error_str = str(e).lower()
             if "authentication" in error_str or "refresh token" in error_str or "unauthorized" in error_str:
                 logger.info(f"Players requested with invalid/expired auth: {e}")
                 raise HTTPException(
                     status_code=status.HTTP_401_UNAUTHORIZED,
                     detail="Not authenticated with Yoto API. Please connect your Yoto account."
                 )
             # Re-raise other exceptions to be caught by the outer except
             raise

        # Update library to get card metadata
        try:
            client.update_library()
        except Exception as e:
            logger.warning(f"Failed to update library: {e}")

        try:
            manager = client.get_manager()
        except RuntimeError as e:
            logger.info(f"Players requested without Yoto auth (manager): {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Yoto API. Please connect your Yoto account."
            )

        if not manager.players:
            return []

        # Convert to response models
        players = []
        for player_id, player in manager.players.items():
            players.append(extract_player_info(player_id, player, manager))

        return players

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch players: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch players: {str(e)}",
        ) from e


@router.get("/players/{player_id}", response_model=PlayerDetailInfo)
async def get_player(player_id: str, user: User = Depends(require_auth)):
    """
    Get detailed information about a specific player.

    Args:
        player_id: The unique identifier of the player

    Returns:
        Detailed player information including battery, firmware, WiFi, and playback status
    """
    client = get_yoto_client()

    # Refresh player status to get latest information
    try:
        client.update_player_status()
    except Exception as e:
        logger.warning(f"Failed to refresh player status: {e}")

    # Update library to get card metadata (needed for card_title, card_author, card_cover_url)
    try:
        client.update_library()
    except Exception as e:
        logger.warning(f"Failed to update library: {e}")

    manager = client.get_manager()

    if player_id not in manager.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    player = manager.players[player_id]
    return extract_player_detail_info(player_id, player, manager)


@router.get("/players/{player_id}/status")
async def get_player_status(player_id: str, user: User = Depends(require_auth)):
    """
    Get device status from Yoto API.

    Fetches real-time status information directly from GET /device-v2/{deviceId}/status
    including battery, connectivity, temperature, and sensor data.

    Args:
        player_id: The unique identifier of the player

    Returns:
        Raw device status data from Yoto API
    """
    client = get_yoto_client()
    manager = client.get_manager()

    if player_id not in manager.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    try:
        access_token = client.get_access_token()
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Yoto API"
            )

        url = f"https://api.yotoplay.com/device-v2/{player_id}/status"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()

    except requests.HTTPError as e:
        logger.error(f"Failed to fetch device status: {e}")
        raise HTTPException(
            status_code=e.response.status_code if e.response else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch device status: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Error fetching device status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching device status: {str(e)}"
        ) from e


@router.get("/players/{player_id}/config")
async def get_player_config(player_id: str, user: User = Depends(require_auth)):
    """
    Get device configuration from Yoto API.

    Fetches configuration settings directly from GET /device-v2/{deviceId}/config
    including day/night modes, volume limits, display settings, and alarms.

    Args:
        player_id: The unique identifier of the player

    Returns:
        Raw device config data from Yoto API
    """
    client = get_yoto_client()
    manager = client.get_manager()

    if player_id not in manager.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    try:
        access_token = client.get_access_token()
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Yoto API"
            )

        url = f"https://api.yotoplay.com/device-v2/{player_id}/config"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        return response.json()

    except requests.HTTPError as e:
        logger.error(f"Failed to fetch device config: {e}")
        raise HTTPException(
            status_code=e.response.status_code if e.response else status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch device config: {str(e)}"
        ) from e
    except Exception as e:
        logger.error(f"Error fetching device config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching device config: {str(e)}"
        ) from e


@router.post("/players/{player_id}/control")
async def control_player(player_id: str, control: PlayerControl, user: User = Depends(require_auth)):
    """
    Control a Yoto player via MQTT using official Yoto command topics.
    
    Uses official Yoto MQTT commands:
    - pause: /device/{id}/command/card/pause
    - play: /device/{id}/command/card/resume  
    - stop: /device/{id}/command/card/stop
    - volume: /device/{id}/command/volume/set
    
    Supported actions:
    - play: Resume playback
    - pause: Pause playback
    - stop: Stop playback
    - skip_forward: Skip to next chapter
    - skip_backward: Skip to previous chapter
    - volume: Set volume level

    Optional parameters:
    - volume: Set volume level (0-100)
    """
    import json
    
    client = get_yoto_client()
    manager = client.get_manager()

    if player_id not in manager.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    # Check MQTT connection
    if not hasattr(manager, 'mqtt_client') or not manager.mqtt_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT connection not available"
        )

    try:
        # Execute action using official MQTT topics
        if control.action == "pause":
            topic = f"device/{player_id}/command/card/pause"
            logger.info(f"Publishing MQTT pause command to {topic}")
            manager.mqtt_client.client.publish(topic, "")
            
        elif control.action == "play":
            topic = f"device/{player_id}/command/card/resume"
            logger.info(f"Publishing MQTT resume command to {topic}")
            manager.mqtt_client.client.publish(topic, "")
            
        elif control.action == "stop":
            topic = f"device/{player_id}/command/card/stop"
            logger.info(f"Publishing MQTT stop command to {topic}")
            manager.mqtt_client.client.publish(topic, "")
            
        elif control.action == "skip_forward":
            # Skip forward uses the library method (no official MQTT topic documented)
            manager.skip_chapter(player_id, direction="forward")
            
        elif control.action == "skip_backward":
            # Skip backward uses the library method (no official MQTT topic documented)
            manager.skip_chapter(player_id, direction="backward")
            
        elif control.action == "volume":
            # Volume-only action
            if control.volume is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Volume value required for volume action"
                )
            # Official topic: device/{id}/command/volume/set
            topic = f"device/{player_id}/command/volume/set"
            payload = json.dumps({"volume": control.volume})
            logger.info(f"Publishing MQTT volume command to {topic}: {payload}")
            manager.mqtt_client.client.publish(topic, payload)
            
            # Cache the volume change to prevent stale MQTT data from overriding it
            _volume_cache[player_id] = (control.volume, time.time())
            logger.info(f"Cached volume {control.volume} for player {player_id}")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {control.action}"
            )

        # Set volume if provided for other actions
        if control.action != "volume" and control.volume is not None:
            topic = f"device/{player_id}/command/volume/set"
            payload = json.dumps({"volume": control.volume})
            logger.info(f"Publishing MQTT volume command with action to {topic}: {payload}")
            manager.mqtt_client.client.publish(topic, payload)
            
            # Cache the volume change
            _volume_cache[player_id] = (control.volume, time.time())
            logger.info(f"Cached volume {control.volume} for player {player_id}")

        return {"success": True, "player_id": player_id, "action": control.action}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to control player {player_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control player: {str(e)}",
        ) from e


@router.post("/players/{player_id}/play-card")
async def play_card(player_id: str, card_id: str, chapter: int = 1, user: User = Depends(require_auth)):
    """
    Play a specific card and chapter on a Yoto player via MQTT.
    
    Uses the official Yoto MQTT command format:
    Topic: /device/{id}/command/card/start
    Payload: {"uri": "https://yoto.io/{card_id}", "chapterKey": "01"}
    
    Args:
        player_id: The player ID
        card_id: The card ID from the library
        chapter: Chapter number to start from (default: 1)
    
    Returns:
        Success status
    """
    import json
    
    client = get_yoto_client()
    manager = client.get_manager()

    if player_id not in manager.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    # Check MQTT connection
    if not hasattr(manager, 'mqtt_client') or not manager.mqtt_client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MQTT connection not available"
        )

    try:
        # Format chapter key with zero-padding (e.g., "01", "02", "10")
        chapter_key = str(chapter).zfill(2)
        
        # Build MQTT payload per official Yoto MQTT documentation
        # https://yoto.dev/players-mqtt/mqtt-docs/
        payload = {
            "uri": f"https://yoto.io/{card_id}",
            "chapterKey": chapter_key
        }
        
        # Official MQTT topic format: device/{id}/command/card/start
        topic = f"device/{player_id}/command/card/start"
        
        logger.info(f"Publishing to MQTT - Topic: {topic}, Payload: {payload}")
        
        # Publish directly to MQTT
        manager.mqtt_client.client.publish(topic, json.dumps(payload))
        
        logger.info(f"Successfully published card play command for player {player_id}")
        
        return {
            "success": True,
            "player_id": player_id,
            "card_id": card_id,
            "chapter": chapter,
            "mqtt_topic": topic
        }

    except Exception as e:
        logger.error(f"Failed to play card via MQTT: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to play card: {str(e)}",
        ) from e
