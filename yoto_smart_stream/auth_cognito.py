"""
AWS Cognito authentication utilities.

Provides functions for Cognito-based authentication when deployed on AWS.
"""

import os
import logging
from typing import Optional, Dict

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class CognitoAuth:
    """AWS Cognito authentication manager"""
    
    def __init__(self):
        """Initialize Cognito client"""
        self.user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
        self.client_id = os.getenv("COGNITO_CLIENT_ID")
        
        if not self.user_pool_id:
            logger.warning("COGNITO_USER_POOL_ID not set, Cognito auth disabled")
            self.client = None
            return
        
        try:
            self.client = boto3.client("cognito-idp")
            logger.info(f"Cognito client initialized for pool: {self.user_pool_id}")
        except Exception as e:
            logger.error(f"Failed to initialize Cognito client: {e}")
            self.client = None
    
    def is_enabled(self) -> bool:
        """Check if Cognito authentication is enabled"""
        return self.client is not None and self.user_pool_id is not None
    
    def authenticate(self, username: str, password: str) -> Optional[Dict]:
        """
        Authenticate user with Cognito.
        
        Args:
            username: Username or email
            password: User password
            
        Returns:
            Authentication result with tokens or None if failed
        """
        if not self.is_enabled():
            logger.debug("Cognito not enabled, skipping authentication")
            return None
        
        try:
            response = self.client.admin_initiate_auth(
                UserPoolId=self.user_pool_id,
                ClientId=self.client_id,
                AuthFlow="ADMIN_NO_SRP_AUTH",
                AuthParameters={
                    "USERNAME": username,
                    "PASSWORD": password,
                },
            )
            
            logger.info(f"Successful Cognito authentication for user: {username}")
            return {
                "access_token": response["AuthenticationResult"]["AccessToken"],
                "id_token": response["AuthenticationResult"]["IdToken"],
                "refresh_token": response["AuthenticationResult"]["RefreshToken"],
                "expires_in": response["AuthenticationResult"]["ExpiresIn"],
            }
            
        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            if error_code == "NotAuthorizedException":
                logger.warning(f"Invalid credentials for user: {username}")
            elif error_code == "UserNotFoundException":
                logger.warning(f"User not found: {username}")
            else:
                logger.error(f"Cognito authentication error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during Cognito authentication: {e}")
            return None
    
    def verify_token(self, access_token: str) -> Optional[Dict]:
        """
        Verify and decode a Cognito access token.
        
        Args:
            access_token: Cognito access token
            
        Returns:
            Token payload or None if invalid
        """
        if not self.is_enabled():
            return None
        
        try:
            response = self.client.get_user(AccessToken=access_token)
            
            # Extract user attributes
            user_attrs = {attr["Name"]: attr["Value"] for attr in response["UserAttributes"]}
            
            return {
                "username": response["Username"],
                "email": user_attrs.get("email"),
                "email_verified": user_attrs.get("email_verified") == "true",
            }
            
        except ClientError as e:
            logger.warning(f"Token verification failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error verifying token: {e}")
            return None
    
    def create_user(
        self, username: str, email: str, password: str, temporary_password: bool = False
    ) -> bool:
        """
        Create a new user in Cognito.
        
        Args:
            username: Username for the new user
            email: Email address
            password: User password
            temporary_password: If True, user must change password on first login
            
        Returns:
            True if user created successfully, False otherwise
        """
        if not self.is_enabled():
            logger.warning("Cannot create user: Cognito not enabled")
            return False
        
        try:
            self.client.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=username,
                UserAttributes=[
                    {"Name": "email", "Value": email},
                    {"Name": "email_verified", "Value": "true"},
                ],
                TemporaryPassword=password if temporary_password else None,
                MessageAction="SUPPRESS",  # Don't send welcome email
            )
            
            # Set permanent password if not temporary
            if not temporary_password:
                self.client.admin_set_user_password(
                    UserPoolId=self.user_pool_id,
                    Username=username,
                    Password=password,
                    Permanent=True,
                )
            
            logger.info(f"Created Cognito user: {username}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to create user: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error creating user: {e}")
            return False
    
    def list_users(self, limit: int = 60) -> list:
        """
        List all users in the Cognito user pool.
        
        Args:
            limit: Maximum number of users to return
            
        Returns:
            List of user dictionaries
        """
        if not self.is_enabled():
            return []
        
        try:
            response = self.client.list_users(
                UserPoolId=self.user_pool_id,
                Limit=limit,
            )
            
            users = []
            for user in response.get("Users", []):
                user_attrs = {attr["Name"]: attr["Value"] for attr in user.get("Attributes", [])}
                users.append({
                    "username": user["Username"],
                    "email": user_attrs.get("email"),
                    "enabled": user["Enabled"],
                    "status": user["UserStatus"],
                    "created": user["UserCreateDate"],
                })
            
            return users
            
        except Exception as e:
            logger.error(f"Failed to list users: {e}")
            return []


# Global instance
_cognito_auth = None


def get_cognito_auth() -> CognitoAuth:
    """Get global Cognito authentication manager"""
    global _cognito_auth
    if _cognito_auth is None:
        _cognito_auth = CognitoAuth()
    return _cognito_auth
