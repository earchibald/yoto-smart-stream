"""Core Yoto API client wrapper with enhanced features."""

import logging
from typing import Optional

from yoto_api import YotoManager

from ..config import Settings
from .oauth_client import OAuth2ConfidentialClient

logger = logging.getLogger(__name__)


class YotoClient:
    """
    Enhanced Yoto API client with authentication and error handling.

    This wraps the yoto_api library with additional features:
    - Automatic token refresh
    - Token persistence
    - Error handling
    - Support for both public (device code) and confidential (with secret) OAuth flows
    """

    def __init__(self, settings: Settings):
        """
        Initialize Yoto client.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.manager: Optional[YotoManager] = None
        self.oauth_client: Optional[OAuth2ConfidentialClient] = None
        self._authenticated = False
        self._uses_confidential_flow = False
        
        # Determine which OAuth flow to use
        if settings.yoto_client_secret:
            self._uses_confidential_flow = True
            logger.info("Initializing with confidential client flow (client secret provided)")
        else:
            logger.info("Initializing with public client flow (device code flow)")

    def initialize(self) -> None:
        """Initialize YotoManager or OAuth2ConfidentialClient instance."""
        if self._uses_confidential_flow:
            # Use confidential client with secret
            if self.oauth_client is None:
                self.oauth_client = OAuth2ConfidentialClient(
                    client_id=self.settings.yoto_client_id,
                    client_secret=self.settings.yoto_client_secret
                )
                logger.info("OAuth2ConfidentialClient initialized")
        else:
            # Use standard yoto_api manager for device code flow
            if self.manager is None:
                self.manager = YotoManager(client_id=self.settings.yoto_client_id)
                logger.info("YotoManager initialized")

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._authenticated and (self.manager is not None or self.oauth_client is not None)

    def authenticate(self) -> None:
        """
        Authenticate with Yoto API using stored refresh token.
        
        Supports both confidential (with secret) and public (device code) flows.

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
        
        try:
            if self._uses_confidential_flow:
                # Use confidential client with secret
                token_data = self.oauth_client.refresh_token(refresh_token)
                # Store the new tokens (confidential flow returns new refresh token)
                if "refresh_token" in token_data:
                    token_file.write_text(token_data["refresh_token"])
                    logger.info("Updated refresh token from confidential client")
                self._authenticated = True
                logger.info("Successfully authenticated with confidential client flow")
            else:
                # Use standard yoto_api manager for device code flow
                self.manager.set_refresh_token(refresh_token)
                self.manager.check_and_refresh_token()
                self._authenticated = True
                logger.info("Successfully authenticated with public client flow")
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
                if self._uses_confidential_flow:
                    # For confidential client, re-authenticate to refresh
                    self.authenticate()
                else:
                    # For public client, use standard refresh
                    self.manager.check_and_refresh_token()
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
                # Try full authentication
                self.authenticate()

    def update_player_status(self) -> None:
        """Update player status from API."""
        self.ensure_authenticated()
        if self._uses_confidential_flow:
            logger.warning("Player status update not available with confidential client flow - requires full YotoManager")
            return
        self.manager.update_players_status()
        logger.debug(f"Updated status for {len(self.manager.players)} players")

    def connect_mqtt(self) -> None:
        """Connect to MQTT for real-time events."""
        self.ensure_authenticated()
        if self._uses_confidential_flow:
            logger.warning("MQTT connection not available with confidential client flow - requires full YotoManager")
            return
        try:
            self.manager.connect_to_events()
            logger.info("Connected to MQTT")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            raise

    def disconnect_mqtt(self) -> None:
        """Disconnect from MQTT."""
        if self._uses_confidential_flow:
            return
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
            RuntimeError: If not authenticated or using confidential client flow
        """
        if self._uses_confidential_flow:
            raise RuntimeError("YotoManager not available when using confidential client flow. Use YotoAPI directly or switch to device code flow.")
        if not self.is_authenticated():
            raise RuntimeError("Client not authenticated. Call authenticate() first.")
        return self.manager

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
