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


class PlayerDetailInfo(BaseModel):
    """Detailed player information response model."""

    id: str
    name: str
    online: bool
    volume: int = Field(..., ge=0, le=100)
    playing: bool = False
    battery_level: Optional[int] = None
    is_charging: Optional[bool] = None
    firmware_version: Optional[str] = None
    wifi_strength: Optional[int] = None
    temperature: Optional[float] = None
    active_card: Optional[str] = None
    playback_status: Optional[str] = None
    playback_position: Optional[int] = None
    track_length: Optional[int] = None
    current_chapter: Optional[str] = None
    nightlight_mode: Optional[str] = None
    day_mode: Optional[bool] = None
    power_source: Optional[str] = None
    device_type: Optional[str] = None


class PlayerControl(BaseModel):
    """Player control request model."""

    action: str = Field(
        ..., description="Action to perform: play, pause, skip_forward, skip_backward"
    )
    volume: Optional[int] = Field(None, ge=0, le=100, description="Volume level (0-100)")


def extract_player_info(player_id: str, player) -> PlayerInfo:
    """
    Extract PlayerInfo from a YotoPlayer object.

    This helper function handles the extraction of player data from the yoto_api
    library's YotoPlayer object, with proper fallbacks for missing data.

    Args:
        player_id: The player's unique identifier
        player: YotoPlayer object from yoto_api library

    Returns:
        PlayerInfo with extracted data
    """
    # Get volume: prefer MQTT volume, fallback to user_volume, then default to 8
    volume = getattr(player, 'volume', None)
    if volume is None:
        volume = getattr(player, 'user_volume', None)
    if volume is None:
        volume = 8

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

    return PlayerInfo(
        id=player_id,
        name=player.name,
        online=player.online,
        volume=volume,
        playing=playing,
        battery_level=battery_level,
    )


def extract_player_detail_info(player_id: str, player) -> PlayerDetailInfo:
    """
    Extract comprehensive PlayerDetailInfo from a YotoPlayer object.

    Args:
        player_id: The player's unique identifier
        player: YotoPlayer object from yoto_api library

    Returns:
        PlayerDetailInfo with all available data
    """
    # Get volume - try both snake_case and camelCase
    volume = getattr(player, 'volume', None)
    if volume is None:
        volume = getattr(player, 'user_volume', None)
    if volume is None:
        volume = getattr(player, 'userVolume', None)
    if volume is None:
        volume = 8

    # Get playing status
    playing = False
    playback_status = getattr(player, 'playback_status', None) or getattr(player, 'playbackStatus', None)
    if playback_status is not None:
        playing = playback_status == "playing"
    else:
        is_playing = getattr(player, 'is_playing', None) or getattr(player, 'isPlaying', None)
        if is_playing is not None:
            playing = is_playing

    # Map power source integer to string
    power_source_map = {0: "Battery", 1: "V2 Dock", 2: "USB-C", 3: "Qi Dock"}
    power_source_int = getattr(player, 'power_source', None) or getattr(player, 'powerSource', None)
    power_source = power_source_map.get(power_source_int) if power_source_int is not None else None

    # Get charging status - try both naming conventions
    is_charging = getattr(player, 'is_charging', None)
    if is_charging is None:
        is_charging = getattr(player, 'isCharging', None)
    # Convert from integer if needed (0=not charging, 1=charging)
    if isinstance(is_charging, int):
        is_charging = bool(is_charging)

    # Get battery level
    battery_level = getattr(player, 'battery_level_percentage', None)
    if battery_level is None:
        battery_level = getattr(player, 'batteryLevelPercentage', None)

    # Get firmware version
    firmware_version = getattr(player, 'firmware_version', None)
    if firmware_version is None:
        firmware_version = getattr(player, 'firmwareVersion', None)

    # Get wifi strength
    wifi_strength = getattr(player, 'wifi_strength', None)
    if wifi_strength is None:
        wifi_strength = getattr(player, 'wifiStrength', None)

    # Get temperature
    temperature = getattr(player, 'temperature_celsius', None)
    if temperature is None:
        temperature = getattr(player, 'temperatureCelsius', None)

    # Get active card
    active_card = getattr(player, 'active_card', None)
    if active_card is None:
        active_card = getattr(player, 'activeCard', None)

    # Get playback position
    playback_position = getattr(player, 'playback_position', None)
    if playback_position is None:
        playback_position = getattr(player, 'playbackPosition', None)

    # Get track length
    track_length = getattr(player, 'track_length', None)
    if track_length is None:
        track_length = getattr(player, 'trackLength', None)

    # Get current chapter
    current_chapter = getattr(player, 'current_chapter', None)
    if current_chapter is None:
        current_chapter = getattr(player, 'currentChapter', None)

    # Get nightlight mode
    nightlight_mode = getattr(player, 'nightlight_mode', None)
    if nightlight_mode is None:
        nightlight_mode = getattr(player, 'nightlightMode', None)

    # Get day mode
    day_mode = getattr(player, 'day_mode', None)
    if day_mode is None:
        day_mode = getattr(player, 'dayMode', None)

    # Get device type
    device_type = getattr(player, 'device_type', None)
    if device_type is None:
        device_type = getattr(player, 'deviceType', None)

    return PlayerDetailInfo(
        id=player_id,
        name=player.name,
        online=player.online,
        volume=volume,
        playing=playing,
        battery_level=battery_level,
        is_charging=is_charging,
        firmware_version=firmware_version,
        wifi_strength=wifi_strength,
        temperature=temperature,
        active_card=active_card,
        playback_status=playback_status,
        playback_position=playback_position,
        track_length=track_length,
        current_chapter=current_chapter,
        nightlight_mode=nightlight_mode,
        day_mode=day_mode,
        power_source=power_source,
        device_type=device_type,
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
        manager = client.get_manager()

        if not manager.players:
            return []

        # Convert to response models
        players = []
        for player_id, player in manager.players.items():
            players.append(extract_player_info(player_id, player))

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

    manager = client.get_manager()

    if player_id not in manager.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    player = manager.players[player_id]
    return extract_player_detail_info(player_id, player)


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
            manager.play_player(player_id)
        elif control.action == "skip_forward":
            manager.skip_chapter(player_id, direction="forward")
        elif control.action == "skip_backward":
            manager.skip_chapter(player_id, direction="backward")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {control.action}"
            )

        # Set volume if provided
        if control.volume is not None:
            manager.set_volume(player_id, control.volume)

        return {"success": True, "player_id": player_id, "action": control.action}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control player: {str(e)}",
        ) from e
