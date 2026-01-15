"""FastAPI dependencies for dependency injection."""

from ..core import YotoClient

# Global Yoto client instance
_yoto_client: YotoClient | None = None


def set_yoto_client(client: YotoClient) -> None:
    """Set the global Yoto client instance."""
    global _yoto_client
    _yoto_client = client


def get_yoto_client() -> YotoClient:
    """
    Get the global Yoto client instance.

    Returns:
        Initialized and authenticated YotoClient

    Raises:
        RuntimeError: If client not initialized
    """
    if _yoto_client is None:
        raise RuntimeError("Yoto client not initialized")
    return _yoto_client
