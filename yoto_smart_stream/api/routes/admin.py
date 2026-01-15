"""Admin endpoints for user management and system administration."""

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ...auth import get_password_hash
from ...auth_cognito import get_cognito_auth
from ...database import get_db
from ...models import User
from .user_auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

# Check if running on AWS (Cognito enabled)
USE_COGNITO = os.getenv("COGNITO_USER_POOL_ID") is not None


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


class UpdateUserRequest(BaseModel):
    """Request model for updating a user."""

    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=4)


class UpdateUserResponse(BaseModel):
    """Response model for user update."""

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
    
    Creates user in both Cognito (if enabled) and local database.
    Non-admin users are created with access to the library and devices
    using the server's Yoto OAuth credentials (single-tenant mode).
    
    Args:
        user_data: User creation data
        admin: Current admin user
        db: Database session
        
    Returns:
        Created user information
    """
    logger.info(f"Admin {admin.username} creating new user: {user_data.username} (Cognito: {USE_COGNITO})")
    
    # Create in Cognito if enabled
    if USE_COGNITO:
        cognito = get_cognito_auth()
        if cognito.is_enabled():
            email = user_data.email or f"{user_data.username}@example.com"
            success = cognito.create_user(
                username=user_data.username,
                email=email,
                password=user_data.password,
                temporary_password=False
            )
            
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to create user in Cognito"
                )
            
            logger.info(f"✓ User created in Cognito: {user_data.username}")
    
    # Check if username already exists in local database
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


@router.patch("/admin/users/{user_id}", response_model=UpdateUserResponse)
async def update_user(
    user_id: int,
    update_data: UpdateUserRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update an existing user's email and/or password (admin only).
    
    Passwords are stored as one-way hashes and cannot be retrieved.
    Only email and password can be updated.
    
    Args:
        user_id: ID of the user to update
        update_data: Update data (email and/or password)
        admin: Current admin user
        db: Database session
        
    Returns:
        Updated user information
    """
    logger.info(f"Admin {admin.username} updating user {user_id}")
    
    # At least one field must be provided
    if not update_data.email and not update_data.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field (email or password) must be provided"
        )
    
    # Get the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    try:
        # Update email if provided
        if update_data.email is not None:
            # Check if email is already in use by another user
            existing_user = db.query(User).filter(
                User.email == update_data.email,
                User.id != user_id
            ).first()
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Email '{update_data.email}' is already in use by another user"
                )
            user.email = update_data.email
            logger.info(f"Updated email for user {user.username}")
        
        # Update password if provided
        if update_data.password:
            user.hashed_password = get_password_hash(update_data.password)
            logger.info(f"Updated password for user {user.username}")
        
        db.commit()
        db.refresh(user)
        
        logger.info(f"✓ User updated successfully: {user.username} (id: {user.id})")
        
        return UpdateUserResponse(
            success=True,
            message=f"User '{user.username}' updated successfully",
            user=UserResponse(
                id=user.id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at.isoformat()
            )
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )
