"""User authentication endpoints for login/logout."""

import logging
import os
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel

from ...auth import create_access_token, decode_access_token, verify_password
from ...auth_cognito import get_cognito_auth
from ...config import get_settings
from ...storage.dynamodb_store import DynamoStore, UserRecord, get_store

logger = logging.getLogger(__name__)

router = APIRouter()

# Check if running on AWS (Cognito enabled)
USE_COGNITO = os.getenv("COGNITO_USER_POOL_ID") is not None


# Request/Response models
class LoginRequest(BaseModel):
    """Login request model."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response model."""

    success: bool
    message: str
    username: Optional[str] = None


class SessionResponse(BaseModel):
    """Session status response model."""

    authenticated: bool
    username: Optional[str] = None
    is_admin: bool = False


def get_store_dep() -> DynamoStore:
    settings = get_settings()
    return get_store(settings.dynamodb_table, region_name=settings.dynamodb_region)


def get_current_user(
    session_token: Optional[str] = Cookie(None, alias="session"),
    store: DynamoStore = Depends(get_store_dep)
) -> Optional[UserRecord]:
    """
    Get current user from session cookie.
    
    Args:
        session_token: Session token from cookie
        db: Database session
        
    Returns:
        User object if authenticated, None otherwise
    """
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


def require_auth(user: Optional[UserRecord] = Depends(get_current_user)) -> UserRecord:
    """
    Dependency that requires authentication.
    
    Args:
        user: Current user from session
        
    Returns:
        User object
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user


@router.post("/user/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
    response: Response,
    store: DynamoStore = Depends(get_store_dep)
):
    """
    User login endpoint.
    
    Validates credentials and creates a session cookie.
    Supports both Cognito (AWS) and local SQLite authentication.
    
    Args:
        login_data: Username and password
        response: Response object to set cookies
        db: Database session
        
    Returns:
        Login response with success status
    """
    logger.info(f"Login attempt for username: {login_data.username} (Cognito: {USE_COGNITO})")
    
    # Try Cognito authentication if enabled
    if USE_COGNITO:
        cognito = get_cognito_auth()
        if cognito.is_enabled():
            cognito_result = cognito.authenticate(login_data.username, login_data.password)
            
            if cognito_result:
                # Create our own JWT token for the session
                access_token = create_access_token(data={"sub": login_data.username})
                
                # Set cookie with token
                response.set_cookie(
                    key="session",
                    value=access_token,
                    httponly=True,
                    max_age=30 * 24 * 60 * 60,  # 30 days
                    samesite="lax",
                    secure=False  # Set to True in production with HTTPS
                )
                
                logger.info(f"Successful Cognito login for user: {login_data.username}")
                
                return LoginResponse(
                    success=True,
                    message="Login successful",
                    username=login_data.username
                )
    
    # Fall back to local database authentication
    logger.debug("Using local database authentication")
    
    # Query user from database
    user = store.get_user(login_data.username)
    
    if not user:
        logger.warning(f"User not found: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Verify password
    password_valid = verify_password(login_data.password, user.hashed_password)
    logger.debug(f"Password verification result for {login_data.username}: {password_valid}")
    
    if not password_valid:
        logger.warning(f"Invalid password for username: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Login attempt for inactive user: {login_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.username})
    
    # Set cookie with token
    response.set_cookie(
        key="session",
        value=access_token,
        httponly=True,
        max_age=30 * 24 * 60 * 60,  # 30 days
        samesite="lax",
        secure=False  # Set to True in production with HTTPS
    )
    
    logger.info(f"Successful local login for user: {user.username}")
    
    return LoginResponse(
        success=True,
        message="Login successful",
        username=user.username
    )


@router.post("/user/logout")
async def logout(response: Response):
    """
    User logout endpoint.
    
    Clears the session cookie.
    
    Args:
        response: Response object to clear cookies
        
    Returns:
        Logout confirmation
    """
    response.delete_cookie(key="session")
    return {"success": True, "message": "Logged out successfully"}


@router.get("/user/session", response_model=SessionResponse)
async def check_session(user: Optional[UserRecord] = Depends(get_current_user)):
    """
    Check current session status.
    
    Args:
        user: Current user from session
        
    Returns:
        Session status and username if authenticated
    """
    if user:
        return SessionResponse(authenticated=True, username=user.username, is_admin=user.is_admin)
    return SessionResponse(authenticated=False)


@router.get("/user/debug")
async def debug_users(store: DynamoStore = Depends(get_store_dep)):
    """
    Debug endpoint to check user database state.
    
    Returns count and list of usernames (NOT FOR PRODUCTION).
    """
    try:
        users = store.list_users()
        return {
            "user_count": len(users),
            "usernames": [u.username for u in users],
            "persistence": "dynamodb"
        }
    except Exception as e:
        return {
            "error": str(e),
            "user_count": 0,
            "usernames": []
        }
