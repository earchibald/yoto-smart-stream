"""Tests for configuration management."""

import pytest
from pydantic import ValidationError

from yoto_smart_stream.config import Settings


class TestEnvironmentConfiguration:
    """Test environment variable configuration priority."""

    def test_railway_environment_name_takes_priority(self, monkeypatch):
        """Test that RAILWAY_ENVIRONMENT_NAME takes priority over ENVIRONMENT."""
        # Set both variables
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "pr-123")
        monkeypatch.setenv("ENVIRONMENT", "staging")

        settings = Settings()
        assert settings.environment == "pr-123"

    def test_environment_fallback_when_no_railway_var(self, monkeypatch):
        """Test that ENVIRONMENT is used when RAILWAY_ENVIRONMENT_NAME is not set."""
        # Clear RAILWAY_ENVIRONMENT_NAME if it exists
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "staging")

        settings = Settings()
        assert settings.environment == "staging"

    def test_default_when_no_env_vars(self, monkeypatch):
        """Test that default value is used when neither variable is set."""
        # Clear both variables
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        settings = Settings()
        assert settings.environment == "development"

    def test_railway_environment_name_production(self, monkeypatch):
        """Test with production environment name from Railway."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")

        settings = Settings()
        assert settings.environment == "production"

    def test_railway_environment_name_staging(self, monkeypatch):
        """Test with staging environment name from Railway."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "staging")

        settings = Settings()
        assert settings.environment == "staging"

    def test_railway_environment_name_pr_format(self, monkeypatch):
        """Test with PR environment name format from Railway."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "pr-42")

        settings = Settings()
        assert settings.environment == "pr-42"

    def test_backward_compatibility_preview(self, monkeypatch):
        """Test backward compatibility with ENVIRONMENT=preview."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        monkeypatch.setenv("ENVIRONMENT", "preview")

        settings = Settings()
        assert settings.environment == "preview"


class TestOtherSettings:
    """Test other configuration settings remain unchanged."""

    def test_default_settings(self, monkeypatch):
        """Test that other default settings work correctly."""
        # Clear environment variables that might affect the test
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
        monkeypatch.delenv("ENVIRONMENT", raising=False)

        settings = Settings()

        assert settings.app_name == "Yoto Smart Stream"
        assert settings.debug is False
        assert settings.log_level == "INFO"
        assert settings.host == "0.0.0.0"
        assert settings.port == 8080

    def test_custom_settings_override(self, monkeypatch):
        """Test that custom settings can override defaults."""
        monkeypatch.setenv("DEBUG", "true")
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("PORT", "3000")

        settings = Settings()

        assert settings.debug is True
        assert settings.log_level == "DEBUG"
        assert settings.port == 3000


class TestRailwayStartupWait:
    """Test Railway startup wait configuration."""

    def test_default_railway_startup_wait(self, monkeypatch):
        """Test that default railway_startup_wait_seconds is 0."""
        monkeypatch.delenv("RAILWAY_STARTUP_WAIT_SECONDS", raising=False)

        settings = Settings()
        assert settings.railway_startup_wait_seconds == 0

    def test_railway_startup_wait_from_env(self, monkeypatch):
        """Test that RAILWAY_STARTUP_WAIT_SECONDS can be set from environment."""
        monkeypatch.setenv("RAILWAY_STARTUP_WAIT_SECONDS", "10")

        settings = Settings()
        assert settings.railway_startup_wait_seconds == 10

    def test_railway_startup_wait_custom_value(self, monkeypatch):
        """Test that custom wait times work correctly."""
        monkeypatch.setenv("RAILWAY_STARTUP_WAIT_SECONDS", "5")

        settings = Settings()
        assert settings.railway_startup_wait_seconds == 5

    def test_railway_startup_wait_max_value(self, monkeypatch):
        """Test that maximum wait time (30s) is enforced."""
        monkeypatch.setenv("RAILWAY_STARTUP_WAIT_SECONDS", "30")

        settings = Settings()
        assert settings.railway_startup_wait_seconds == 30

    def test_railway_startup_wait_exceeds_max(self, monkeypatch):
        """Test that values exceeding 30 seconds are rejected."""
        monkeypatch.setenv("RAILWAY_STARTUP_WAIT_SECONDS", "60")

        with pytest.raises(ValidationError):
            Settings()

    def test_railway_startup_wait_negative(self, monkeypatch):
        """Test that negative values are rejected."""
        monkeypatch.setenv("RAILWAY_STARTUP_WAIT_SECONDS", "-1")

        with pytest.raises(ValidationError):
            Settings()

    def test_railway_startup_wait_zero(self, monkeypatch):
        """Test that zero is a valid value (no wait)."""
        monkeypatch.setenv("RAILWAY_STARTUP_WAIT_SECONDS", "0")

        settings = Settings()
        assert settings.railway_startup_wait_seconds == 0
