#!/usr/bin/env python3
"""
Basic FastAPI Server Example for Yoto Smart Stream

This demonstrates a FastAPI server with:
- Player listing endpoint
- Player control endpoint
- Audio streaming endpoint for MYO cards
- MYO card creation with streaming URLs
- Basic error handling
- CORS support

Run with: uvicorn basic_server:app --reload
Then visit: http://localhost:8080/docs
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

try:
    from yoto_api import YotoManager
except ImportError:
    print("Error: yoto_api library not found.")
    print("Install with: pip install yoto_api")
    exit(1)

# Audio files directory
AUDIO_FILES_DIR = Path("audio_files")
AUDIO_FILES_DIR.mkdir(exist_ok=True)


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
    volume = player.volume if player.volume is not None else (
        player.user_volume if player.user_volume is not None else 8
    )

    # Get playing status: check playback_status string or is_playing boolean
    playing = False
    if player.playback_status is not None:
        playing = player.playback_status == "playing"
    elif player.is_playing is not None:
        playing = player.is_playing

    # Get battery level from battery_level_percentage attribute
    battery_level = player.battery_level_percentage

    return PlayerInfo(
        id=player_id,
        name=player.name,
        online=player.online,
        volume=volume,
        playing=playing,
        battery_level=battery_level,
    )



class ErrorResponse(BaseModel):
    """Error response model."""

    detail: str


class CreateCardRequest(BaseModel):
    """Request model for creating a streaming MYO card."""

    title: str = Field(..., description="Card title")
    description: str = Field(default="", description="Card description")
    author: str = Field(default="Yoto Smart Stream", description="Card author")
    audio_filename: str = Field(
        ..., description="Audio filename in audio_files directory (e.g., 'story.mp3')"
    )
    cover_image_id: Optional[str] = Field(None, description="Optional cover image ID")


# Global Yoto Manager instance (in production, use dependency injection)
yoto_manager: Optional[YotoManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup and cleanup on shutdown."""
    try:
        ym = get_yoto_manager()
        ym.update_players_status()
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

    yield  # Application runs here

    # Cleanup (if needed)
    pass


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Yoto Smart Stream API",
    description="API for controlling Yoto players and managing audio content",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_yoto_manager() -> YotoManager:
    """Get or initialize Yoto Manager."""
    global yoto_manager

    if yoto_manager is None:
        client_id = os.getenv("YOTO_CLIENT_ID")
        if not client_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="YOTO_CLIENT_ID not configured",
            )

        token_file = Path(".yoto_refresh_token")
        if not token_file.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Not authenticated. Run authentication first.",
            )

        # Initialize and authenticate
        yoto_manager = YotoManager(client_id=client_id)
        refresh_token = token_file.read_text().strip()
        yoto_manager.set_refresh_token(refresh_token)

        try:
            yoto_manager.check_and_refresh_token()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Authentication failed: {str(e)}"
            ) from e

    return yoto_manager


@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Yoto Smart Stream API",
        "version": "0.2.0",
        "status": "running",
        "docs": "/docs",
        "features": {
            "player_control": True,
            "audio_streaming": True,
            "myo_card_creation": True,
        },
    }


@app.get("/api/players", response_model=list[PlayerInfo], tags=["Players"])
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
        ym.update_players_status()

        if not ym.players:
            return []

        # Convert to response models
        players = []
        for player_id, player in ym.players.items():
            players.append(extract_player_info(player_id, player))

        return players

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch players: {str(e)}",
        ) from e


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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
        )

    player = ym.players[player_id]
    return extract_player_info(player_id, player)



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
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Player {player_id} not found"
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
                status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown action: {control.action}"
            )

        # Set volume if provided
        if control.volume is not None:
            ym.set_volume(player_id, control.volume)

        return {"success": True, "player_id": player_id, "action": control.action}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control player: {str(e)}",
        ) from e


