"""
Tests for background token refresh functionality.

Tests the periodic token refresh task that keeps OAuth tokens valid.
"""

import asyncio
from unittest.mock import MagicMock

import pytest

from yoto_smart_stream.api.app import periodic_token_refresh
from yoto_smart_stream.core import YotoClient


@pytest.fixture
def mock_yoto_client():
    """Create a mock YotoClient."""
    client = MagicMock(spec=YotoClient)
    client.is_authenticated.return_value = True
    client.ensure_authenticated = MagicMock()
    return client


@pytest.mark.asyncio
async def test_periodic_token_refresh_success(mock_yoto_client):
    """Test that token refresh task successfully refreshes tokens."""
    # We'll run the task for a very short interval and then cancel it
    task = asyncio.create_task(periodic_token_refresh(mock_yoto_client, interval_hours=0.0001))

    # Wait a bit for at least one refresh cycle
    await asyncio.sleep(0.5)

    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Verify ensure_authenticated was called
    assert mock_yoto_client.ensure_authenticated.call_count >= 1


@pytest.mark.asyncio
async def test_periodic_token_refresh_handles_errors(mock_yoto_client):
    """Test that token refresh task handles errors gracefully."""
    # Make ensure_authenticated raise an error
    mock_yoto_client.ensure_authenticated.side_effect = Exception("Refresh failed")

    # Run the task for a short time
    task = asyncio.create_task(periodic_token_refresh(mock_yoto_client, interval_hours=0.0001))

    # Wait a bit for at least one refresh cycle
    await asyncio.sleep(0.5)

    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # Task should continue running despite errors
    assert mock_yoto_client.ensure_authenticated.call_count >= 1


@pytest.mark.asyncio
async def test_periodic_token_refresh_skips_if_not_authenticated(mock_yoto_client):
    """Test that token refresh is skipped if client is not authenticated."""
    mock_yoto_client.is_authenticated.return_value = False

    # Run the task for a short time
    task = asyncio.create_task(periodic_token_refresh(mock_yoto_client, interval_hours=0.0001))

    # Wait a bit
    await asyncio.sleep(0.5)

    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    # ensure_authenticated should not be called since client is not authenticated
    assert mock_yoto_client.ensure_authenticated.call_count == 0


@pytest.mark.asyncio
async def test_periodic_token_refresh_respects_interval():
    """Test that token refresh respects the configured interval."""
    mock_client = MagicMock(spec=YotoClient)
    mock_client.is_authenticated.return_value = True
    mock_client.ensure_authenticated = MagicMock()

    # Use a very small interval for testing (0.001 hours = 3.6 seconds)
    task = asyncio.create_task(periodic_token_refresh(mock_client, interval_hours=0.001))

    # Wait less than one interval
    await asyncio.sleep(1)

    # Should not have been called yet
    assert mock_client.ensure_authenticated.call_count == 0

    # Wait for the interval to complete
    await asyncio.sleep(3)

    # Should have been called once
    assert mock_client.ensure_authenticated.call_count >= 1

    # Cancel the task
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
