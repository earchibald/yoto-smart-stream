"""FastAPI dependencies for dependency injection."""

import logging

from ..config import Settings
from ..core import YotoClient

logger = logging.getLogger(__name__)

# Global Yoto client instance
_yoto_client: YotoClient | None = None


def set_yoto_client(client: YotoClient) -> None:
    """Set the global Yoto client instance."""
    global _yoto_client
    _yoto_client = client


def get_yoto_client() -> YotoClient:
    """
    Get the global Yoto client instance.
    
    If client not yet initialized, creates it lazily and attempts to load
    persisted authentication from Secrets Manager (Lambda) or local file.
    If no persisted auth exists, client will be unauthenticated until OAuth completes.
    
    IMPORTANT: This function returns a client that may not be authenticated.
    Callers MUST call ensure_authenticated() to guarantee a valid token before
    making API calls. This handles the case where:
    - Token expiration between requests
    - Lambda container reuse with stale tokens
    - Secrets Manager token updates

    Returns:
        Initialized YotoClient (may not be authenticated - caller must check/refresh)

    Raises:
        RuntimeError: If client cannot be created
    """
    global _yoto_client
    
    if _yoto_client is None:
        try:
            # Create client if it doesn't exist yet
            settings = Settings()
            _yoto_client = YotoClient(settings)
            logger.debug("Lazy-created YotoClient instance")

            # Try to load persisted authentication automatically
            # This ensures cold/warm Lambda containers reload tokens after OAuth completes
            try:
                _yoto_client.authenticate()
                logger.info("✓ Client authenticated with persisted token")
            except FileNotFoundError:
                logger.debug("No persisted token found; client remains unauthenticated until OAuth")
            except Exception as e:
                logger.debug(f"Could not load persisted auth: {e}; client will be unauthenticated")
        except Exception as e:
            logger.error(f"Failed to lazy-create YotoClient: {e}")
            raise RuntimeError(f"Could not create Yoto client: {e}") from e
    
    return _yoto_client
