"""Card management and audio streaming endpoints."""

import asyncio
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import requests
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from gtts import gTTS
from pydantic import BaseModel, Field
from pydub import AudioSegment
from sqlalchemy.orm import Session

from ...config import get_settings
from ...database import get_db
from ...models import User
from ..dependencies import get_yoto_client
from .user_auth import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


# Background task for transcription
def transcribe_audio_background(filename: str, audio_path: str, db_url: str):
    """
    Background task to transcribe audio file.

    Args:
        filename: Audio filename
        audio_path: Full path to audio file
        db_url: Database URL for creating a new session
    """
    from pathlib import Path

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from ...config import get_settings
    from ...core.audio_db import get_audio_file_by_filename, update_transcript
    from ...core.transcription import get_transcription_service

    # Create a new database session for this background task
    engine = create_engine(
        db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        settings = get_settings()
        if not settings.transcription_enabled:
            logger.info(f"Transcription disabled; skipping background transcription for {filename}")
            update_transcript(
                db,
                filename,
                None,
                "disabled",
                "Transcription disabled in this environment",
            )
            return

        logger.info(f"Starting background transcription for {filename}")

        # Update status to processing
        update_transcript(db, filename, None, "processing", None)

        # Check if still processing (could have been cancelled)
        audio_record = get_audio_file_by_filename(db, filename)
        if audio_record and audio_record.transcript_status != "processing":
            logger.info(f"Transcription was cancelled for {filename}")
            return

        # Perform transcription
        transcription_service = get_transcription_service()
        transcript_text, error_msg = transcription_service.transcribe_audio(Path(audio_path))

        # Check again before saving (in case cancelled during transcription)
        audio_record = get_audio_file_by_filename(db, filename)
        if audio_record and audio_record.transcript_status != "processing":
            logger.info(f"Transcription was cancelled for {filename} during processing")
            return

        if transcript_text:
            update_transcript(db, filename, transcript_text, "completed", None)
            logger.info(f"✓ Background transcription completed for {filename}")
        else:
            update_transcript(db, filename, None, "error", error_msg)
            logger.warning(f"Background transcription failed for {filename}: {error_msg}")
    except Exception as e:
        logger.error(f"Background transcription error for {filename}: {e}", exc_info=True)
        # Only update to error if still processing
        audio_record = get_audio_file_by_filename(db, filename)
        if audio_record and audio_record.transcript_status == "processing":
            update_transcript(db, filename, None, "error", str(e))
    finally:
        db.close()


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
async def list_audio_files(user: User = Depends(require_auth), db: Session = Depends(get_db)):
    """
    List available audio files.

    Returns:
        List of audio files in the audio_files directory with duration, size, and transcript info.
        Static files (1.mp3 through 10.mp3) are marked with is_static flag.
    """
    settings = get_settings()
    storage = settings.get_storage()
    audio_files = []

    # Define static file names
    static_files = {f"{i}.mp3" for i in range(1, 11)}

    # Get list of audio files from storage
    filenames = await storage.list_files()

    for filename in filenames:
        try:
            # For local storage, we can read the file for duration
            # For S3, we'll need to download or skip duration check
            if settings.storage_backend == "local":
                audio_path = settings.audio_files_dir / filename
                audio = AudioSegment.from_mp3(str(audio_path))
                duration_seconds = int(len(audio) / 1000)  # Convert milliseconds to seconds
            else:
                # For S3, skip duration calculation to avoid downloading files
                # This could be enhanced later by storing duration in database
                duration_seconds = 0
        except Exception as e:
            logger.warning(f"Could not read duration for {filename}: {e}")
            duration_seconds = 0

        # Check if this is a static file
        is_static = filename in static_files

        # Get transcript info from database
        from ...core.audio_db import get_audio_file_by_filename

        audio_record = get_audio_file_by_filename(db, filename)

        transcript_info = {
            "status": audio_record.transcript_status if audio_record else "pending",
            "has_transcript": bool(audio_record and audio_record.transcript),
        }

        # Get file size from storage
        file_size = await storage.get_file_size(filename)

        audio_files.append(
            {
                "filename": filename,
                "size": file_size,
                "duration": duration_seconds,
                "url": f"/api/audio/{filename}",
                "is_static": is_static,
                "transcript": transcript_info,
            }
        )

    return {"files": audio_files, "count": len(audio_files)}


@router.post("/audio/generate-tts")
async def generate_tts_audio(
    request: GenerateTTSRequest, user: User = Depends(require_auth), db: Session = Depends(get_db)
):
    """
    Generate text-to-speech audio and save to storage.

    This endpoint creates an MP3 file from the provided text using Google Text-to-Speech.
    The generated file is saved to storage (local filesystem or S3) and can be used
    in MYO cards or accessed via the audio streaming endpoint.

    A transcript record is automatically created, and since we have the source text,
    we can store it directly without needing to run speech-to-text.

    Args:
        request: GenerateTTSRequest with filename and text

    Returns:
        Success message with filename and file information
    """
    settings = get_settings()
    storage = settings.get_storage()

    # Sanitize filename - remove any path separators and special chars
    filename = request.filename.strip()
    # Remove file extension if provided
    if filename.lower().endswith(".mp3"):
        filename = filename[:-4]

    # Only allow alphanumeric, hyphens, underscores, and spaces
    # Replace spaces with hyphens for better shell/URL compatibility
    sanitized_filename = "".join(
        c if c.isalnum() or c in ("-", "_") else "-" if c == " " else "" for c in filename
    )

    if not sanitized_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename. Use only letters, numbers, hyphens, underscores, and spaces.",
        )

    # Create final filename with .mp3 extension
    final_filename = f"{sanitized_filename}.mp3"

    # Check if file already exists
    if await storage.exists(final_filename):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File '{final_filename}' already exists. Please choose a different name.",
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

            # Export to bytes buffer
            buffer = io.BytesIO()
            audio.export(
                buffer,
                format="mp3",
                bitrate="192k",
                parameters=["-ac", "1"],  # Ensure mono
            )
            file_data = buffer.getvalue()
            file_size = len(file_data)
            duration_seconds = int(len(audio) / 1000)

            # Save to storage
            await storage.save(final_filename, file_data)

            logger.info(
                f"✓ TTS audio generated: {final_filename} ({file_size} bytes, {duration_seconds}s)"
            )

            # Create database record with the source text as transcript
            from ...core.audio_db import get_or_create_audio_file, update_transcript

            get_or_create_audio_file(db, final_filename, file_size, duration_seconds)
            # Store the original text as the transcript since we already have it
            update_transcript(db, final_filename, request.text, "completed", None)

            return {
                "success": True,
                "filename": final_filename,
                "size": file_size,
                "duration": duration_seconds,
                "url": f"/api/audio/{final_filename}",
                "message": f"Successfully generated '{final_filename}'",
                "transcript_status": "completed",
            }

        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)

    except Exception as e:
        logger.error(f"Failed to generate TTS audio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate TTS audio. Please try again.",
        ) from e


