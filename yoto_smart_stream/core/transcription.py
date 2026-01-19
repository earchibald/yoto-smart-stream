"""
Speech-to-text transcription service for audio files.

This module provides transcription functionality using OpenAI Whisper.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import get_settings

try:
    import whisper  # type: ignore
except Exception as import_err:  # pragma: no cover - optional dependency
    whisper = None  # type: ignore
    _import_error = import_err
else:
    _import_error = None

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio files to text using Whisper."""

    def __init__(self, model_name: str = "base", enabled: bool = True):
        """
        Initialize the transcription service.

        Args:
            model_name: Whisper model to use (tiny, base, small, medium, large)
                       base is a good balance between speed and accuracy
            enabled: Whether transcription should be attempted
        """
        self.model_name = model_name
        self.enabled = enabled and whisper is not None and _import_error is None
        self._disabled_reason: Optional[str] = None
        self._model = None

        if not enabled:
            self._disabled_reason = "Transcription disabled via configuration"
            logger.info(self._disabled_reason)
        elif whisper is None:
            self._disabled_reason = "Whisper dependency not installed"
            logger.warning(self._disabled_reason)
            if _import_error:
                logger.debug(f"Whisper import error: {_import_error}")
        logger.info(f"Transcription service initialized with model: {model_name}, enabled={self.enabled}")

    def _load_model(self):
        """Load the Whisper model lazily (only when needed)."""
        if not self.enabled:
            raise RuntimeError(self._disabled_reason or "Transcription disabled")

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
        if not self.enabled:
            error_msg = self._disabled_reason or "Transcription disabled"
            logger.info(f"Skipping transcription for {audio_path.name}: {error_msg}")
            return None, error_msg

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
        settings = get_settings()
        _transcription_service = TranscriptionService(
            model_name=settings.transcription_model,
            enabled=settings.transcription_enabled,
        )
    return _transcription_service
