"""Authentication endpoints for Yoto account login."""

import logging
import os
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Cookie, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...config import get_settings
from ...core import YotoClient
from ...database import get_db
from ...models import User
from ..dependencies import get_yoto_client, set_yoto_client

logger = logging.getLogger(__name__)

router = APIRouter()


def get_current_user_optional(
    session_token: Optional[str] = Cookie(None, alias="session"),
    db: Session = Depends(get_db)
) -> Optional[User]:
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
    
    user = db.query(User).filter(User.username == username).first()
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
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
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
        logger.info(f"Polling auth status for device_code: {poll_request.device_code[:10]}...")
        
        # Use single-attempt polling (non-blocking, suitable for Lambda/serverless)
        # The frontend will poll this endpoint repeatedly until success
        poll_status = client.poll_device_code_single_attempt(poll_request.device_code)
        
        logger.info(f"Poll status result: {poll_status}")
        
        if poll_status == "success":
            # Authentication succeeded
            client.set_authenticated(True)

            # Save refresh token using Secrets Manager (AWS Lambda) or file (local dev)
            if client.manager.token and client.manager.token.refresh_token:
                # Determine user_id for token storage
                user_id = current_user.username if current_user else "default"
                
                # On Lambda, use Secrets Manager for persistent storage
                if os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                    try:
                        from ...utils.token_storage import TokenStorage
                        token_storage = TokenStorage()
                        
                        # Extract token data
                        access_token = client.manager.token.access_token if client.manager.token.access_token else None
                        expires_at = None
                        if hasattr(client.manager.token, 'expires_at') and client.manager.token.expires_at:
                            expires_at = client.manager.token.expires_at if isinstance(client.manager.token.expires_at, datetime) else None
                        
                        # Save to Secrets Manager
                        token_storage.save_token(
                            user_id=user_id,
                            refresh_token=client.manager.token.refresh_token,
                            access_token=access_token,
                            expires_at=expires_at
                        )
                        logger.info(f"Yoto OAuth tokens saved to Secrets Manager for user: {user_id}")
                    except Exception as e:
                        logger.error(f"Failed to save tokens to Secrets Manager: {e}")
                        # Don't fail authentication, continue
                else:
                    # Local development: use file storage
                    token_file = settings.yoto_refresh_token_file
                    token_file.parent.mkdir(parents=True, exist_ok=True)
                    token_file.write_text(client.manager.token.refresh_token)
                    logger.info(f"Refresh token saved to {token_file}")
                
                # Also save tokens to database for backward compatibility
                if current_user:
                    try:
                        current_user.yoto_access_token = client.manager.token.access_token
                        current_user.yoto_refresh_token = client.manager.token.refresh_token
                        if hasattr(client.manager.token, 'expires_at'):
                            current_user.yoto_token_expires_at = client.manager.token.expires_at
                        db.commit()
                        logger.info(f"Yoto tokens also saved to database for user: {current_user.username}")
                    except Exception as e:
                        logger.error(f"Failed to save tokens to database: {e}")
                        db.rollback()
            else:
                logger.error("No refresh token available after authentication!")

            # Update player status
            try:
                client.update_player_status()
            except Exception as e:
                logger.warning(f"Failed to update player status: {e}")

            logger.info("Authentication successful!")

            return AuthPollResponse(
                status="success",
                message="Successfully authenticated with Yoto API",
                authenticated=True
            )
        
        elif poll_status == "pending":
            return AuthPollResponse(
                status="pending",
                message="Waiting for user to authorize...",
                authenticated=False
            )
        
        elif poll_status == "expired":
            return AuthPollResponse(
                status="expired",
                message="Authentication expired. Please start again.",
                authenticated=False
            )
        
        else:
            # Unknown status
            return AuthPollResponse(
                status="error",
                message=f"Unknown status: {poll_status}",
                authenticated=False
            )

    except Exception as e:
        error_msg = str(e).lower()
        logger.error(f"Auth poll error: {e}", exc_info=True)
        
        # Try to provide helpful error messages
        if "expired" in error_msg or "token expired" in error_msg:
            return AuthPollResponse(
                status="expired",
                message="Authentication expired. Please start again.",
                authenticated=False
            )
        else:
            return AuthPollResponse(
                status="error",
                message=f"Authentication error: {str(e)}",
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