@router.post("/audio/upload")
async def upload_audio(
    file: UploadFile = File(...),
    filename: str = Form(...),
    description: str = Form(default=""),
    background_tasks: BackgroundTasks = None,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db),
):
    """
    Upload a recorded or imported audio file to the audio library.

    This endpoint accepts audio files (MP3, WebM, WAV) and saves them to storage.
    If the uploaded file is not MP3, it will be converted to MP3 format.

    Transcription is triggered as a background task after upload completes.

    Args:
        file: Audio file upload
        filename: Desired filename (without extension)
        description: Optional description for the audio file

    Returns:
        Success message with filename and file information
    """
    settings = get_settings()
    storage = settings.get_storage()

    # Sanitize filename
    filename = filename.strip()
    if filename.lower().endswith((".mp3", ".webm", ".wav", ".ogg", ".m4a")):
        filename = os.path.splitext(filename)[0]

    # Only allow alphanumeric, hyphens, underscores, and spaces
    sanitized_filename = "".join(
        c if c.isalnum() or c in ("-", "_") else "-" if c == " " else "" for c in filename
    )

    if not sanitized_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename. Use only letters, numbers, hyphens, underscores, and spaces.",
        )

    # Create final filename with .mp3 extension
    final_filename = f"{sanitized_filename}.mp3"

    # Check if file already exists
    if await storage.exists(final_filename):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"File '{final_filename}' already exists. Please choose a different name.",
        )

    logger.info(f"Uploading audio file: {final_filename} (original: {file.filename})")

    temp_path = None
    try:
        # Save uploaded file to temporary location
        # Get safe file extension, default to empty string if filename is None
        file_ext = ""
        if file.filename:
            # Only use the extension, not the path components
            _, ext = os.path.splitext(os.path.basename(file.filename))
            file_ext = ext

        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as temp_file:
            temp_path = temp_file.name
            content = await file.read()
            temp_file.write(content)

        # Load audio with pydub (supports many formats)
        audio = AudioSegment.from_file(temp_path)

        # Convert to mono and set appropriate settings for Yoto compatibility
        audio = audio.set_channels(1)  # Mono
        audio = audio.set_frame_rate(44100)  # 44.1kHz sample rate

        # Export to bytes buffer
        buffer = io.BytesIO()
        audio.export(
            buffer,
            format="mp3",
            bitrate="192k",
            parameters=["-ac", "1"],  # Ensure mono
        )
        file_data = buffer.getvalue()
        file_size = len(file_data)
        duration_seconds = int(len(audio) / 1000)

        # Save to storage
        await storage.save(final_filename, file_data)

        logger.info(
            f"✓ Audio uploaded and converted: {final_filename} ({file_size} bytes, {duration_seconds}s)"
        )

        # Create database record
        from ...core.audio_db import get_or_create_audio_file, update_transcript

        get_or_create_audio_file(db, final_filename, file_size, duration_seconds)

        if settings.transcription_enabled:
            # Mark transcription as pending and schedule background task
            update_transcript(db, final_filename, None, "pending", None)

            # For S3 storage, we need to download the file for transcription
            # For local storage, use the existing path
            if settings.storage_backend == "s3":
                # Download file to temp location for transcription
                transcription_path = f"/tmp/{final_filename}"
                with open(transcription_path, "wb") as f:
                    f.write(file_data)
                audio_path_for_transcription = transcription_path
            else:
                audio_path_for_transcription = str(settings.audio_files_dir / final_filename)

            # Schedule background transcription (non-blocking)
            if background_tasks:
                settings = get_settings()
                background_tasks.add_task(
                    transcribe_audio_background,
                    final_filename,
                    audio_path_for_transcription,
                    settings.database_url,
                )
                logger.info(f"Scheduled background transcription for {final_filename}")
        else:
            update_transcript(
                db,
                final_filename,
                None,
                "disabled",
                "Transcription disabled in this environment",
            )
            logger.info(
                f"Transcription disabled; skipping background transcription for {final_filename}"
            )

        return {
            "success": True,
            "filename": final_filename,
            "size": file_size,
            "duration": duration_seconds,
            "description": description,
            "url": f"/api/audio/{final_filename}",
            "message": f"Successfully uploaded '{final_filename}'",
            "transcript_status": "pending" if settings.transcription_enabled else "disabled",
        }

    except Exception as e:
        logger.error(f"Failed to upload audio: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload audio: {str(e)}",
        ) from e
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/audio/search")
async def search_audio_files(
    q: str = "", user: User = Depends(require_auth), db: Session = Depends(get_db)
):
    """
    Search audio files by name and metadata (fuzzy search).

    Returns matching audio files with their metadata.
    """

    from ...core.audio_db import get_audio_file_by_filename

    settings = get_settings()
    storage = settings.get_storage()
    audio_files = []
    query = q.lower().strip()

    # Get list of audio files from storage
    filenames = await storage.list_files()

    # Collect all audio files
    for filename in filenames:
        try:
            # For local storage, we can read the file for duration
            # For S3, skip duration check to avoid downloading files
            if settings.storage_backend == "local":
                audio_path = settings.audio_files_dir / filename
                audio = AudioSegment.from_mp3(str(audio_path))
                duration_seconds = int(len(audio) / 1000)
            else:
                # For S3, skip duration calculation
                duration_seconds = 0
        except Exception as e:
            logger.warning(f"Could not read duration for {filename}: {e}")
            duration_seconds = 0

        # Get transcript/metadata from database
        audio_record = get_audio_file_by_filename(db, filename)
        transcript = audio_record.transcript if audio_record else None

        # Get file size from storage
        file_size = await storage.get_file_size(filename)

        audio_files.append(
            {
                "filename": filename,
                "size": file_size,
                "duration": duration_seconds,
                "transcript": transcript,
            }
        )

    # Simple fuzzy search: match by filename or transcript
    if query:
        filtered_files = []
        for f in audio_files:
            # Search in filename
            if query in f["filename"].lower():
                filtered_files.append(f)
            # Search in transcript
            elif f["transcript"] and query in f["transcript"].lower():
                filtered_files.append(f)
        audio_files = filtered_files

    return {
        "query": q,
        "results": audio_files,
        "count": len(audio_files),
    }


