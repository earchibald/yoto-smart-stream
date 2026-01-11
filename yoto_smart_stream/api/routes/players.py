"""Player control endpoints."""

import logging
from typing import Optional

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
    volume: int = Field(..., ge=0, le=16)
    playing: bool = False
    battery_level: Optional[int] = None


class PlayerControl(BaseModel):
    """Player control request model."""

    action: str = Field(
        ..., description="Action to perform: play, pause, skip_forward, skip_backward"
    )
    volume: Optional[int] = Field(None, ge=0, le=16, description="Volume level (0-16)")


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


@router.get("/players/{player_id}", response_model=PlayerInfo)
async def get_player(player_id: str):
    """
    Get detailed information about a specific player.

    Args:
        player_id: The unique identifier of the player

    Returns:
        Detailed player information
    """
    client = get_yoto_client()
    manager = client.get_manager()

    if player_id not in manager.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    player = manager.players[player_id]
    return extract_player_info(player_id, player)



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
    - volume: Set volume level (0-16)
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
