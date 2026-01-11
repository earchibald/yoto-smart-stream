"""
Main FastAPI application factory.

This module creates and configures the FastAPI application with all routes,
middleware, and lifecycle management.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from ..config import get_settings
from ..core import YotoClient
from .dependencies import set_yoto_client
from .routes import cards, health, players

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks:
    - Initialize Yoto client
    - Authenticate with Yoto API
    - Connect to MQTT
    - Cleanup on shutdown
    """
    settings = get_settings()

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    yoto_client = None
    try:
        # Initialize Yoto client
        yoto_client = YotoClient(settings)
        yoto_client.authenticate()
        yoto_client.update_player_status()
        set_yoto_client(yoto_client)
        logger.info("✓ Yoto API connected successfully")

        # Connect to MQTT if enabled
        if settings.mqtt_enabled:
            try:
                yoto_client.connect_mqtt()
                logger.info("✓ MQTT connected successfully")
            except Exception as e:
                logger.warning(f"⚠ MQTT connection failed: {e}")
                logger.warning("  Continuing without MQTT (some features may not work)")

    except Exception as e:
        logger.error(f"⚠ Warning: Could not initialize Yoto API: {e}")
        logger.error("  Some endpoints may not work until authentication is completed.")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down...")
    if yoto_client:
        yoto_client.disconnect_mqtt()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        Configured FastAPI application
    """
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description="API for controlling Yoto players and managing audio content",
        version=settings.app_version,
        lifespan=lifespan,
        debug=settings.debug,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Define static directory path once
    static_dir = Path(__file__).parent.parent / "static"

    # Mount static files directory
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(players.router, prefix="/api", tags=["Players"])
    app.include_router(cards.router, prefix="/api", tags=["Cards"])

    @app.get("/", tags=["Web UI"])
    async def root():
        """Serve the admin dashboard web UI."""
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        # Fallback if static files don't exist
        return {
            "message": "Web UI not available",
            "docs": "/docs",
            "api": "/api/status",
        }

    @app.get("/streams", tags=["Web UI"])
    async def streams():
        """Serve the music streams interface."""
        streams_path = static_dir / "streams.html"
        if streams_path.exists():
            return FileResponse(streams_path)
        return {"message": "Streams UI not available", "docs": "/docs"}

    @app.get("/api/status", tags=["General"])
    async def api_status():
        """API status endpoint with system information."""
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "environment": settings.environment,
            "docs": "/docs",
            "features": {
                "player_control": True,
                "audio_streaming": True,
                "myo_card_creation": True,
                "mqtt_events": settings.mqtt_enabled,
            },
        }

    return app


# Create application instance
app = create_app()
