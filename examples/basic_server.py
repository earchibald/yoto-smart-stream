#!/usr/bin/env python3
"""
Basic FastAPI Server Example for Yoto Smart Stream

This demonstrates a minimal FastAPI server with:
- Player listing endpoint
- Player control endpoint
- Basic error handling
- CORS support

Run with: uvicorn basic_server:app --reload
Then visit: http://localhost:8000/docs
"""

import os
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

try:
    from yoto_api import YotoManager
except ImportError:
    print("Error: yoto_api library not found.")
    print("Install with: pip install yoto_api")
    exit(1)


# Pydantic models for request/response
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
    action: str = Field(..., description="Action to perform: play, pause, skip_forward, skip_backward")
    volume: Optional[int] = Field(None, ge=0, le=16, description="Volume level (0-16)")


class ErrorResponse(BaseModel):
    """Error response model."""
    detail: str


# Initialize FastAPI app
app = FastAPI(
    title="Yoto Smart Stream API",
    description="API for controlling Yoto players and managing audio content",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Yoto Manager instance (in production, use dependency injection)
yoto_manager: Optional[YotoManager] = None


def get_yoto_manager() -> YotoManager:
    """Get or initialize Yoto Manager."""
    global yoto_manager

    if yoto_manager is None:
        client_id = os.getenv("YOTO_CLIENT_ID")
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="YOTO_CLIENT_ID not configured"
            )

        token_file = Path(".yoto_refresh_token")
        if not token_file.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Not authenticated. Run authentication first."
            )

        # Initialize and authenticate
        yoto_manager = YotoManager(client_id=client_id)
        refresh_token = token_file.read_text().strip()
        yoto_manager.set_refresh_token(refresh_token)

        try:
            yoto_manager.check_and_refresh_token()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Authentication failed: {str(e)}"
            )

    return yoto_manager


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    try:
        ym = get_yoto_manager()
        ym.update_player_status()
        print("✓ Yoto API connected successfully")

        # Connect to MQTT
        try:
            ym.connect_to_events()
            print("✓ MQTT connected successfully")
        except Exception as e:
            print(f"⚠ MQTT connection failed: {e}")

    except Exception as e:
        print(f"⚠ Warning: Could not initialize Yoto API: {e}")
        print("  Some endpoints may not work until authentication is completed.")


@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Yoto Smart Stream API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/api/players", response_model=List[PlayerInfo], tags=["Players"])
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
    ym = get_yoto_manager()

    try:
        # Refresh player status
        ym.update_player_status()

        if not ym.players:
            return []

        # Convert to response models
        players = []
        for player_id, player in ym.players.items():
            player_info = PlayerInfo(
                id=player_id,
                name=player.name,
                online=player.online,
                volume=player.volume if hasattr(player, 'volume') else 8,
                playing=player.playing if hasattr(player, 'playing') else False,
                battery_level=player.battery_level if hasattr(player, 'battery_level') else None
            )
            players.append(player_info)

        return players

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch players: {str(e)}"
        )


@app.get("/api/players/{player_id}", response_model=PlayerInfo, tags=["Players"])
async def get_player(player_id: str):
    """
    Get detailed information about a specific player.

    Args:
        player_id: The unique identifier of the player

    Returns:
        Detailed player information
    """
    ym = get_yoto_manager()

    if player_id not in ym.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found"
        )

    player = ym.players[player_id]
    return PlayerInfo(
        id=player_id,
        name=player.name,
        online=player.online,
        volume=player.volume if hasattr(player, 'volume') else 8,
        playing=player.playing if hasattr(player, 'playing') else False,
        battery_level=player.battery_level if hasattr(player, 'battery_level') else None
    )


@app.post("/api/players/{player_id}/control", tags=["Players"])
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
    ym = get_yoto_manager()

    if player_id not in ym.players:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player {player_id} not found"
        )

    try:
        # Execute action
        if control.action == "pause":
            ym.pause_player(player_id)
        elif control.action == "play":
            ym.play_player(player_id)
        elif control.action == "skip_forward":
            ym.skip_chapter(player_id, direction="forward")
        elif control.action == "skip_backward":
            ym.skip_chapter(player_id, direction="backward")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown action: {control.action}"
            )

        # Set volume if provided
        if control.volume is not None:
            ym.set_volume(player_id, control.volume)

        return {
            "success": True,
            "player_id": player_id,
            "action": control.action
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control player: {str(e)}"
        )


@app.get("/health", tags=["General"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "yoto_api": "connected" if yoto_manager else "not initialized"
    }


if __name__ == "__main__":
    import uvicorn

    print("\nStarting Yoto Smart Stream API Server...")
    print("API Documentation: http://localhost:8000/docs")
    print("Interactive API: http://localhost:8000/redoc\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
