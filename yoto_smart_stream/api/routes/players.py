"""Player control endpoints."""

import logging
from typing import Optional

import requests
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..dependencies import get_yoto_client

logger = logging.getLogger(__name__)
router = APIRouter()


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
    volume: Optional[int] = Field(None, ge=0, le=100, description="Volume level (0-100)")


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
    # Get volume:  
    # player.volume = MQTT value (0-16 scale)
    # player.user_volume = REST API userVolumePercentage (0-100 scale) 
    # player.system_volume = REST API systemVolumePercentage (0-100 scale)
    # We want the user-controlled volume percentage (0-100)
    volume = getattr(player, 'user_volume', None)
    if volume is None:
        # Fallback to system_volume if user_volume not available
        volume = getattr(player, 'system_volume', None)
    if volume is None:
        # If still no volume, try MQTT volume and convert from 0-16 to 0-100
        mqtt_volume = getattr(player, 'volume', None)
        if mqtt_volume is not None:
            # Convert 0-16 scale to 0-100 percentage (matching yoto_ha's / 16 logic)
            volume = round((mqtt_volume / 16) * 100)
        else:
            volume = 50  # Default to 50% if no volume available

    # Convert volume from 0-16 scale to 0-100 percentage
    if volume is not None:
        volume = int((volume / 16) * 100)
    else:
        volume = 50  # Default to 50%

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
    if active_card and manager and hasattr(manager, 'library'):
        try:
            # Use dictionary access like yoto_ha does
            if active_card in manager.library:
                card = manager.library[active_card]
                card_title = getattr(card, 'title', None)
                card_author = getattr(card, 'author', None)
                # yoto_ha uses cover_image_large
                card_cover_url = getattr(card, 'cover_image_large', None)
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
    if active_card and manager and hasattr(manager, 'library'):
        try:
            card = manager.library.get(active_card)
            if card:
                card_title = getattr(card, 'title', None)
                card_author = getattr(card, 'author', None)
                # yoto_ha uses cover_image_large
                card_cover_url = getattr(card, 'cover_image_large', None)
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
async def list_players():
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

    try:
        # Refresh player status
        client.update_player_status()

        # Update library to get card metadata
        try:
            client.update_library()
        except Exception as e:
            logger.warning(f"Failed to update library: {e}")

        manager = client.get_manager()

        if not manager.players:
            return []

        # Convert to response models
        players = []
        for player_id, player in manager.players.items():
            players.append(extract_player_info(player_id, player, manager))

        return players

    except Exception as e:
        logger.error(f"Failed to fetch players: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch players: {str(e)}",
        ) from e


@router.get("/players/{player_id}", response_model=PlayerDetailInfo)
async def get_player(player_id: str):
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
async def get_player_status(player_id: str):
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
async def get_player_config(player_id: str):
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
async def control_player(player_id: str, control: PlayerControl):
    """
    Control a Yoto player.

    Supported actions:
    - play: Resume playback
    - pause: Pause playback
    - skip_forward: Skip to next chapter
    - skip_backward: Skip to previous chapter

    Optional parameters:
    - volume: Set volume level (0-100)
    """
    client = get_yoto_client()
    manager = client.get_manager()

    if player_id not in manager.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    try:
        # Execute action
        if control.action == "pause":
            manager.pause_player(player_id)
        elif control.action == "play":
            manager.resume_player(player_id)
        elif control.action == "stop":
            manager.stop_player(player_id)
        elif control.action == "skip_forward":
            manager.skip_chapter(player_id, direction="forward")
        elif control.action == "skip_backward":
            manager.skip_chapter(player_id, direction="backward")
        elif control.action == "volume":
            # Volume-only action
            if control.volume is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Volume value required for volume action"
                )
            manager.set_volume(player_id, control.volume)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {control.action}"
            )

        # Set volume if provided for other actions
        if control.action != "volume" and control.volume is not None:
            manager.set_volume(player_id, control.volume)

        return {"success": True, "player_id": player_id, "action": control.action}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control player: {str(e)}",
        ) from e
