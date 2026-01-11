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
         patch("yoto_smart_stream.api.routes.health.get_yoto_client") as mock_health, \
         patch("yoto_smart_stream.api.routes.library.get_yoto_client") as mock_library:
        client = MagicMock()
        client.is_authenticated.return_value = True
        client.get_manager.return_value.players = {}
        mock_players.return_value = client
        mock_health.return_value = client
        mock_library.return_value = client
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


class TestPlayerDataExtraction:
    """Test that player data is correctly extracted from YotoPlayer objects."""

    def test_player_volume_from_mqtt(self, client):
        """Test that player volume is correctly read from MQTT volume attribute."""
        with patch("yoto_smart_stream.api.routes.players.get_yoto_client") as mock_get_client:
            # Create mock player with MQTT volume
            mock_player = MagicMock()
            mock_player.id = "test-player-1"
            mock_player.name = "Test Player"
            mock_player.online = True
            mock_player.volume = 12  # MQTT volume
            mock_player.user_volume = None
            mock_player.playback_status = "playing"
            mock_player.is_playing = None
            mock_player.battery_level_percentage = 85

            # Setup mock client
            mock_client = MagicMock()
            mock_manager = MagicMock()
            mock_manager.players = {"test-player-1": mock_player}
            mock_client.get_manager.return_value = mock_manager
            mock_get_client.return_value = mock_client

            # Call endpoint
            response = client.get("/api/players")
            assert response.status_code == 200

            players = response.json()
            assert len(players) == 1
            assert players[0]["volume"] == 12
            assert players[0]["playing"] is True
            assert players[0]["battery_level"] == 85

    def test_player_volume_fallback_to_user_volume(self, client):
        """Test that player volume falls back to user_volume when MQTT volume is None."""
        with patch("yoto_smart_stream.api.routes.players.get_yoto_client") as mock_get_client:
            # Create mock player with user_volume but no MQTT volume
            mock_player = MagicMock()
            mock_player.id = "test-player-2"
            mock_player.name = "Test Player 2"
            mock_player.online = True
            mock_player.volume = None  # No MQTT volume
            mock_player.user_volume = 10  # User volume
            mock_player.playback_status = None
            mock_player.is_playing = False
            mock_player.battery_level_percentage = None

            # Setup mock client
            mock_client = MagicMock()
            mock_manager = MagicMock()
            mock_manager.players = {"test-player-2": mock_player}
            mock_client.get_manager.return_value = mock_manager
            mock_get_client.return_value = mock_client

            # Call endpoint
            response = client.get("/api/players")
            assert response.status_code == 200

            players = response.json()
            assert len(players) == 1
            assert players[0]["volume"] == 10
            assert players[0]["playing"] is False

    def test_player_playback_status_parsing(self, client):
        """Test that playback_status string is correctly parsed to boolean."""
        with patch("yoto_smart_stream.api.routes.players.get_yoto_client") as mock_get_client:
            # Create mock players with different playback statuses
            mock_player1 = MagicMock()
            mock_player1.id = "player-playing"
            mock_player1.name = "Playing Player"
            mock_player1.online = True
            mock_player1.volume = 8
            mock_player1.user_volume = None
            mock_player1.playback_status = "playing"
            mock_player1.is_playing = None
            mock_player1.battery_level_percentage = None

            mock_player2 = MagicMock()
            mock_player2.id = "player-paused"
            mock_player2.name = "Paused Player"
            mock_player2.online = True
            mock_player2.volume = 8
            mock_player2.user_volume = None
            mock_player2.playback_status = "paused"
            mock_player2.is_playing = None
            mock_player2.battery_level_percentage = None

            mock_player3 = MagicMock()
            mock_player3.id = "player-stopped"
            mock_player3.name = "Stopped Player"
            mock_player3.online = True
            mock_player3.volume = 8
            mock_player3.user_volume = None
            mock_player3.playback_status = "stopped"
            mock_player3.is_playing = None
            mock_player3.battery_level_percentage = None

            # Setup mock client
            mock_client = MagicMock()
            mock_manager = MagicMock()
            mock_manager.players = {
                "player-playing": mock_player1,
                "player-paused": mock_player2,
                "player-stopped": mock_player3,
            }
            mock_client.get_manager.return_value = mock_manager
            mock_get_client.return_value = mock_client

            # Call endpoint
            response = client.get("/api/players")
            assert response.status_code == 200

            players = response.json()
            assert len(players) == 3

            # Find each player and check their playing status
            playing_player = next(p for p in players if p["id"] == "player-playing")
            assert playing_player["playing"] is True

            paused_player = next(p for p in players if p["id"] == "player-paused")
            assert paused_player["playing"] is False

            stopped_player = next(p for p in players if p["id"] == "player-stopped")
            assert stopped_player["playing"] is False

    def test_player_is_playing_fallback(self, client):
        """Test that is_playing boolean is used when playback_status is None."""
        with patch("yoto_smart_stream.api.routes.players.get_yoto_client") as mock_get_client:
            # Create mock player with is_playing but no playback_status
            mock_player = MagicMock()
            mock_player.id = "test-player-3"
            mock_player.name = "Test Player 3"
            mock_player.online = True
            mock_player.volume = 8
            mock_player.user_volume = None
            mock_player.playback_status = None  # No MQTT playback_status
            mock_player.is_playing = True  # API is_playing
            mock_player.battery_level_percentage = None

            # Setup mock client
            mock_client = MagicMock()
            mock_manager = MagicMock()
            mock_manager.players = {"test-player-3": mock_player}
            mock_client.get_manager.return_value = mock_manager
            mock_get_client.return_value = mock_client

            # Call endpoint
            response = client.get("/api/players")
            assert response.status_code == 200

            players = response.json()
            assert len(players) == 1
            assert players[0]["playing"] is True

    def test_player_volume_range_0_to_100(self, client):
        """Test that player volume accepts values in 0-100 range (API range, not hardware 0-16)."""
        with patch("yoto_smart_stream.api.routes.players.get_yoto_client") as mock_get_client:
            # Create mock player with volume=50 (the value that was causing ValidationError)
            mock_player = MagicMock()
            mock_player.id = "test-player-volume"
            mock_player.name = "Test Player Volume"
            mock_player.online = True
            mock_player.volume = 50  # API volume range (0-100), not hardware range (0-16)
            mock_player.user_volume = None
            mock_player.playback_status = None
            mock_player.is_playing = False
            mock_player.battery_level_percentage = None

            # Setup mock client
            mock_client = MagicMock()
            mock_manager = MagicMock()
            mock_manager.players = {"test-player-volume": mock_player}
            mock_client.get_manager.return_value = mock_manager
            mock_get_client.return_value = mock_client

            # Call endpoint - should NOT raise ValidationError
            response = client.get("/api/players")
            assert response.status_code == 200

            players = response.json()
            assert len(players) == 1
            assert players[0]["volume"] == 50

    def test_player_volume_boundary_values(self, client):
        """Test that player volume accepts boundary values (0, 100)."""
        with patch("yoto_smart_stream.api.routes.players.get_yoto_client") as mock_get_client:
            # Create mock players with boundary volume values
            mock_player1 = MagicMock()
            mock_player1.id = "player-vol-0"
            mock_player1.name = "Volume 0"
            mock_player1.online = True
            mock_player1.volume = 0
            mock_player1.user_volume = None
            mock_player1.playback_status = None
            mock_player1.is_playing = False
            mock_player1.battery_level_percentage = None

            mock_player2 = MagicMock()
            mock_player2.id = "player-vol-100"
            mock_player2.name = "Volume 100"
            mock_player2.online = True
            mock_player2.volume = 100
            mock_player2.user_volume = None
            mock_player2.playback_status = None
            mock_player2.is_playing = False
            mock_player2.battery_level_percentage = None

            # Setup mock client
            mock_client = MagicMock()
            mock_manager = MagicMock()
            mock_manager.players = {
                "player-vol-0": mock_player1,
                "player-vol-100": mock_player2,
            }
            mock_client.get_manager.return_value = mock_manager
            mock_get_client.return_value = mock_client

            # Call endpoint - should accept both boundary values
            response = client.get("/api/players")
            assert response.status_code == 200

            players = response.json()
            assert len(players) == 2

            vol_0_player = next(p for p in players if p["id"] == "player-vol-0")
            assert vol_0_player["volume"] == 0

            vol_100_player = next(p for p in players if p["id"] == "player-vol-100")
            assert vol_100_player["volume"] == 100