@router.get("/audio/{filename}")
async def stream_audio(filename: str):
    """
    Stream audio file for Yoto MYO cards.

    This endpoint serves audio files that can be referenced in MYO card URLs.
    For S3 storage, it redirects to presigned URLs.
    For local storage, it streams files directly.

    Example:
        Access at: http://your-server.com/audio/story.mp3
        Use in card: {"url": "https://your-server.com/audio/story.mp3"}

    Args:
        filename: Audio filename (e.g., 'story.mp3')

    Returns:
        Audio file with proper headers for streaming (local) or redirect (S3)
    """
    settings = get_settings()
    storage = settings.get_storage()

    if not await storage.exists(filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio file not found: {filename}"
        )

    # For S3 storage, redirect to presigned URL
    if settings.storage_backend == "s3":
        from fastapi.responses import RedirectResponse

        url = await storage.get_url(filename, expiry=settings.presigned_url_expiry)
        return RedirectResponse(url=url, status_code=307)

    # For local storage, stream file directly
    audio_path = settings.audio_files_dir / filename

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


@router.delete("/audio/{filename}")
async def delete_audio_file(
    filename: str, user: User = Depends(require_auth), db: Session = Depends(get_db)
):
    """
    Delete an audio file from storage and database.

    This permanently removes:
    - The audio file from storage (S3 bucket or local filesystem)
    - The database record including transcripts and metadata

    Args:
        filename: Audio filename to delete (e.g., 'story.mp3')

    Returns:
        Success message with deletion details
    """
    from ...core.audio_db import delete_audio_file as delete_audio_record

    settings = get_settings()
    storage = settings.get_storage()

    # Check if file exists in storage
    if not await storage.exists(filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio file not found: {filename}"
        )

    try:
        # Delete from storage (S3 or local)
        deleted_from_storage = await storage.delete(filename)

        if not deleted_from_storage:
            logger.warning(f"Failed to delete {filename} from storage, but continuing with DB cleanup")

        # Delete from database (including transcripts)
        deleted_from_db = delete_audio_record(db, filename)

        if deleted_from_storage:
            logger.info(f"✓ Deleted audio file: {filename} (storage + database)")
        else:
            logger.info(f"⚠ Deleted audio file: {filename} (database only, storage deletion failed)")

        return {
            "success": True,
            "filename": filename,
            "deleted_from_storage": deleted_from_storage,
            "deleted_from_database": deleted_from_db,
            "message": f"Successfully deleted {filename}",
        }

    except Exception as e:
        logger.error(f"Failed to delete audio file {filename}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete audio file: {str(e)}",
        ) from e


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
    storage = settings.get_storage()
    client = get_yoto_client()
    manager = client.get_manager()

    # Verify audio file exists
    if not await storage.exists(request.audio_filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio file not found: {request.audio_filename}. "
            f"Upload the file using the /api/audio/upload endpoint.",
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


@router.put("/cards/{card_id}")
async def update_card(card_id: str, card_data: dict, user: User = Depends(require_auth)):
    """
    Update an existing Yoto MYO card.
    
    Only MYO (Make Your Own) cards can be updated. Commercial cards will return an error.
    
    Args:
        card_id: The ID of the card to update
        card_data: The complete card data (same format as create)
    
    Returns:
        Updated card information
    """
    client = get_yoto_client()
    manager = client.get_manager()
    
    logger.info(f"[UPDATE CARD] Starting update for card {card_id}")
    logger.info(f"[UPDATE CARD] Request payload: {card_data}")
    
    # Ensure cardId is in the payload for update operation
    update_payload = {**card_data, "cardId": card_id}
    
    try:
        response = requests.post(
            "https://api.yotoplay.com/content",
            headers={
                "Authorization": f"Bearer {manager.token.access_token}",
                "Content-Type": "application/json",
            },
            json=update_payload,
            timeout=30,
        )
        
        logger.info(f"[UPDATE CARD] Yoto API response status: {response.status_code}")
        logger.info(f"[UPDATE CARD] Yoto API response body: {response.text}")
        
        response.raise_for_status()
        card = response.json()
        
        logger.info(f"✓ Updated card: {card_id}")
        return {
            "success": True,
            "card_id": card.get("id") or card.get("cardId"),
            "message": "Card updated successfully!",
            "card": card
        }
        
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.text
        logger.error(f"[UPDATE CARD] Yoto API error: {error_detail}")
        
        # Check if it's a 404 (likely a commercial card that can't be edited)
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update this card. It may be a commercial card (not MYO).",
            ) from e
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to update card: {error_detail}",
        ) from e
    except Exception as e:
        logger.error(f"[UPDATE CARD] Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update card: {str(e)}",
        ) from e


