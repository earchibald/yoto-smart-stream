"""
Token storage utilities for persistent OAuth token management using AWS Secrets Manager.

This module provides Secrets Manager-backed token storage for Yoto API OAuth tokens,
ensuring tokens persist across Lambda cold starts and redeployments.
"""

import json
import os
from typing import Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TokenStorage:
    """
    Handles persistent storage of OAuth tokens in AWS Secrets Manager.
    
    Stores tokens as JSON in a single secret per user with structure:
    {
        "refresh_token": "...",
        "access_token": "...",
        "expires_at": "ISO-8601 datetime",
        "updated_at": "ISO-8601 datetime"
    }
    """
    
    def __init__(self, secret_name_prefix: Optional[str] = None):
        """
        Initialize token storage.
        
        Args:
            secret_name_prefix: Prefix for secret names (e.g., "yoto-smart-stream-dev").
                               If not provided, uses YOTO_SECRET_PREFIX environment variable.
        """
        self.secret_name_prefix = secret_name_prefix or os.environ.get("YOTO_SECRET_PREFIX", "yoto-smart-stream")
        self._secrets_client = None
        
    @property
    def secrets_client(self):
        """Lazy-load boto3 Secrets Manager client."""
        if self._secrets_client is None:
            try:
                import boto3
                self._secrets_client = boto3.client("secretsmanager")
            except ImportError:
                logger.error("boto3 not installed - Secrets Manager token storage unavailable")
                raise
        return self._secrets_client
    
    def _get_secret_name(self, user_id: str) -> str:
        """Generate secret name for a user's Yoto tokens."""
        # Sanitize user_id for secret name (alphanumeric, hyphens, underscores only)
        safe_user_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in user_id)
        return f"{self.secret_name_prefix}/yoto-token/{safe_user_id}"
    
    def save_token(
        self,
        user_id: str,
        refresh_token: str,
        access_token: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """
        Save OAuth tokens to Secrets Manager.
        
        Args:
            user_id: User identifier (e.g., Cognito sub or username)
            refresh_token: OAuth refresh token
            access_token: OAuth access token (optional)
            expires_at: Token expiration datetime (optional)
        """
        secret_name = self._get_secret_name(user_id)
        
        token_data = {
            "refresh_token": refresh_token,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if access_token:
            token_data["access_token"] = access_token
        
        if expires_at:
            token_data["expires_at"] = expires_at.isoformat()
        
        try:
            # Try to update existing secret
            self.secrets_client.update_secret(
                SecretId=secret_name,
                SecretString=json.dumps(token_data),
            )
            logger.info(f"Updated Yoto OAuth token in Secrets Manager for user {user_id}")
            
        except self.secrets_client.exceptions.ResourceNotFoundException:
            # Secret doesn't exist, create it
            try:
                self.secrets_client.create_secret(
                    Name=secret_name,
                    Description=f"Yoto API OAuth tokens for user {user_id}",
                    SecretString=json.dumps(token_data),
                )
                logger.info(f"Created Yoto OAuth token in Secrets Manager for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to create secret: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Failed to save token to Secrets Manager: {e}")
            raise
    
    def get_token(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve OAuth tokens from Secrets Manager.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary containing token data, or None if not found.
            Keys: refresh_token, access_token (optional), expires_at (optional), updated_at
        """
        secret_name = self._get_secret_name(user_id)
        
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            token_data = json.loads(response["SecretString"])
            logger.info(f"Retrieved Yoto OAuth token from Secrets Manager for user {user_id}")
            return token_data
            
        except self.secrets_client.exceptions.ResourceNotFoundException:
            logger.info(f"No Yoto OAuth token found in Secrets Manager for user {user_id}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to retrieve token from Secrets Manager: {e}")
            raise
    
    def delete_token(self, user_id: str) -> None:
        """
        Delete OAuth tokens from Secrets Manager.
        
        Args:
            user_id: User identifier
        """
        secret_name = self._get_secret_name(user_id)
        
        try:
            # Schedule deletion (7 day waiting period)
            self.secrets_client.delete_secret(
                SecretId=secret_name,
                RecoveryWindowInDays=7,
            )
            logger.info(f"Scheduled deletion of Yoto OAuth token for user {user_id}")
            
        except self.secrets_client.exceptions.ResourceNotFoundException:
            logger.info(f"Secret not found for user {user_id}, nothing to delete")
            
        except Exception as e:
            logger.error(f"Failed to delete token from Secrets Manager: {e}")
            raise
