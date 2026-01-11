"""Tests for configuration management."""

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
