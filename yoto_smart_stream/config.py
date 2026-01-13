"""
Configuration management for Yoto Smart Stream.

Handles environment variables and application settings.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application settings
    app_name: str = "Yoto Smart Stream"
    app_version: str = "0.2.1"
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    log_full_streams_requests: bool = Field(
        default=False, description="Log full HTTP requests (headers and body) for audio stream endpoints"
    )
    environment: str = Field(
        default="development",
        description="Environment name (auto-populated from RAILWAY_ENVIRONMENT_NAME)",
    )

    @field_validator("environment", mode="before")
    @classmethod
    def get_environment_name(cls, v):
        """Get environment name from RAILWAY_ENVIRONMENT_NAME or fall back to ENVIRONMENT."""
        # Priority: RAILWAY_ENVIRONMENT_NAME > ENVIRONMENT > provided value > default
        railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME")
        if railway_env:
            return railway_env

        # Fall back to ENVIRONMENT for backward compatibility
        env_var = os.environ.get("ENVIRONMENT")
        if env_var:
            return env_var

        # Use provided value or default
        return v if v is not None else "development"

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8080, description="Server port")
    public_url: Optional[str] = Field(
        default=None, description="Public URL for audio streaming (e.g., https://example.ngrok.io)"
    )

    # Yoto API settings
    yoto_client_id: Optional[str] = Field(None, description="Yoto API client ID")
    yoto_refresh_token_file: Path = Field(
        default=Path(".yoto_refresh_token"), description="Path to refresh token file"
    )

    @field_validator("yoto_refresh_token_file", mode="before")
    @classmethod
    def get_token_file_path(cls, v):
        """
        Get token file path based on environment.

        Uses /data directory for Railway deployments (persistent volume),
        falls back to local path for development.
        """
        # Check if running on Railway (has RAILWAY_ENVIRONMENT_NAME set)
        railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME")

        if railway_env:
            # On Railway, use persistent volume at /data
            data_dir = Path("/data")
            # Try to create directory if it doesn't exist
            # This will succeed on Railway, but may fail in test environments
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as e:
                # In test environments, /data may not be writable
                # Use the path anyway - it will be created at runtime on Railway
                logger.debug(
                    f"Could not create {data_dir} during validation (expected in tests): {e}"
                )
            return data_dir / ".yoto_refresh_token"

        # Local development - use current directory or provided value
        if isinstance(v, (str, Path)):
            return Path(v)
        return Path(".yoto_refresh_token")

    # Storage settings
    audio_files_dir: Path = Field(default=Path("audio_files"), description="Audio files directory")
    
    @field_validator("audio_files_dir", mode="before")
    @classmethod
    def get_audio_files_dir(cls, v):
        """
        Get audio files directory based on environment.
        
        Uses /data directory for Railway deployments (persistent volume) so TTS
        files survive restarts. Falls back to local path for development.
        """
        # Check if running on Railway (has RAILWAY_ENVIRONMENT_NAME set)
        railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME")
        
        if railway_env:
            # On Railway, use persistent volume at /data/audio_files
            data_dir = Path("/data/audio_files")
            # Try to create directory if it doesn't exist
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as e:
                logger.debug(
                    f"Could not create {data_dir} during validation (expected in tests): {e}"
                )
            return data_dir
        
        # Local development - use provided value or default
        if v and str(v) != "audio_files":
            return v if isinstance(v, Path) else Path(v)
        return Path("audio_files")
    database_url: str = Field(
        default="sqlite:///./yoto_smart_stream.db", description="Database connection URL"
    )
    
    @field_validator("database_url", mode="before")
    @classmethod
    def get_database_url(cls, v):
        """
        Get database URL based on environment.
        
        Uses /data directory for Railway deployments (persistent volume) with
        environment-specific database names to avoid conflicts between environments.
        Falls back to local path for development.
        """
        # Check if running on Railway (has RAILWAY_ENVIRONMENT_NAME set)
        railway_env = os.environ.get("RAILWAY_ENVIRONMENT_NAME")
        
        if railway_env:
            # On Railway, use persistent volume at /data with environment-specific name
            # This prevents different environments from sharing the same database
            data_dir = Path("/data")
            # Try to create directory if it doesn't exist
            try:
                data_dir.mkdir(parents=True, exist_ok=True)
            except (PermissionError, OSError) as e:
                logger.debug(
                    f"Could not create {data_dir} during validation (expected in tests): {e}"
                )
            # Use environment name in database filename (e.g., yoto_smart_stream_pr-56.db)
            db_filename = f"yoto_smart_stream_{railway_env}.db"
            return f"sqlite:///{data_dir}/{db_filename}"
        
        # Local development - use provided value or default
        if v and v != "sqlite:///./yoto_smart_stream.db":
            return v
        return "sqlite:///./yoto_smart_stream.db"

    # MQTT settings
    mqtt_enabled: bool = Field(default=True, description="Enable MQTT event handling")

    # Token refresh settings
    token_refresh_interval_hours: int = Field(
        default=12,
        description="Hours between automatic token refresh (1-23, default: 12)",
        ge=1,
        le=23,
    )

    # Railway startup settings
    railway_startup_wait_seconds: int = Field(
        default=0,
        description="Seconds to wait at startup for Railway shared variables to initialize (0-30)",
        ge=0,
        le=30,
    )
    log_env_on_startup: bool = Field(
        default=False,
        description="Log all environment variables on startup (useful for debugging Railway variables)",
    )

    # CORS settings
    cors_origins: list[str] = Field(
        default=["http://localhost:8080", "http://localhost:3000"],
        description="Allowed CORS origins",
    )

    def __init__(self, **kwargs):
        """Initialize settings and create required directories."""
        super().__init__(**kwargs)
        self.audio_files_dir.mkdir(exist_ok=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def log_configuration(settings: Settings) -> None:
    """
    Log configuration details for debugging.

    This should be called after logging is configured.
    """
    import os

    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("YOTO SMART STREAM CONFIGURATION")
    logger.info("=" * 60)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Log level: {settings.log_level}")
    logger.info(f"YOTO_CLIENT_ID from env: {os.environ.get('YOTO_CLIENT_ID', 'NOT SET')}")
    logger.info(f"YOTO_CLIENT_ID loaded: {settings.yoto_client_id or 'NOT SET'}")
    logger.info(f"Refresh token file: {settings.yoto_refresh_token_file}")
    logger.info(f"Public URL: {settings.public_url or 'NOT SET'}")
    logger.info("=" * 60)
