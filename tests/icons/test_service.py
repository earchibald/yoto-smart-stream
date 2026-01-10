"""
Tests for icon service functionality.
"""

from io import BytesIO
from unittest.mock import AsyncMock

import pytest
from PIL import Image

from yoto_smart_stream.icons.models import DisplayIcon, IconListResponse
from yoto_smart_stream.icons.service import IconService


@pytest.fixture
def mock_icon_client():
    """Create a mock IconClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def icon_service(mock_icon_client):
    """Create an IconService with mocked client."""
    return IconService(mock_icon_client)


@pytest.fixture
def valid_icon_bytes():
    """Create valid 16x16 PNG icon bytes."""
    img = Image.new("RGBA", (16, 16), color="red")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_icon():
    """Create a sample DisplayIcon."""
    return DisplayIcon(
        id="icon-001",
        name="Test Icon",
        url="https://example.com/icon.png",
        category="test",
        tags=["test"],
    )


class TestIconValidation:
    """Tests for icon validation."""

    def test_validate_valid_icon(self, icon_service, valid_icon_bytes):
        """Test that valid icon passes validation."""
        # Should not raise an exception
        icon_service.validate_icon(valid_icon_bytes)

    def test_validate_wrong_size(self, icon_service):
        """Test that wrong size icons are rejected."""
        img = Image.new("RGBA", (32, 32), color="red")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        icon_data = buffer.getvalue()

        with pytest.raises(ValueError, match="must be exactly 16x16 pixels"):
            icon_service.validate_icon(icon_data)

    def test_validate_wrong_format(self, icon_service):
        """Test that non-PNG formats are rejected."""
        img = Image.new("RGB", (16, 16), color="red")
        buffer = BytesIO()
        img.save(buffer, format="JPEG")
        icon_data = buffer.getvalue()

        with pytest.raises(ValueError, match="must be PNG format"):
            icon_service.validate_icon(icon_data)

    def test_validate_too_large(self, icon_service):
        """Test that oversized files are rejected."""
        # Create a large file (> 10KB)
        icon_data = b"x" * (11 * 1024)

        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            icon_service.validate_icon(icon_data)

    def test_validate_invalid_data(self, icon_service):
        """Test that invalid image data is rejected."""
        icon_data = b"not an image"

        with pytest.raises(ValueError, match="Invalid image data"):
            icon_service.validate_icon(icon_data)


class TestGetPublicIcons:
    """Tests for getting public icons."""

    @pytest.mark.asyncio
    async def test_get_public_icons(self, icon_service, mock_icon_client, sample_icon):
        """Test getting public icons."""
        mock_response = IconListResponse(
            icons=[sample_icon],
            total=1,
            page=1,
            per_page=50,
            has_next=False,
        )
        mock_icon_client.list_public_icons.return_value = mock_response

        result = await icon_service.get_public_icons()

        assert len(result.icons) == 1
        assert result.icons[0].id == "icon-001"
        mock_icon_client.list_public_icons.assert_called_once_with(
            category=None,
            page=1,
            per_page=50,
        )

    @pytest.mark.asyncio
    async def test_get_public_icons_with_category(
        self, icon_service, mock_icon_client, sample_icon
    ):
        """Test getting public icons filtered by category."""
        mock_response = IconListResponse(
            icons=[sample_icon],
            total=1,
            page=1,
            per_page=50,
            has_next=False,
        )
        mock_icon_client.list_public_icons.return_value = mock_response

        await icon_service.get_public_icons(category="music")

        mock_icon_client.list_public_icons.assert_called_once_with(
            category="music",
            page=1,
            per_page=50,
        )

    @pytest.mark.asyncio
    async def test_get_public_icons_with_search(self, icon_service, mock_icon_client):
        """Test searching public icons by name."""
        icon1 = DisplayIcon(
            id="icon-001",
            name="Music Note",
            url="https://example.com/icon1.png",
            tags=["music"],
        )
        icon2 = DisplayIcon(
            id="icon-002",
            name="Book",
            url="https://example.com/icon2.png",
            tags=["reading"],
        )

        mock_response = IconListResponse(
            icons=[icon1, icon2],
            total=2,
            page=1,
            per_page=50,
            has_next=False,
        )
        mock_icon_client.list_public_icons.return_value = mock_response

        # Search for "music"
        result = await icon_service.get_public_icons(search="music")

        assert len(result.icons) == 1
        assert result.icons[0].name == "Music Note"


class TestGetUserIcons:
    """Tests for getting user icons."""

    @pytest.mark.asyncio
    async def test_get_user_icons(self, icon_service, mock_icon_client, sample_icon):
        """Test getting user's custom icons."""
        mock_response = IconListResponse(
            icons=[sample_icon],
            total=1,
            page=1,
            per_page=50,
            has_next=False,
        )
        mock_icon_client.list_user_icons.return_value = mock_response

        result = await icon_service.get_user_icons()

        assert len(result.icons) == 1
        mock_icon_client.list_user_icons.assert_called_once_with(
            page=1,
            per_page=50,
        )