@app.get("/api/health", tags=["General"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "yoto_api": "connected" if yoto_manager else "not initialized",
        "audio_files": len(list(AUDIO_FILES_DIR.glob("*.mp3"))),
    }


# === Audio Streaming Endpoints ===


@app.get("/audio/list", tags=["Audio Streaming"])
async def list_audio_files():
    """
    List available audio files.
    
    Returns:
        List of audio files in the audio_files directory
    """
    audio_files = []
    for audio_path in AUDIO_FILES_DIR.glob("*.mp3"):
        audio_files.append(
            {
                "filename": audio_path.name,
                "size": audio_path.stat().st_size,
                "url": f"/audio/{audio_path.name}",
            }
        )

    return {"files": audio_files, "count": len(audio_files)}


@app.get("/audio/dynamic/{card_id}.mp3", tags=["Audio Streaming"])
async def stream_dynamic_audio(card_id: str):
    """
    Stream dynamic audio based on time or other factors.
    
    This endpoint demonstrates how to serve different content
    for the same URL based on context (time, user, etc.).
    
    Example use case: Bedtime stories that change based on time of day.
    
    Args:
        card_id: Identifier for the dynamic card
    
    Returns:
        Audio file appropriate for current context
    """
    hour = datetime.now().hour

    # Serve different audio based on time of day
    if 6 <= hour < 12:
        audio_file = "morning-story.mp3"
    elif 12 <= hour < 18:
        audio_file = "afternoon-story.mp3"
    else:
        audio_file = "bedtime-story.mp3"

    audio_path = AUDIO_FILES_DIR / audio_file

    # Fallback to default if specific file doesn't exist
    if not audio_path.exists():
        audio_path = AUDIO_FILES_DIR / "default-story.mp3"

    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audio files found. Add MP3 files to {AUDIO_FILES_DIR}/",
        )

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",  # Don't cache dynamic content
        },
    )


@app.get("/audio/{filename}", tags=["Audio Streaming"])
async def stream_audio(filename: str):
    """
    Stream audio file for Yoto MYO cards.
    
    This endpoint serves audio files that can be referenced in MYO card URLs.
    Audio files should be placed in the 'audio_files/' directory.
    
    Example:
        Place story.mp3 in audio_files/
        Access at: http://your-server.com/audio/story.mp3
        Use in card: {"url": "https://your-server.com/audio/story.mp3"}
    
    Args:
        filename: Audio filename (e.g., 'story.mp3')
    
    Returns:
        Audio file with proper headers for streaming
    """
    audio_path = AUDIO_FILES_DIR / filename

    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio file not found: {filename}"
        )

    # Determine media type from extension
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/aac"

    return FileResponse(
        audio_path,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",  # Enable seeking
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
        },
    )


# === MYO Card Creation Endpoints ===


@app.post("/api/cards/create-streaming", tags=["Cards"])
async def create_streaming_card(request: CreateCardRequest):
    """
    Create a Yoto MYO card that streams from this server.
    
    This endpoint creates a card that points to audio hosted on THIS server,
    not uploaded to Yoto's servers. This allows:
    - Dynamic content updates without recreating cards
    - No upload size limits
    - Complete control over content
    
    The audio file must exist in the audio_files/ directory.
    
    Example:
        {
            "title": "My Story",
            "audio_filename": "story.mp3",
            "description": "A wonderful tale"
        }
    
    Returns:
        Created card information including card ID
    """
    ym = get_yoto_manager()

    # Verify audio file exists
    audio_path = AUDIO_FILES_DIR / request.audio_filename
    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {request.audio_filename}. "
            f"Add it to {AUDIO_FILES_DIR}/",
        )

    # Get the base URL (in production, use env var or config)
    # For now, use a placeholder that needs to be configured
    base_url = os.getenv("PUBLIC_URL", "https://your-server.com")
    if base_url == "https://your-server.com":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PUBLIC_URL environment variable not set. "
            "Set it to your public server URL (e.g., https://example.ngrok.io)",
        )

    streaming_url = f"{base_url}/audio/{request.audio_filename}"

    # Create the card
    card_data = {
        "title": request.title,
        "description": request.description,
        "author": request.author,
        "metadata": {},
        "content": {
            "chapters": [
                {
                    "key": "01",
                    "title": "Chapter 1",
                    "tracks": [
                        {
                            "key": "01",
                            "title": request.title,
                            "format": "mp3",
                            "channels": "mono",
                            "url": streaming_url,  # Stream from THIS server!
                        }
                    ],
                }
            ]
        },
    }

    # Add cover image if provided
    if request.cover_image_id:
        card_data["metadata"]["cover"] = {"imageId": request.cover_image_id}

    try:
        response = requests.post(
            "https://api.yotoplay.com/card",
            headers={
                "Authorization": f"Bearer {ym.token.access_token}",
                "Content-Type": "application/json",
            },
            json=card_data,
            timeout=30,
        )

        response.raise_for_status()
        card = response.json()

        return {
            "success": True,
            "card_id": card.get("cardId"),
            "streaming_url": streaming_url,
            "message": "Card created successfully! It will stream from this server.",
        }

    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create card: {e.response.text}",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create card: {str(e)}",
        ) from e