@router.delete("/cards/{card_id}")
async def delete_card(card_id: str, user: User = Depends(require_auth)):
    """
    Delete a Yoto MYO card.
    
    Only MYO (Make Your Own) cards can be deleted. Commercial cards will return an error.
    
    Args:
        card_id: The ID of the card to delete
    
    Returns:
        Success confirmation
    """
    client = get_yoto_client()
    manager = client.get_manager()
    
    logger.info(f"[DELETE CARD] Starting deletion for card {card_id}")
    
    try:
        response = requests.delete(
            f"https://api.yotoplay.com/content/{card_id}",
            headers={
                "Authorization": f"Bearer {manager.token.access_token}",
            },
            timeout=30,
        )
        
        logger.info(f"[DELETE CARD] Yoto API response status: {response.status_code}")
        logger.info(f"[DELETE CARD] Yoto API response body: {response.text}")
        
        response.raise_for_status()
        
        logger.info(f"✓ Deleted card: {card_id}")
        return {
            "success": True,
            "card_id": card_id,
            "message": "Card deleted successfully!",
        }
        
    except requests.exceptions.HTTPError as e:
        error_detail = e.response.text
        logger.error(f"[DELETE CARD] Yoto API error: {error_detail}")
        
        # Check if it's a 404 (likely a commercial card that can't be deleted)
        if e.response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete this card. It may be a commercial card (not MYO).",
            ) from e
        
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Failed to delete card: {error_detail}",
        ) from e
    except Exception as e:
        logger.error(f"[DELETE CARD] Error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete card: {str(e)}",
        ) from e