class TestGetIconById:
    """Tests for getting icon by ID."""

    @pytest.mark.asyncio
    async def test_get_icon_by_id(self, icon_service, mock_icon_client, sample_icon):
        """Test getting a specific icon."""
        mock_icon_client.get_icon.return_value = sample_icon

        result = await icon_service.get_icon_by_id("icon-001")

        assert result.id == "icon-001"
        mock_icon_client.get_icon.assert_called_once_with("icon-001")

    @pytest.mark.asyncio
    async def test_get_icon_by_id_cached(self, icon_service, mock_icon_client, sample_icon):
        """Test that icons are cached after first retrieval."""
        mock_icon_client.get_icon.return_value = sample_icon

        # First call
        result1 = await icon_service.get_icon_by_id("icon-001")
        # Second call
        result2 = await icon_service.get_icon_by_id("icon-001")

        # Should only call API once
        assert mock_icon_client.get_icon.call_count == 1
        assert result1.id == result2.id


class TestUploadIcon:
    """Tests for uploading custom icons."""

    @pytest.mark.asyncio
    async def test_upload_custom_icon_bytes(
        self, icon_service, mock_icon_client, valid_icon_bytes, sample_icon
    ):
        """Test uploading a custom icon from bytes."""
        mock_icon_client.upload_icon.return_value = sample_icon

        result = await icon_service.upload_custom_icon_bytes(
            icon_data=valid_icon_bytes,
            name="My Icon",
            tags=["custom"],
            category="misc",
        )

        assert result.id == "icon-001"
        mock_icon_client.upload_icon.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_custom_icon_invalid(self, icon_service, mock_icon_client):
        """Test that invalid icons are rejected before upload."""
        invalid_data = b"not an image"

        with pytest.raises(ValueError):
            await icon_service.upload_custom_icon_bytes(
                icon_data=invalid_data,
                name="Invalid",
            )

        # Should not call API
        mock_icon_client.upload_icon.assert_not_called()


class TestDeleteIcon:
    """Tests for deleting custom icons."""

    @pytest.mark.asyncio
    async def test_delete_custom_icon(self, icon_service, mock_icon_client):
        """Test deleting a custom icon."""
        mock_icon_client.delete_icon.return_value = True

        result = await icon_service.delete_custom_icon("icon-001")

        assert result is True
        mock_icon_client.delete_icon.assert_called_once_with("icon-001")

    @pytest.mark.asyncio
    async def test_delete_icon_removes_from_cache(
        self, icon_service, mock_icon_client, sample_icon
    ):
        """Test that deleted icons are removed from cache."""
        # Add to cache
        icon_service._cache["icon-001"] = sample_icon

        mock_icon_client.delete_icon.return_value = True

        await icon_service.delete_custom_icon("icon-001")

        # Should be removed from cache
        assert "icon-001" not in icon_service._cache


class TestCache:
    """Tests for cache functionality."""

    def test_clear_cache(self, icon_service, sample_icon):
        """Test clearing the cache."""
        # Add some items to cache
        icon_service._cache["icon-001"] = sample_icon
        icon_service._cache["icon-002"] = sample_icon

        assert len(icon_service._cache) == 2

        icon_service.clear_cache()

        assert len(icon_service._cache) == 0