class TestLibraryEndpoints:
    """Test library viewing endpoints."""

    def test_library_ui_serves_html(self, client):
        """Test /library endpoint serves HTML."""
        response = client.get("/library")
        assert response.status_code == 200
        # Check if response is HTML
        content_type = response.headers.get("content-type", "")
        assert "text/html" in content_type or response.text.startswith("<!DOCTYPE html>")

    def test_library_api_not_authenticated(self, client):
        """Test /api/library returns 401 when not authenticated."""
        with patch("yoto_smart_stream.api.routes.library.get_yoto_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.get_manager.side_effect = RuntimeError("Not authenticated")
            mock_get_client.return_value = mock_client
            
            response = client.get("/api/library")
            assert response.status_code == 401
            data = response.json()
            assert "detail" in data

    def test_library_api_returns_cards_and_playlists(self, client):
        """Test /api/library returns cards and playlists data."""
        with patch("yoto_smart_stream.api.routes.library.get_yoto_client") as mock_get_client, \
             patch("yoto_smart_stream.api.routes.library.requests") as mock_requests:
            # Create mock card (Card dataclass)
            mock_card = MagicMock()
            mock_card.id = "card-123"
            mock_card.title = "Test Card"
            mock_card.description = "A test card"
            mock_card.author = "Test Author"
            mock_card.cover_image_large = "https://example.com/image.jpg"
            
            # Setup mock client
            mock_client = MagicMock()
            mock_manager = MagicMock()
            
            # Setup library as a dictionary (how yoto_api actually works)
            mock_manager.library = {"card-123": mock_card}
            
            # Setup token with token_type (as yoto_api Token object has)
            mock_token = MagicMock()
            mock_token.access_token = "test_token"
            mock_token.token_type = "Bearer"
            mock_manager.token = mock_token
            
            # Mock requests.get for /groups endpoint
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = [
                {
                    'id': 'group-456',
                    'name': 'Test Playlist',
                    'imageId': 'fp-cards',
                    'items': [{'contentId': 'card-1'}, {'contentId': 'card-2'}]
                }
            ]
            mock_requests.get.return_value = mock_response
            
            mock_client.get_manager.return_value = mock_manager
            mock_get_client.return_value = mock_client
            
            response = client.get("/api/library")
            assert response.status_code == 200
            
            data = response.json()
            assert "cards" in data
            assert "playlists" in data
            assert "totalCards" in data
            assert "totalPlaylists" in data
            
            # Check card data
            assert len(data["cards"]) == 1
            card = data["cards"][0]
            assert card["id"] == "card-123"
            assert card["title"] == "Test Card"
            assert card["author"] == "Test Author"
            assert card["cover"] == "https://example.com/image.jpg"
            
            # Check playlist data (now fetched from /groups endpoint)
            assert len(data["playlists"]) == 1
            playlist = data["playlists"][0]
            assert playlist["id"] == "group-456"
            assert playlist["name"] == "Test Playlist"
            assert playlist["itemCount"] == 2

    def test_library_api_handles_empty_library(self, client):
        """Test /api/library handles empty library gracefully."""
        with patch("yoto_smart_stream.api.routes.library.get_yoto_client") as mock_get_client, \
             patch("yoto_smart_stream.api.routes.library.requests") as mock_requests:
            mock_client = MagicMock()
            mock_manager = MagicMock()
            
            # Empty library dictionary
            mock_manager.library = {}
            
            # Setup token with token_type (as yoto_api Token object has)
            mock_token = MagicMock()
            mock_token.access_token = "test_token"
            mock_token.token_type = "Bearer"
            mock_manager.token = mock_token
            
            # Mock empty groups response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_requests.get.return_value = mock_response
            
            mock_client.get_manager.return_value = mock_manager
            mock_get_client.return_value = mock_client
            
            response = client.get("/api/library")
            assert response.status_code == 200
            
            data = response.json()
            assert data["totalCards"] == 0
            assert data["totalPlaylists"] == 0
