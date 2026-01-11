"""
Integration tests for example scripts.

These tests verify that examples can be imported and basic functionality works.
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Add examples directory to path
examples_dir = Path(__file__).parent.parent / "examples"
sys.path.insert(0, str(examples_dir))


class TestSimpleClientImports:
    """Test that simple_client.py can be imported."""

    def test_import_simple_client(self):
        """Test that simple_client module can be imported."""
        # This will fail if there are syntax errors or missing imports
        import simple_client

        assert simple_client is not None


class TestBasicServerImports:
    """Test that basic_server.py can be imported and app is created."""

    def test_import_basic_server(self):
        """Test that basic_server module can be imported."""
        import basic_server

        assert basic_server is not None
        assert basic_server.app is not None

    def test_app_routes_exist(self):
        """Test that expected API routes exist."""
        import basic_server

        # Get all routes
        routes = [route.path for route in basic_server.app.routes]

        assert "/" in routes
        assert "/api/players" in routes
        assert "/api/players/{player_id}" in routes
        assert "/api/players/{player_id}/control" in routes
        assert "/api/health" in routes


class TestMQTTListenerImports:
    """Test that mqtt_listener.py can be imported."""

    def test_import_mqtt_listener(self):
        """Test that mqtt_listener module can be imported."""
        import mqtt_listener

        assert mqtt_listener is not None
        assert hasattr(mqtt_listener, "EventLogger")


class TestIconManagementImports:
    """Test that icon_management.py can be imported."""

    def test_import_icon_management(self):
        """Test that icon_management module can be imported."""
        import icon_management

        assert icon_management is not None
        assert hasattr(icon_management, "main")


class TestBasicServerStartup:
    """Test basic server startup without credentials."""

    def test_health_endpoint_without_auth(self):
        """Test health endpoint works without authentication."""
        import basic_server
        from fastapi.testclient import TestClient

        # Clear any existing yoto_manager
        basic_server.yoto_manager = None

        with TestClient(basic_server.app) as client:
            response = client.get("/api/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    def test_root_endpoint(self):
        """Test root endpoint serves HTML."""
        import basic_server
        from fastapi.testclient import TestClient

        with TestClient(basic_server.app) as client:
            response = client.get("/")
            assert response.status_code == 200
            # Root now serves HTML, so we check for that
            # It may return a fallback JSON if static files don't exist
            if "text/html" in response.headers.get("content-type", ""):
                # HTML response
                assert response.text
            else:
                # Fallback JSON response
                data = response.json()
                assert "message" in data or "name" in data


class TestExampleFunctions:
    """Test individual functions from examples."""

    def test_event_logger_creation(self):
        """Test EventLogger can be created."""
        import mqtt_listener

        logger = mqtt_listener.EventLogger(log_to_file=False)
        assert logger is not None
        assert logger.event_count == 0

    def test_event_logger_log_event(self):
        """Test EventLogger.log_event works."""
        import mqtt_listener

        logger = mqtt_listener.EventLogger(log_to_file=False)

        # Log a test event
        with patch("builtins.print"):  # Suppress output
            logger.log_event("test/topic", {"key": "value"})

        assert logger.event_count == 1
