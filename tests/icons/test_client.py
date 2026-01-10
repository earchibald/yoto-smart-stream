"""
Tests for icon API client.
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from yoto_smart_stream.icons.client import IconClient
from yoto_smart_stream.icons.models import DisplayIcon, IconUploadRequest


@pytest.fixture
def access_token():
    """Provide a test access token."""
    return "test_access_token_123"


@pytest.fixture
def icon_client(access_token):
    """Create an IconClient instance."""
    return IconClient(access_token)


@pytest.fixture
def mock_httpx_response():
    """Create a mock httpx response."""
    response = AsyncMock(spec=httpx.Response)
    response.raise_for_status = Mock()  # This is not async
    return response


class TestIconClientInitialization:
    """Tests for IconClient initialization."""

    def test_client_initialization(self, access_token):
        """Test that client initializes with access token."""
        client = IconClient(access_token)

        assert client.access_token == access_token
        assert client.BASE_URL == "https://api.yotoplay.com"
        assert client.timeout == 30.0

    def test_client_custom_timeout(self, access_token):
        """Test client with custom timeout."""
        client = IconClient(access_token, timeout=60.0)

        assert client.timeout == 60.0

    @pytest.mark.asyncio
    async def test_client_context_manager(self, access_token):
        """Test that client can be used as async context manager."""
        async with IconClient(access_token) as client:
            assert client.access_token == access_token


class TestListPublicIcons:
    """Tests for listing public icons."""

    @pytest.mark.asyncio
    async def test_list_public_icons(self, icon_client, mock_httpx_response):
        """Test listing public icons."""
        # Mock API response
        mock_httpx_response.json.return_value = {
            "icons": [
                {
                    "id": "icon-001",
                    "name": "Music Note",
                    "url": "https://example.com/icon.png",
                    "category": "music",
                    "tags": ["music", "note"],
                }
            ],
            "total": 100,
        }

        with patch.object(icon_client._client, "get", return_value=mock_httpx_response) as mock_get:
            result = await icon_client.list_public_icons()

            # Verify API call
            mock_get.assert_called_once_with(
                "/media/displayIcons/public",
                params={"page": 1, "per_page": 50},
            )

            # Verify response
            assert len(result.icons) == 1
            assert result.icons[0].id == "icon-001"
            assert result.icons[0].name == "Music Note"
            assert result.total == 100

    @pytest.mark.asyncio
    async def test_list_public_icons_with_category(self, icon_client, mock_httpx_response):
        """Test listing public icons filtered by category."""
        mock_httpx_response.json.return_value = {
            "icons": [],
            "total": 0,
        }

        with patch.object(icon_client._client, "get", return_value=mock_httpx_response) as mock_get:
            await icon_client.list_public_icons(category="bedtime")

            mock_get.assert_called_once_with(
                "/media/displayIcons/public",
                params={"page": 1, "per_page": 50, "category": "bedtime"},
            )

    @pytest.mark.asyncio
    async def test_list_public_icons_pagination(self, icon_client, mock_httpx_response):
        """Test listing public icons with pagination."""
        mock_httpx_response.json.return_value = {
            "icons": [],
            "total": 0,
        }

        with patch.object(icon_client._client, "get", return_value=mock_httpx_response) as mock_get:
            await icon_client.list_public_icons(page=2, per_page=25)

            mock_get.assert_called_once_with(
                "/media/displayIcons/public",
                params={"page": 2, "per_page": 25},
            )


class TestListUserIcons:
    """Tests for listing user icons."""

    @pytest.mark.asyncio
    async def test_list_user_icons(self, icon_client, mock_httpx_response):
        """Test listing user's custom icons."""
        mock_httpx_response.json.return_value = {
            "icons": [
                {
                    "id": "user-icon-001",
                    "name": "My Custom Icon",
                    "url": "https://example.com/user/icon.png",
                    "tags": ["custom"],
                }
            ],
            "total": 5,
        }

        with patch.object(icon_client._client, "get", return_value=mock_httpx_response) as mock_get:
            result = await icon_client.list_user_icons()

            mock_get.assert_called_once_with(
                "/media/displayIcons/user/me",
                params={"page": 1, "per_page": 50},
            )

            assert len(result.icons) == 1
            assert result.icons[0].id == "user-icon-001"
            # User icons should be marked as not public
            assert result.icons[0].is_public is False


