"""
Tests for text-to-speech audio generation endpoint.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yoto_smart_stream.api import app
from yoto_smart_stream.models import AudioFile


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def temp_audio_dir(tmp_path):
    """Create a temporary audio directory for testing."""
    audio_dir = tmp_path / "audio_files"
    audio_dir.mkdir()
    return audio_dir


class TestTTSGeneration:
    """Test text-to-speech generation endpoint."""

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.api.routes.cards.gTTS")
    @patch("yoto_smart_stream.api.routes.cards.AudioSegment")
    def test_generate_tts_success(self, mock_audio_segment, mock_gtts, mock_settings, client, temp_audio_dir):
        """Test successful TTS generation."""
        # Setup mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Setup mock TTS
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance

        # Setup mock AudioSegment
        mock_audio = MagicMock()
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio

        # Mock the export to create an actual file
        def mock_export(path, *args, **kwargs):
            # Create the file
            Path(path).write_bytes(b"fake audio data")

        mock_audio.export.side_effect = mock_export
        mock_audio_segment.from_mp3.return_value = mock_audio

        # Make the request
        response = client.post(
            "/api/audio/generate-tts",
            json={
                "filename": "test-story",
                "text": "This is a test story for text to speech."
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["filename"] == "test-story.mp3"
        assert "url" in data
        assert data["url"] == "/api/audio/test-story.mp3"

        # Verify gTTS was called correctly
        mock_gtts.assert_called_once_with(
            text="This is a test story for text to speech.",
            lang="en",
            slow=False
        )
        mock_tts_instance.save.assert_called_once()

        # Verify audio processing
        mock_audio.set_channels.assert_called_once_with(1)  # Mono
        mock_audio.set_frame_rate.assert_called_once_with(44100)  # 44.1kHz
        mock_audio.export.assert_called_once()

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    def test_generate_tts_file_exists(self, mock_settings, client, temp_audio_dir):
        """Test TTS generation when file already exists."""
        # Setup mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Create existing file
        existing_file = temp_audio_dir / "existing-file.mp3"
        existing_file.write_text("dummy content")

        # Make the request
        response = client.post(
            "/api/audio/generate-tts",
            json={
                "filename": "existing-file",
                "text": "Some text"
            }
        )

        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "already exists" in data["detail"]

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.api.routes.cards.gTTS")
    def test_generate_tts_invalid_filename(self, mock_gtts, mock_settings, client, temp_audio_dir):
        """Test TTS generation with invalid filename."""
        # Setup mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Setup mock TTS - won't be called if filename validation fails
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance

        with patch("yoto_smart_stream.api.routes.cards.AudioSegment") as mock_audio_segment:
            mock_audio = MagicMock()
            mock_audio.set_channels.return_value = mock_audio
            mock_audio.set_frame_rate.return_value = mock_audio

            # Mock export to create file
            def mock_export(path, *args, **kwargs):
                Path(path).write_bytes(b"fake audio data")

            mock_audio.export.side_effect = mock_export
            mock_audio_segment.from_mp3.return_value = mock_audio

            # Test with special characters that should be stripped, resulting in valid filename
            response = client.post(
                "/api/audio/generate-tts",
                json={
                    "filename": "../../../etc/passwd",
                    "text": "Malicious text"
                }
            )

            # The filename gets sanitized to "etcpasswd.mp3" which is valid
            assert response.status_code == 200

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    def test_generate_tts_empty_filename(self, mock_settings, client, temp_audio_dir):
        """Test TTS generation with empty filename after sanitization."""
        # Setup mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Test with filename that becomes empty after sanitization
        response = client.post(
            "/api/audio/generate-tts",
            json={
                "filename": "!@#$%^&*()",
                "text": "Some text"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "Invalid filename" in data["detail"]

    def test_generate_tts_empty_text(self, client):
        """Test TTS generation with empty text."""
        response = client.post(
            "/api/audio/generate-tts",
            json={
                "filename": "test",
                "text": ""
            }
        )

        # Should fail validation
        assert response.status_code == 422

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.api.routes.cards.gTTS")
    def test_generate_tts_removes_mp3_extension(self, mock_gtts, mock_settings, client, temp_audio_dir):
        """Test that .mp3 extension is removed if user provides it."""
        # Setup mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Setup mock TTS
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance

        with patch("yoto_smart_stream.api.routes.cards.AudioSegment") as mock_audio_segment:
            mock_audio = MagicMock()
            mock_audio.set_channels.return_value = mock_audio
            mock_audio.set_frame_rate.return_value = mock_audio

            # Mock export to create file
            def mock_export(path, *args, **kwargs):
                Path(path).write_bytes(b"fake audio data")

            mock_audio.export.side_effect = mock_export
            mock_audio_segment.from_mp3.return_value = mock_audio

            # Request with .mp3 extension
            response = client.post(
                "/api/audio/generate-tts",
                json={
                    "filename": "my-story.mp3",
                    "text": "Test story"
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Should still be my-story.mp3, not my-story.mp3.mp3
            assert data["filename"] == "my-story.mp3"

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.api.routes.cards.gTTS")
    def test_generate_tts_sanitizes_filename(self, mock_gtts, mock_settings, client, temp_audio_dir):
        """Test that filename is properly sanitized."""
        # Setup mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Setup mock TTS
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance

        with patch("yoto_smart_stream.api.routes.cards.AudioSegment") as mock_audio_segment:
            mock_audio = MagicMock()
            mock_audio.set_channels.return_value = mock_audio
            mock_audio.set_frame_rate.return_value = mock_audio

            # Mock export to create file
            def mock_export(path, *args, **kwargs):
                Path(path).write_bytes(b"fake audio data")

            mock_audio.export.side_effect = mock_export
            mock_audio_segment.from_mp3.return_value = mock_audio

            # Request with special characters
            response = client.post(
                "/api/audio/generate-tts",
                json={
                    "filename": "My Story #1 (Final)",
                    "text": "Test story"
                }
            )

            assert response.status_code == 200
            data = response.json()

            # Should be sanitized - spaces converted to hyphens
            assert data["filename"] == "My-Story-1-Final.mp3"

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.api.routes.cards.gTTS")
    def test_generate_tts_handles_generation_error(self, mock_gtts, mock_settings, client, temp_audio_dir):
        """Test TTS generation handles errors gracefully."""
        # Setup mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Setup mock TTS to raise an error
        mock_gtts.side_effect = Exception("TTS service unavailable")

        # Make the request
        response = client.post(
            "/api/audio/generate-tts",
            json={
                "filename": "test-story",
                "text": "This is a test story."
            }
        )

        assert response.status_code == 500
        data = response.json()
        assert "Failed to generate TTS audio" in data["detail"]

    @patch("yoto_smart_stream.api.routes.cards.require_auth")
    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.api.routes.cards.gTTS")
    @patch("yoto_smart_stream.api.routes.cards.AudioSegment")
    @patch("yoto_smart_stream.core.audio_db.get_or_create_audio_file")
    @patch("yoto_smart_stream.core.audio_db.update_transcript")
    def test_generate_tts_creates_transcript(
        self, mock_update_transcript, mock_get_or_create, mock_audio_segment, 
        mock_gtts, mock_settings, mock_require_auth, client, temp_audio_dir
    ):
        """Test that TTS generation creates a transcript in the database."""
        # Mock authentication
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_require_auth.return_value = mock_user
        
        # Setup mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Setup mock TTS
        mock_tts_instance = MagicMock()
        mock_gtts.return_value = mock_tts_instance

        # Setup mock AudioSegment
        mock_audio = MagicMock()
        mock_audio.set_channels.return_value = mock_audio
        mock_audio.set_frame_rate.return_value = mock_audio
        mock_audio.__len__ = MagicMock(return_value=5000)  # 5 seconds

        # Mock the export to create an actual file
        def mock_export(buffer_or_path, *args, **kwargs):
            if hasattr(buffer_or_path, 'write'):
                buffer_or_path.write(b"fake audio data")
            else:
                Path(buffer_or_path).write_bytes(b"fake audio data")

        mock_audio.export.side_effect = mock_export
        mock_audio_segment.from_mp3.return_value = mock_audio

        # Mock database functions
        mock_audio_file = MagicMock(spec=AudioFile)
        mock_get_or_create.return_value = mock_audio_file

        # Make the request
        test_text = "This is a test story for text to speech."
        response = client.post(
            "/api/audio/generate-tts",
            json={
                "filename": "test-story",
                "text": test_text
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify the response includes transcript status
        assert data["transcript_status"] == "completed"

        # Verify that get_or_create_audio_file was called
        mock_get_or_create.assert_called_once()
        call_args = mock_get_or_create.call_args
        # It's called with positional args: db, filename, size, duration
        assert call_args[0][1] == "test-story.mp3"
        assert call_args[0][3] == 5

        # Verify that update_transcript was called with the TTS text
        mock_update_transcript.assert_called_once()
        call_args = mock_update_transcript.call_args
        # It's called with positional args: db, filename, transcript, status, error
        assert call_args[0][1] == "test-story.mp3"
        assert call_args[0][2] == test_text
        assert call_args[0][3] == "completed"
        assert call_args[0][4] is None
