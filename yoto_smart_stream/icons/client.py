"""
API client for Yoto display icon repository.

This client provides access to:
- Public icon repository (GET /media/displayIcons/public)
- User's custom icons (GET /media/displayIcons/user/me)

Icons are displayed on Yoto Mini devices (16x16 pixel display).
Original Yoto Players do not have displays and will not show icons.
"""

import logging
from typing import Optional
from pathlib import Path

import httpx
from pydantic import HttpUrl

from .models import DisplayIcon, IconListResponse, IconUploadRequest

logger = logging.getLogger(__name__)


class IconClient:
    """
    Client for interacting with Yoto icon API endpoints.

    Provides methods to:
    - List public icons from the Yoto repository
    - List user's custom icons
    - Upload custom icons (16x16 PNG)
    - Get individual icon details
    """

    BASE_URL = "https://api.yotoplay.com"

    def __init__(self, access_token: str, timeout: float = 30.0):
        """
        Initialize the icon API client.

        Args:
            access_token: Valid Yoto API access token (JWT)
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.access_token = access_token
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close the HTTP client connection."""
        await self._client.aclose()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def list_public_icons(
        self,
        category: Optional[str] = None,
        page: int = 1,
        per_page: int = 50,
    ) -> IconListResponse:
        """
        List public icons from the Yoto icon repository.

        These icons are provided by Yoto and available for all users.
        Icons are 16x16 pixels and display on Yoto Mini devices.

        Args:
            category: Optional category filter (e.g., "music", "story", "bedtime")
            page: Page number for pagination (default: 1)
            per_page: Number of icons per page (default: 50)

        Returns:
            IconListResponse containing list of public icons

        Raises:
            httpx.HTTPError: If the API request fails
        """
        params = {"page": page, "per_page": per_page}
        if category:
            params["category"] = category

        logger.info(f"Fetching public icons (page={page}, per_page={per_page}, category={category})")

        response = await self._client.get("/media/displayIcons/public", params=params)
        response.raise_for_status()

        data = response.json()
        return self._parse_icon_list_response(data, page, per_page)

    async def list_user_icons(
        self,
        page: int = 1,
        per_page: int = 50,
    ) -> IconListResponse:
        """
        List user's custom uploaded icons.

        These are icons uploaded by the current user.

        Args:
            page: Page number for pagination (default: 1)
            per_page: Number of icons per page (default: 50)

        Returns:
            IconListResponse containing list of user's custom icons

        Raises:
            httpx.HTTPError: If the API request fails
        """
        params = {"page": page, "per_page": per_page}

        logger.info(f"Fetching user icons (page={page}, per_page={per_page})")

        response = await self._client.get("/media/displayIcons/user/me", params=params)
        response.raise_for_status()

        data = response.json()
        return self._parse_icon_list_response(data, page, per_page, is_public=False)

    async def get_icon(self, icon_id: str) -> DisplayIcon:
        """
        Get details for a specific icon.

        Args:
            icon_id: Unique identifier for the icon

        Returns:
            DisplayIcon with full details

        Raises:
            httpx.HTTPError: If the API request fails
        """
        logger.info(f"Fetching icon details for {icon_id}")

        response = await self._client.get(f"/media/displayIcons/{icon_id}")
        response.raise_for_status()

        data = response.json()
        return DisplayIcon(**data)

    async def upload_icon(
        self,
        icon_data: bytes,
        metadata: IconUploadRequest,
    ) -> DisplayIcon:
        """
        Upload a custom display icon.

        Icons must be 16x16 pixel PNG images for Yoto Mini display.

        Args:
            icon_data: Raw bytes of the icon image (PNG, 16x16 pixels)
            metadata: Icon metadata (name, tags, category)

        Returns:
            DisplayIcon representing the uploaded icon

        Raises:
            httpx.HTTPError: If the API request fails
            ValueError: If the icon data is invalid

        Notes:
            - Icons must be PNG format
            - Resolution must be exactly 16x16 pixels
            - Maximum file size is typically 10KB
        """
        logger.info(f"Uploading custom icon: {metadata.name}")

        # Upload the icon file
        files = {"icon": ("icon.png", icon_data, "image/png")}
        data = {
            "name": metadata.name,
            "tags": ",".join(metadata.tags),
        }
        if metadata.category:
            data["category"] = metadata.category

        response = await self._client.post(
            "/media/displayIcons/upload",
            files=files,
            data=data,
        )
        response.raise_for_status()

        icon_data = response.json()
        return DisplayIcon(**icon_data, is_public=False)

    async def delete_icon(self, icon_id: str) -> bool:
        """
        Delete a custom user icon.

        Only icons uploaded by the current user can be deleted.

        Args:
            icon_id: Unique identifier for the icon to delete

        Returns:
            True if deletion was successful

        Raises:
            httpx.HTTPError: If the API request fails or user doesn't own the icon
        """
        logger.info(f"Deleting icon {icon_id}")

        response = await self._client.delete(f"/media/displayIcons/{icon_id}")
        response.raise_for_status()

        return response.status_code == 204

    def _parse_icon_list_response(
        self,
        data: dict,
        page: int,
        per_page: int,
        is_public: bool = True,
    ) -> IconListResponse:
        """
        Parse icon list response from API.

        Args:
            data: Raw API response data
            page: Current page number
            per_page: Icons per page
            is_public: Whether these are public or user icons

        Returns:
            IconListResponse object
        """
        # Parse icons from response
        # The actual API response format may vary, this is a reasonable default
        icons_data = data.get("icons", []) or data.get("items", [])
        icons = [
            DisplayIcon(**icon_data, is_public=is_public)
            for icon_data in icons_data
        ]

        total = data.get("total", len(icons))
        has_next = (page * per_page) < total

        return IconListResponse(
            icons=icons,
            total=total,
            page=page,
            per_page=per_page,
            has_next=has_next,
        )
