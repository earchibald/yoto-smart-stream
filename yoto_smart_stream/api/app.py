"""
Main FastAPI application factory.

This module creates and configures the FastAPI application with all routes,
middleware, and lifecycle management.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(players.router, prefix="/api", tags=["Players"])
    app.include_router(cards.router, prefix="/api", tags=["Cards"])

    @app.get("/", tags=["General"])
    async def root():
        """Root endpoint with API information."""
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
