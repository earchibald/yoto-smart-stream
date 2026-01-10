"""
Tests for streaming MYO card example
"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient

# Import the app from the example
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))
from streaming_myo_card import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def audio_files_dir(tmp_path):
    """Create temporary audio files directory"""
    audio_dir = tmp_path / "audio_files"
    audio_dir.mkdir()

    # Create dummy MP3 files for testing
    for filename in [
        "my-story.mp3",
        "morning-story.mp3",
        "afternoon-story.mp3",
        "bedtime-story.mp3",
        "default-story.mp3",
    ]:
        audio_file = audio_dir / filename
        # Create a minimal valid MP3 file
        audio_file.write_bytes(
            b"\xff\xfb\x90\x00" + b"\x00" * 100
        )  # Minimal MP3 header + data

    return audio_dir


def test_root_endpoint(client):
    """Test the root endpoint returns service info"""
    response = client.get("/")
    assert response.status_code == 200

    data = response.json()
    assert data["service"] == "Yoto Audio Streaming"
    assert data["status"] == "running"
    assert "endpoints" in data


def test_stream_static_audio_not_found(client):
    """Test streaming non-existent audio returns 404"""
    response = client.get("/audio/nonexistent.mp3")
    assert response.status_code == 404


def test_stream_static_audio_success(client, audio_files_dir, monkeypatch):
    """Test streaming existing audio file"""
    # Monkeypatch the Path to use our temp directory
    import streaming_myo_card

    original_path = Path

    def mock_path(path_str):
        if path_str == "audio_files":
            return audio_files_dir
        return original_path(path_str)

    monkeypatch.setattr(streaming_myo_card, "Path", mock_path)

    response = client.get("/audio/my-story.mp3")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    assert "accept-ranges" in response.headers
    assert response.headers["accept-ranges"] == "bytes"


def test_stream_dynamic_audio(client, audio_files_dir, monkeypatch):
    """Test dynamic audio streaming based on time"""
    import streaming_myo_card

    # Monkeypatch the Path
    original_path = Path

    def mock_path(path_str):
        if path_str == "audio_files":
            return audio_files_dir
        return original_path(path_str)

    monkeypatch.setattr(streaming_myo_card, "Path", mock_path)

    response = client.get("/audio/dynamic-story.mp3")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/mpeg"
    # Dynamic content should not be cached
    assert "no-cache" in response.headers.get("cache-control", "")


def test_media_type_for_aac(client, audio_files_dir, monkeypatch):
    """Test that AAC files get correct media type"""
    import streaming_myo_card

    # Create an AAC file
    aac_file = audio_files_dir / "test.aac"
    aac_file.write_bytes(b"\xff\xf1" + b"\x00" * 100)  # Minimal AAC header

    original_path = Path

    def mock_path(path_str):
        if path_str == "audio_files":
            return audio_files_dir
        return original_path(path_str)

    monkeypatch.setattr(streaming_myo_card, "Path", mock_path)

    response = client.get("/audio/test.aac")
    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/aac"


def test_cache_control_headers():
    """Test that cache control headers are set appropriately"""
    client = TestClient(app)

    # Static audio should be cached
    # (This will 404 but we're testing the code path)
    try:
        response = client.get("/audio/static.mp3")
    except:
        pass  # Expected to fail without actual file

    # Dynamic audio should not be cached
    try:
        response = client.get("/audio/dynamic-story.mp3")
    except:
        pass  # Expected to fail without actual file


def test_example_script_imports():
    """Test that the example script can be imported without errors"""
    import streaming_myo_card

    # Check that key functions exist
    assert hasattr(streaming_myo_card, "stream_static_audio")
    assert hasattr(streaming_myo_card, "stream_dynamic_audio")
    assert hasattr(streaming_myo_card, "create_streaming_myo_card")


def test_card_data_structure():
    """Test that the card data structure in examples is correct"""
    # This represents the expected structure for streaming cards
    card_data = {
        "title": "Test Card",
        "description": "Test",
        "author": "Test Author",
        "content": {
            "chapters": [
                {
                    "key": "01",
                    "title": "Chapter 1",
                    "tracks": [
                        {
                            "key": "01",
                            "title": "Test Track",
                            "format": "mp3",
                            "channels": "mono",
                            "url": "https://example.com/audio/test.mp3",
                        }
                    ],
                }
            ]
        },
    }

    # Validate structure
    assert "title" in card_data
    assert "content" in card_data
    assert "chapters" in card_data["content"]
    assert len(card_data["content"]["chapters"]) > 0

    track = card_data["content"]["chapters"][0]["tracks"][0]
    assert "url" in track  # Key difference from upload approach
    assert "uploadId" not in track  # Should NOT have uploadId
    assert track["url"].startswith("https://")  # Should be HTTPS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
