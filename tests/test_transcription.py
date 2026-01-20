"""
Tests for speech-to-text transcription service.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from yoto_smart_stream.core.transcription import TranscriptionService, get_transcription_service


class TestTranscriptionService:
    """Test transcription service."""

    def test_init_elevenlabs(self):
        """Test service initialization with ElevenLabs."""
        service = TranscriptionService(model_name="scribe_v2", elevenlabs_api_key="test_key")
        assert service.model_name == "scribe_v2"
        assert service.elevenlabs_api_key == "test_key"
        assert service._elevenlabs_client is None  # Client not loaded yet

    def test_init_elevenlabs_no_key(self):
        """Test service initialization with ElevenLabs but no API key."""
        service = TranscriptionService(model_name="scribe_v2", elevenlabs_api_key=None)
        assert service.enabled is False
        assert "API key not configured" in service._disabled_reason

    def test_init_disabled(self):
        """Test service initialization when disabled."""
        service = TranscriptionService(
            model_name="scribe_v2", enabled=False, elevenlabs_api_key="test_key"
        )
        assert service.enabled is False
        assert "Transcription disabled via configuration" in service._disabled_reason

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_load_client_elevenlabs(self, mock_elevenlabs_class):
        """Test lazy client loading for ElevenLabs."""
        mock_client = MagicMock()
        mock_elevenlabs_class.return_value = mock_client

        service = TranscriptionService(model_name="scribe_v2", elevenlabs_api_key="test_key")
        assert service._elevenlabs_client is None

        # Load the client
        service._load_client()

        mock_elevenlabs_class.assert_called_once_with(api_key="test_key")
        assert service._elevenlabs_client == mock_client

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_transcribe_audio_success(self, mock_elevenlabs_class):
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

            service = TranscriptionService(model_name="scribe_v2", elevenlabs_api_key="test_key")
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

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_transcribe_audio_empty_result(self, mock_elevenlabs_class):
        """Test transcription with empty result."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the ElevenLabs client to return empty text
            mock_client = MagicMock()
            mock_result = MagicMock()
            mock_result.text = ""
            mock_client.speech_to_text.convert.return_value = mock_result
            mock_elevenlabs_class.return_value = mock_client

            service = TranscriptionService(elevenlabs_api_key="test_key")
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert error == "Transcription completed but no text was extracted"

        finally:
            temp_path.unlink()

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_transcribe_audio_file_not_found(self, mock_elevenlabs_class):
        """Test transcription with non-existent file."""
        # Mock ElevenLabs to be available
        mock_elevenlabs_class.return_value = MagicMock()

        service = TranscriptionService(elevenlabs_api_key="test_key")
        non_existent_path = Path("/tmp/non_existent_file.mp3")

        transcript, error = service.transcribe_audio(non_existent_path)

        assert transcript is None
        assert "Audio file not found" in error

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_transcribe_audio_exception(self, mock_elevenlabs_class):
        """Test transcription with exception in ElevenLabs."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the ElevenLabs client to raise an exception
            mock_client = MagicMock()
            mock_client.speech_to_text.convert.side_effect = Exception("ElevenLabs API error")
            mock_elevenlabs_class.return_value = mock_client

            service = TranscriptionService(elevenlabs_api_key="test_key")
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert "Error transcribing audio" in error
            assert "ElevenLabs API error" in error

        finally:
            temp_path.unlink()

    @patch("yoto_smart_stream.core.transcription.ElevenLabs")
    def test_transcribe_audio_missing_text_attribute(self, mock_elevenlabs_class):
        """Test transcription when API response is missing text attribute."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the ElevenLabs client to return object without text attribute
            mock_client = MagicMock()
            mock_result = MagicMock(spec=[])  # Empty spec means no attributes
            mock_client.speech_to_text.convert.return_value = mock_result
            mock_elevenlabs_class.return_value = mock_client

            service = TranscriptionService(elevenlabs_api_key="test_key")
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert "missing 'text' attribute" in error

        finally:
            temp_path.unlink()

    def test_transcribe_audio_disabled(self):
        """Test transcription when service is disabled."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            service = TranscriptionService(enabled=False, elevenlabs_api_key="test_key")
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert "disabled" in error.lower()

        finally:
            temp_path.unlink()

    def test_get_transcription_service_singleton(self):
        """Test that get_transcription_service returns a singleton."""
        service1 = get_transcription_service()
        service2 = get_transcription_service()

        assert service1 is service2
