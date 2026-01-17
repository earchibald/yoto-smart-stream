"""FastAPI dependencies for dependency injection."""

import json
import logging
import os
from typing import Optional

from ..config import get_settings
from ..core import YotoClient

logger = logging.getLogger(__name__)

# Global Yoto client instance
_yoto_client: YotoClient | None = None


def set_yoto_client(client: YotoClient | None) -> None:
    """Set the global Yoto client instance."""
    global _yoto_client
    _yoto_client = client


def get_yoto_client() -> YotoClient:
    """
    Get the global Yoto client instance.
    On Lambda, attempts to load persisted tokens from Secrets Manager.

    Returns:
        Initialized YotoClient

    Raises:
        RuntimeError: If client not initialized and no persisted tokens found
    """
    global _yoto_client
    
    if _yoto_client is None:
        try:
            settings = get_settings()
            _yoto_client = YotoClient(settings)
            logger.debug("Created YotoClient instance")
            
            # On Lambda, try to load persisted tokens from Secrets Manager
            if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                try:
                    import boto3
                    sm_client = boto3.client("secretsmanager", region_name="us-east-1")
                    response = sm_client.get_secret_value(SecretId="yoto-oauth-token")
                    token_data = json.loads(response["SecretString"])
                    
                    # Authenticate with persisted refresh token
                    if token_data.get("refresh_token"):
                        _yoto_client.initialize()
                        _yoto_client.manager.set_refresh_token(token_data["refresh_token"])
                        _yoto_client.manager.check_and_refresh_token()
                        _yoto_client.set_authenticated(True)
                        logger.info("✓ Client authenticated with persisted token from Secrets Manager")
                except sm_client.exceptions.ResourceNotFoundException:
                    logger.debug("No persisted tokens found in Secrets Manager - client not yet authenticated")
                except Exception as e:
                    logger.debug(f"Could not load persisted tokens from Secrets Manager: {e}")
            
        except Exception as e:
            logger.error(f"Failed to create YotoClient: {e}")
            raise RuntimeError(f"Could not create Yoto client: {e}") from e
    
    return _yoto_client
