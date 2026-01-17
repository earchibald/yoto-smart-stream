"""Card management and audio streaming endpoints."""

import asyncio
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
from fastapi.responses import FileResponse, StreamingResponse
from gtts import gTTS
from pydantic import BaseModel, Field
from pydub import AudioSegment
from sqlalchemy.orm import Session

from ...config import get_settings
from ...database import get_db
from ...models import User
from ...storage.dynamodb_store import get_store
from ...utils.s3 import object_exists, s3_enabled, stream_object, upload_file
from ..dependencies import get_yoto_client
from .user_auth import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


# Background task for transcription
def transcribe_audio_background(
    filename: str,
    audio_path: str,
    db_url: Optional[str],
    dynamodb_table: Optional[str] = None,
    dynamodb_region: Optional[str] = None,
):
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

    persistence = None
    db_session = None

    # Prefer DynamoDB when configured
    if dynamodb_table:
        try:
            persistence = get_store(dynamodb_table, region_name=dynamodb_region)
        except Exception as exc:
            logger.error(f"Failed to initialize DynamoDB store for transcription: {exc}")
    elif db_url:
        engine = create_engine(
            db_url, connect_args={"check_same_thread": False} if "sqlite" in db_url else {}
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        db_session = SessionLocal()
        persistence = db_session

    if persistence is None:
        logger.error("No persistence backend available for transcription task")
        return

    try:
        settings = get_settings()
        if not settings.transcription_enabled:
            logger.info(f"Transcription disabled; skipping background transcription for {filename}")
            update_transcript(
                persistence,
                filename,
                None,
                "disabled",
                "Transcription disabled in this environment",
            )
            return

        logger.info(f"Starting background transcription for {filename}")

        # Update status to processing
        update_transcript(persistence, filename, None, "processing", None)

        # Check if still processing (could have been cancelled)
        audio_record = get_audio_file_by_filename(persistence, filename)
        if audio_record and audio_record.transcript_status != "processing":
            logger.info(f"Transcription was cancelled for {filename}")
            return

        # Perform transcription
        transcription_service = get_transcription_service()
        transcript_text, error_msg = transcription_service.transcribe_audio(Path(audio_path))

        # Check again before saving (in case cancelled during transcription)
        audio_record = get_audio_file_by_filename(persistence, filename)
        if audio_record and audio_record.transcript_status != "processing":
            logger.info(f"Transcription was cancelled for {filename} during processing")
            return

        if transcript_text:
            update_transcript(persistence, filename, transcript_text, "completed", None)
            logger.info(f"✓ Background transcription completed for {filename}")
        else:
            update_transcript(persistence, filename, None, "error", error_msg)
            logger.warning(f"Background transcription failed for {filename}: {error_msg}")
    except Exception as e:
        logger.error(f"Background transcription error for {filename}: {e}", exc_info=True)
        audio_record = get_audio_file_by_filename(persistence, filename)
        if audio_record and audio_record.transcript_status == "processing":
            update_transcript(persistence, filename, None, "error", str(e))
    finally:
        if db_session:
            db_session.close()


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


class CreateCardFromUrlRequest(BaseModel):
    """Request model for creating a streaming MYO card from external URL."""

    title: str = Field(..., description="Card title")
    description: str = Field(default="", description="Card description")
    author: str = Field(default="Yoto Smart Stream", description="Card author")
    audio_url: str = Field(
        ..., description="External audio URL (e.g., 'https://example.com/audio.mp3')"
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
    audio_files = []
    static_files = {f"{i}.mp3" for i in range(1, 11)}

    if s3_enabled(settings):
        try:
            import boto3

            s3 = boto3.client("s3")
            resp = s3.list_objects_v2(Bucket=settings.s3_audio_bucket)
            for obj in resp.get("Contents", []):
                key = obj.get("Key")
                if not key or not key.lower().endswith(".mp3"):
                    continue

                # Get transcript info from database
                from ...core.audio_db import get_audio_file_by_filename

                audio_record = get_audio_file_by_filename(db, key)

                transcript_info = {
                    "status": audio_record.transcript_status if audio_record else "pending",
                    "has_transcript": bool(audio_record and audio_record.transcript),
                }

                audio_files.append(
                    {
                        "filename": key,
                        "size": obj.get("Size", 0),
                        "duration": 0,  # Duration unavailable without downloading
                        "url": f"/api/audio/{key}",
                        "is_static": key in static_files,
                        "transcript": transcript_info,
                    }
                )
        except Exception as e:
            logger.error(f"Failed to list S3 audio files: {e}")
    else:
        for audio_path in settings.audio_files_dir.glob("*.mp3"):
            try:
                audio = AudioSegment.from_mp3(str(audio_path))
                duration_seconds = int(len(audio) / 1000)
            except Exception as e:
                logger.warning(f"Could not read duration for {audio_path.name}: {e}")
                duration_seconds = 0

            is_static = audio_path.name in static_files
            from ...core.audio_db import get_audio_file_by_filename

            audio_record = get_audio_file_by_filename(db, audio_path.name)

            transcript_info = {
                "status": audio_record.transcript_status if audio_record else "pending",
                "has_transcript": bool(audio_record and audio_record.transcript),
            }

            audio_files.append(
                {
                    "filename": audio_path.name,
                    "size": audio_path.stat().st_size,
                    "duration": duration_seconds,
                    "url": f"/api/audio/{audio_path.name}",
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
    Generate text-to-speech audio and save to audio_files directory.

    This endpoint creates an MP3 file from the provided text using Google Text-to-Speech.
    The generated file is saved to the audio_files directory and can be used
    in MYO cards or accessed via the audio streaming endpoint.

    A transcript record is automatically created, and since we have the source text,
    we can store it directly without needing to run speech-to-text.

    Args:
        request: GenerateTTSRequest with filename and text

    Returns:
        Success message with filename and file information
    """
    settings = get_settings()

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
    use_s3 = s3_enabled(settings)
    if use_s3:
        if object_exists(settings.s3_audio_bucket, final_filename):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File '{final_filename}' already exists in S3. Please choose a different name.",
            )
        output_path = Path(tempfile.mktemp(suffix=".mp3"))
    else:
        output_path = settings.audio_files_dir / final_filename
        if output_path.exists():
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

            # Export as optimized MP3
            audio.export(
                output_path,
                format="mp3",
                bitrate="192k",
                parameters=["-ac", "1"],  # Ensure mono
            )

            file_size = output_path.stat().st_size
            duration_seconds = int(len(audio) / 1000)

            if use_s3:
                upload_file(settings.s3_audio_bucket, final_filename, str(output_path))

            logger.info(
                f"✓ TTS audio generated: {final_filename} ({file_size} bytes, {duration_seconds}s)"
            )

            from ...core.audio_db import get_or_create_audio_file, update_transcript

            audio_record = get_or_create_audio_file(db, final_filename, file_size, duration_seconds)
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
            if use_s3 and os.path.exists(output_path):
                os.remove(output_path)

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

    This endpoint accepts audio files (MP3, WebM, WAV) and saves them to the audio_files
    directory. If the uploaded file is not MP3, it will be converted to MP3 format.

    Transcription is triggered as a background task after upload completes.

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
    use_s3 = s3_enabled(settings)
    if use_s3:
        if object_exists(settings.s3_audio_bucket, final_filename):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"File '{final_filename}' already exists in S3. Please choose a different name.",
            )
        output_path = Path(tempfile.mktemp(suffix=".mp3"))
    else:
        output_path = settings.audio_files_dir / final_filename
        if output_path.exists():
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

        # Export as optimized MP3
        audio.export(
            output_path,
            format="mp3",
            bitrate="192k",
            parameters=["-ac", "1"],  # Ensure mono
        )

        file_size = output_path.stat().st_size
        duration_seconds = int(len(audio) / 1000)

        if use_s3:
            upload_file(settings.s3_audio_bucket, final_filename, str(output_path))

        logger.info(
            f"✓ Audio uploaded and converted: {final_filename} ({file_size} bytes, {duration_seconds}s)"
        )

        from ...core.audio_db import get_or_create_audio_file, update_transcript

        audio_record = get_or_create_audio_file(db, final_filename, file_size, duration_seconds)

        if settings.transcription_enabled:
            # Mark transcription as pending and schedule background task
            update_transcript(db, final_filename, None, "pending", None)

            # Schedule background transcription (non-blocking)
            if background_tasks:
                settings = get_settings()
                background_tasks.add_task(
                    transcribe_audio_background,
                    final_filename,
                    str(output_path),
                    settings.database_url,
                    settings.dynamodb_table,
                    settings.dynamodb_region,
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
        if use_s3 and output_path and os.path.exists(output_path):
            os.remove(output_path)


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
    audio_files = []
    query = q.lower().strip()

    if s3_enabled(settings):
        try:
            import boto3

            s3 = boto3.client("s3")
            resp = s3.list_objects_v2(Bucket=settings.s3_audio_bucket)
            for obj in resp.get("Contents", []):
                key = obj.get("Key")
                if not key or not key.lower().endswith(".mp3"):
                    continue
                audio_record = get_audio_file_by_filename(db, key)
                transcript = audio_record.transcript if audio_record else None
                audio_files.append(
                    {
                        "filename": key,
                        "size": obj.get("Size", 0),
                        "duration": 0,
                        "transcript": transcript,
                    }
                )
        except Exception as e:
            logger.error(f"Failed to search S3 audio files: {e}")
    else:
        for audio_path in settings.audio_files_dir.glob("*.mp3"):
            try:
                audio = AudioSegment.from_mp3(str(audio_path))
                duration_seconds = int(len(audio) / 1000)
            except Exception as e:
                logger.warning(f"Could not read duration for {audio_path.name}: {e}")
                duration_seconds = 0

            audio_record = get_audio_file_by_filename(db, audio_path.name)
            transcript = audio_record.transcript if audio_record else None

            audio_files.append(
                {
                    "filename": audio_path.name,
                    "size": audio_path.stat().st_size,
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

    # Determine media type from extension
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/aac"

    if s3_enabled(settings):
        if not object_exists(settings.s3_audio_bucket, filename):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audio file not found: {filename}",
            )

        return StreamingResponse(
            stream_object(settings.s3_audio_bucket, filename, 64 * 1024),
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
            },
        )

    audio_path = settings.audio_files_dir / filename

    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio file not found: {filename}"
        )

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
    if s3_enabled(settings):
        if not object_exists(settings.s3_audio_bucket, request.audio_filename):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audio file not found: {request.audio_filename} in S3 bucket {settings.s3_audio_bucket}.",
            )
    else:
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


@router.post("/cards/create-streaming-url")
async def create_streaming_card_from_url(
    request: CreateCardFromUrlRequest, user: User = Depends(require_auth)
):
    """
    Create a Yoto MYO card that streams from an external URL.

    This endpoint creates a card that points to audio hosted at an external URL.
    This is useful for testing and creating cards without uploading audio files
    to the server first.

    Example:
        {
            "title": "Test Card",
            "audio_url": "https://example.com/audio.mp3",
            "description": "A test card"
        }

    Returns:
        Created card information including card ID and content ID
    """
    client = get_yoto_client()
    manager = client.get_manager()

    # Create the card payload using Yoto's /content endpoint format
    card_data = {
        "title": request.title,
        "metadata": {
            "description": request.description,
            "author": request.author,
        },
        "content": {
            "chapters": [
                {
                    "key": "01",
                    "title": "Chapter 1",
                    "tracks": [
                        {
                            "key": "01",
                            "title": request.title,
                            "type": "stream",
                            "format": "mp3",
                            "trackUrl": request.audio_url,
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
        # Use the /content endpoint which supports streaming URLs
        response = requests.post(
            "https://api.yotoplay.com/content",
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
            "content_id": card.get("id") or card.get("contentId") or card.get("cardId"),
            "streaming_url": request.audio_url,
            "message": "Card created successfully! It will stream from the external URL.",
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
    audio_path = settings.audio_files_dir / filename

    if not audio_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Audio file '{filename}' not found"
        )

    if not settings.transcription_enabled:
        from ...core.audio_db import get_or_create_audio_file, update_transcript

        # Ensure record exists even when transcription is disabled
        file_size = audio_path.stat().st_size
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
        file_size = audio_path.stat().st_size
        try:
            audio = AudioSegment.from_mp3(str(audio_path))
            duration_seconds = int(len(audio) / 1000)
        except Exception:
            duration_seconds = None

        # Ensure database record exists
        audio_record = get_or_create_audio_file(db, filename, file_size, duration_seconds)

        # Update status to processing
        update_transcript(db, filename, None, "processing", None)

        # Perform transcription
        from ...core.transcription import get_transcription_service

        transcription_service = get_transcription_service()
        transcript_text, error_msg = transcription_service.transcribe_audio(audio_path)

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
    audio_files = []
    for chapter_item in request.chapters:
        audio_path = settings.audio_files_dir / chapter_item.filename
        if not audio_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audio file not found: {chapter_item.filename}",
            )
        audio_files.append((audio_path, chapter_item))

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
    for idx, (audio_path, chapter_item) in enumerate(audio_files, 1):
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
        "metadata": {"description": request.description or ""},
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
    for audio_path, chapter_item in audio_files:
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