class TestGetIcon:
    """Tests for getting a specific icon."""

    @pytest.mark.asyncio
    async def test_get_icon(self, icon_client, mock_httpx_response):
        """Test getting a specific icon by ID."""
        mock_httpx_response.json.return_value = {
            "id": "icon-001",
            "name": "Test Icon",
            "url": "https://example.com/icon.png",
        }

        with patch.object(icon_client._client, "get", return_value=mock_httpx_response) as mock_get:
            result = await icon_client.get_icon("icon-001")

            mock_get.assert_called_once_with("/media/displayIcons/icon-001")

            assert isinstance(result, DisplayIcon)
            assert result.id == "icon-001"
            assert result.name == "Test Icon"


class TestUploadIcon:
    """Tests for uploading custom icons."""

    @pytest.mark.asyncio
    async def test_upload_icon(self, icon_client, mock_httpx_response):
        """Test uploading a custom icon."""
        icon_data = b"fake_png_data"
        metadata = IconUploadRequest(
            name="My Icon",
            tags=["custom", "test"],
            category="misc",
        )

        mock_httpx_response.json.return_value = {
            "id": "user-icon-new",
            "name": "My Icon",
            "url": "https://example.com/user/new.png",
        }

        with patch.object(
            icon_client._client, "post", return_value=mock_httpx_response
        ) as mock_post:
            result = await icon_client.upload_icon(icon_data, metadata)

            # Verify API call
            mock_post.assert_called_once()
            call_args = mock_post.call_args

            assert call_args[0][0] == "/media/displayIcons/upload"
            assert "files" in call_args[1]
            assert "data" in call_args[1]

            # Verify response
            assert isinstance(result, DisplayIcon)
            assert result.id == "user-icon-new"
            assert result.is_public is False


class TestDeleteIcon:
    """Tests for deleting custom icons."""

    @pytest.mark.asyncio
    async def test_delete_icon(self, icon_client, mock_httpx_response):
        """Test deleting a custom icon."""
        mock_httpx_response.status_code = 204

        with patch.object(
            icon_client._client, "delete", return_value=mock_httpx_response
        ) as mock_delete:
            result = await icon_client.delete_icon("icon-001")

            mock_delete.assert_called_once_with("/media/displayIcons/icon-001")

            assert result is True


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_http_error_handling(self, icon_client):
        """Test that HTTP errors are properly raised."""
        mock_response = AsyncMock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=Mock()
        )

        with patch.object(icon_client._client, "get", return_value=mock_response):
            with pytest.raises(httpx.HTTPStatusError):
                await icon_client.list_public_icons()


class TestParseIconListResponse:
    """Tests for parsing icon list responses."""

    def test_parse_icon_list_response_with_icons_key(self, icon_client):
        """Test parsing response with 'icons' key."""
        data = {
            "icons": [
                {
                    "id": "icon-001",
                    "name": "Icon 1",
                    "url": "https://example.com/1.png",
                }
            ],
            "total": 100,
        }

        result = icon_client._parse_icon_list_response(data, 1, 50)

        assert len(result.icons) == 1
        assert result.total == 100
        assert result.page == 1
        assert result.has_next is True

    def test_parse_icon_list_response_with_items_key(self, icon_client):
        """Test parsing response with 'items' key (alternative format)."""
        data = {
            "items": [
                {
                    "id": "icon-001",
                    "name": "Icon 1",
                    "url": "https://example.com/1.png",
                }
            ],
            "total": 25,
        }

        result = icon_client._parse_icon_list_response(data, 1, 50)

        assert len(result.icons) == 1
        assert result.total == 25
        assert result.has_next is False

    def test_parse_icon_list_response_user_icons(self, icon_client):
        """Test that user icons are marked as not public."""
        data = {
            "icons": [
                {
                    "id": "icon-001",
                    "name": "User Icon",
                    "url": "https://example.com/1.png",
                }
            ],
            "total": 5,
        }

        result = icon_client._parse_icon_list_response(data, 1, 50, is_public=False)

        assert result.icons[0].is_public is False
