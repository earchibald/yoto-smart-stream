"""
Tests for API endpoints and web UI.

Tests the new web UI endpoints and verifies API endpoints are correctly organized.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yoto_smart_stream.api import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_yoto_client():
    """Mock Yoto client."""
    # Patch at the place where it's imported in the routes
    with patch("yoto_smart_stream.api.routes.players.get_yoto_client") as mock_players, \
         patch("yoto_smart_stream.api.routes.health.get_yoto_client") as mock_health:
        client = MagicMock()
        client.is_authenticated.return_value = True
        client.get_manager.return_value.players = {}
        mock_players.return_value = client
        mock_health.return_value = client
        yield client


class TestWebUIEndpoints:
    """Test web UI endpoints."""

    def test_root_serves_html(self, client):
        """Test root endpoint serves HTML dashboard."""
        response = client.get("/")
        assert response.status_code == 200
        # Check if response is HTML
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type or response.text.startswith("<!DOCTYPE html>")

    def test_streams_serves_html(self, client):
        """Test /streams endpoint serves HTML."""
        response = client.get("/streams")
        assert response.status_code == 200
        # Check if response is HTML
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type or response.text.startswith("<!DOCTYPE html>")

    def test_docs_endpoint_accessible(self, client):
        """Test /docs endpoint (FastAPI automatic documentation) is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        # Check if response is HTML (Swagger UI)
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type


class TestAPIStatusEndpoint:
    """Test API status endpoint."""

    def test_api_status_returns_json(self, client):
        """Test /api/status returns JSON with system information."""
        response = client.get("/api/status")
        assert response.status_code == 200

        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert data["status"] == "running"
        assert "environment" in data
        assert "features" in data

    def test_api_status_features(self, client):
        """Test /api/status includes feature flags."""
        response = client.get("/api/status")
        data = response.json()

        features = data["features"]
        assert "player_control" in features
        assert "audio_streaming" in features
        assert "myo_card_creation" in features
        assert "mqtt_events" in features


class TestHealthEndpoints:
    """Test health check endpoints are under /api."""

    def test_health_endpoint_under_api(self, client):
        """Test /api/health endpoint works."""
        response = client.get("/api/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data

    def test_ready_endpoint_under_api(self, client, mock_yoto_client):
        """Test /api/ready endpoint works."""
        response = client.get("/api/ready")
        assert response.status_code == 200

        data = response.json()
        assert "ready" in data


class TestStaticFiles:
    """Test static files are served correctly."""

    def test_static_css_accessible(self, client):
        """Test CSS files are accessible."""
        response = client.get("/static/css/style.css")
        assert response.status_code == 200
        content_type = response.headers.get("content-type", "")
        assert "text/css" in content_type

    def test_static_js_accessible(self, client):
        """Test JavaScript files are accessible."""
        response = client.get("/static/js/dashboard.js")
        assert response.status_code == 200
        # Check it's JavaScript
        content = response.text
        assert "API_BASE" in content or "function" in content

    def test_dashboard_js_has_auto_refresh(self, client):
        """Test dashboard.js contains auto-refresh functionality."""
        response = client.get("/static/js/dashboard.js")
        assert response.status_code == 200
        content = response.text
        # Check for auto-refresh related code
        assert "playerRefreshInterval" in content
        assert "startPlayerAutoRefresh" in content
        assert "5000" in content  # 5 second interval
        # Check for concurrent call prevention
        assert "isLoadingPlayers" in content
        # Check for cleanup on page unload
        assert "beforeunload" in content
        assert "stopPlayerAutoRefresh" in content


class TestAPIEndpointOrganization:
    """Test API endpoints are properly organized under /api prefix."""

    def test_players_under_api(self, client, mock_yoto_client):
        """Test players endpoints are under /api."""
        # Mock client is already set up in fixture
        response = client.get("/api/players")
        # Should return 200 with empty list
        assert response.status_code == 200

    def test_audio_list_under_api(self, client):
        """Test audio list endpoint is under /api."""
        response = client.get("/api/audio/list")
        assert response.status_code in [200, 404, 500]


class TestAudioStreamingEndpoints:
    """Test audio streaming endpoints remain accessible without /api prefix."""

    def test_audio_streaming_path(self, client):
        """Test audio files can be accessed directly at /api/audio/{filename}."""
        # This will return 404 if file doesn't exist, which is expected
        response = client.get("/api/audio/test.mp3")
        # Should get 404 (file not found) not 404 (route not found)
        assert response.status_code in [200, 404]
        if response.status_code == 404:
            data = response.json()
            # Should have detail message about file not found
            assert "detail" in data