# Transcription endpoints
@router.get("/audio/{filename}/transcript")
async def get_transcript(
    filename: str, user: User = Depends(require_auth), db: Session = Depends(get_db)
):
    """
    Get the transcript for an audio file.

    Args:
        filename: Audio filename

    Returns:
        Dictionary with transcript information
    """
    from ...core.audio_db import get_audio_file_by_filename

    audio_record = get_audio_file_by_filename(db, filename)

    if not audio_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No transcript record found for '{filename}'",
        )

    return {
        "filename": filename,
        "transcript": audio_record.transcript,
        "status": audio_record.transcript_status,
        "error": audio_record.transcript_error,
        "transcribed_at": audio_record.transcribed_at.isoformat()
        if audio_record.transcribed_at
        else None,
    }


@router.post("/audio/{filename}/transcribe")
async def trigger_transcription(
    filename: str, user: User = Depends(require_auth), db: Session = Depends(get_db)
):
    """
    Manually trigger transcription for an audio file.

    This will start a new transcription even if one exists.

    Args:
        filename: Audio filename

    Returns:
        Success message with status
    """
    settings = get_settings()
    storage = settings.get_storage()

    if not await storage.exists(filename):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio file '{filename}' not found"
        )

    if not settings.transcription_enabled:
        from ...core.audio_db import get_or_create_audio_file, update_transcript

        # Ensure record exists even when transcription is disabled
        file_size = await storage.get_file_size(filename)
        get_or_create_audio_file(db, filename, file_size, None)
        update_transcript(
            db,
            filename,
            None,
            "disabled",
            "Transcription disabled in this environment",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transcription disabled in this environment. Set TRANSCRIPTION_ENABLED=true and install whisper dependencies to enable.",
        )

    # Get or create audio file record
    from pydub import AudioSegment

    from ...core.audio_db import get_or_create_audio_file, update_transcript

    try:
        # Get file info
        file_size = await storage.get_file_size(filename)

        # For S3 storage, download file to temp location for transcription
        # For local storage, use the existing path
        if settings.storage_backend == "s3":
            # Download file to temp location
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=f"_{filename}", delete=False) as temp_file:
                transcription_path = temp_file.name
                file_data = await storage.read(filename)
                temp_file.write(file_data)
            audio_path = transcription_path
        else:
            audio_path = str(settings.audio_files_dir / filename)

        try:
            audio = AudioSegment.from_mp3(audio_path)
            duration_seconds = int(len(audio) / 1000)
        except Exception:
            duration_seconds = None

        # Ensure database record exists
        get_or_create_audio_file(db, filename, file_size, duration_seconds)

        # Update status to processing
        update_transcript(db, filename, None, "processing", None)

        # Perform transcription
        from ...core.transcription import get_transcription_service

        transcription_service = get_transcription_service()
        transcript_text, error_msg = transcription_service.transcribe_audio(audio_path)

        # Clean up temp file for S3
        if settings.storage_backend == "s3" and os.path.exists(audio_path):
            os.remove(audio_path)

        if transcript_text:
            # Success
            update_transcript(db, filename, transcript_text, "completed", None)
            return {
                "success": True,
                "filename": filename,
                "status": "completed",
                "transcript_length": len(transcript_text),
                "message": "Transcription completed successfully",
            }
        else:
            # Error
            update_transcript(db, filename, None, "error", error_msg)
            return {
                "success": False,
                "filename": filename,
                "status": "error",
                "error": error_msg,
                "message": "Transcription failed",
            }

    except Exception as e:
        logger.error(f"Error during transcription: {e}", exc_info=True)
        # Update record with error (import already done above)
        update_transcript(db, filename, None, "error", str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transcribe audio: {str(e)}",
        ) from e


