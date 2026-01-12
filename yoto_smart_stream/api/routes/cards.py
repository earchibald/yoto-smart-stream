"""Card management and audio streaming endpoints."""

import logging
import os
import tempfile
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from gtts import gTTS
from pydantic import BaseModel, Field
from pydub import AudioSegment
from sqlalchemy.orm import Session

from ...config import get_settings
from ..dependencies import get_yoto_client
from ...database import get_db
from ..utils import get_time_based_audio_file, get_time_schedule
from ...models import User
from ...auth import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


# Request/Response models
class CreateCardRequest(BaseModel):
    """Request model for creating a streaming MYO card."""

    title: str = Field(..., description="Card title")
    description: str = Field(default="", description="Card description")
    author: str = Field(default="Yoto Smart Stream", description="Card author")
    audio_filename: str = Field(
        ..., description="Audio filename in audio_files directory (e.g., 'story.mp3')"
    )
    cover_image_id: Optional[str] = Field(None, description="Optional cover image ID")


class GenerateTTSRequest(BaseModel):
    """Request model for generating text-to-speech audio."""

    filename: str = Field(..., description="Output filename (without extension)")
    text: str = Field(..., description="Text to convert to speech", min_length=1)


# Audio streaming endpoints
@router.get("/audio/list")
async def list_audio_files(user: User = Depends(require_auth)):
    """
    List available audio files.

    Returns:
        List of audio files in the audio_files directory
    """
    settings = get_settings()
    audio_files = []

    for audio_path in settings.audio_files_dir.glob("*.mp3"):
        audio_files.append(
            {
                "filename": audio_path.name,
                "size": audio_path.stat().st_size,
                "url": f"/api/audio/{audio_path.name}",
            }
        )

    return {"files": audio_files, "count": len(audio_files)}


@router.post("/audio/generate-tts")
async def generate_tts_audio(request: GenerateTTSRequest, user: User = Depends(require_auth)):
    """
    Generate text-to-speech audio and save to audio_files directory.

    This endpoint creates an MP3 file from the provided text using Google Text-to-Speech.
    The generated file is saved to the audio_files directory and can be used
    in MYO cards or accessed via the audio streaming endpoint.

    Args:
        request: GenerateTTSRequest with filename and text

    Returns:
        Success message with filename and file information
    """
    settings = get_settings()

    # Sanitize filename - remove any path separators and special chars
    filename = request.filename.strip()
    # Remove file extension if provided
    if filename.lower().endswith('.mp3'):
        filename = filename[:-4]

    # Only allow alphanumeric, hyphens, underscores, and spaces
    # Replace spaces with hyphens for better shell/URL compatibility
    sanitized_filename = "".join(
        c if c.isalnum() or c in ('-', '_') else '-' if c == ' ' else ''
        for c in filename
    )

    if not sanitized_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename. Use only letters, numbers, hyphens, underscores, and spaces."
        )

    # Create final filename with .mp3 extension
    final_filename = f"{sanitized_filename}.mp3"
    output_path = settings.audio_files_dir / final_filename

    # Check if file already exists
    if output_path.exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File '{final_filename}' already exists. Please choose a different name."
        )

    logger.info(f"Generating TTS audio for: {final_filename}")

    try:
        # Create a temporary file for the initial TTS output
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Generate speech using gTTS
            tts = gTTS(text=request.text, lang="en", slow=False)
            tts.save(temp_path)

            # Load and optimize with pydub
            audio = AudioSegment.from_mp3(temp_path)

            # Convert to mono and set appropriate settings for Yoto compatibility
            audio = audio.set_channels(1)  # Mono
            audio = audio.set_frame_rate(44100)  # 44.1kHz sample rate

            # Export as optimized MP3
            audio.export(
                output_path,
                format="mp3",
                bitrate="192k",
                parameters=["-ac", "1"],  # Ensure mono
            )

            file_size = output_path.stat().st_size
            logger.info(f"✓ TTS audio generated: {final_filename} ({file_size} bytes)")

            return {
                "success": True,
                "filename": final_filename,
                "size": file_size,
                "url": f"/api/audio/{final_filename}",
                "message": f"Successfully generated '{final_filename}'"
            }

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Failed to generate TTS audio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate TTS audio. Please try again."
        ) from e


@router.get("/audio/dynamic/{card_id}.mp3")
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
    settings = get_settings()
    audio_file = get_time_based_audio_file()
    audio_path = settings.audio_files_dir / audio_file

    # Fallback to default if specific file doesn't exist
    if not audio_path.exists():
        audio_path = settings.audio_files_dir / "default-story.mp3"

    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No audio files found. Add MP3 files to {settings.audio_files_dir}/",
        )

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache",  # Don't cache dynamic content
        },
    )


@router.get("/audio/{filename}")
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
    settings = get_settings()
    audio_path = settings.audio_files_dir / filename

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


# Card creation endpoints
@router.post("/cards/create-streaming")
async def create_streaming_card(request: CreateCardRequest, user: User = Depends(require_auth)):
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
    settings = get_settings()
    client = get_yoto_client()
    manager = client.get_manager()

    # Verify audio file exists
    audio_path = settings.audio_files_dir / request.audio_filename
    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {request.audio_filename}. "
            f"Add it to {settings.audio_files_dir}/",
        )

    # Check PUBLIC_URL is configured
    if not settings.public_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PUBLIC_URL environment variable not set. "
            "Set it to your public server URL (e.g., https://example.ngrok.io)",
        )

    streaming_url = f"{settings.public_url}/audio/{request.audio_filename}"

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
                "Authorization": f"Bearer {manager.token.access_token}",
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


@router.post("/cards/create-dynamic")
async def create_dynamic_card(title: str, card_id: str, user: User = Depends(require_auth)):
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
    settings = get_settings()
    client = get_yoto_client()
    manager = client.get_manager()

    if not settings.public_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PUBLIC_URL environment variable not set",
        )

    streaming_url = f"{settings.public_url}/audio/dynamic/{card_id}.mp3"

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
                "Authorization": f"Bearer {manager.token.access_token}",
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
            "time_schedule": get_time_schedule(),
        }

    except requests.exceptions.HTTPError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create card: {e.response.text}",
        ) from e
