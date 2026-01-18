"""OAuth token storage in AWS Secrets Manager with Lambda Extension caching.

OAuth tokens are sensitive credentials and should never be stored in databases.
This module uses the AWS Parameters and Secrets Lambda Extension to provide
secure storage in AWS Secrets Manager with automatic in-memory caching and
refresh based on configurable TTL.

The extension runs as a daemon and handles:
- Caching secrets in memory
- Automatic refresh based on TTL
- Local HTTP endpoint for fast access (localhost:2773)
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Extension configuration
SECRETS_EXTENSION_HTTP_PORT = os.environ.get("SECRETS_EXTENSION_HTTP_PORT", "2773")


@dataclass
class YotoTokens:
    """Yoto OAuth tokens."""

    access_token: str
    refresh_token: str
    expires_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "YotoTokens":
        """Create from dictionary."""
        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token", ""),
            expires_at=data.get("expires_at"),
        )


def get_secret_name() -> str:
    """Get the Secrets Manager secret name based on environment."""
    env = os.environ.get("ENVIRONMENT", "dev")
    prefix = os.environ.get("YOTO_SECRET_PREFIX", f"yoto-smart-stream-{env}")
    return f"{prefix}/oauth-tokens"


def _get_secret_from_extension(secret_name: str) -> Optional[dict]:
    """
    Fetch secret from the Lambda Extension using HTTP endpoint.

    The extension provides automatic caching and refresh based on TTL.
    This is the preferred method in Lambda environments.

    Args:
        secret_name: Name of the secret in Secrets Manager

    Returns:
        Parsed secret dictionary or None if not found
    """
    try:
        import urllib.request

        # Use the local HTTP endpoint provided by the Lambda Extension
        extension_endpoint = f"http://localhost:{SECRETS_EXTENSION_HTTP_PORT}/secretsmanager/get?secretId={secret_name}"

        request = urllib.request.Request(extension_endpoint)
        request.add_header(
            "X-Aws-Parameters-Secrets-Token", os.environ.get("AWS_SESSION_TOKEN", "")
        )

        with urllib.request.urlopen(request, timeout=5) as response:
            response_data = json.loads(response.read().decode("utf-8"))

            if "SecretString" in response_data:
                logger.info(f"✓ Loaded secret from Lambda Extension (HTTP caching): {secret_name}")
                return json.loads(response_data["SecretString"])

            logger.warning(f"No SecretString in extension response for {secret_name}")
            return None

    except Exception as e:
        logger.debug(f"Failed to fetch from extension endpoint (will try boto3): {e}")
        return None


def _get_secret_from_boto3(secret_name: str) -> Optional[dict]:
    """
    Fetch secret directly from Secrets Manager using boto3.

    This is used as a fallback if the extension is not available
    (e.g., local development).

    Args:
        secret_name: Name of the secret in Secrets Manager

    Returns:
        Parsed secret dictionary or None if not found
    """
    try:
        import boto3

        region = os.environ.get("AWS_REGION", "us-east-1")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            logger.info(f"✓ Loaded secret from boto3 (no extension available): {secret_name}")
            return json.loads(response["SecretString"])

        logger.warning(f"No SecretString in boto3 response for {secret_name}")
        return None

    except Exception as e:
        logger.warning(f"Failed to fetch secret via boto3: {e}")
        return None


def save_yoto_tokens(tokens: YotoTokens) -> None:
    """
    Save Yoto OAuth tokens to AWS Secrets Manager.

    The Lambda Extension will automatically cache and refresh this secret.

    Args:
        tokens: Yoto OAuth tokens to save
    """
    secret_name = get_secret_name()
    secret_value = json.dumps(tokens.to_dict())

    try:
        import boto3

        region = os.environ.get("AWS_REGION", "us-east-1")
        sm_client = boto3.client("secretsmanager", region_name=region)

        try:
            # Try to update existing secret
            sm_client.put_secret_value(SecretId=secret_name, SecretString=secret_value)
            logger.info(f"✓ Yoto OAuth tokens updated in Secrets Manager: {secret_name}")
        except sm_client.exceptions.ResourceNotFoundException:
            # Create new secret if it doesn't exist
            sm_client.create_secret(
                Name=secret_name,
                Description="Yoto Smart Stream OAuth tokens",
                SecretString=secret_value,
            )
            logger.info(f"✓ Yoto OAuth tokens created in Secrets Manager: {secret_name}")

    except Exception as e:
        logger.error(f"Failed to save tokens to Secrets Manager: {e}")
        raise


def load_yoto_tokens() -> Optional[YotoTokens]:
    """
    Load Yoto OAuth tokens from AWS Secrets Manager.

    Uses the Lambda Extension for automatic caching and refresh.
    Falls back to direct boto3 access if extension is unavailable.

    Returns:
        Yoto tokens if found, None otherwise
    """
    secret_name = get_secret_name()

    # Try extension first (Lambda environment)
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
        secret_data = _get_secret_from_extension(secret_name)
        if secret_data:
            return YotoTokens.from_dict(secret_data)

    # Fall back to direct boto3 access
    secret_data = _get_secret_from_boto3(secret_name)
    if secret_data:
        return YotoTokens.from_dict(secret_data)

    logger.debug(f"Refresh token not found in Secrets Manager: {secret_name}")
    return None


def delete_yoto_tokens() -> None:
    """Delete Yoto OAuth tokens from Secrets Manager."""
    secret_name = get_secret_name()

    try:
        import boto3

        region = os.environ.get("AWS_REGION", "us-east-1")
        sm_client = boto3.client("secretsmanager", region_name=region)

        sm_client.delete_secret(SecretId=secret_name, ForceDeleteWithoutRecovery=True)
        logger.info(f"✓ Yoto OAuth tokens deleted from Secrets Manager: {secret_name}")

    except Exception as e:
        logger.warning(f"Failed to delete tokens from Secrets Manager: {e}")
