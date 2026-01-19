"""Media management endpoints (cover images, icons, etc.)."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from ...config import get_settings
from ...models import User
from ..dependencies import get_yoto_client
from .user_auth import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/media/cover-image")
async def upload_cover_image(
    image: UploadFile = File(...), user: User = Depends(require_auth)
):
    """
    Upload a cover image for a Yoto card.

    Uploads the image to Yoto's media service and returns the image ID
    that can be used in card metadata.

    Args:
        image: Image file to upload (JPEG, PNG)
        user: Authenticated user

    Returns:
        dict: Contains image_id for use in card creation

    Example response:
        {
            "image_id": "img_abc123xyz",
            "status": "uploaded"
        }
    """
    # Validate file type
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type: {image.content_type}. Must be an image.",
        )

    # Validate file size (max 5MB)
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    contents = await image.read()
    if len(contents) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Image file too large. Maximum size is 5MB.",
        )

    # Reset file position
    await image.seek(0)

    try:
        client = get_yoto_client()
        manager = client.get_manager()

        # Verify authentication
        if not manager.token or not manager.token.access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not authenticated with Yoto API. Please log in again.",
            )

        # Upload to Yoto media service
        # Use the Yoto API to upload cover image
        import requests

        headers = {
            "Authorization": f"Bearer {manager.token.access_token}",
        }

        files = {"image": (image.filename, contents, image.content_type)}

        # Yoto cover image upload endpoint
        response = requests.post(
            "https://api.yoto.io/media/coverImages/user/me",
            headers=headers,
            files=files,
            timeout=30,
        )

        if response.status_code != 200:
            error_detail = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get("message", error_detail)
            except:
                pass

            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to upload cover image to Yoto: {error_detail}",
            )

        result = response.json()

        # Extract image ID from response
        # Yoto returns: {"id": "img_...", ...}
        image_id = result.get("id")
        if not image_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Yoto API did not return an image ID",
            )

        logger.info(f"✓ Cover image uploaded successfully: {image_id}")

        return {"image_id": image_id, "status": "uploaded"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload cover image: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload cover image: {str(e)}",
        )


# Future: Icon management endpoints
# TODO: Add endpoints for browsing and uploading display icons (16x16 PNG for Yoto Mini)
# GET /media/displayIcons/public - Browse public icon repository
# POST /media/displayIcons/user/me - Upload custom 16x16 icon
# See examples/icon_management.py for implementation patterns
