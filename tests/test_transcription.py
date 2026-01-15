"""
Tests for speech-to-text transcription service.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import tempfile

import pytest

from yoto_smart_stream.core.transcription import TranscriptionService, get_transcription_service


class TestTranscriptionService:
    """Test transcription service."""

    def test_init(self):
        """Test service initialization."""
        service = TranscriptionService(model_name="tiny")
        assert service.model_name == "tiny"
        assert service._model is None  # Model not loaded yet

    @patch("yoto_smart_stream.core.transcription.whisper.load_model")
    def test_load_model(self, mock_load_model):
        """Test lazy model loading."""
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model

        service = TranscriptionService(model_name="base")
        assert service._model is None

        # Load the model
        service._load_model()

        mock_load_model.assert_called_once_with("base")
        assert service._model == mock_model

    @patch("yoto_smart_stream.core.transcription.whisper.load_model")
    def test_transcribe_audio_success(self, mock_load_model):
        """Test successful audio transcription."""
        # Create a temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the Whisper model
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {"text": "Hello, this is a test transcript."}
            mock_load_model.return_value = mock_model

            service = TranscriptionService()
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript == "Hello, this is a test transcript."
            assert error is None
            mock_model.transcribe.assert_called_once_with(str(temp_path))

        finally:
            # Clean up
            temp_path.unlink()

    @patch("yoto_smart_stream.core.transcription.whisper.load_model")
    def test_transcribe_audio_empty_result(self, mock_load_model):
        """Test transcription with empty result."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the Whisper model to return empty text
            mock_model = MagicMock()
            mock_model.transcribe.return_value = {"text": ""}
            mock_load_model.return_value = mock_model

            service = TranscriptionService()
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert error == "Transcription completed but no text was extracted"

        finally:
            temp_path.unlink()

    def test_transcribe_audio_file_not_found(self):
        """Test transcription with non-existent file."""
        service = TranscriptionService()
        non_existent_path = Path("/tmp/non_existent_file.mp3")

        transcript, error = service.transcribe_audio(non_existent_path)

        assert transcript is None
        assert "Audio file not found" in error

    @patch("yoto_smart_stream.core.transcription.whisper.load_model")
    def test_transcribe_audio_exception(self, mock_load_model):
        """Test transcription with exception."""
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_path = Path(temp_file.name)
            temp_file.write(b"fake audio data")

        try:
            # Mock the Whisper model to raise an exception
            mock_model = MagicMock()
            mock_model.transcribe.side_effect = Exception("Transcription failed")
            mock_load_model.return_value = mock_model

            service = TranscriptionService()
            transcript, error = service.transcribe_audio(temp_path)

            assert transcript is None
            assert "Error transcribing audio" in error

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
    def test_real_transcription(self):
        """
        Test real transcription with actual Whisper model.
        
        This test is skipped by default as it requires:
        - Downloading the Whisper model (~140MB for base model)
        - Significant CPU/GPU time for transcription
        - A real audio file
        
        To run this test, remove the skipif decorator and provide a real audio file.
        """
        service = TranscriptionService(model_name="tiny")  # Use tiny model for faster testing
        
        # Create a test audio file (you would need a real MP3 file here)
        # For now, this is just a placeholder
        test_audio_path = Path("test_audio.mp3")
        
        if test_audio_path.exists():
            transcript, error = service.transcribe_audio(test_audio_path)
            assert transcript is not None or error is not None
