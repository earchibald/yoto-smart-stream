"""
Tests for audio recorder functionality including upload endpoint.
"""

import io
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yoto_smart_stream.api.app import create_app
from yoto_smart_stream.api.routes.user_auth import require_auth
from yoto_smart_stream.models import User


@pytest.fixture
def mock_authenticated_user():
    """Mock an authenticated user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.is_active = True
    user.is_admin = False
    return user


@pytest.fixture
def client(mock_authenticated_user):
    """Create a test client with auth override."""
    app = create_app()
    
    # Override the auth dependency
    def override_require_auth():
        return mock_authenticated_user
    
    app.dependency_overrides[require_auth] = override_require_auth
    
    with TestClient(app) as test_client:
        yield test_client


class TestAudioUploadEndpoint:
    """Test audio upload endpoint for recorder."""

    def test_upload_audio_success(self, client):
        """Test successful audio upload."""
        # Create a simple audio file content (mock WebM data)
        audio_content = b"MOCK_AUDIO_DATA_WEBM_FORMAT"
        
        # Create file upload data
        files = {
            'file': ('recording.webm', io.BytesIO(audio_content), 'audio/webm')
        }
        data = {
            'filename': 'test-recording',
            'description': 'Test description'
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir)
            
            # Mock get_settings to use temp directory
            with patch("yoto_smart_stream.api.routes.cards.get_settings") as mock_settings:
                settings = MagicMock()
                settings.audio_files_dir = audio_dir
                mock_settings.return_value = settings
                
                # Mock pydub AudioSegment to avoid actual audio processing
                with patch("yoto_smart_stream.api.routes.cards.AudioSegment") as mock_audio:
                    mock_segment = MagicMock()
                    mock_segment.set_channels.return_value = mock_segment
                    mock_segment.set_frame_rate.return_value = mock_segment
                    mock_segment.__len__ = lambda self: 5000  # 5 seconds
                    
                    # Mock export to create the file
                    def mock_export(output_path, **kwargs):
                        Path(output_path).write_bytes(b"MOCK_MP3_DATA")
                    
                    mock_segment.export = mock_export
                    mock_audio.from_file.return_value = mock_segment
                    
                    response = client.post(
                        "/api/audio/upload",
                        files=files,
                        data=data
                    )
        
        assert response.status_code == 200
        result = response.json()
        assert result['success'] is True
        assert result['filename'] == 'test-recording.mp3'
        assert 'url' in result

    def test_upload_audio_invalid_filename(self, client):
        """Test upload with invalid filename that becomes empty after sanitization."""
        audio_content = b"MOCK_AUDIO_DATA"
        
        files = {
            'file': ('recording.webm', io.BytesIO(audio_content), 'audio/webm')
        }
        data = {
            'filename': '!!!',  # This will become empty after sanitization
            'description': ''
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir)
            
            with patch("yoto_smart_stream.api.routes.cards.get_settings") as mock_settings:
                settings = MagicMock()
                settings.audio_files_dir = audio_dir
                mock_settings.return_value = settings
                
                response = client.post(
                    "/api/audio/upload",
                    files=files,
                    data=data
                )
        
        assert response.status_code == 400
        assert 'Invalid filename' in response.json()['detail']

    def test_upload_audio_duplicate_filename(self, client):
        """Test upload with duplicate filename."""
        audio_content = b"MOCK_AUDIO_DATA"
        
        files = {
            'file': ('recording.webm', io.BytesIO(audio_content), 'audio/webm')
        }
        data = {
            'filename': 'existing-file',
            'description': ''
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir)
            
            # Create existing file
            existing_file = audio_dir / "existing-file.mp3"
            existing_file.write_text("existing content")
            
            with patch("yoto_smart_stream.api.routes.cards.get_settings") as mock_settings:
                settings = MagicMock()
                settings.audio_files_dir = audio_dir
                mock_settings.return_value = settings
                
                response = client.post(
                    "/api/audio/upload",
                    files=files,
                    data=data
                )
        
        assert response.status_code == 409
        assert 'already exists' in response.json()['detail']

    def test_upload_audio_sanitizes_filename(self, client):
        """Test that special characters in filename are sanitized."""
        audio_content = b"MOCK_AUDIO_DATA"
        
        files = {
            'file': ('recording.webm', io.BytesIO(audio_content), 'audio/webm')
        }
        data = {
            'filename': 'my test recording!',
            'description': ''
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir)
            
            with patch("yoto_smart_stream.api.routes.cards.get_settings") as mock_settings:
                settings = MagicMock()
                settings.audio_files_dir = audio_dir
                mock_settings.return_value = settings
                
                with patch("yoto_smart_stream.api.routes.cards.AudioSegment") as mock_audio:
                    mock_segment = MagicMock()
                    mock_segment.set_channels.return_value = mock_segment
                    mock_segment.set_frame_rate.return_value = mock_segment
                    mock_segment.__len__ = lambda self: 5000
                    
                    def mock_export(output_path, **kwargs):
                        Path(output_path).write_bytes(b"MOCK_MP3_DATA")
                    
                    mock_segment.export = mock_export
                    mock_audio.from_file.return_value = mock_segment
                    
                    response = client.post(
                        "/api/audio/upload",
                        files=files,
                        data=data
                    )
        
        assert response.status_code == 200
        result = response.json()
        # Special chars should be replaced with hyphens
        assert result['filename'] == 'my-test-recording.mp3'

    def test_upload_audio_strips_extension(self, client):
        """Test that .mp3 extension is stripped from filename if provided."""
        audio_content = b"MOCK_AUDIO_DATA"
        
        files = {
            'file': ('recording.webm', io.BytesIO(audio_content), 'audio/webm')
        }
        data = {
            'filename': 'my-recording.mp3',
            'description': ''
        }
        
        with tempfile.TemporaryDirectory() as tmpdir:
            audio_dir = Path(tmpdir)
            
            with patch("yoto_smart_stream.api.routes.cards.get_settings") as mock_settings:
                settings = MagicMock()
                settings.audio_files_dir = audio_dir
                mock_settings.return_value = settings
                
                with patch("yoto_smart_stream.api.routes.cards.AudioSegment") as mock_audio:
                    mock_segment = MagicMock()
                    mock_segment.set_channels.return_value = mock_segment
                    mock_segment.set_frame_rate.return_value = mock_segment
                    mock_segment.__len__ = lambda self: 5000
                    
                    def mock_export(output_path, **kwargs):
                        Path(output_path).write_bytes(b"MOCK_MP3_DATA")
                    
                    mock_segment.export = mock_export
                    mock_audio.from_file.return_value = mock_segment
                    
                    response = client.post(
                        "/api/audio/upload",
                        files=files,
                        data=data
                    )
        
        assert response.status_code == 200
        result = response.json()
        # Should not double the extension
        assert result['filename'] == 'my-recording.mp3'
        assert not result['filename'].endswith('.mp3.mp3')
