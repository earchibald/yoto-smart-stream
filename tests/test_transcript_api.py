"""
Tests for transcript API endpoints.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile

import pytest
from fastapi.testclient import TestClient

from yoto_smart_stream.api import app
from yoto_smart_stream.api.routes.user_auth import require_auth
from yoto_smart_stream.models import AudioFile, User


def mock_authenticated_user():
    """Mock an authenticated user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.is_active = True
    user.is_admin = False
    return user


@pytest.fixture
def client():
    """Create a test client with mocked authentication."""
    # Override the auth dependency
    def override_require_auth():
        return mock_authenticated_user()
    
    app.dependency_overrides[require_auth] = override_require_auth
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Clean up
    app.dependency_overrides.clear()


@pytest.fixture
def temp_audio_dir(tmp_path):
    """Create a temporary audio directory for testing."""
    audio_dir = tmp_path / "audio_files"
    audio_dir.mkdir()
    return audio_dir


class TestTranscriptEndpoints:
    """Test transcript API endpoints."""

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.core.audio_db.get_audio_file_by_filename")
    def test_get_transcript_success(self, mock_get_audio, mock_settings, client):
        """Test successful transcript retrieval."""
        # Mock audio file with transcript
        mock_audio = MagicMock(spec=AudioFile)
        mock_audio.filename = "test.mp3"
        mock_audio.transcript = "This is a test transcript."
        mock_audio.transcript_status = "completed"
        mock_audio.transcript_error = None
        mock_audio.transcribed_at = None
        mock_get_audio.return_value = mock_audio

        response = client.get("/api/audio/test.mp3/transcript")

        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "test.mp3"
        assert data["transcript"] == "This is a test transcript."
        assert data["status"] == "completed"
        assert data["error"] is None

    @patch("yoto_smart_stream.core.audio_db.get_audio_file_by_filename")
    def test_get_transcript_not_found(self, mock_get_audio, client):
        """Test transcript retrieval for non-existent file."""
        mock_get_audio.return_value = None

        response = client.get("/api/audio/nonexistent.mp3/transcript")

        assert response.status_code == 404
        assert "No transcript record found" in response.json()["detail"]

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.core.transcription.get_transcription_service")
    @patch("yoto_smart_stream.core.audio_db.get_or_create_audio_file")
    @patch("yoto_smart_stream.core.audio_db.update_transcript")
    @patch("yoto_smart_stream.api.routes.cards.AudioSegment")
    def test_trigger_transcription_success(
        self,
        mock_audio_segment,
        mock_update_transcript,
        mock_get_or_create,
        mock_get_service,
        mock_settings,
        client,
        temp_audio_dir,
    ):
        """Test successful transcription trigger."""
        # Create a test audio file
        test_file = temp_audio_dir / "test.mp3"
        test_file.write_bytes(b"fake audio data")

        # Mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Mock audio segment
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=5000)  # 5 seconds
        mock_audio_segment.from_mp3.return_value = mock_audio

        # Mock transcription service
        mock_service = MagicMock()
        mock_service.transcribe_audio.return_value = ("This is a test transcript.", None)
        mock_get_service.return_value = mock_service

        # Mock database functions
        mock_audio_record = MagicMock(spec=AudioFile)
        mock_get_or_create.return_value = mock_audio_record

        response = client.post("/api/audio/test.mp3/transcribe")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "completed"
        assert data["transcript_length"] == 26

        # Verify transcription was called
        mock_service.transcribe_audio.assert_called_once()

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    def test_trigger_transcription_file_not_found(
        self, mock_settings, client, temp_audio_dir
    ):
        """Test transcription trigger for non-existent file."""
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        response = client.post("/api/audio/nonexistent.mp3/transcribe")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @patch("yoto_smart_stream.api.routes.cards.get_settings")
    @patch("yoto_smart_stream.core.transcription.get_transcription_service")
    @patch("yoto_smart_stream.core.audio_db.get_or_create_audio_file")
    @patch("yoto_smart_stream.core.audio_db.update_transcript")
    @patch("yoto_smart_stream.api.routes.cards.AudioSegment")
    def test_trigger_transcription_error(
        self,
        mock_audio_segment,
        mock_update_transcript,
        mock_get_or_create,
        mock_get_service,
        mock_settings,
        client,
        temp_audio_dir,
    ):
        """Test transcription trigger with error."""
        # Create a test audio file
        test_file = temp_audio_dir / "test.mp3"
        test_file.write_bytes(b"fake audio data")

        # Mock settings
        mock_settings_obj = MagicMock()
        mock_settings_obj.audio_files_dir = temp_audio_dir
        mock_settings.return_value = mock_settings_obj

        # Mock audio segment
        mock_audio = MagicMock()
        mock_audio.__len__ = MagicMock(return_value=5000)
        mock_audio_segment.from_mp3.return_value = mock_audio

        # Mock transcription service to return error
        mock_service = MagicMock()
        mock_service.transcribe_audio.return_value = (None, "Transcription failed")
        mock_get_service.return_value = mock_service

        # Mock database functions
        mock_audio_record = MagicMock(spec=AudioFile)
        mock_get_or_create.return_value = mock_audio_record

        response = client.post("/api/audio/test.mp3/transcribe")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert data["status"] == "error"
        assert "Transcription failed" in data["error"]
