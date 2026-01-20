"""
Speech-to-text transcription service for audio files.

This module provides transcription functionality using ElevenLabs.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import get_settings

try:
    from elevenlabs.client import ElevenLabs  # type: ignore
except Exception as import_err:  # pragma: no cover - optional dependency
    ElevenLabs = None  # type: ignore
    _elevenlabs_import_error = import_err
else:
    _elevenlabs_import_error = None

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio files to text using ElevenLabs."""

    def __init__(
        self,
        model_name: str = "scribe_v2",
        enabled: bool = True,
        elevenlabs_api_key: Optional[str] = None,
    ):
        """
        Initialize the transcription service.

        Args:
            model_name: ElevenLabs model to use (default: scribe_v2)
            enabled: Whether transcription should be attempted
            elevenlabs_api_key: ElevenLabs API key (required)
        """
        self.model_name = model_name
        self.elevenlabs_api_key = elevenlabs_api_key
        self._disabled_reason: Optional[str] = None
        self._elevenlabs_client = None

        # Determine if service should be enabled
        if not enabled:
            self.enabled = False
            self._disabled_reason = "Transcription disabled via configuration"
            logger.info(self._disabled_reason)
        elif ElevenLabs is None:
            self.enabled = False
            self._disabled_reason = "ElevenLabs dependency not installed"
            logger.warning(self._disabled_reason)
            if _elevenlabs_import_error:
                logger.debug(f"ElevenLabs import error: {_elevenlabs_import_error}")
        elif not elevenlabs_api_key:
            self.enabled = False
            self._disabled_reason = "ElevenLabs API key not configured"
            logger.warning(self._disabled_reason)
        else:
            self.enabled = True
            logger.info(
                f"Transcription service initialized with ElevenLabs, model: {model_name}, enabled=True"
            )

    def _load_client(self):
        """Initialize the ElevenLabs client lazily (only when needed)."""
        if not self.enabled:
            raise RuntimeError(self._disabled_reason or "Transcription disabled")

        if self._elevenlabs_client is None:
            logger.info("Initializing ElevenLabs client")
            self._elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
            logger.info("ElevenLabs client initialized successfully")

    def transcribe_audio(self, audio_path: Path) -> tuple[Optional[str], Optional[str]]:
        """
        Transcribe an audio file to text using ElevenLabs.

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

            # Initialize client if not already loaded
            self._load_client()

            logger.info(f"Starting transcription for: {audio_path.name} using ElevenLabs")

            # Transcribe using ElevenLabs
            settings = get_settings()
            with open(audio_path, "rb") as audio_file:
                result = self._elevenlabs_client.speech_to_text.convert(
                    file=audio_file,
                    model_id=self.model_name or settings.transcription_model,
                    tag_audio_events=True,
                    language_code=None,  # Auto-detect language
                    diarize=False,  # Disable speaker diarization for simplicity
                )

            # Extract text from ElevenLabs response
            try:
                transcript = result.text.strip() if result.text else ""
            except AttributeError:
                error_msg = "ElevenLabs API response missing 'text' attribute"
                logger.error(f"{error_msg}: {result}")
                return None, error_msg

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
            enabled=settings.get_transcription_enabled(),
            elevenlabs_api_key=settings.elevenlabs_api_key,
        )
    return _transcription_service
