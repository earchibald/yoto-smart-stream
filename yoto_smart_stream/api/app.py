"""
Main FastAPI application factory.

This module creates and configures the FastAPI application with all routes,
middleware, and lifecycle management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..config import get_settings, log_configuration
from ..core import YotoClient
from ..database import init_db
from ..utils import log_environment_variables
from .dependencies import set_yoto_client
from .routes import admin, auth, cards, health, library, media, players, streams, user_auth
from .routes import settings as settings_routes
from .stream_manager import get_stream_manager

logger = logging.getLogger(__name__)


async def periodic_token_refresh(yoto_client: YotoClient, interval_hours: int = 12):
    """
    Periodically refresh OAuth tokens to prevent expiration.

    Access tokens expire in 24 hours. This task refreshes them every 12 hours
    to ensure tokens remain valid even during idle periods.

    Args:
        yoto_client: YotoClient instance to refresh tokens for
        interval_hours: Hours between token refresh attempts (default: 12)
    """
    interval_seconds = interval_hours * 3600
    logger.info(f"Starting background token refresh task (every {interval_hours} hours)")

    while True:
        try:
            await asyncio.sleep(interval_seconds)

            if yoto_client.is_authenticated():
                logger.info("Performing scheduled token refresh...")
                try:
                    # Run sync method in thread pool to avoid blocking event loop
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, yoto_client.ensure_authenticated)
                    logger.info("✓ Token refresh successful")
                except Exception as e:
                    logger.error(f"✗ Token refresh failed: {e}")
                    logger.error("  Tokens may expire if not refreshed manually")
            else:
                logger.debug("Skipping token refresh - client not authenticated")

        except asyncio.CancelledError:
            logger.info("Token refresh task cancelled")
            break
        except Exception as e:
            logger.error(f"Unexpected error in token refresh task: {e}")
            # Continue running despite errors


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown tasks:
    - Wait for Railway shared variables to initialize if configured
    - Initialize Yoto client
    - Authenticate with Yoto API
    - Connect to MQTT
    - Start background token refresh task
    - Cleanup on shutdown
    """
    settings = get_settings()

    # Initialize database
    logger.info("Initializing database...")
    logger.info(f"Database URL: {settings.database_url}")
    init_db()

    # Create default admin user if it doesn't exist
    from ..auth import get_password_hash
    from ..database import SessionLocal
    from ..models import User

    db = SessionLocal()
    try:
        # Count existing users
        user_count = db.query(User).count()
        logger.info(f"Current user count in database: {user_count}")

        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            try:
                # Hash password with error details
                logger.info("Hashing default password...")
                hashed = get_password_hash("yoto")
                logger.info(f"Password hash generated successfully (length: {len(hashed)} bytes)")

                admin_user = User(
                    username="admin",
                    email="eugenearchibald@gmail.com",
                    hashed_password=hashed,
                    is_active=True,
                    is_admin=True,
                )
                logger.info("User object created, committing to database...")
                db.add(admin_user)
                db.commit()
                logger.info("✓ Default admin user created (username: admin, password: yoto)")
            except Exception as hash_err:
                logger.error(f"Error during user creation: {hash_err}")
                import traceback

                logger.error(traceback.format_exc())
                db.rollback()
                raise
        else:
            logger.info(
                f"✓ Admin user already exists (id: {admin_user.id}, active: {admin_user.is_active})"
            )
    except Exception as e:
        logger.error(f"Failed to create admin user: {e}")
        logger.error(f"Database URL was: {settings.database_url}")
        db.rollback()
    finally:
        db.close()

    # Wait for Railway shared variables to initialize if configured
    # This helps when Railway shared variables take time to load at startup
    if settings.railway_startup_wait_seconds > 0:
        logger.info(
            f"Waiting {settings.railway_startup_wait_seconds} seconds for Railway shared variables to initialize..."
        )
        # Use asyncio.sleep for async context
        await asyncio.sleep(settings.railway_startup_wait_seconds)
        logger.info("Railway startup wait complete")

    # Log environment variables if configured
    if settings.log_env_on_startup:
        log_environment_variables(logger.info)

    # Enable debug logging for yoto_api library to see MQTT events
    yoto_api_logger = logging.getLogger("yoto_api")
    yoto_api_logger.setLevel(logging.DEBUG)
    mqtt_logger = logging.getLogger("paho.mqtt")
    mqtt_logger.setLevel(logging.INFO)

    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    yoto_client = None
    refresh_task = None
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

        # Start background token refresh task
        refresh_task = asyncio.create_task(
            periodic_token_refresh(yoto_client, settings.token_refresh_interval_hours)
        )

    except Exception as e:
        logger.error(f"⚠ Warning: Could not initialize Yoto API: {e}")
        logger.error("  Some endpoints may not work until authentication is completed.")

    # Create test stream with 1.mp3 through 10.mp3
    try:
        stream_manager = get_stream_manager()
        test_queue = await stream_manager.get_or_create_queue("test-stream")

        # Check if test files exist and add them to the queue
        test_files = [f"{i}.mp3" for i in range(1, 11)]
        existing_files = []
        for filename in test_files:
            audio_path = settings.audio_files_dir / filename
            if audio_path.exists():
                existing_files.append(filename)

        if existing_files:
            # Clear any existing files and add all test files
            test_queue.clear()
            for filename in existing_files:
                test_queue.add_file(filename)
            logger.info(f"✓ Test stream created with {len(existing_files)} files (1.mp3-10.mp3)")
        else:
            logger.warning("⚠ No test audio files (1.mp3-10.mp3) found for test stream")
    except Exception as e:
        logger.error(f"⚠ Failed to create test stream: {e}")

    yield  # Application runs here

    # Shutdown
    logger.info("Shutting down...")

    # Cancel background token refresh task
    if refresh_task:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            pass

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

    # Log configuration for debugging (after logging is configured)
    log_configuration(settings)

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
    app.include_router(user_auth.router, prefix="/api", tags=["User Authentication"])
    app.include_router(admin.router, prefix="/api", tags=["Admin"])
    app.include_router(settings_routes.router, prefix="/api", tags=["Settings"])
    app.include_router(auth.router, prefix="/api", tags=["Yoto Authentication"])
    app.include_router(players.router, prefix="/api", tags=["Players"])
    app.include_router(cards.router, prefix="/api", tags=["Cards"])
    app.include_router(library.router, prefix="/api", tags=["Library"])
    app.include_router(streams.router, prefix="/api", tags=["Streams"])
    app.include_router(media.router, prefix="/api", tags=["Media"])

    # PWA Routes - Service Worker and Manifest
    @app.get("/service-worker.js", tags=["PWA"])
    async def service_worker():
        """Serve the service worker for PWA functionality."""
        sw_path = static_dir / "service-worker.js"
        if sw_path.exists():
            return FileResponse(sw_path, media_type="application/javascript")
        raise HTTPException(status_code=404, detail="Service worker not found")

    @app.get("/manifest.json", tags=["PWA"])
    async def manifest():
        """Serve the PWA manifest file."""
        manifest_path = static_dir / "manifest.json"
        if manifest_path.exists():
            return FileResponse(manifest_path, media_type="application/json")
        raise HTTPException(status_code=404, detail="Manifest not found")

    @app.get("/login", tags=["Web UI"])
    async def login_page():
        """Serve the login page."""
        login_path = static_dir / "login.html"
        if login_path.exists():
            return FileResponse(login_path)
        return {"message": "Login page not available"}

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
    async def streams_ui():
        """Serve the music streams interface."""
        streams_path = static_dir / "streams.html"
        if streams_path.exists():
            return FileResponse(streams_path)
        return {"message": "Streams UI not available", "docs": "/docs"}

    @app.get("/library", tags=["Web UI"])
    async def library_ui():
        """Serve the library viewer interface."""
        library_path = static_dir / "library.html"
        if library_path.exists():
            return FileResponse(library_path)
        return {"message": "Library UI not available", "docs": "/docs"}

    @app.get("/audio-library", tags=["Web UI"])
    async def audio_library_ui():
        """Serve the audio library interface."""
        audio_library_path = static_dir / "audio-library.html"
        if audio_library_path.exists():
            return FileResponse(audio_library_path)
        return {"message": "Audio Library UI not available", "docs": "/docs"}

    @app.get("/audio/{filename}", tags=["Audio"])
    async def get_audio_file(filename: str):
        """
        Serve raw audio files from storage.

        For S3 storage: Returns presigned URL (307 redirect) for direct access.
        For local storage: Returns file directly via FileResponse.
        """
        safe_name = Path(filename).name  # Prevent path traversal
        storage = settings.get_storage()

        if not await storage.exists(safe_name):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found",
            )

        # For S3: return presigned URL (redirect)
        if settings.storage_backend == "s3":
            url = await storage.get_url(safe_name, expiry=settings.presigned_url_expiry)
            return RedirectResponse(url=url, status_code=307)

        # For local: return FileResponse (existing behavior)
        audio_path = settings.audio_files_dir / safe_name
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            filename=safe_name,
        )

    @app.get("/api/audio-preview/{preview_id}", tags=["Audio"])
    async def get_audio_preview(preview_id: str):
        """Serve temporary preview audio stored in workspace tmp/, auto-deleted via cleanup endpoint."""
        from pathlib import Path
        # Use workspace tmp/ directory instead of /tmp
        temp_path = settings.audio_files_dir.parent / 'tmp' / f"preview_{preview_id}.mp3"
        if not temp_path.exists():
            return JSONResponse(status_code=404, content={"detail": "Preview not found"})
        return FileResponse(str(temp_path), media_type="audio/mpeg")

    @app.get("/admin", tags=["Web UI"])
    async def admin_ui():
        """Serve the admin interface."""
        admin_path = static_dir / "admin.html"
        if admin_path.exists():
            return FileResponse(admin_path)
        return {"message": "Admin UI not available", "docs": "/docs"}

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


