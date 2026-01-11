"""
Tests for OAuth token persistence after refresh.

Ensures that new refresh tokens are saved to file after token refresh operations.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from yoto_smart_stream.config import Settings
from yoto_smart_stream.core import YotoClient


@pytest.fixture
def temp_token_file():
    """Create a temporary token file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.token') as f:
        token_file = Path(f.name)
        f.write("old_refresh_token_123")

    yield token_file

    # Cleanup
    if token_file.exists():
        token_file.unlink()


@pytest.fixture
def mock_settings(temp_token_file):
    """Create mock settings with temporary token file."""
    settings = MagicMock(spec=Settings)
    settings.yoto_client_id = "test_client_id"
    settings.yoto_refresh_token_file = temp_token_file
    return settings


@pytest.fixture
def mock_token():
    """Create a mock Token object."""
    token = MagicMock()
    token.refresh_token = "new_refresh_token_456"
    token.access_token = "access_token_789"
    return token


def test_authenticate_saves_new_refresh_token(mock_settings, temp_token_file, mock_token):
    """Test that authenticate() saves the new refresh token after successful authentication."""
    client = YotoClient(mock_settings)

    # Mock the YotoManager
    with patch('yoto_smart_stream.core.yoto_client.YotoManager') as MockManager:
        mock_manager = MagicMock()
        mock_manager.token = mock_token
        MockManager.return_value = mock_manager

        # Call authenticate
        client.authenticate()

        # Verify manager was initialized
        MockManager.assert_called_once_with(client_id="test_client_id")

        # Verify check_and_refresh_token was called
        mock_manager.check_and_refresh_token.assert_called_once()

        # Verify the NEW refresh token was saved to file
        saved_token = temp_token_file.read_text()
        assert saved_token == "new_refresh_token_456", \
            "New refresh token should be saved to file after authentication"

        # Verify client is authenticated
        assert client.is_authenticated()


def test_ensure_authenticated_saves_new_refresh_token_on_refresh(mock_settings, temp_token_file, mock_token):
    """Test that ensure_authenticated() saves the new refresh token after successful refresh."""
    client = YotoClient(mock_settings)

    # Mock the YotoManager
    with patch('yoto_smart_stream.core.yoto_client.YotoManager') as MockManager:
        mock_manager = MagicMock()
        mock_manager.token = mock_token
        MockManager.return_value = mock_manager

        # Set up client as already authenticated
        client.manager = mock_manager
        client._authenticated = True

        # Call ensure_authenticated (should trigger refresh)
        client.ensure_authenticated()

        # Verify check_and_refresh_token was called
        mock_manager.check_and_refresh_token.assert_called_once()

        # Verify the NEW refresh token was saved to file
        saved_token = temp_token_file.read_text()
        assert saved_token == "new_refresh_token_456", \
            "New refresh token should be saved to file after token refresh"


def test_ensure_authenticated_saves_token_after_full_reauth_on_error(mock_settings, temp_token_file, mock_token):
    """Test that ensure_authenticated() saves token after full re-authentication on refresh error."""
    client = YotoClient(mock_settings)

    # Mock the YotoManager
    with patch('yoto_smart_stream.core.yoto_client.YotoManager') as MockManager:
        mock_manager = MagicMock()
        mock_manager.token = mock_token
        MockManager.return_value = mock_manager

        # Set up client as already authenticated
        client.manager = mock_manager
        client._authenticated = True

        # Make check_and_refresh_token fail first time, succeed second time
        call_count = 0
        def check_and_refresh_side_effect():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Token refresh failed")
            # Second call succeeds (during re-authentication)
            return None

        mock_manager.check_and_refresh_token.side_effect = check_and_refresh_side_effect

        # Call ensure_authenticated
        client.ensure_authenticated()

        # Verify check_and_refresh_token was called twice (once for refresh, once for re-auth)
        assert mock_manager.check_and_refresh_token.call_count >= 1

        # Verify the NEW refresh token was saved to file
        saved_token = temp_token_file.read_text()
        assert saved_token == "new_refresh_token_456", \
            "New refresh token should be saved to file after re-authentication"


def test_save_refresh_token_logs_warning_when_no_token(mock_settings, caplog):
    """Test that _save_refresh_token() logs warning when no token is available."""
    client = YotoClient(mock_settings)

    # Mock manager with no token
    client.manager = MagicMock()
    client.manager.token = None

    # Call _save_refresh_token
    client._save_refresh_token()

    # Verify warning was logged
    assert "No refresh token available to save" in caplog.text


def test_save_refresh_token_creates_parent_directory(mock_settings):
    """Test that _save_refresh_token() creates parent directory if it doesn't exist."""
    # Create a path in a non-existent directory
    with tempfile.TemporaryDirectory() as tmpdir:
        token_file = Path(tmpdir) / "subdir" / "another" / ".token"
        mock_settings.yoto_refresh_token_file = token_file

        client = YotoClient(mock_settings)

        # Mock manager with token
        mock_token = MagicMock()
        mock_token.refresh_token = "test_token"
        client.manager = MagicMock()
        client.manager.token = mock_token

        # Call _save_refresh_token
        client._save_refresh_token()

        # Verify parent directory was created
        assert token_file.parent.exists()
        assert token_file.exists()
        assert token_file.read_text() == "test_token"


def test_periodic_refresh_persists_tokens(mock_settings, temp_token_file, mock_token):
    """
    Integration test: Verify that periodic token refresh saves new refresh tokens.

    This simulates the background refresh task scenario.
    """
    client = YotoClient(mock_settings)

    # Mock the YotoManager
    with patch('yoto_smart_stream.core.yoto_client.YotoManager') as MockManager:
        mock_manager = MagicMock()

        # Simulate token changing on each refresh
        refresh_tokens = ["token_0", "token_1", "token_2"]
        token_index = [0]  # Use list to allow modification in nested function

        def check_and_refresh_side_effect():
            # Simulate token rotation - each refresh gets a new token
            if token_index[0] < len(refresh_tokens) - 1:
                token_index[0] += 1
            # Update the token on the manager
            token = MagicMock()
            token.refresh_token = refresh_tokens[token_index[0]]
            token.access_token = f"access_{token_index[0]}"
            mock_manager.token = token

        # Set up manager with initial token
        initial_token = MagicMock()
        initial_token.refresh_token = refresh_tokens[0]
        initial_token.access_token = "access_0"
        mock_manager.token = initial_token
        mock_manager.check_and_refresh_token.side_effect = check_and_refresh_side_effect
        MockManager.return_value = mock_manager

        # Initial authentication
        client.authenticate()
        # After first authenticate() call, check_and_refresh_token is called once, so token_index is now 1
        assert temp_token_file.read_text() == "token_1"

        # First refresh (simulating periodic task)
        client.ensure_authenticated()
        assert temp_token_file.read_text() == "token_2", \
            "Token should be updated after first refresh"
