"""
Configuration management for Yoto Smart Stream.

Handles environment variables and application settings.
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    app_version: str = "0.2.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    log_level: str = Field(default="INFO", description="Logging level")
    environment: str = Field(default="development", description="Environment name")

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

    # Storage settings
    audio_files_dir: Path = Field(default=Path("audio_files"), description="Audio files directory")
    database_url: str = Field(
        default="sqlite:///./yoto_smart_stream.db", description="Database connection URL"
    )

    # MQTT settings
    mqtt_enabled: bool = Field(default=True, description="Enable MQTT event handling")

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
