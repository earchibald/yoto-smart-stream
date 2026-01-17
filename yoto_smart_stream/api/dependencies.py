"""FastAPI dependencies for dependency injection."""

import logging
from fastapi import HTTPException, status

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


def get_authenticated_yoto_client() -> YotoClient:
    """
    Get an authenticated Yoto client, ensuring token is fresh.
    
    IMPORTANT: This creates a FRESH client instance for each request to avoid
    race conditions and token corruption from concurrent requests sharing state.
    
    This is the recommended way to get a client in route handlers.
    It automatically:
    1. Creates a fresh client instance (not shared globally)
    2. Loads persisted authentication from Secrets Manager/file
    3. Ensures token is valid (refreshes if needed)
    4. Returns 401 if not authenticated
    
    Returns:
        Fresh authenticated YotoClient with valid token
    
    Raises:
        HTTPException 401: If not authenticated with Yoto API
        HTTPException 500: If there's a server error during auth
    """
    try:
        # Create a FRESH client instance for this request
        # Don't reuse the global one to avoid race conditions with concurrent requests
        settings = Settings()
        client = YotoClient(settings)
        logger.debug("Created fresh YotoClient instance for request")
    except Exception as e:
        logger.error(f"Failed to create Yoto client: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize Yoto client"
        )
    
    try:
        client.ensure_authenticated()
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
            logger.info(f"Authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated with Yoto API. Please connect your Yoto account."
            )
        else:
            logger.error(f"Unexpected error during authentication: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error during authentication"
            )

