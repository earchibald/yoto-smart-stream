"""Core Yoto API client wrapper with enhanced features."""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import Optional

from yoto_api import YotoManager

from ..config import Settings
from ..api.mqtt_event_store import MQTTEvent, get_mqtt_event_store

logger = logging.getLogger(__name__)

# Module-level cache for expensive API calls (persists across Lambda invocations in same container)
_player_status_cache_time: Optional[float] = None
_library_cache_time: Optional[float] = None
_CACHE_TTL = 5.0  # seconds - cache TTL for player status and library


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
            try:
                from ..storage.secrets_manager import load_client_credentials
                creds = load_client_credentials()
                client_id = (creds.client_id if creds and creds.client_id else self.settings.yoto_client_id)
            except Exception:
                client_id = self.settings.yoto_client_id
            self.manager = YotoManager(client_id=client_id)
            logger.info("YotoManager initialized")

    def is_authenticated(self) -> bool:
        """Check if client is authenticated."""
        return self._authenticated and self.manager is not None

    def _save_refresh_token(self, user_id: Optional[str] = None, lock_owner: Optional[str] = None, clear_lock: bool = False) -> None:
        """
        Save the current refresh token to DynamoDB, Secrets Manager, and/or file.

        This should be called after any operation that may update the refresh token,
        including authentication and token refresh operations.
        
        Args:
            user_id: User identifier (ignored, kept for backward compatibility)
        """
        if self.manager and self.manager.token and self.manager.token.refresh_token:
            # Try to save to DynamoDB first (primary storage - most reliable)
            try:
                from ..storage.dynamodb_store import get_store
                store = get_store(self.settings.dynamodb_table, region_name=self.settings.dynamodb_region)
                store.save_yoto_tokens(
                    username="admin",
                    refresh_token=self.manager.token.refresh_token,
                    access_token=getattr(self.manager.token, "access_token", None),
                    expires_at=getattr(self.manager.token, "expires_at", None),
                    lock_owner=lock_owner,
                    clear_lock=clear_lock,
                )
                logger.info("✓ Refresh token saved to DynamoDB")
            except Exception as e:
                logger.debug(f"Failed to save token to DynamoDB: {e}")
            
            # Per security model, do not store dynamic tokens in Secrets Manager
            logger.debug("Skipping Secrets Manager backup for tokens; using DynamoDB only")
        else:
            logger.warning("No refresh token available to save")
    
    def _save_token_to_file(self) -> None:
        """Save refresh token to file (for local development)."""
        if self.manager and self.manager.token and self.manager.token.refresh_token:
            token_file = self.settings.yoto_refresh_token_file
            token_file.parent.mkdir(parents=True, exist_ok=True)
            token_file.write_text(self.manager.token.refresh_token)
            logger.debug("Refresh token saved to %s", token_file)
        else:
            logger.warning("No refresh token available to save")

    def authenticate(self, user_id: Optional[str] = None, force_reload: bool = False) -> None:
        """
        Authenticate with Yoto API using stored refresh token from DynamoDB, Secrets Manager, or file.

        Args:
            user_id: User identifier (ignored, kept for backward compatibility)

        Raises:
            FileNotFoundError: If refresh token not found in any storage location
            Exception: If authentication fails
        """
        self.initialize()

        if force_reload:
            logger.debug("Force reload requested; bypassing any cached auth state")

        # Always reload token from persistence to avoid stale values
        refresh_token = None
        access_token = None
        expires_at = None
        logger.info("Authenticating with Yoto API (fresh token load)...")
        self._authenticated = False

        # Try loading from DynamoDB first (primary storage - most reliable)
        lock_owner = str(uuid.uuid4())
        store = None
        try:
            from ..storage.dynamodb_store import get_store
            store = get_store(self.settings.dynamodb_table, region_name=self.settings.dynamodb_region)
            tokens = store.load_yoto_tokens("admin")
            if tokens:
                refresh_token = tokens[0]
                access_token = tokens[1]
                expires_at = tokens[2]
                logger.info("✓ Loaded refresh token from DynamoDB")
                logger.debug(f"🔍 Loaded refresh token: {str(refresh_token)[:50]}..." if len(str(refresh_token)) > 50 else f"🔍 Loaded refresh token: {refresh_token}")
                logger.debug(f"🔍 Token type: {type(refresh_token)}, length: {len(str(refresh_token))}")
        except Exception as e:
            logger.debug(f"Failed to load token from DynamoDB: {e}")
        
        # Fall back to Secrets Manager if not found in DynamoDB
        if not refresh_token:
            try:
                from ..storage.secrets_manager import load_yoto_tokens
                tokens = load_yoto_tokens()
                if tokens:
                    refresh_token = tokens.refresh_token
                    logger.info("✓ Loaded refresh token from Secrets Manager")
            except Exception as e:
                logger.debug(f"Failed to load token from Secrets Manager: {e}")
        
        # Fall back to file if not found in DynamoDB or Secrets Manager
        if not refresh_token:
            token_file = self.settings.yoto_refresh_token_file
            if not token_file.exists():
                raise FileNotFoundError(
                    f"Refresh token not found in DynamoDB, Secrets Manager, or file: {token_file}. "
                    "Run authentication first."
                )
            refresh_token = token_file.read_text().strip()
            logger.info("Loaded refresh token from local file")

        # Force overwrite any existing in-memory token with freshly loaded value
        self.manager.set_refresh_token(refresh_token)

        lock_acquired = False
        try:
            if store:
                lock_acquired = store.acquire_yoto_token_lock("admin", lock_owner, ttl_seconds=30)
                if not lock_acquired:
                    logger.info("Token refresh lock held elsewhere; waiting briefly and reloading token")
                    time.sleep(0.5)
                    tokens = store.load_yoto_tokens("admin")
                    if tokens:
                        refresh_token = tokens[0]
                        self.manager.set_refresh_token(refresh_token)
            self.manager.check_and_refresh_token()
            self._authenticated = True
            # Save the new refresh token (OAuth2 returns new refresh token on refresh)
            self._save_refresh_token(lock_owner=lock_owner if lock_acquired else None, clear_lock=lock_acquired)
            logger.info("✓ Successfully authenticated with Yoto API")
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
        finally:
            if store and lock_acquired:
                store.release_yoto_token_lock("admin", lock_owner)

    def ensure_authenticated(self) -> None:
        """Always re-authenticate using the latest persisted token."""
        # No caching: always load the current token from persistence and refresh
        self.authenticate(force_reload=True)

    def update_player_status(self, force: bool = False) -> None:
        """Update player status from API with retry logic and caching.
        
        Args:
            force: If True, bypass cache and force a fresh API call
        """
        global _player_status_cache_time
        
        # Check cache first (unless forced)
        current_time = time.time()
        if not force and _player_status_cache_time is not None:
            cache_age = current_time - _player_status_cache_time
            if cache_age < _CACHE_TTL:
                logger.debug(f"Using cached player status (age: {cache_age:.1f}s)")
                return
        
        self.ensure_authenticated()
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.manager.update_players_status()
                _player_status_cache_time = current_time  # Update cache timestamp
                logger.debug(f"Updated status for {len(self.manager.players)} players (cached for {_CACHE_TTL}s)")
                return
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Player status update failed (attempt {attempt + 1}/{max_retries}): {type(e).__name__}: {e}, "
                        f"retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to update player status after {max_retries} attempts: {type(e).__name__}: {e}")
                    raise

    def update_library(self, force: bool = False) -> None:
        """Update library from API to get card metadata with caching.
        
        Args:
            force: If True, bypass cache and force a fresh API call
        """
        global _library_cache_time
        
        # Check cache first (unless forced)
        current_time = time.time()
        if not force and _library_cache_time is not None:
            cache_age = current_time - _library_cache_time
            if cache_age < _CACHE_TTL:
                logger.debug(f"Using cached library (age: {cache_age:.1f}s)")
                return
        
        self.ensure_authenticated()
        # Clear any cached library items before refreshing to avoid stale merges
        try:
            if hasattr(self.manager, "library") and isinstance(self.manager.library, dict):
                self.manager.library.clear()
        except Exception:
            logger.debug("Could not clear cached library before refresh", exc_info=True)
        self.manager.update_library()
        _library_cache_time = current_time  # Update cache timestamp
        logger.debug(f"Updated library with {len(self.manager.library)} items (cached for {_CACHE_TTL}s)")

    def _mqtt_event_callback(self) -> None:
        """
        Callback for MQTT events - triggered when real-time events are received.
        
        The yoto_api library has already updated the manager.players dict with
        the MQTT event data BEFORE this callback is invoked. We extract the
        current player state and store it in the MQTT event store for correlation
        with stream requests and real-time analytics.
        """
        logger.info("MQTT Callback: Event received, processing...")
        try:
            mqtt_store = get_mqtt_event_store()
            
            # The yoto_api library updates manager.players during MQTT events
            if not hasattr(self.manager, 'players') or not self.manager.players:
                logger.debug("No players available in manager, skipping MQTT event store")
                return
            
            # Extract event data from the latest manager state
            for player_id, player in self.manager.players.items():
                # Create MQTT event from player state
                # The player object may have various attribute names depending on the yoto_api version
                mqtt_event = MQTTEvent(
                    timestamp=datetime.now(),
                    device_id=player_id,
                    raw_payload=getattr(player, '__dict__', {}),
                    volume=getattr(player, 'volume', None),
                    volume_max=getattr(player, 'volume_max', None),
                    card_id=getattr(player, 'card_id', None),
                    playback_status=getattr(player, 'playback_status', None),
                    streaming=getattr(player, 'streaming', None),
                    playback_wait=getattr(player, 'playback_wait', None),
                    sleep_timer_active=getattr(player, 'sleep_timer_active', None),
                    repeat_all=getattr(player, 'repeat_all', None),
                )
                
                # Store the event
                mqtt_store.add_event(mqtt_event)
                
                logger.debug(
                    f"MQTT event stored for {player_id}: "
                    f"status={mqtt_event.playback_status}, volume={mqtt_event.volume}"
                )
        except Exception as e:
            logger.error(f"Error in MQTT event callback: {e}", exc_info=True)

    def connect_mqtt(self) -> None:
        """Connect to MQTT for real-time events."""
        self.ensure_authenticated()
        try:
            # Connect with callback for event logging
            self.manager.connect_to_events(callback=self._mqtt_event_callback)
            logger.info("Connected to MQTT with event logging enabled")
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

    def poll_device_code_single_attempt(self, device_code: str) -> Optional[str]:
        """
        Make a single attempt to poll for OAuth token completion.
        
        This is a non-blocking version suitable for serverless environments
        where the frontend polls repeatedly instead of the backend blocking.
        
        Args:
            device_code: The device code from device_code_flow_start
            
        Returns:
            Status string: "success", "pending", "expired", or "error"
            
        Raises:
            Exception: On unexpected errors
        """
        import requests
        import datetime
        
        if not self.manager or not self.manager.api:
            logger.error("Manager not initialized when polling device code")
            raise RuntimeError("Manager not initialized")
            
        logger.info(f"Polling OAuth token with device_code: {device_code[:10]}...")
        
        # Make a single token request
        token_data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": self.manager.client_id,
            "audience": self.manager.api.BASE_URL,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            logger.debug(f"Sending token request to: {self.manager.api.TOKEN_URL}")
            response = requests.post(self.manager.api.TOKEN_URL, data=token_data, headers=headers, timeout=10)
            
            logger.info(f"Token response status: {response.status_code}")
            
            try:
                response_body = response.json()
            except Exception as json_err:
                logger.error(f"Failed to parse response JSON: {json_err}, response text: {response.text[:200]}")
                raise Exception(f"Invalid JSON response from OAuth server")
            
            # Successful authentication
            if response.ok:
                logger.info("✓ OAuth device code authentication successful!")
                
                # Create token object
                from yoto_api import Token
                import pytz
                
                valid_until = datetime.datetime.now(pytz.utc) + datetime.timedelta(
                    seconds=response_body.get("expires_in", 3600)
                )
                
                self.manager.token = Token(
                    access_token=response_body["access_token"],
                    refresh_token=response_body["refresh_token"],
                    token_type=response_body.get("token_type", "Bearer"),
                    scope=response_body.get("scope", "openid profile offline_access"),
                    valid_until=valid_until,
                )
                
                logger.info(f"Token created, expires at: {valid_until}")
                
                # Update players with the new token
                try:
                    self.manager.api.update_players(self.manager.token, self.manager.players)
                    logger.info("Players updated with new token")
                except Exception as player_err:
                    logger.warning(f"Failed to update players: {player_err}")
                
                return "success"
                
            # Handle OAuth2 errors - check for authorization_pending regardless of status code
            error = response_body.get("error", "")
            error_desc = response_body.get("error_description", "")
            
            if error == "authorization_pending":
                logger.debug("Authorization pending - user hasn't completed authorization yet")
                return "pending"
            elif error == "expired_token" or error == "token_expired":
                logger.warning("Device code has expired")
                return "expired"
            elif error == "access_denied":
                logger.error("User denied authorization")
                return "expired"  # Treat as expired so user can restart
            else:
                # Log full error details
                logger.error(f"OAuth error ({response.status_code}): error={error}, description={error_desc}")
                logger.error(f"Full response body: {response_body}")
                # Return error but don't raise exception - frontend will keep polling or show error
                return "error"
            
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout polling for token: {e}")
            # Return pending on timeout - frontend will retry
            return "pending"
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error polling for token: {e}")
            raise
    
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