@router.delete("/audio/{filename}/transcript")
async def delete_transcript(
    filename: str, user: User = Depends(require_auth), db: Session = Depends(get_db)
):
    """
    Delete the transcript for an audio file.

    This removes the transcript text but keeps the audio file record.
    The transcript can be regenerated later.

    Args:
        filename: Audio filename

    Returns:
        Success message
    """
    from ...core.audio_db import get_audio_file_by_filename, update_transcript

    audio_record = get_audio_file_by_filename(db, filename)

    if not audio_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No audio record found for '{filename}'"
        )

    # Clear the transcript and reset status to pending
    update_transcript(db, filename, None, "pending", None)

    logger.info(f"Deleted transcript for {filename}")

    return {"success": True, "filename": filename, "message": "Transcript deleted successfully"}


@router.post("/audio/{filename}/transcript/cancel")
async def cancel_transcription(
    filename: str, user: User = Depends(require_auth), db: Session = Depends(get_db)
):
    """
    Cancel an in-progress transcription.

    Note: This only updates the database status. The actual background task
    may continue to run but its result will be ignored if status is no longer 'processing'.

    Args:
        filename: Audio filename

    Returns:
        Success message
    """
    from ...core.audio_db import get_audio_file_by_filename, update_transcript

    audio_record = get_audio_file_by_filename(db, filename)

    if not audio_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"No audio record found for '{filename}'"
        )

    if audio_record.transcript_status != "processing":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Transcription is not in progress (current status: {audio_record.transcript_status})",
        )

    # Update status to cancelled
    update_transcript(db, filename, None, "cancelled", None)

    logger.info(f"Cancelled transcription for {filename}")

    return {"success": True, "filename": filename, "message": "Transcription cancelled"}


# Playlist creation endpoints
class PlaylistChapterItem(BaseModel):
    """Item in a playlist being built."""

    filename: str = Field(..., description="Audio filename")
    chapter_title: str = Field(..., description="Custom title for this chapter")


class CreatePlaylistRequest(BaseModel):
    """Request model for creating a playlist from multiple audio files."""

    title: str = Field(..., description="Playlist title")
    description: str = Field(default="", description="Playlist description")
    author: str = Field(default="Yoto Smart Stream", description="Playlist author")
    chapters: list[PlaylistChapterItem] = Field(
        ..., description="List of chapters with audio files"
    )
    cover_image_id: Optional[str] = Field(None, description="Optional cover image ID")
    mode: str = Field(
        default="streaming",
        description="Playlist mode: 'streaming' (hosted on server) or 'standard' (uploaded to Yoto)",
    )


class AudioUploadResponse(BaseModel):
    """Response from requesting an upload URL from Yoto."""

    uploadUrl: str = Field(..., description="URL to upload audio to")
    uploadId: str = Field(..., description="ID of the upload")


class AudioTranscodingResponse(BaseModel):
    """Response from retrieving transcoding status."""

    transcodedSha256: str = Field(..., description="SHA256 hash of transcoded audio")
    transcodingProgress: int = Field(..., description="Transcoding progress percentage")


