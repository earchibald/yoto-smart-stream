"""
Speech-to-text transcription service for audio files.

This module provides transcription functionality using OpenAI Whisper or ElevenLabs.
"""

import logging
from pathlib import Path
from typing import Optional

from ..config import get_settings

try:
    import whisper  # type: ignore
except Exception as import_err:  # pragma: no cover - optional dependency
    whisper = None  # type: ignore
    _whisper_import_error = import_err
else:
    _whisper_import_error = None

try:
    from elevenlabs.client import ElevenLabs  # type: ignore
except Exception as import_err:  # pragma: no cover - optional dependency
    ElevenLabs = None  # type: ignore
    _elevenlabs_import_error = import_err
else:
    _elevenlabs_import_error = None

logger = logging.getLogger(__name__)


class TranscriptionService:
    """Service for transcribing audio files to text using Whisper or ElevenLabs."""

    def __init__(
        self,
        model_name: str = "base",
        enabled: bool = True,
        provider: str = "whisper",
        elevenlabs_api_key: Optional[str] = None,
    ):
        """
        Initialize the transcription service.

        Args:
            model_name: Model to use (for Whisper: tiny, base, small, medium, large)
                       (for ElevenLabs: scribe_v2)
            enabled: Whether transcription should be attempted
            provider: Transcription provider ('whisper' or 'elevenlabs')
            elevenlabs_api_key: ElevenLabs API key (required if provider is 'elevenlabs')
        """
        self.model_name = model_name
        self.provider = provider
        self.elevenlabs_api_key = elevenlabs_api_key
        self._disabled_reason: Optional[str] = None
        self._model = None
        self._elevenlabs_client = None

        # Determine if service should be enabled
        if not enabled:
            self.enabled = False
            self._disabled_reason = "Transcription disabled via configuration"
            logger.info(self._disabled_reason)
        elif provider == "elevenlabs":
            if ElevenLabs is None:
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
        elif provider == "whisper":
            if whisper is None:
                self.enabled = False
                self._disabled_reason = "Whisper dependency not installed"
                logger.warning(self._disabled_reason)
                if _whisper_import_error:
                    logger.debug(f"Whisper import error: {_whisper_import_error}")
            else:
                self.enabled = True
                logger.info(
                    f"Transcription service initialized with Whisper, model: {model_name}, enabled=True"
                )
        else:
            self.enabled = False
            self._disabled_reason = f"Unknown transcription provider: {provider}"
            logger.error(self._disabled_reason)

    def _load_model(self):
        """Load the transcription model lazily (only when needed)."""
        if not self.enabled:
            raise RuntimeError(self._disabled_reason or "Transcription disabled")

        if self.provider == "whisper":
            if self._model is None:
                logger.info(f"Loading Whisper model: {self.model_name}")
                self._model = whisper.load_model(self.model_name)
                logger.info("Whisper model loaded successfully")
        elif self.provider == "elevenlabs":
            if self._elevenlabs_client is None:
                logger.info("Initializing ElevenLabs client")
                self._elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
                logger.info("ElevenLabs client initialized successfully")

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

            logger.info(f"Starting transcription for: {audio_path.name} using {self.provider}")

            if self.provider == "whisper":
                # Transcribe using Whisper
                result = self._model.transcribe(str(audio_path))
                transcript = result.get("text", "").strip()
            elif self.provider == "elevenlabs":
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
                # The result object has a 'text' attribute
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
            enabled=settings.transcription_enabled,
            provider=settings.transcription_provider,
            elevenlabs_api_key=settings.elevenlabs_api_key,
        )
    return _transcription_service
