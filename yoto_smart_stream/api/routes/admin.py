"""Admin endpoints for user management and system administration."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ...auth import get_password_hash
from ...database import get_db
from ...models import User
from .user_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class CreateUserRequest(BaseModel):
    """Request model for creating a new user."""

    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    password: str = Field(..., min_length=4)
    email: Optional[EmailStr] = None


class UserResponse(BaseModel):
    """Response model for user information."""

    id: int
    username: str
    email: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: str

    class Config:
        from_attributes = True


class CreateUserResponse(BaseModel):
    """Response model for user creation."""

    success: bool
    message: str
    user: Optional[UserResponse] = None


def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires admin authentication.
    
    Args:
        user: Current user from session
        
    Returns:
        User object if admin
        
    Raises:
        HTTPException: If user is not authenticated or not an admin
    """
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


@router.get("/admin/users", response_model=List[UserResponse])
async def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    List all users (admin only).
    
    Args:
        admin: Current admin user
        db: Database session
        
    Returns:
        List of all users
    """
    logger.info(f"Admin {admin.username} listing all users")
    
    users = db.query(User).all()
    
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at.isoformat()
        )
        for user in users
    ]


@router.post("/admin/users", response_model=CreateUserResponse)
async def create_user(
    user_data: CreateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create a new user (admin only).
    
    Non-admin users are created with access to the library and devices
    using the server's Yoto OAuth credentials (single-tenant mode).
    
    Args:
        user_data: User creation data
        admin: Current admin user
        db: Database session
        
    Returns:
        Created user information
    """
    logger.info(f"Admin {admin.username} creating new user: {user_data.username}")
    
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' already exists"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create new user (non-admin by default)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True,
        is_admin=False  # New users are not admins
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        logger.info(f"✓ User created successfully: {new_user.username} (id: {new_user.id})")
        
        return CreateUserResponse(
            success=True,
            message=f"User '{new_user.username}' created successfully",
            user=UserResponse(
                id=new_user.id,
                username=new_user.username,
                email=new_user.email,
                is_active=new_user.is_active,
                is_admin=new_user.is_admin,
                created_at=new_user.created_at.isoformat()
            )
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
