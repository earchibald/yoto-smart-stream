"""
Data models for Yoto display icons.

These models represent display icons that can be shown on Yoto Mini devices
(16x16 pixel display). Original Yoto Players do not have display screens.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class IconCategory(BaseModel):
    """Category for organizing display icons."""

    id: str = Field(..., description="Unique identifier for the category")
    name: str = Field(..., description="Human-readable category name")
    description: Optional[str] = Field(None, description="Category description")


class DisplayIcon(BaseModel):
    """
    Display icon model for Yoto Mini devices.

    Yoto Mini has a 16x16 pixel display that can show custom icons during playback.
    Icons are typically PNG images at 16x16 resolution.

    Device Compatibility:
    - Yoto Mini: Displays icons on 16x16 pixel screen
    - Yoto Player (original): Does not have a display (icons ignored)
    """

    id: str = Field(..., description="Unique identifier for the icon")
    name: str = Field(..., description="Human-readable icon name")
    url: HttpUrl = Field(..., description="URL to the icon image (16x16 PNG)")
    thumbnail_url: Optional[HttpUrl] = Field(
        None, description="URL to a larger preview of the icon"
    )
    category: Optional[str] = Field(None, description="Icon category (e.g., music, story, bedtime)")
    tags: list[str] = Field(default_factory=list, description="Tags for searching and filtering")
    is_public: bool = Field(
        default=True, description="Whether this is from the public repository or user-uploaded"
    )
    owner_id: Optional[str] = Field(
        None, description="User ID of the owner (for custom icons)"
    )
    created_at: Optional[datetime] = Field(None, description="When the icon was created/uploaded")
    updated_at: Optional[datetime] = Field(None, description="When the icon was last modified")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "icon-music-001",
                "name": "Music Note",
                "url": "https://cdn.yotoplay.com/icons/music-001.png",
                "category": "music",
                "tags": ["music", "note", "audio"],
                "is_public": True,
            }
        }
    )


class IconUploadRequest(BaseModel):
    """Request model for uploading a custom display icon."""

    name: str = Field(..., description="Name for the custom icon")
    tags: list[str] = Field(default_factory=list, description="Tags for the icon")
    category: Optional[str] = Field(None, description="Category for the icon")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "My Custom Bedtime Icon",
                "tags": ["bedtime", "moon", "stars"],
                "category": "bedtime",
            }
        }
    )


class IconListResponse(BaseModel):
    """Response model for listing icons."""

    icons: list[DisplayIcon] = Field(..., description="List of display icons")
    total: int = Field(..., description="Total number of icons available")
    page: int = Field(1, description="Current page number")
    per_page: int = Field(50, description="Number of icons per page")
    has_next: bool = Field(False, description="Whether there are more pages")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "icons": [],
                "total": 150,
                "page": 1,
                "per_page": 50,
                "has_next": True,
            }
        }
    )
