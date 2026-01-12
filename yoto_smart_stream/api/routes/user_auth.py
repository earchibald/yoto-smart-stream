"""User authentication endpoints for login/logout."""

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...auth import create_access_token, decode_access_token, verify_password
from ...database import get_db
from ...models import User

logger = logging.getLogger(__name__)

router = APIRouter()


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


def get_current_user(
    session_token: Optional[str] = Cookie(None, alias="session"),
    db: Session = Depends(get_db)
) -> Optional[User]:
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
    
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        return None
    
    return user


def require_auth(user: Optional[User] = Depends(get_current_user)) -> User:
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
    db: Session = Depends(get_db)
):
    """
    User login endpoint.
    
    Validates credentials and creates a session cookie.
    
    Args:
        login_data: Username and password
        response: Response object to set cookies
        db: Database session
        
    Returns:
        Login response with success status
    """
    logger.info(f"Login attempt for username: {login_data.username}")
    
    # Query user from database
    user = db.query(User).filter(User.username == login_data.username).first()
    
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
    
    logger.info(f"Successful login for user: {user.username}")
    
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
async def check_session(user: Optional[User] = Depends(get_current_user)):
    """
    Check current session status.
    
    Args:
        user: Current user from session
        
    Returns:
        Session status and username if authenticated
    """
    if user:
        return SessionResponse(authenticated=True, username=user.username)
    return SessionResponse(authenticated=False)


@router.get("/user/debug")
async def debug_users(db: Session = Depends(get_db)):
    """
    Debug endpoint to check user database state.
    
    Returns count and list of usernames (NOT FOR PRODUCTION).
    """
    try:
        users = db.query(User).all()
        return {
            "user_count": len(users),
            "usernames": [u.username for u in users],
            "database_url": "Check server logs for database path"
        }
    except Exception as e:
        return {
            "error": str(e),
            "user_count": 0,
            "usernames": []
        }
