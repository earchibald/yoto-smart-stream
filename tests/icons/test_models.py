"""
Tests for icon data models.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from yoto_smart_stream.icons.models import (
    DisplayIcon,
    IconCategory,
    IconListResponse,
    IconUploadRequest,
)


def test_display_icon_creation():
    """Test creating a DisplayIcon with required fields."""
    icon = DisplayIcon(
        id="icon-001",
        name="Music Note",
        url="https://cdn.yotoplay.com/icons/music.png",
    )

    assert icon.id == "icon-001"
    assert icon.name == "Music Note"
    assert str(icon.url) == "https://cdn.yotoplay.com/icons/music.png"
    assert icon.is_public is True
    assert icon.tags == []


def test_display_icon_with_all_fields():
    """Test creating a DisplayIcon with all optional fields."""
    now = datetime.now()

    icon = DisplayIcon(
        id="icon-002",
        name="Bedtime Moon",
        url="https://cdn.yotoplay.com/icons/moon.png",
        thumbnail_url="https://cdn.yotoplay.com/icons/moon_thumb.png",
        category="bedtime",
        tags=["bedtime", "moon", "night"],
        is_public=False,
        owner_id="user-123",
        created_at=now,
        updated_at=now,
    )

    assert icon.category == "bedtime"
    assert len(icon.tags) == 3
    assert "moon" in icon.tags
    assert icon.is_public is False
    assert icon.owner_id == "user-123"


def test_display_icon_invalid_url():
    """Test that invalid URLs are rejected."""
    with pytest.raises(ValidationError):
        DisplayIcon(
            id="icon-003",
            name="Invalid",
            url="not-a-valid-url",
        )


def test_icon_category_creation():
    """Test creating an IconCategory."""
    category = IconCategory(
        id="cat-001",
        name="Music",
        description="Music-related icons",
    )

    assert category.id == "cat-001"
    assert category.name == "Music"
    assert category.description == "Music-related icons"


def test_icon_upload_request():
    """Test creating an IconUploadRequest."""
    request = IconUploadRequest(
        name="My Custom Icon",
        tags=["custom", "special"],
        category="misc",
    )

    assert request.name == "My Custom Icon"
    assert len(request.tags) == 2
    assert request.category == "misc"


def test_icon_upload_request_defaults():
    """Test IconUploadRequest with default values."""
    request = IconUploadRequest(name="Simple Icon")

    assert request.name == "Simple Icon"
    assert request.tags == []
    assert request.category is None


def test_icon_list_response():
    """Test creating an IconListResponse."""
    icon1 = DisplayIcon(
        id="icon-001",
        name="Icon 1",
        url="https://example.com/icon1.png",
    )
    icon2 = DisplayIcon(
        id="icon-002",
        name="Icon 2",
        url="https://example.com/icon2.png",
    )

    response = IconListResponse(
        icons=[icon1, icon2],
        total=100,
        page=1,
        per_page=50,
        has_next=True,
    )

    assert len(response.icons) == 2
    assert response.total == 100
    assert response.page == 1
    assert response.has_next is True


def test_icon_list_response_defaults():
    """Test IconListResponse with default values."""
    response = IconListResponse(
        icons=[],
        total=0,
    )

    assert response.page == 1
    assert response.per_page == 50
    assert response.has_next is False


def test_display_icon_json_serialization():
    """Test that DisplayIcon can be serialized to JSON."""
    icon = DisplayIcon(
        id="icon-001",
        name="Test Icon",
        url="https://example.com/icon.png",
        tags=["test"],
    )

    json_data = icon.model_dump()

    assert json_data["id"] == "icon-001"
    assert json_data["name"] == "Test Icon"
    assert json_data["tags"] == ["test"]
    assert json_data["is_public"] is True
