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


class TestLogEnvOnStartup:
    """Test log_env_on_startup configuration."""

    def test_default_log_env_on_startup(self, monkeypatch):
        """Test that default log_env_on_startup is False."""
        monkeypatch.delenv("LOG_ENV_ON_STARTUP", raising=False)

        settings = Settings()
        assert settings.log_env_on_startup is False

    def test_log_env_on_startup_enabled(self, monkeypatch):
        """Test that LOG_ENV_ON_STARTUP can be enabled."""
        monkeypatch.setenv("LOG_ENV_ON_STARTUP", "true")

        settings = Settings()
        assert settings.log_env_on_startup is True

    def test_log_env_on_startup_disabled(self, monkeypatch):
        """Test that LOG_ENV_ON_STARTUP can be explicitly disabled."""
        monkeypatch.setenv("LOG_ENV_ON_STARTUP", "false")

        settings = Settings()
        assert settings.log_env_on_startup is False


class TestTokenFilePath:
    """Test token file path configuration based on environment."""

    def test_local_development_default_path(self, monkeypatch):
        """Test that local development uses default .yoto_refresh_token path."""
        # Clear Railway environment variable
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)

        settings = Settings()
        # Should use current directory
        assert settings.yoto_refresh_token_file.name == ".yoto_refresh_token"
        # Should not be in /data
        assert "/data" not in str(settings.yoto_refresh_token_file)

    def test_railway_uses_persistent_volume(self, monkeypatch, tmp_path):
        """Test that Railway environment uses /data volume for token."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")

        # Mock the /data directory to use tmp_path for testing
        data_dir = tmp_path / "data"
        data_dir.mkdir(exist_ok=True)

        # Patch Path to redirect /data to our test directory
        import yoto_smart_stream.config
        original_path = yoto_smart_stream.config.Path

        def mock_path(path_str):
            if path_str == "/data":
                return data_dir
            return original_path(path_str)

        monkeypatch.setattr("yoto_smart_stream.config.Path", mock_path)

        settings = Settings()
        assert settings.yoto_refresh_token_file.name == ".yoto_refresh_token"
        # Should be under data directory
        assert "data" in str(settings.yoto_refresh_token_file)

    def test_railway_staging_uses_persistent_volume(self, monkeypatch):
        """Test that Railway staging environment also uses persistent volume."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "staging")

        settings = Settings()
        # Should use /data path on Railway
        assert str(settings.yoto_refresh_token_file).startswith("/data")

    def test_railway_pr_environment_uses_persistent_volume(self, monkeypatch):
        """Test that Railway PR environments use persistent volume."""
        monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "pr-123")

        settings = Settings()
        # Should use /data path on Railway
        assert str(settings.yoto_refresh_token_file).startswith("/data")

    def test_custom_token_file_path_local(self, monkeypatch, tmp_path):
        """Test that custom token file path works in local development."""
        monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)

        custom_path = tmp_path / "custom_token.txt"
        monkeypatch.setenv("YOTO_REFRESH_TOKEN_FILE", str(custom_path))

        settings = Settings()
        assert settings.yoto_refresh_token_file == custom_path


class TestDatabaseUrlSelection:
    """Test database URL selection for MySQL and SQLite."""

    def _clear_database_env(self, monkeypatch):
        for var in [
            "MYSQL_URL",
            "MYSQLHOST",
            "MYSQLPORT",
            "MYSQLUSER",
            "MYSQLPASSWORD",
            "MYSQLDATABASE",
            "RAILWAY_ENVIRONMENT_NAME",
            "ENVIRONMENT",
        ]:
            monkeypatch.delenv(var, raising=False)

    def test_mysql_url_normalized_from_env(self, monkeypatch):
        """MYSQL_URL should be preferred and normalized to pymysql driver."""
        self._clear_database_env(monkeypatch)
        monkeypatch.setenv("MYSQL_URL", "mysql://user:pass@railway-host:3306/appdb")

        settings = Settings()

        assert settings.database_url == "mysql+pymysql://user:pass@railway-host:3306/appdb"

    def test_mysql_url_built_from_components(self, monkeypatch):
        """Build MySQL URL from Railway component variables when MYSQL_URL is absent."""
        self._clear_database_env(monkeypatch)
        monkeypatch.setenv("MYSQLHOST", "railway-db")
        monkeypatch.setenv("MYSQLPORT", "3307")
        monkeypatch.setenv("MYSQLUSER", "db-user")
        monkeypatch.setenv("MYSQLPASSWORD", "p@ss word")
        monkeypatch.setenv("MYSQLDATABASE", "dbname")

        settings = Settings()

        assert (
            settings.database_url
            == "mysql+pymysql://db-user:p%40ss+word@railway-db:3307/dbname"
        )

    def test_sqlite_default_without_mysql(self, monkeypatch):
        """Fallback to SQLite when no MySQL variables are set."""
        self._clear_database_env(monkeypatch)

        settings = Settings()

        assert settings.database_url == "sqlite:///./yoto_smart_stream.db"
