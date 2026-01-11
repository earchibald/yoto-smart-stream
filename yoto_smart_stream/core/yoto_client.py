"""Core Yoto API client wrapper with enhanced features."""

import logging
from typing import Optional

from yoto_api import YotoManager

from ..config import Settings

logger = logging.getLogger(__name__)


class YotoClient:
    """
    Enhanced Yoto API client with authentication and error handling.

    This wraps the yoto_api library with additional features:
    - Automatic token refresh
    - Token persistence
    - Error handling
    """

    def __init__(self, settings: Settings):
        """
        Initialize Yoto client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.manager: Optional[YotoManager] = None
        self._authenticated = False

    def initialize(self) -> None:
        """Initialize YotoManager instance."""
        if self.manager is None:
            self.manager = YotoManager(client_id=self.settings.yoto_client_id)
            logger.info("YotoManager initialized")

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._authenticated and self.manager is not None

    def _save_refresh_token(self) -> None:
        """
        Save the current refresh token to file.

        This should be called after any operation that may update the refresh token,
        including authentication and token refresh operations.
        """
        if self.manager and self.manager.token and self.manager.token.refresh_token:
            token_file = self.settings.yoto_refresh_token_file
            # Ensure parent directory exists
            token_file.parent.mkdir(parents=True, exist_ok=True)
            token_file.write_text(self.manager.token.refresh_token)
            logger.debug("Refresh token saved to %s", token_file)
        else:
            logger.warning("No refresh token available to save")

    def authenticate(self) -> None:
        """
        Authenticate with Yoto API using stored refresh token.

        Raises:
            FileNotFoundError: If refresh token file doesn't exist
            Exception: If authentication fails
        """
        self.initialize()

        token_file = self.settings.yoto_refresh_token_file
        if not token_file.exists():
            raise FileNotFoundError(
                f"Refresh token file not found: {token_file}. "
                "Run authentication first with examples/simple_client.py"
            )

        refresh_token = token_file.read_text().strip()
        self.manager.set_refresh_token(refresh_token)

        try:
            self.manager.check_and_refresh_token()
            self._authenticated = True
            # Save the new refresh token (OAuth2 returns new refresh token on refresh)
            self._save_refresh_token()
            logger.info("Successfully authenticated with Yoto API")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise

    def ensure_authenticated(self) -> None:
        """Ensure client is authenticated, authenticate if needed."""
        if not self.is_authenticated():
            self.authenticate()
        else:
            # Refresh token if needed
            try:
                self.manager.check_and_refresh_token()
                # Save the new refresh token after successful refresh
                self._save_refresh_token()
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
                # Try full authentication
                self.authenticate()

    def update_player_status(self) -> None:
        """Update player status from API."""
        self.ensure_authenticated()
        self.manager.update_players_status()
        logger.debug(f"Updated status for {len(self.manager.players)} players")

    def connect_mqtt(self) -> None:
        """Connect to MQTT for real-time events."""
        self.ensure_authenticated()
        try:
            self.manager.connect_to_events()
            logger.info("Connected to MQTT")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            raise

    def disconnect_mqtt(self) -> None:
        """Disconnect from MQTT."""
        if self.manager and hasattr(self.manager, "disconnect_from_events"):
            try:
                self.manager.disconnect_from_events()
                logger.info("Disconnected from MQTT")
            except Exception as e:
                logger.warning(f"Error disconnecting from MQTT: {e}")

    def get_manager(self) -> YotoManager:
        """
        Get the underlying YotoManager instance.

        Returns:
            YotoManager instance

        Raises:
            RuntimeError: If not authenticated
        """
        if not self.is_authenticated():
            raise RuntimeError("Client not authenticated. Call authenticate() first.")
        return self.manager

    def get_access_token(self) -> Optional[str]:
        """
        Get the current access token from the YotoManager.
        
        Returns:
            Access token string, or None if not available
            
        Raises:
            RuntimeError: If not authenticated
        """
        if not self.is_authenticated():
            raise RuntimeError("Client not authenticated. Call authenticate() first.")
        
        # The yoto_api library stores tokens in manager.token object
        if hasattr(self.manager, 'token') and self.manager.token:
            # token object should have access_token attribute
            if hasattr(self.manager.token, 'access_token'):
                return self.manager.token.access_token
            # Or it might be stored as 'token' string directly
            elif isinstance(self.manager.token, str):
                return self.manager.token
        
        return None

    def set_authenticated(self, authenticated: bool) -> None:
        """
        Set authentication status.

        Args:
            authenticated: Authentication status
        """
        self._authenticated = authenticated
        logger.debug(f"Authentication status set to: {authenticated}")

    def reset(self) -> None:
        """
        Reset client state and clear authentication.

        This clears the authentication flag and resets the manager instance.
        Used during logout or when needing to re-authenticate.
        """
        self._authenticated = False
        self.manager = None
        logger.info("Client state reset")