@router.post("/cards/create-playlist-from-audio")
async def create_playlist_from_audio(
    request: CreatePlaylistRequest, user: User = Depends(require_auth)
):
    """
    Create a Yoto MYO card as a playlist from multiple audio files.

    Supports two modes:
    - streaming: Each file becomes a chapter, hosted on our server
    - standard: All files are uploaded to Yoto and form tracks in a single chapter

    Example:
        {
            "title": "Bedtime Stories",
            "description": "A collection of stories",
            "mode": "streaming",
            "chapters": [
                {"filename": "story1.mp3", "chapter_title": "The Lost Forest"},
                {"filename": "story2.mp3", "chapter_title": "Dragon Tales"}
            ]
        }

    Returns:
        Created card information including card ID
    """
    settings = get_settings()
    client = get_yoto_client()
    manager = client.get_manager()

    # Verify all audio files exist
    storage = settings.get_storage()
    audio_files = []
    for chapter_item in request.chapters:
        if not await storage.exists(chapter_item.filename):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audio file not found: {chapter_item.filename}",
            )

        # For local storage, get the path. For S3, we'll need presigned URLs
        if settings.storage_backend == "local":
            audio_path_or_filename = settings.audio_files_dir / chapter_item.filename
        else:
            # For S3, pass filename instead of path - the playlist methods will need to handle this
            audio_path_or_filename = chapter_item.filename

        audio_files.append((audio_path_or_filename, chapter_item))

    # Route to appropriate creation method
    if request.mode == "standard":
        return await _create_standard_playlist(manager, request, audio_files)
    else:
        return await _create_streaming_playlist(settings, manager, request, audio_files)


async def _create_streaming_playlist(
    settings, manager, request: CreatePlaylistRequest, audio_files
):
    """Create a streaming playlist (hosted on our server)."""
    # Verify public URL is set
    if not settings.public_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PUBLIC_URL environment variable not set.",
        )

    chapters = []
    for idx, (_, chapter_item) in enumerate(audio_files, 1):
        streaming_url = f"{settings.public_url}/audio/{chapter_item.filename}"

        # Create chapter with streaming track (Yoto streaming format)
        chapter = {
            "key": f"{idx:02d}",
            "title": chapter_item.chapter_title,
            "overlayLabel": str(idx),
            "tracks": [
                {
                    "key": "01",
                    "title": chapter_item.chapter_title,
                    "type": "stream",
                    "format": "mp3",
                    "trackUrl": streaming_url,
                }
            ],
        }
        chapters.append(chapter)

    # Create the card payload (Yoto /content endpoint format)
    card_data = {
        "title": request.title,
        "content": {"chapters": chapters},
        "metadata": {
            "description": request.description or "",
            "author": request.author,
        },
    }

    # Add cover image if provided
    if request.cover_image_id:
        card_data["metadata"]["cover"] = {"imageId": request.cover_image_id}

    return await _submit_playlist_card(manager, card_data, request.title, len(chapters))


async def _create_standard_playlist(manager, request: CreatePlaylistRequest, audio_files):
    """Create a standard playlist using Yoto's upload workflow."""

    # Get the access token and verify it's available
    if not manager.token or not manager.token.access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not authenticated with Yoto API. Please log in again.",
        )

    headers = {
        "Authorization": f"Bearer {manager.token.access_token}",
        "Content-Type": "application/json",
    }

    # Upload all files in parallel
    upload_tasks = []
    for audio_path_or_filename, chapter_item in audio_files:
        # If it's a Path object, use it. If it's a string (S3), need to download or raise error
        if isinstance(audio_path_or_filename, Path):
            audio_path = audio_path_or_filename
        else:
            # For S3, standard mode upload not yet supported
            # This requires either downloading files from S3 to local temp or
            # implementing direct S3-to-Yoto upload (future enhancement)
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Standard mode playlist creation not yet supported with S3 storage. "
                "Use streaming mode instead, or switch to local storage. "
                "See issue #85 for implementation roadmap.",
            )

        task = _upload_audio_file(headers, audio_path, chapter_item)
        upload_tasks.append(task)

    try:
        # Wait for all uploads to complete
        upload_results = await asyncio.gather(*upload_tasks, return_exceptions=True)

        # Check for errors
        transcoded_hashes = []
        for result in upload_results:
            if isinstance(result, Exception):
                raise result
            transcoded_hashes.append(result)

        # Build single chapter with all tracks
        chapter = {
            "key": "01",
            "title": request.title,
            "overlayLabel": "1",
            "tracks": [
                {
                    "key": f"{idx:02d}",
                    "title": audio_files[idx - 1][1].chapter_title,
                    "type": "audio",
                    "format": "mp3",
                    "trackUrl": f"yoto:#{transcoded_hashes[idx-1]}",
                }
                for idx in range(1, len(transcoded_hashes) + 1)
            ],
        }

        # Create the card payload
        card_data = {
            "title": request.title,
            "content": {"chapters": [chapter]},
            "metadata": {"description": request.description or ""},
        }

        # Add cover image if provided
        if request.cover_image_id:
            card_data["metadata"]["cover"] = {"imageId": request.cover_image_id}

        return await _submit_playlist_card(
            manager, card_data, request.title, len(transcoded_hashes)
        )

    except Exception as e:
        logger.error(f"Error creating standard playlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload audio files: {str(e)}",
        ) from e