# WebSocket for stitch progress
@app.websocket("/ws/stitch/{task_id}")
async def stitch_progress_ws(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        # Import here to avoid circular import issues during app creation
        from .routes.cards import STITCH_TASKS

        task = STITCH_TASKS.get(task_id)
        if not task:
            await websocket.send_json({"event": "error", "message": "Task not found"})
            await websocket.close()
            return

        # Send initial snapshot
        await websocket.send_json({
            "event": "snapshot",
            "status": task.get("status"),
            "progress": task.get("progress"),
            "current_file": task.get("current_file"),
        })

        queue = task.get("queue")
        # Stream events until task finishes or client disconnects
        while True:
            try:
                message = await asyncio.wait_for(queue.get(), timeout=5.0)
                await websocket.send_json(message)
                # Stop after completed/failed/cancelled
                if message.get("event") in {"completed", "error", "cancelled"}:
                    break
            except asyncio.TimeoutError:
                # Periodic heartbeat with latest state
                current = STITCH_TASKS.get(task_id)
                if not current:
                    await websocket.send_json({"event": "error", "message": "Task missing"})
                    break
                await websocket.send_json({
                    "event": "heartbeat",
                    "status": current.get("status"),
                    "progress": current.get("progress"),
                    "current_file": current.get("current_file"),
                })
                if current.get("status") in {"completed", "failed", "cancelled"}:
                    break
    except WebSocketDisconnect:
        # Client disconnected; just exit
        return
    except Exception as e:
        try:
            await websocket.send_json({"event": "error", "message": str(e)})
        except Exception:
            pass
        try:
            await websocket.close()
        except Exception:
            pass
