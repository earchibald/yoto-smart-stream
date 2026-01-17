"""
Audio file database management utilities.

This module provides helper functions for managing AudioFile records.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from ..models import AudioFile

logger = logging.getLogger(__name__)


def get_or_create_audio_file(db: Session, filename: str, size: int, duration: Optional[int] = None) -> AudioFile:
    """
    Get existing AudioFile record or create a new one.

    Args:
        db: Database session
        filename: Audio filename
        size: File size in bytes
        duration: Duration in seconds (optional)

    Returns:
        AudioFile instance
    """
    # Try to get existing record
    audio_file = db.query(AudioFile).filter(AudioFile.filename == filename).first()

    if audio_file:
        # Update size and duration if provided
        audio_file.size = size
        if duration is not None:
            audio_file.duration = duration
        audio_file.updated_at = datetime.utcnow()
        db.commit()
        logger.debug(f"Updated existing AudioFile record: {filename}")
    else:
        # Create new record
        audio_file = AudioFile(
            filename=filename,
            size=size,
            duration=duration,
            transcript_status="pending"
        )
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        logger.info(f"Created new AudioFile record: {filename}")

    return audio_file


def update_transcript(
    db: Session,
    filename: str,
    transcript: Optional[str],
    status: str,
    error: Optional[str] = None
) -> Optional[AudioFile]:
    """
    Update transcript for an audio file.

    Args:
        db: Database session
        filename: Audio filename
        transcript: Transcript text (if successful)
        status: Transcript status (processing, completed, error)
        error: Error message (if failed)

    Returns:
        Updated AudioFile instance or None if not found
    """
    audio_file = db.query(AudioFile).filter(AudioFile.filename == filename).first()

    if not audio_file:
        logger.warning(f"AudioFile record not found: {filename}")
        return None

    audio_file.transcript = transcript
    audio_file.transcript_status = status
    audio_file.transcript_error = error
    audio_file.updated_at = datetime.utcnow()

    if status == "completed":
        audio_file.transcribed_at = datetime.utcnow()

    db.commit()
    db.refresh(audio_file)

    logger.info(f"Updated transcript for {filename}: status={status}")
    return audio_file


def get_audio_file_by_filename(db: Session, filename: str) -> Optional[AudioFile]:
    """
    Get AudioFile record by filename.

    Args:
        db: Database session
        filename: Audio filename

    Returns:
        AudioFile instance or None if not found
    """
    return db.query(AudioFile).filter(AudioFile.filename == filename).first()
