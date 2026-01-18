"""
Main FastAPI application factory.

This module creates and configures the FastAPI application with all routes,
middleware, and lifecycle management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
import os

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from ..config import get_settings, log_configuration
from ..core import YotoClient
from ..database import init_db
from ..utils import log_environment_variables
from .dependencies import set_yoto_client
from .routes import admin, auth, cards, health, library, players, streams, user_auth
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

    use_dynamo = bool(settings.dynamodb_table or os.environ.get("DYNAMODB_TABLE"))

    if use_dynamo:
        logger.info("Initializing DynamoDB store...")
        from ..auth import get_password_hash
        from ..storage.dynamodb_store import get_store

        store = get_store(settings.dynamodb_table, region_name=settings.dynamodb_region)
        admin = store.ensure_admin_user(
            hashed_password=get_password_hash("yoto"),
            email="eugenearchibald@gmail.com",
        )
        logger.info("✓ DynamoDB admin bootstrap complete")
    elif settings.database_url:
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
                        is_admin=True
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
                logger.info(f"✓ Admin user already exists (id: {admin_user.id}, active: {admin_user.is_active})")
        except Exception as e:
            logger.error(f"Failed to create admin user: {e}")
            logger.error(f"Database URL was: {settings.database_url}")
            db.rollback()
        finally:
            db.close()
    else:
        logger.info("Skipping database initialization and admin bootstrap (database_url not configured)")

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
    yoto_api_logger = logging.getLogger('yoto_api')
    yoto_api_logger.setLevel(logging.DEBUG)
    mqtt_logger = logging.getLogger('paho.mqtt')
    mqtt_logger.setLevel(logging.INFO)
    
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    yoto_client = None
    refresh_task = None
    try:
        # Initialize Yoto client (always, even if auth fails)
        yoto_client = YotoClient(settings)
        set_yoto_client(yoto_client)
        
        # Try to authenticate with existing token
        try:
            yoto_client.authenticate()
            yoto_client.update_player_status()
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
        except Exception as auth_error:
            logger.warning(f"⚠ Could not authenticate with Yoto API on startup: {auth_error}")
            logger.warning("  User must complete OAuth flow to use player features")

    except Exception as e:
        logger.error(f"⚠ Warning: Could not initialize Yoto client: {e}")
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

    # S3-based static file serving
    s3_client = boto3.client('s3')
    ui_bucket_name = os.getenv('S3_UI_BUCKET', '')

    async def serve_from_s3(file_path: str, content_type: str = "text/html"):
        """Helper function to serve files from S3 with local fallback."""
        # Try S3 first
        if ui_bucket_name:
            try:
                response = s3_client.get_object(
                    Bucket=ui_bucket_name,
                    Key=file_path
                )
                content = response['Body'].read()
                return Response(
                    content=content,
                    media_type=content_type,
                    headers={"Cache-Control": "public, max-age=3600"}
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'NoSuchKey':
                    logger.warning(f"File not found in S3: {file_path}, trying local")
                else:
                    logger.error(f"S3 error fetching {file_path}: {e}")
        
        # Fallback to local file (for development/backward compatibility)
        local_path = static_dir / file_path
        if local_path.exists():
            return FileResponse(local_path)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found: {file_path}"
        )

    # Serve static assets (CSS, JS, images)
    @app.get("/static/{file_path:path}", tags=["Static Files"])
    async def serve_static(file_path: str):
        """Serve static files (CSS, JS, images) from S3."""
        # Determine content type
        content_type = "application/octet-stream"
        if file_path.endswith('.css'):
            content_type = "text/css"
        elif file_path.endswith('.js'):
            content_type = "application/javascript"
        elif file_path.endswith('.png'):
            content_type = "image/png"
        elif file_path.endswith('.jpg') or file_path.endswith('.jpeg'):
            content_type = "image/jpeg"
        elif file_path.endswith('.svg'):
            content_type = "image/svg+xml"
        
        return await serve_from_s3(file_path, content_type)

    # Include routers
    app.include_router(health.router, prefix="/api", tags=["Health"])
    app.include_router(user_auth.router, prefix="/api", tags=["User Authentication"])
    app.include_router(admin.router, prefix="/api", tags=["Admin"])
    app.include_router(auth.router, prefix="/api", tags=["Yoto Authentication"])
    app.include_router(players.router, prefix="/api", tags=["Players"])
    app.include_router(cards.router, prefix="/api", tags=["Cards"])
    app.include_router(library.router, prefix="/api", tags=["Library"])
    app.include_router(streams.router, prefix="/api", tags=["Streams"])

    # HTML page routes
    @app.get("/login", tags=["Web UI"])
    async def login_page():
        """Serve the login page from S3."""
        return await serve_from_s3("login.html", "text/html")

    @app.get("/", tags=["Web UI"])
    async def root():
        """Serve the admin dashboard web UI from S3."""
        return await serve_from_s3("index.html", "text/html")

    @app.get("/streams", tags=["Web UI"])
    async def streams_ui():
        """Serve the music streams interface from S3."""
        return await serve_from_s3("streams.html", "text/html")

    @app.get("/library", tags=["Web UI"])
    async def library_ui():
        """Serve the library viewer interface from S3."""
        return await serve_from_s3("library.html", "text/html")

    @app.get("/audio-library", tags=["Web UI"])
    async def audio_library_ui():
        """Serve the audio library interface from S3."""
        return await serve_from_s3("audio-library.html", "text/html")

    @app.get("/audio/{filename}", tags=["Audio"], response_class=FileResponse)
    async def get_audio_file(filename: str):
        """Serve raw audio files from the configured audio directory."""
        safe_name = Path(filename).name  # Prevent path traversal
        audio_path = settings.audio_files_dir / safe_name

        if not audio_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file not found",
            )

        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            filename=safe_name,
        )

    @app.get("/admin", tags=["Web UI"])
    async def admin_ui():
        """Serve the admin interface from S3."""
        return await serve_from_s3("admin.html", "text/html")

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
