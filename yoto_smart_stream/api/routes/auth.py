"""Authentication endpoints for Yoto account login."""

import logging

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from ...config import get_settings
from ..dependencies import get_yoto_client

logger = logging.getLogger(__name__)

router = APIRouter()


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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="YOTO_CLIENT_ID not configured. Please set environment variable."
        )

    try:
        # Get or create client
        client = get_yoto_client()
        if client is None:
            from ...core import YotoClient
            client = YotoClient(settings)
            from ..dependencies import set_yoto_client
            set_yoto_client(client)

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
async def poll_auth_status(poll_request: AuthPollRequest):
    """
    Poll for authentication completion.

    Args:
        poll_request: Contains device_code from start_auth_flow

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
        # Try to complete the device code flow
        client.manager.device_code_flow_complete()

        # If we get here, authentication succeeded
        client._authenticated = True

        # Save refresh token
        if hasattr(client.manager.token, "refresh_token"):
            token_file = settings.yoto_refresh_token_file
            token_file.write_text(client.manager.token.refresh_token)
            logger.info(f"Refresh token saved to {token_file}")

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

    except Exception as e:
        error_msg = str(e).lower()

        # Check for common error types
        if "authorization_pending" in error_msg or "pending" in error_msg:
            return AuthPollResponse(
                status="pending",
                message="Waiting for user to authorize...",
                authenticated=False
            )
        elif "expired" in error_msg or "token" in error_msg:
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

        # Clear client authentication
        client = get_yoto_client()
        if client:
            client._authenticated = False
            client.manager = None

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
