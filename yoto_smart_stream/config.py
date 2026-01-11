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
        # Exclude yoto_client_id from automatic env var loading
        # We handle it manually in the validator for backward compatibility
        env_ignore={"yoto_client_id"},
    )

    # Application settings
    app_name: str = "Yoto Smart Stream"
    app_version: str = "0.2.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
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
    # Note: This field is manually populated from YOTO_SERVER_CLIENT_ID or YOTO_CLIENT_ID
    # in the validator to support backward compatibility
    yoto_client_id: Optional[str] = Field(
        default=None, 
        description="Yoto API server client ID (for OAuth2 device flow)",
        validate_default=True
    )

    @field_validator("yoto_client_id", mode="before")
    @classmethod
    def get_client_id(cls, v, info):
        """
        Get client ID with backward compatibility.
        
        Prefers YOTO_SERVER_CLIENT_ID over legacy YOTO_CLIENT_ID.
        This validator runs before pydantic's environment variable loading,
        so we manually check both variable names.
        """
        import os
        
        # Check for new variable name first (highest priority)
        server_client_id = os.environ.get("YOTO_SERVER_CLIENT_ID")
        if server_client_id:
            return server_client_id
        
        # Fallback to legacy variable name for backward compatibility
        legacy_client_id = os.environ.get("YOTO_CLIENT_ID")
        if legacy_client_id:
            return legacy_client_id
        
        # If neither is set, return None
        return None
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
    database_url: str = Field(
        default="sqlite:///./yoto_smart_stream.db", description="Database connection URL"
    )

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
    # Check both YOTO_SERVER_CLIENT_ID (new) and YOTO_CLIENT_ID (deprecated)
    server_client_id = os.environ.get('YOTO_SERVER_CLIENT_ID')
    legacy_client_id = os.environ.get('YOTO_CLIENT_ID')
    logger.info(f"YOTO_SERVER_CLIENT_ID from env: {server_client_id or 'NOT SET'}")
    logger.info(f"YOTO_CLIENT_ID from env (deprecated): {legacy_client_id or 'NOT SET'}")
    logger.info(f"Loaded client_id: {settings.yoto_client_id or 'NOT SET'}")
    logger.info(f"Refresh token file: {settings.yoto_refresh_token_file}")
    logger.info(f"Public URL: {settings.public_url or 'NOT SET'}")
    logger.info("=" * 60)