async def _upload_audio_file(headers: dict, audio_path, chapter_item) -> str:
    """Upload a single audio file and return its transcodedSha256.

    Uses Yoto's /media/transcode/audio/uploadUrl endpoint per:
    https://yoto.dev/myo/uploading-to-cards/
    """

    loop = asyncio.get_event_loop()

    # Step 1: Request upload URL (GET request)
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: requests.get(
                "https://api.yotoplay.com/media/transcode/audio/uploadUrl",
                headers=headers,
                timeout=30,
            ),
        )
        resp.raise_for_status()
        upload_response = resp.json()

        # Response format: { upload: { uploadUrl: "...", uploadId: "..." } }
        upload_data = upload_response.get("upload", {})
        upload_url = upload_data.get("uploadUrl")
        upload_id = upload_data.get("uploadId")

        if not upload_url or not upload_id:
            raise ValueError(f"Invalid upload response: {upload_response}")

        logger.info(f"Got upload URL for {chapter_item.filename}, uploadId: {upload_id}")
    except Exception as e:
        logger.error(f"Failed to request upload URL for {chapter_item.filename}: {e}")
        raise

    # Step 2: Upload the audio file via PUT
    try:
        with open(audio_path, "rb") as f:
            file_data = f.read()

        await loop.run_in_executor(
            None,
            lambda: requests.put(
                upload_url,
                data=file_data,
                headers={"Content-Type": "audio/mpeg"},
                timeout=60,
            ),
        )
        logger.info(f"✓ Uploaded {chapter_item.filename} to Yoto ({len(file_data)} bytes)")
    except Exception as e:
        logger.error(f"Failed to upload {chapter_item.filename}: {e}")
        raise

    # Step 3: Poll for transcoding completion
    # Large files can take several minutes to transcode
    # Allow up to 5 minutes: 60 attempts at 5 second intervals
    max_attempts = 60
    attempt = 0
    while attempt < max_attempts:
        try:
            resp = await loop.run_in_executor(
                None,
                lambda: requests.get(
                    f"https://api.yotoplay.com/media/upload/{upload_id}/transcoded?loudnorm=false",
                    headers=headers,
                    timeout=30,
                ),
            )

            if resp.status_code == 200:
                transcoding_response = resp.json()
                transcode_data = transcoding_response.get("transcode", {})
                transcoded_sha = transcode_data.get("transcodedSha256")

                if transcoded_sha:
                    logger.info(
                        f"✓ Transcoding complete for {chapter_item.filename}: {transcoded_sha[:16]}..."
                    )
                    return transcoded_sha

            logger.debug(
                f"Transcoding {chapter_item.filename} in progress (attempt {attempt + 1}/{max_attempts})"
            )
            await asyncio.sleep(5)
            attempt += 1
        except Exception as e:
            logger.debug(f"Transcoding check for {chapter_item.filename}: {e}")
            raise

    raise HTTPException(
        status_code=status.HTTP_408_REQUEST_TIMEOUT,
        detail=f"Transcoding timeout for {chapter_item.filename}",
    )


async def _submit_playlist_card(manager, card_data: dict, title: str, track_count: int):
    """Submit the playlist card to Yoto API."""
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: requests.post(
                "https://api.yotoplay.com/content",
                headers={
                    "Authorization": f"Bearer {manager.token.access_token}",
                    "Content-Type": "application/json",
                },
                json=card_data,
                timeout=30,
            ),
        )

        response.raise_for_status()
        card = response.json()

        logger.info(f"✓ Created playlist card: {title} with {track_count} tracks")
        return {
            "success": True,
            "card_id": card.get("cardId"),
            "track_count": track_count,
            "message": f"Playlist created successfully with {track_count} tracks!",
        }

    except requests.exceptions.HTTPError as e:
        error_detail = e.response.text
        logger.error(f"Yoto API error creating playlist: {error_detail}")

        # Check if it's an authorization error from Yoto API
        if e.response.status_code == 401 or '"code":"unauthorized"' in error_detail:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Your Yoto session has expired. Please log in again on the Dashboard.",
            ) from e

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create playlist: {error_detail}",
        ) from e
    except Exception as e:
        logger.error(f"Error creating playlist: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create playlist: {str(e)}",
        ) from e
