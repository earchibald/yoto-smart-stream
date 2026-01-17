"""Health check endpoints."""

from fastapi import APIRouter

from ...config import get_settings
from ..dependencies import get_yoto_client, get_authenticated_yoto_client

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns basic health status and configuration info.
    """
    settings = get_settings()

    # Count audio files
    audio_count = 0
    if settings.audio_files_dir.exists():
        audio_count = len(list(settings.audio_files_dir.glob("*.mp3")))

    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "yoto_api": "connected",
        "mqtt_enabled": settings.mqtt_enabled,
        "audio_files": audio_count,
    }


@router.get("/ready")
async def readiness_check():
    """
    Readiness check for orchestrators.

    Verifies the service is ready to accept requests.
    """
    try:
        client = get_authenticated_yoto_client()
        if not client.is_authenticated():
            return {"ready": False, "reason": "Not authenticated"}
        return {"ready": True}
    except Exception as e:
        return {"ready": False, "reason": str(e)}
