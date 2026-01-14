"""Card management and audio streaming endpoints."""

import logging
import os
import tempfile
from typing import Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from gtts import gTTS
from pydantic import BaseModel, Field
from pydub import AudioSegment
from sqlalchemy.orm import Session

from ...config import get_settings
from ..dependencies import get_yoto_client
from ...database import get_db
from ...models import User
from .user_auth import require_auth

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
        List of audio files in the audio_files directory with duration and size info.
        Static files (1.mp3 through 10.mp3) are marked with is_static flag.
    """
    settings = get_settings()
    audio_files = []
    
    # Define static file names
    static_files = {f"{i}.mp3" for i in range(1, 11)}

    for audio_path in settings.audio_files_dir.glob("*.mp3"):
        try:
            # Get duration in seconds using pydub
            audio = AudioSegment.from_mp3(str(audio_path))
            duration_seconds = int(len(audio) / 1000)  # Convert milliseconds to seconds
        except Exception as e:
            logger.warning(f"Could not read duration for {audio_path.name}: {e}")
            duration_seconds = 0
        
        # Check if this is a static file
        is_static = audio_path.name in static_files
        
        audio_files.append(
            {
                "filename": audio_path.name,
                "size": audio_path.stat().st_size,
                "duration": duration_seconds,
                "url": f"/api/audio/{audio_path.name}",
                "is_static": is_static,
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


@router.post("/audio/upload")
async def upload_audio(
    file: UploadFile = File(...),
    filename: str = Form(...),
    description: str = Form(default=""),
    user: User = Depends(require_auth)
):
    """
    Upload a recorded or imported audio file to the audio library.
    
    This endpoint accepts audio files (MP3, WebM, WAV) and saves them to the audio_files
    directory. If the uploaded file is not MP3, it will be converted to MP3 format.
    
    Args:
        file: Audio file upload
        filename: Desired filename (without extension)
        description: Optional description for the audio file
        
    Returns:
        Success message with filename and file information
    """
    settings = get_settings()
    
    # Sanitize filename
    filename = filename.strip()
    if filename.lower().endswith(('.mp3', '.webm', '.wav', '.ogg', '.m4a')):
        filename = os.path.splitext(filename)[0]
    
    # Only allow alphanumeric, hyphens, underscores, and spaces
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
    
    logger.info(f"Uploading audio file: {final_filename} (original: {file.filename})")
    
    temp_path = None
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)
        
        # Load audio with pydub (supports many formats)
        audio = AudioSegment.from_file(temp_path)
        
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
        duration_seconds = int(len(audio) / 1000)
        
        logger.info(f"✓ Audio uploaded and converted: {final_filename} ({file_size} bytes, {duration_seconds}s)")
        
        return {
            "success": True,
            "filename": final_filename,
            "size": file_size,
            "duration": duration_seconds,
            "description": description,
            "url": f"/api/audio/{final_filename}",
            "message": f"Successfully uploaded '{final_filename}'"
        }
        
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
                
    except Exception as e:
        logger.error(f"Failed to upload audio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload audio: {str(e)}"
        ) from e


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
