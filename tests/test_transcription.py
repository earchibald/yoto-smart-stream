"""
Tests for speech-to-text transcription service.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yoto_smart_stream.core.transcription import TranscriptionService, get_transcription_service


class TestTranscriptionService:
    """Test transcription service."""

    def test_init_whisper(self):
        """Test service initialization with Whisper."""
        service = TranscriptionService(model_name="tiny", provider="whisper")
        assert service.model_name == "tiny"
        assert service.provider == "whisper"
        assert service._model is None  # Model not loaded yet

    def test_init_elevenlabs(self):
        """Test service initialization with ElevenLabs."""
        service = TranscriptionService(
            model_name="scribe_v2", provider="elevenlabs", elevenlabs_api_key="test_key"
        )
        assert service.model_name == "scribe_v2"
        assert service.provider == "elevenlabs"
        assert service.elevenlabs_api_key == "test_key"
        assert service._elevenlabs_client is None  # Client not loaded yet

    def test_init_elevenlabs_no_key(self):
        """Test service initialization with ElevenLabs but no API key."""
        service = TranscriptionService(
            model_name="scribe_v2", provider="elevenlabs", elevenlabs_api_key=None
        )
        assert service.enabled is False
        assert "API key not configured" in service._disabled_reason

    @patch("yoto_smart_stream.core.transcription.whisper")
    def test_load_model_whisper(self, mock_whisper):
        """Test lazy model loading for Whisper."""
        mock_model = MagicMock()
        mock_whisper.load_model.return_value = mock_model

        service = TranscriptionService(model_name="base", provider="whisper")
        assert service._model is None

        # Load the model
        service._load_model()

        mock_whisper.load_model.assert_called_once_with("base")
        assert service._model == mock_model

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_load_model_elevenlabs(self, mock_elevenlabs_class):
        """Test lazy client loading for ElevenLabs."""
        mock_client = MagicMock()
        mock_elevenlabs_class.return_value = mock_client

        service = TranscriptionService(
            model_name="scribe_v2", provider="elevenlabs", elevenlabs_api_key="test_key"
        )
        assert service._elevenlabs_client is None

        # Load the client
        service._load_model()

        mock_elevenlabs_class.assert_called_once_with(api_key="test_key")
        assert service._elevenlabs_client == mock_client

    @patch("yoto_smart_stream.core.transcription.whisper")
    def test_transcribe_audio_success_whisper(self, mock_whisper):
        """Test successful audio transcription with Whisper."""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the Whisper model
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {"text": "Hello, this is a test transcript."}
            mock_whisper.load_model.return_value = mock_model

            service = TranscriptionService(provider="whisper")
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript == "Hello, this is a test transcript."
            assert error is None
            mock_model.transcribe.assert_called_once_with(str(temp_path))

        finally:
            # Clean up
            temp_path.unlink()

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_transcribe_audio_success_elevenlabs(self, mock_elevenlabs_class):
        """Test successful audio transcription with ElevenLabs."""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the ElevenLabs client
            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.text = "This is transcribed by ElevenLabs."
            mock_client.speech_to_text.convert.return_value = mock_result
            mock_elevenlabs_class.return_value = mock_client

            service = TranscriptionService(
                model_name="scribe_v2", provider="elevenlabs", elevenlabs_api_key="test_key"
            )
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript == "This is transcribed by ElevenLabs."
            assert error is None
            # Verify the method was called once
            assert mock_client.speech_to_text.convert.call_count == 1
            # Check the call arguments
            call_args = mock_client.speech_to_text.convert.call_args
            assert call_args[1]["model_id"] == "scribe_v2"
            assert call_args[1]["tag_audio_events"] is True
            assert call_args[1]["language_code"] is None
            assert call_args[1]["diarize"] is False

        finally:
            # Clean up
            temp_path.unlink()

    @patch("yoto_smart_stream.core.transcription.whisper")
    def test_transcribe_audio_empty_result(self, mock_whisper):
        """Test transcription with empty result."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the Whisper model to return empty text
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {"text": ""}
            mock_whisper.load_model.return_value = mock_model

            service = TranscriptionService(provider="whisper")
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert error == "Transcription completed but no text was extracted"

        finally:
            temp_path.unlink()

    @patch("yoto_smart_stream.core.transcription.whisper")
    def test_transcribe_audio_file_not_found(self, mock_whisper):
        """Test transcription with non-existent file."""
        # Mock whisper to be available
        mock_whisper.load_model.return_value = MagicMock()

        service = TranscriptionService(provider="whisper")
        non_existent_path = Path("/tmp/non_existent_file.mp3")

        transcript, error = service.transcribe_audio(non_existent_path)

        assert transcript is None
        assert "Audio file not found" in error

    @patch("yoto_smart_stream.core.transcription.whisper")
    def test_transcribe_audio_exception_whisper(self, mock_whisper):
        """Test transcription with exception in Whisper."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the Whisper model to raise an exception
            mock_model = MagicMock()
            mock_model.transcribe.side_effect = Exception("Transcription failed")
            mock_whisper.load_model.return_value = mock_model

            service = TranscriptionService(provider="whisper")
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert "Error transcribing audio" in error

        finally:
            temp_path.unlink()

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_transcribe_audio_exception_elevenlabs(self, mock_elevenlabs_class):
        """Test transcription with exception in ElevenLabs."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the ElevenLabs client to raise an exception
            mock_client = MagicMock()
            mock_client.speech_to_text.convert.side_effect = Exception("ElevenLabs API error")
            mock_elevenlabs_class.return_value = mock_client

            service = TranscriptionService(provider="elevenlabs", elevenlabs_api_key="test_key")
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert "Error transcribing audio" in error
            assert "ElevenLabs API error" in error

        finally:
            temp_path.unlink()

    def test_get_transcription_service_singleton(self):
        """Test that get_transcription_service returns a singleton."""
        service1 = get_transcription_service()
        service2 = get_transcription_service()

        assert service1 is service2


class TestTranscriptionIntegration:
    """Integration tests for transcription (require actual Whisper model)."""

    @pytest.mark.slow
    @pytest.mark.skipif(
        True, reason="Skipped by default - requires large model download and GPU/CPU time"
    )
    @patch("yoto_smart_stream.core.transcription.whisper")
    def test_real_transcription(self, mock_whisper):
        """
        Test real transcription with actual Whisper model.

        This test is skipped by default as it requires:
        - Downloading the Whisper model (~140MB for base model)
        - Significant CPU/GPU time for transcription
        - A real audio file

        To run this test, remove the skipif decorator and provide a real audio file.
        """
        # Mock whisper for this test since it's skipped anyway
        service = TranscriptionService(
            model_name="tiny", provider="whisper"
        )  # Use tiny model for faster testing

        # Create a test audio file (you would need a real MP3 file here)
        # For now, this is just a placeholder
        test_audio_path = Path("test_audio.mp3")

        if test_audio_path.exists():
            transcript, error = service.transcribe_audio(test_audio_path)
            assert transcript is not None or error is not None
