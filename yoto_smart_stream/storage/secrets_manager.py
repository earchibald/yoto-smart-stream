"""OAuth token storage in AWS Secrets Manager with in-memory caching.

OAuth tokens are sensitive credentials and should never be stored in databases.
This module provides secure storage in AWS Secrets Manager with in-memory caching
for performance in Lambda environments.
"""

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory token cache for Lambda warm starts
_cached_tokens: Optional["YotoTokens"] = None
_cache_timestamp: Optional[datetime] = None
_CACHE_TTL_SECONDS = 300  # 5 minutes


@dataclass
class YotoTokens:
    """Yoto OAuth tokens."""
    
    access_token: str
    refresh_token: str
    expires_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "YotoTokens":
        """Create from dictionary."""
        expires_at = None
        if data.get("expires_at"):
            try:
                expires_at = datetime.fromisoformat(data["expires_at"])
            except (ValueError, AttributeError):
                pass
        
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=expires_at
        )


def get_secret_name() -> str:
    """Get the Secrets Manager secret name based on environment."""
    env = os.environ.get("ENVIRONMENT", "dev")
    prefix = os.environ.get("YOTO_SECRET_PREFIX", f"yoto-smart-stream-{env}")
    return f"{prefix}/oauth-tokens"


def save_yoto_tokens(tokens: YotoTokens) -> None:
    """
    Save Yoto OAuth tokens to AWS Secrets Manager.
    
    Updates in-memory cache after successful save.
    
    Args:
        tokens: Yoto OAuth tokens to save
    """
    global _cached_tokens, _cache_timestamp
    
    secret_name = get_secret_name()
    secret_value = json.dumps(tokens.to_dict())
    
    try:
        import boto3
        
        region = os.environ.get("AWS_REGION", "us-east-1")
        sm_client = boto3.client("secretsmanager", region_name=region)
        
        try:
            # Try to update existing secret
            sm_client.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_value
            )
            logger.info(f"✓ Yoto OAuth tokens updated in Secrets Manager: {secret_name}")
        except sm_client.exceptions.ResourceNotFoundException:
            # Create new secret if it doesn't exist
            sm_client.create_secret(
                Name=secret_name,
                Description="Yoto Smart Stream OAuth tokens",
                SecretString=secret_value
            )
            logger.info(f"✓ Yoto OAuth tokens created in Secrets Manager: {secret_name}")
        
        # Update cache
        _cached_tokens = tokens
        _cache_timestamp = datetime.now(timezone.utc)
        
    except Exception as e:
        logger.error(f"Failed to save tokens to Secrets Manager: {e}")
        raise


def load_yoto_tokens() -> Optional[YotoTokens]:
    """
    Load Yoto OAuth tokens from AWS Secrets Manager.
    
    Uses in-memory cache if available and fresh (< 5 minutes old).
    
    Returns:
        Yoto tokens if found, None otherwise
    """
    global _cached_tokens, _cache_timestamp
    
    # Check cache first
    if _cached_tokens and _cache_timestamp:
        age_seconds = (datetime.now(timezone.utc) - _cache_timestamp).total_seconds()
        if age_seconds < _CACHE_TTL_SECONDS:
            logger.debug(f"Using cached Yoto tokens (age: {age_seconds:.1f}s)")
            return _cached_tokens
    
    secret_name = get_secret_name()
    
    try:
        import boto3
        
        region = os.environ.get("AWS_REGION", "us-east-1")
        sm_client = boto3.client("secretsmanager", region_name=region)
        
        response = sm_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response["SecretString"])
        
        tokens = YotoTokens.from_dict(secret_data)
        
        # Update cache
        _cached_tokens = tokens
        _cache_timestamp = datetime.now(timezone.utc)
        
        logger.info(f"✓ Yoto OAuth tokens loaded from Secrets Manager: {secret_name}")
        return tokens
        
    except Exception as e:
        if "ResourceNotFoundException" in str(e):
            logger.debug(f"No Yoto tokens found in Secrets Manager: {secret_name}")
        else:
            logger.error(f"Failed to load tokens from Secrets Manager: {e}")
        return None


def delete_yoto_tokens() -> None:
    """Delete Yoto OAuth tokens from Secrets Manager and clear cache."""
    global _cached_tokens, _cache_timestamp
    
    secret_name = get_secret_name()
    
    try:
        import boto3
        
        region = os.environ.get("AWS_REGION", "us-east-1")
        sm_client = boto3.client("secretsmanager", region_name=region)
        
        sm_client.delete_secret(
            SecretId=secret_name,
            ForceDeleteWithoutRecovery=True
        )
        logger.info(f"✓ Yoto OAuth tokens deleted from Secrets Manager: {secret_name}")
        
    except Exception as e:
        if "ResourceNotFoundException" not in str(e):
            logger.error(f"Failed to delete tokens from Secrets Manager: {e}")
    
    # Clear cache
    _cached_tokens = None
    _cache_timestamp = None


def clear_token_cache() -> None:
    """Clear the in-memory token cache."""
    global _cached_tokens, _cache_timestamp
    _cached_tokens = None
    _cache_timestamp = None
    logger.debug("Token cache cleared")
