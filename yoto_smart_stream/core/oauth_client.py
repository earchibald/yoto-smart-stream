"""OAuth2 client for confidential/private client authentication with Yoto API."""

import logging
from typing import Dict, Optional

import requests

logger = logging.getLogger(__name__)


class OAuth2ConfidentialClient:
    """
    OAuth2 confidential client implementation for Yoto API.
    
    This supports the confidential/private client flow using client_id and client_secret.
    Use this when you have a client secret (server-to-server authentication).
    
    For device code flow (no secret), use the standard yoto_api library instead.
    """
    
    def __init__(self, client_id: str, client_secret: str):
        """
        Initialize OAuth2 confidential client.
        
        Args:
            client_id: OAuth2 client ID
            client_secret: OAuth2 client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://login.yotoplay.com/oauth/token"
        self.audience = "https://api.yotoplay.com"
        
    def refresh_token(self, refresh_token: str) -> Dict[str, any]:
        """
        Refresh access token using refresh token with client secret.
        
        This is the confidential/private client flow that includes the client_secret
        in the token refresh request.
        
        Args:
            refresh_token: The refresh token to use
            
        Returns:
            Dict containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            requests.HTTPError: If the request fails
            Exception: If authentication fails
        """
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        logger.info("Refreshing token using confidential client flow (with client secret)")
        
        try:
            response = requests.post(self.token_url, data=data, headers=headers)
            response.raise_for_status()
            
            token_data = response.json()
            logger.info("Successfully refreshed token with confidential client")
            
            return token_data
            
        except requests.HTTPError as e:
            logger.error(f"Token refresh failed: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Token refresh failed: {e.response.text}") from e
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            raise
    
    def device_code_flow_start(self) -> Dict[str, any]:
        """
        Start device code flow (not typically used with confidential clients).
        
        Note: Confidential clients typically don't use device code flow,
        but this is provided for compatibility.
        
        Returns:
            Dict containing device_code, user_code, verification_uri, etc.
            
        Raises:
            requests.HTTPError: If the request fails
        """
        auth_url = "https://login.yotoplay.com/oauth/device/code"
        
        data = {
            "audience": self.audience,
            "client_id": self.client_id,
            "scope": "offline_access profile",
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        logger.info("Starting device code flow")
        
        try:
            response = requests.post(auth_url, data=data, headers=headers)
            response.raise_for_status()
            
            return response.json()
            
        except requests.HTTPError as e:
            logger.error(f"Device code flow failed: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Device code flow failed: {e.response.text}") from e
        except Exception as e:
            logger.error(f"Device code flow error: {e}")
            raise
    
    def poll_for_token(self, device_code: str) -> Dict[str, any]:
        """
        Poll for token after device code flow.
        
        Args:
            device_code: The device code from device_code_flow_start()
            
        Returns:
            Dict containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            Exception: If polling fails or times out
        """
        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.audience,
        }
        
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        try:
            response = requests.post(self.token_url, data=data, headers=headers)
            
            if response.ok:
                return response.json()
            
            # Handle authorization_pending and other errors
            error_data = response.json()
            error = error_data.get("error", "unknown_error")
            
            if error == "authorization_pending":
                raise Exception("authorization_pending")
            elif error == "slow_down":
                raise Exception("slow_down")
            elif error == "expired_token":
                raise Exception("expired_token")
            else:
                raise Exception(f"Token poll failed: {error}")
                
        except Exception as e:
            raise
