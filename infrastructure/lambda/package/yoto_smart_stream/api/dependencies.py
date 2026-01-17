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
    
    If client not yet initialized, creates it lazily but does not authenticate.
    Client will be authenticated when OAuth flow is completed.

    Returns:
        Initialized YotoClient (may not be authenticated yet)

    Raises:
        RuntimeError: If client cannot be created
    """
    global _yoto_client
    
    if _yoto_client is None:
        try:
            # Create client if it doesn't exist yet
            # This ensures get_yoto_client() always returns a client object
            # Authentication will be completed separately via OAuth flow
            settings = Settings()
            _yoto_client = YotoClient(settings)
            logger.debug("Lazy-created YotoClient instance")
        except Exception as e:
            logger.error(f"Failed to lazy-create YotoClient: {e}")
            raise RuntimeError(f"Could not create Yoto client: {e}") from e
    
    return _yoto_client
