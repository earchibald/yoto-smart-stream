"""FastAPI dependencies for dependency injection."""

import logging
import threading
from fastapi import HTTPException, status

from ..config import Settings
from ..core import YotoClient

logger = logging.getLogger(__name__)

# Global Yoto client instance (thread-safe access)
_yoto_client: YotoClient | None = None
_client_lock = threading.RLock()  # Recursive lock to prevent concurrent token corruption


def set_yoto_client(client: YotoClient | None) -> None:
    """Set the global Yoto client instance (thread-safe)."""
    global _yoto_client
    with _client_lock:
        _yoto_client = client
        logger.debug(f"Global client set to {'authenticated' if client else 'None'}")


def get_yoto_client() -> YotoClient:
    """
    Get the global Yoto client instance (thread-safe).
    
    If client not yet initialized, creates it lazily and attempts to load
    persisted authentication from Secrets Manager (Lambda) or local file.

    Returns:
        Initialized YotoClient

    Raises:
        RuntimeError: If client cannot be created
    """
    global _yoto_client
    
    with _client_lock:
        if _yoto_client is None:
            try:
                settings = Settings()
                _yoto_client = YotoClient(settings)
                logger.debug("Lazy-created YotoClient instance")

                try:
                    _yoto_client.authenticate()
                    logger.info("✓ Client authenticated with persisted token")
                except FileNotFoundError:
                    logger.debug("No persisted token found; client remains unauthenticated")
                except Exception as e:
                    logger.debug(f"Could not load persisted auth: {e}; client will be unauthenticated")
            except Exception as e:
                logger.error(f"Failed to lazy-create YotoClient: {e}")
                raise RuntimeError(f"Could not create Yoto client: {e}") from e
        
        return _yoto_client


def get_authenticated_yoto_client() -> YotoClient:
    """
    Get an authenticated Yoto client with thread-safe token management.
    
    Uses a SINGLE global client instance to avoid repeated expensive
    Secrets Manager lookups, but protects it with a lock to prevent
    concurrent request interference with token state.
    
    This is the recommended way to get a client in route handlers.
    
    Returns:
        Authenticated YotoClient with fresh token
    
    Raises:
        HTTPException 401: If not authenticated with Yoto API
        HTTPException 500: If there's a server error during auth
    """
    try:
        client = get_yoto_client()
    except RuntimeError as e:
        logger.error(f"Failed to get Yoto client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize Yoto client"
        )
    
    # Use lock to ensure token refresh is atomic and doesn't interfere
    # with concurrent requests
    with _client_lock:
        try:
            logger.debug("Ensuring client authentication (thread-safe)")
            client.ensure_authenticated()
            logger.debug("Client authentication check passed")
            return client
        except FileNotFoundError as e:
            logger.info(f"No authentication token found: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Yoto API. Please connect your Yoto account."
            )
        except Exception as e:
            error_str = str(e).lower()
            if "authentication" in error_str or "unauthorized" in error_str or "refresh token" in error_str:
                logger.info(f"Authentication failed: {type(e).__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated with Yoto API. Please connect your Yoto account."
                )
            else:
                logger.error(f"Unexpected error during authentication: {type(e).__name__}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error during authentication"
                )
