"""Authentication endpoints for Yoto account login."""

import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from pydantic import BaseModel

from ...config import get_settings
from ...core import YotoClient
from ...storage.dynamodb_store import DynamoStore, UserRecord, get_store
from ..dependencies import get_yoto_client, set_yoto_client

logger = logging.getLogger(__name__)

router = APIRouter()


def get_store_dep() -> DynamoStore:
    settings = get_settings()
    return get_store(settings.dynamodb_table, region_name=settings.dynamodb_region)


def get_current_user_optional(
    session_token: Optional[str] = Cookie(None, alias="session"),
    store: DynamoStore = Depends(get_store_dep)
) -> Optional[UserRecord]:
    """
    Get current user from session cookie (optional, doesn't raise error if not authenticated).
    
    Args:
        session_token: Session token from cookie
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
    from ...auth import decode_access_token
    
    if not session_token:
        return None
    
    payload = decode_access_token(session_token)
    if not payload:
        return None
    
    username = payload.get("sub")
    if not username:
        return None
    
    user = store.get_user(username)
    if not user or not user.is_active:
        return None
    
    return user


def _get_or_create_client() -> YotoClient:
    """
    Get existing YotoClient or create a new one if needed.

    Returns:
        YotoClient instance

    Raises:
        HTTPException: If client cannot be created
    """
    try:
        return get_yoto_client()
    except RuntimeError:
        # Client doesn't exist yet, create it
        settings = get_settings()
        client = YotoClient(settings)
        set_yoto_client(client)
        return client


# Request/Response models
class AuthStatus(BaseModel):
    """Authentication status response model."""

    authenticated: bool
    message: str


class DeviceCodeResponse(BaseModel):
    """Device code flow response model."""

    verification_uri: str
    verification_uri_complete: str
    user_code: str
    device_code: str
    expires_in: int
    interval: int


class AuthPollRequest(BaseModel):
    """Authentication poll request model."""

    device_code: str


class AuthPollResponse(BaseModel):
    """Authentication poll response model."""

    status: str  # "pending", "success", "expired", "error"
    message: str
    authenticated: bool = False


@router.get("/auth/status", response_model=AuthStatus)
async def get_auth_status():
    """
    Check current authentication status.

    Returns:
        Authentication status and message
    """
    try:
        client = get_yoto_client()
        if client and client.is_authenticated():
            return AuthStatus(
                authenticated=True,
                message="Authenticated with Yoto API"
            )
        else:
            return AuthStatus(
                authenticated=False,
                message="Not authenticated. Please log in."
            )
    except Exception:
        return AuthStatus(
            authenticated=False,
            message="Not authenticated. Please log in."
        )


@router.post("/auth/start", response_model=DeviceCodeResponse)
async def start_auth_flow():
    """
    Start OAuth2 device code flow.

    Returns:
        Device code and verification URL for user to authenticate
    """
    settings = get_settings()

    if not settings.yoto_client_id:
        import os
        env_value = os.environ.get('YOTO_CLIENT_ID', 'NOT SET')
        logger.error(f"YOTO_CLIENT_ID not configured. Environment variable: {env_value}, Settings value: {settings.yoto_client_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"YOTO_CLIENT_ID not configured. Environment check: {env_value}. Please ensure the environment variable is set correctly."
        )

    try:
        # Get or create client
        client = _get_or_create_client()

        # Initialize manager if needed
        client.initialize()
        manager = client.manager

        # Start device code flow
        device_info = manager.device_code_flow_start()

        logger.info(f"Device code flow started: {device_info.get('user_code')}")

        return DeviceCodeResponse(
            verification_uri=device_info["verification_uri"],
            verification_uri_complete=device_info.get(
                "verification_uri_complete",
                device_info["verification_uri"]
            ),
            user_code=device_info["user_code"],
            device_code=device_info["device_code"],
            expires_in=device_info.get("expires_in", 300),
            interval=device_info.get("interval", 5)
        )

    except Exception as e:
        logger.error(f"Failed to start auth flow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start authentication: {str(e)}"
        ) from e


@router.post("/auth/poll", response_model=AuthPollResponse)
async def poll_auth_status(
    poll_request: AuthPollRequest,
    store: DynamoStore = Depends(get_store_dep),
    current_user: Optional[UserRecord] = Depends(get_current_user_optional)
):
    """
    Poll for authentication completion.

    Args:
        poll_request: Contains device_code from start_auth_flow
        db: Database session
        current_user: Current logged-in user (if any)

    Returns:
        Current authentication status
    """
    settings = get_settings()
    client = get_yoto_client()

    if not client or not client.manager:
        return AuthPollResponse(
            status="error",
            message="Authentication not started",
            authenticated=False
        )

    try:
        # Set the auth_result with the device_code from the poll request
        # This is needed because each Lambda invocation may not have the original auth_result
        logger.info(f"🔍 [OAuth Poll] device_code: {poll_request.device_code[:10]}...")
        logger.info(f"🔍 [OAuth Poll] current auth_result: {client.manager.auth_result}")
        
        if not client.manager.auth_result or client.manager.auth_result.get("device_code") != poll_request.device_code:
            logger.info(f"🔍 [OAuth Poll] Setting auth_result with device_code")
            client.manager.auth_result = {
                "device_code": poll_request.device_code
            }
        
        # Try to complete the device code flow
        logger.info(f"🔍 [OAuth Poll] Calling device_code_flow_complete()...")
        result = client.manager.device_code_flow_complete()
        logger.info(f"🔍 [OAuth Poll] device_code_flow_complete() succeeded! result: {result}")
        
        # Log for debugging
        logger.debug(f"device_code_flow_complete() result: {result}")
        logger.debug(f"client.manager.token: {client.manager.token}")
        if client.manager.token:
            logger.info(f"🔍 [OAuth Poll] Token object type: {type(client.manager.token)}")
            logger.info(f"🔍 [OAuth Poll] Token attributes: {dir(client.manager.token)}")
            if hasattr(client.manager.token, 'refresh_token'):
                logger.info(f"🔍 [OAuth Poll] refresh_token value: {client.manager.token.refresh_token[:50]}..." if len(str(client.manager.token.refresh_token)) > 50 else f"🔍 [OAuth Poll] refresh_token value: {client.manager.token.refresh_token}")
                logger.info(f"🔍 [OAuth Poll] refresh_token type: {type(client.manager.token.refresh_token)}")
                logger.info(f"🔍 [OAuth Poll] refresh_token length: {len(str(client.manager.token.refresh_token))}")
        
        # If we get here, authentication succeeded
        client.set_authenticated(True)

        # Save tokens to DynamoDB (primary storage - reliable and persistent)
        if client.manager.token and hasattr(client.manager.token, 'refresh_token') and client.manager.token.refresh_token:
            try:
                # Use current user if authenticated, otherwise use 'admin' for global tokens
                username = current_user.username if current_user else "admin"
                
                # Save to DynamoDB first (most reliable)
                store.save_yoto_tokens(
                    username=username,
                    refresh_token=client.manager.token.refresh_token,
                    access_token=getattr(client.manager.token, "access_token", None),
                    expires_at=getattr(client.manager.token, "expires_at", None)
                )
                logger.info(f"✓ Yoto OAuth tokens saved to DynamoDB for user: {username}")
                
                # Per security model, do not store dynamic tokens in Secrets Manager
                logger.info("Skipping Secrets Manager backup for tokens (use DynamoDB only)")
                
            except Exception as e:
                logger.error(f"Failed to save tokens to DynamoDB: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to save OAuth tokens: {str(e)}"
                )
            
            # Also save to file for local development (fallback)
            if not os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                try:
                    token_file = settings.yoto_refresh_token_file
                    token_file.parent.mkdir(parents=True, exist_ok=True)
                    token_file.write_text(client.manager.token.refresh_token)
                    logger.info(f"Refresh token also saved to local file: {token_file}")
                except Exception as e:
                    logger.warning(f"Could not save token to local file: {e}")
        else:
            logger.error("No refresh token available after authentication!")

        logger.info("Authentication successful!")

        return AuthPollResponse(
            status="success",
            message="Successfully authenticated with Yoto API",
            authenticated=True
        )

    except Exception as e:
        import traceback
        error_msg = str(e).lower()
        
        # Log full traceback for debugging
        logger.error(f"Auth poll exception: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.warning(f"🔍 [OAuth Poll] Checking error: error_msg={repr(error_msg)}, has slow_down={('slow_down' in error_msg)}, has 429={('429' in error_msg)}")

        # Check for common error types
        if "slow_down" in error_msg or "429" in error_msg:
            # Yoto API rate limiting - user is polling too fast
            # Return pending and let frontend increase polling interval
            logger.warning(f"✅ Rate limited by Yoto OAuth - user polling too fast. Returning pending.")
            return AuthPollResponse(
                status="pending",
                message="Waiting for user to authorize...",
                authenticated=False
            )
        elif "authorization_pending" in error_msg or "pending" in error_msg:
            return AuthPollResponse(
                status="pending",
                message="Waiting for user to authorize...",
                authenticated=False
            )
        elif "expired_token" in error_msg or "token expired" in error_msg or "code expired" in error_msg:
            return AuthPollResponse(
                status="expired",
                message="Authentication expired. Please start again.",
                authenticated=False
            )
        else:
            logger.warning(f"Auth poll error: {e}")
            return AuthPollResponse(
                status="pending",
                message="Waiting for authorization...",
                authenticated=False
            )


@router.post("/auth/logout")
async def logout():
    """
    Log out and clear authentication.

    Removes stored refresh token.
    """
    settings = get_settings()

    try:
        # Remove refresh token file
        token_file = settings.yoto_refresh_token_file
        if token_file.exists():
            token_file.unlink()
            logger.info("Refresh token removed")

        # Clear client authentication using public method
        client = get_yoto_client()
        if client:
            client.reset()

        return {
            "success": True,
            "message": "Logged out successfully"
        }

    except Exception as e:
        logger.error(f"Logout error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout: {str(e)}"
        ) from e
