"""
Icon service layer for managing display icons.

Provides high-level business logic for icon management including:
- Caching of frequently used icons
- Icon validation (size, format)
- Icon search and filtering
- Integration with card/chapter management
"""

import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

from PIL import Image

from .client import IconClient
from .models import DisplayIcon, IconListResponse, IconUploadRequest

logger = logging.getLogger(__name__)


class IconService:
    """
    High-level service for managing Yoto display icons.

    Provides functionality for:
    - Browsing public icon repository
    - Managing custom user icons
    - Validating icon uploads (16x16 PNG)
    - Assigning icons to chapters/tracks
    """

    # Icon specifications for Yoto Mini
    REQUIRED_WIDTH = 16
    REQUIRED_HEIGHT = 16
    MAX_FILE_SIZE = 10 * 1024  # 10 KB
    ALLOWED_FORMAT = "PNG"

    def __init__(self, icon_client: IconClient):
        """
        Initialize the icon service.

        Args:
            icon_client: Configured IconClient instance
        """
        self.client = icon_client
        self._cache: dict[str, DisplayIcon] = {}

    async def get_public_icons(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> IconListResponse:
        """
        Get public icons from the Yoto repository.

        Args:
            category: Filter by category (e.g., "music", "story", "bedtime")
            search: Search term to filter icons by name or tags
            page: Page number (default: 1)
            per_page: Icons per page (default: 50)

        Returns:
            IconListResponse containing matching icons
        """
        response = await self.client.list_public_icons(
            category=category,
            page=page,
            per_page=per_page,
        )

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            filtered_icons = [
                icon for icon in response.icons
                if search_lower in icon.name.lower()
                or any(search_lower in tag.lower() for tag in icon.tags)
            ]
            response.icons = filtered_icons
            response.total = len(filtered_icons)

        return response

    async def get_user_icons(
        self,
        page: int = 1,
        per_page: int = 50,
    ) -> IconListResponse:
        """
        Get user's custom uploaded icons.

        Args:
            page: Page number (default: 1)
            per_page: Icons per page (default: 50)

        Returns:
            IconListResponse containing user's icons
        """
        return await self.client.list_user_icons(page=page, per_page=per_page)

    async def get_icon_by_id(self, icon_id: str) -> DisplayIcon:
        """
        Get a specific icon by ID.

        Uses cache if available.

        Args:
            icon_id: Unique icon identifier

        Returns:
            DisplayIcon instance
        """
        # Check cache first
        if icon_id in self._cache:
            logger.debug(f"Returning cached icon {icon_id}")
            return self._cache[icon_id]

        # Fetch from API
        icon = await self.client.get_icon(icon_id)
        self._cache[icon_id] = icon
        return icon

    async def upload_custom_icon(
        self,
        icon_path: Path,
        name: str,
        tags: Optional[list[str]] = None,
        category: Optional[str] = None,
    ) -> DisplayIcon:
        """
        Upload a custom display icon for Yoto Mini.

        Validates the icon before uploading:
        - Must be PNG format
        - Must be exactly 16x16 pixels
        - Must be under 10KB

        Args:
            icon_path: Path to the icon file
            name: Name for the icon
            tags: Optional list of tags
            category: Optional category

        Returns:
            DisplayIcon representing the uploaded icon

        Raises:
            ValueError: If the icon fails validation
        """
        # Read and validate the icon
        with open(icon_path, "rb") as f:
            icon_data = f.read()

        self.validate_icon(icon_data)

        # Create metadata
        metadata = IconUploadRequest(
            name=name,
            tags=tags or [],
            category=category,
        )

        # Upload
        icon = await self.client.upload_icon(icon_data, metadata)
        logger.info(f"Successfully uploaded icon: {icon.id}")

        return icon

    async def upload_custom_icon_bytes(
        self,
        icon_data: bytes,
        name: str,
        tags: Optional[list[str]] = None,
        category: Optional[str] = None,
    ) -> DisplayIcon:
        """
        Upload a custom display icon from bytes.

        Args:
            icon_data: Raw bytes of the icon (PNG)
            name: Name for the icon
            tags: Optional list of tags
            category: Optional category

        Returns:
            DisplayIcon representing the uploaded icon

        Raises:
            ValueError: If the icon fails validation
        """
        self.validate_icon(icon_data)

        metadata = IconUploadRequest(
            name=name,
            tags=tags or [],
            category=category,
        )

        icon = await self.client.upload_icon(icon_data, metadata)
        logger.info(f"Successfully uploaded icon: {icon.id}")

        return icon

    async def delete_custom_icon(self, icon_id: str) -> bool:
        """
        Delete a custom user icon.

        Args:
            icon_id: ID of the icon to delete

        Returns:
            True if deletion was successful
        """
        success = await self.client.delete_icon(icon_id)

        # Remove from cache if present
        if icon_id in self._cache:
            del self._cache[icon_id]

        return success

    def validate_icon(self, icon_data: bytes) -> None:
        """
        Validate icon data meets Yoto Mini requirements.

        Requirements:
        - PNG format
        - Exactly 16x16 pixels
        - Under 10KB file size

        Args:
            icon_data: Raw bytes of the icon

        Raises:
            ValueError: If validation fails with specific reason
        """
        # Check file size
        if len(icon_data) > self.MAX_FILE_SIZE:
            raise ValueError(
                f"Icon file size ({len(icon_data)} bytes) exceeds maximum "
                f"allowed size ({self.MAX_FILE_SIZE} bytes)"
            )

        # Load and validate image
        try:
            img = Image.open(BytesIO(icon_data))
        except Exception as e:
            raise ValueError(f"Invalid image data: {e}") from e

        # Check format
        if img.format != self.ALLOWED_FORMAT:
            raise ValueError(
                f"Icon must be {self.ALLOWED_FORMAT} format, got {img.format}"
            )

        # Check dimensions
        if img.size != (self.REQUIRED_WIDTH, self.REQUIRED_HEIGHT):
            raise ValueError(
                f"Icon must be exactly {self.REQUIRED_WIDTH}x{self.REQUIRED_HEIGHT} pixels, "
                f"got {img.width}x{img.height}"
            )

        logger.debug("Icon validation passed")

    def clear_cache(self) -> None:
        """Clear the icon cache."""
        self._cache.clear()
        logger.debug("Icon cache cleared")
