"""Cover image management endpoints."""

import logging
import mimetypes
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import BaseModel, Field, HttpUrl

from ...config import get_settings
from ...models import User
from .user_auth import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
PERMANENT_IMAGES = {"default.png", "default_large.png"}

# Recommended dimensions for Yoto cover art
RECOMMENDED_DIMENSIONS = [(661, 1054), (784, 1248)]
ASPECT_RATIO = 3 / 5  # width:height


# Request/Response models
class ImageListResponse(BaseModel):
    """Response model for listing cover images."""

    images: list[dict]
    count: int


class ImageUploadResponse(BaseModel):
    """Response model for image upload."""

    filename: str
    size: int
    dimensions: tuple[int, int]
    is_recommended_size: bool


class RemoteImageRequest(BaseModel):
    """Request model for fetching remote images."""

    image_url: HttpUrl = Field(..., description="URL of the image to fetch")
    filename: Optional[str] = Field(None, description="Optional custom filename (with extension)")


def validate_image_dimensions(img: Image.Image) -> tuple[bool, str]:
    """
    Validate image dimensions against Yoto requirements.

    Returns:
        Tuple of (is_valid, message)
    """
    width, height = img.size

    # Check aspect ratio (should be close to 3:5)
    actual_ratio = width / height
    ratio_diff = abs(actual_ratio - ASPECT_RATIO)

    if ratio_diff > 0.1:  # Allow 10% deviation
        return False, f"Image aspect ratio {actual_ratio:.2f} differs from recommended 3:5 ratio"

    # Check if dimensions match recommended sizes
    is_recommended = (width, height) in RECOMMENDED_DIMENSIONS
    if is_recommended:
        return True, f"✓ Perfect! Image matches recommended size {width}×{height}"

    return True, f"Image size {width}×{height} is acceptable (aspect ratio is correct)"


# Endpoints


@router.get("/cover-images", response_model=ImageListResponse)
async def list_cover_images(user: User = Depends(require_auth)):
    """
    List all available cover images.

    Returns:
        List of cover images with metadata
    """
    settings = get_settings()
    images = []

    try:
        for image_path in sorted(settings.cover_images_dir.iterdir()):
            if image_path.is_file() and image_path.suffix.lower() in ALLOWED_EXTENSIONS:
                try:
                    # Get image dimensions
                    with Image.open(image_path) as img:
                        width, height = img.size

                    is_permanent = image_path.name in PERMANENT_IMAGES
                    is_recommended = (width, height) in RECOMMENDED_DIMENSIONS

                    images.append(
                        {
                            "filename": image_path.name,
                            "size": image_path.stat().st_size,
                            "dimensions": {"width": width, "height": height},
                            "is_permanent": is_permanent,
                            "is_recommended_size": is_recommended,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Could not read image {image_path.name}: {e}")

        return {"images": images, "count": len(images)}

    except Exception as e:
        logger.error(f"Error listing cover images: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list cover images",
        )


@router.get("/cover-images/{filename}")
async def get_cover_image(filename: str, user: User = Depends(require_auth)):
    """
    Serve a specific cover image file.

    Args:
        filename: Name of the cover image file

    Returns:
        Image file
    """
    settings = get_settings()
    image_path = settings.cover_images_dir / filename

    if not image_path.exists() or not image_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cover image '{filename}' not found",
        )

    # Verify it's an allowed image type
    if image_path.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Get MIME type
    mime_type, _ = mimetypes.guess_type(str(image_path))
    if mime_type is None:
        mime_type = "application/octet-stream"

    return FileResponse(
        image_path,
        media_type=mime_type,
        filename=filename,
    )


@router.post(
    "/cover-images/upload",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_cover_image(
    file: UploadFile = File(...), user: User = Depends(require_auth)
):
    """
    Upload a new cover image.

    The image should be 661×1054 or 784×1248 pixels (3:5 aspect ratio).

    Args:
        file: Image file to upload

    Returns:
        Upload confirmation with image details
    """
    settings = get_settings()

    # Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file type '{file_ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # Read file content
    try:
        content = await file.read()
        file_size = len(content)

        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
            )

        # Validate image and dimensions
        from io import BytesIO

        img = Image.open(BytesIO(content))
        is_valid, message = validate_image_dimensions(img)

        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image dimensions: {message}",
            )

        width, height = img.size
        is_recommended = (width, height) in RECOMMENDED_DIMENSIONS

        # Save file
        file_path = settings.cover_images_dir / file.filename
        counter = 1
        original_stem = file_path.stem
        while file_path.exists():
            file_path = settings.cover_images_dir / f"{original_stem}_{counter}{file_ext}"
            counter += 1

        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Uploaded cover image: {file_path.name} ({width}×{height})")

        return ImageUploadResponse(
            filename=file_path.name,
            size=file_size,
            dimensions=(width, height),
            is_recommended_size=is_recommended,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading cover image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload image: {str(e)}",
        )


