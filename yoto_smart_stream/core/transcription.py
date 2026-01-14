"""
Speech-to-text transcription service for audio files.

This module provides transcription functionality using OpenAI Whisper.
"""

import logging
from pathlib import Path
from typing import Optional

import whisper

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio files to text using Whisper."""

    def __init__(self, model_name: str = "base"):
        """
        Initialize the transcription service.

        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
                       base is a good balance between speed and accuracy
        """
        self.model_name = model_name
        self._model = None
        logger.info(f"Transcription service initialized with model: {model_name}")

    def _load_model(self):
        """Load the Whisper model lazily (only when needed)."""
        if self._model is None:
            logger.info(f"Loading Whisper model: {self.model_name}")
            self._model = whisper.load_model(self.model_name)
            logger.info("Whisper model loaded successfully")

    def transcribe_audio(self, audio_path: Path) -> tuple[Optional[str], Optional[str]]:
        """
        Transcribe an audio file to text.

        Args:
            audio_path: Path to the audio file

        Returns:
            Tuple of (transcript_text, error_message)
            If successful, returns (text, None)
            If failed, returns (None, error_message)
        """
        try:
            if not audio_path.exists():
                error_msg = f"Audio file not found: {audio_path}"
                logger.error(error_msg)
                return None, error_msg

            # Load model if not already loaded
            self._load_model()

            logger.info(f"Starting transcription for: {audio_path.name}")

            # Transcribe the audio file
            result = self._model.transcribe(str(audio_path))

            # Extract the text from the result
            transcript = result.get("text", "").strip()

            if not transcript:
                error_msg = "Transcription completed but no text was extracted"
                logger.warning(error_msg)
                return None, error_msg

            logger.info(
                f"Transcription completed successfully for {audio_path.name}: {len(transcript)} characters"
            )
            return transcript, None

        except Exception as e:
            error_msg = f"Error transcribing audio: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg


# Global instance (lazy-loaded)
_transcription_service: Optional[TranscriptionService] = None


def get_transcription_service() -> TranscriptionService:
    """
    Get or create the global transcription service instance.

    Returns:
        TranscriptionService instance
    """
    global _transcription_service
    if _transcription_service is None:
        _transcription_service = TranscriptionService()
    return _transcription_service