@app.post("/api/cards/create-dynamic", tags=["Cards"])
async def create_dynamic_card(title: str, card_id: str):
    """
    Create a dynamic MYO card that serves different content based on time.
    
    This creates a card that streams from /audio/dynamic/{card_id}.mp3,
    which serves different audio files based on time of day.
    
    Args:
        title: Card title
        card_id: Unique identifier for this dynamic card
    
    Returns:
        Created card information
    """
    ym = get_yoto_manager()

    base_url = os.getenv("PUBLIC_URL", "https://your-server.com")
    if base_url == "https://your-server.com":
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PUBLIC_URL environment variable not set",
        )

    streaming_url = f"{base_url}/audio/dynamic/{card_id}.mp3"

    card_data = {
        "title": title,
        "description": "Dynamic content that changes based on time of day",
        "author": "Yoto Smart Stream",
        "content": {
            "chapters": [
                {
                    "key": "01",
                    "title": "Chapter 1",
                    "tracks": [
                        {
                            "key": "01",
                            "title": title,
                            "format": "mp3",
                            "channels": "mono",
                            "url": streaming_url,
                        }
                    ],
                }
            ]
        },
    }

    try:
        response = requests.post(
            "https://api.yotoplay.com/card",
            headers={
                "Authorization": f"Bearer {ym.token.access_token}",
                "Content-Type": "application/json",
            },
            json=card_data,
            timeout=30,
        )

        response.raise_for_status()
        card = response.json()

        return {
            "success": True,
            "card_id": card.get("cardId"),
            "streaming_url": streaming_url,
            "message": "Dynamic card created! Content will change based on time of day.",
            "time_schedule": {
                "morning": "6:00 AM - 12:00 PM: morning-story.mp3",
                "afternoon": "12:00 PM - 6:00 PM: afternoon-story.mp3",
                "evening": "6:00 PM - 6:00 AM: bedtime-story.mp3",
            },
        }

    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create card: {e.response.text}",
        ) from e


if __name__ == "__main__":
    import uvicorn

    print("\n" + "=" * 80)
    print("Starting Yoto Smart Stream API Server")
    print("=" * 80)
    print("\n📚 Documentation:")
    print("  API Documentation: http://localhost:8080/docs")
    print("  Interactive API: http://localhost:8080/redoc")
    print("\n🎵 Audio Streaming:")
    print(f"  Audio files directory: {AUDIO_FILES_DIR.absolute()}")
    print("  Add MP3 files to this directory to stream them")
    print("\n🎴 MYO Card Creation:")
    print("  1. Set PUBLIC_URL environment variable (your public URL)")
    print("  2. Add audio files to audio_files/ directory")
    print("  3. Use POST /api/cards/create-streaming to create cards")
    print("\n💡 For local testing, use ngrok:")
    print("  ngrok http 8080")
    print("  Then set: export PUBLIC_URL=https://your-id.ngrok.io")
    print("=" * 80 + "\n")

    uvicorn.run(app, host="0.0.0.0", port=8080)