@router.post(
    "/cover-images/fetch",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def fetch_remote_cover_image(
    request: RemoteImageRequest, user: User = Depends(require_auth)
):
    """
    Fetch a cover image from a remote URL.

    The image should be 661×1054 or 784×1248 pixels (3:5 aspect ratio).

    Args:
        request: Remote image URL and optional filename

    Returns:
        Upload confirmation with image details
    """
    settings = get_settings()

    try:
        # Fetch the image
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(str(request.image_url))
            response.raise_for_status()

            content = response.content
            file_size = len(content)

            if file_size > MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB",
                )

            # Determine filename
            if request.filename:
                filename = request.filename
                file_ext = Path(filename).suffix.lower()
                if file_ext not in ALLOWED_EXTENSIONS:
                    allowed = ', '.join(ALLOWED_EXTENSIONS)
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid file extension '{file_ext}'. Allowed: {allowed}",
                    )
            else:
                # Try to get filename from URL or content-type
                url_path = Path(str(request.image_url).split("?")[0])
                file_ext = url_path.suffix.lower()
                if file_ext not in ALLOWED_EXTENSIONS:
                    # Default to .png
                    file_ext = ".png"
                filename = f"remote_image_{hash(str(request.image_url))}{file_ext}"

            # Validate image and dimensions
            from io import BytesIO

            img = Image.open(BytesIO(content))
            is_valid, message = validate_image_dimensions(img)

            if not is_valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid image dimensions: {message}",
                )

            width, height = img.size
            is_recommended = (width, height) in RECOMMENDED_DIMENSIONS

            # Save file
            file_path = settings.cover_images_dir / filename
            counter = 1
            original_stem = file_path.stem
            original_ext = file_path.suffix
            while file_path.exists():
                file_path = settings.cover_images_dir / f"{original_stem}_{counter}{original_ext}"
                counter += 1

            with open(file_path, "wb") as f:
                f.write(content)

            logger.info(f"Fetched remote cover image: {file_path.name} ({width}×{height})")

            return ImageUploadResponse(
                filename=file_path.name,
                size=file_size,
                dimensions=(width, height),
                is_recommended_size=is_recommended,
            )

    except httpx.HTTPError as e:
        logger.error(f"Error fetching remote image: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch image from URL: {str(e)}",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing remote image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process remote image: {str(e)}",
        )


@router.delete("/cover-images/{filename}", status_code=status.HTTP_200_OK)
async def delete_cover_image(filename: str, user: User = Depends(require_auth)):
    """
    Delete a cover image.

    Permanent images (default.png, default_large.png) cannot be deleted.

    Args:
        filename: Name of the cover image to delete

    Returns:
        Success message
    """
    settings = get_settings()

    # Prevent deletion of permanent images
    if filename in PERMANENT_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot delete permanent cover image '{filename}'",
        )

    image_path = settings.cover_images_dir / filename

    if not image_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cover image '{filename}' not found",
        )

    try:
        image_path.unlink()
        logger.info(f"Deleted cover image: {filename}")

        return {
            "success": True,
            "message": f"Deleted cover image '{filename}'",
        }

    except Exception as e:
        logger.error(f"Error deleting cover image {filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cover image: {str(e)}",
        )
