"""Admin endpoints for user management and system administration."""

import logging
import os
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from ...auth import get_password_hash
from ...auth_cognito import get_cognito_auth
from ...config import get_settings
from ...storage.dynamodb_store import DynamoStore, UserRecord, get_store
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
    is_admin: bool = Field(default=False, description="Whether to grant admin access to this user")


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
    is_admin: Optional[bool] = Field(None, description="Whether to grant admin access to this user")


class UpdateUserResponse(BaseModel):
    """Response model for user update."""

    success: bool
    message: str
    user: Optional[UserResponse] = None


def get_store_dep() -> DynamoStore:
    settings = get_settings()
    return get_store(settings.dynamodb_table, region_name=settings.dynamodb_region)


def require_admin(user: UserRecord = Depends(get_current_user)) -> UserRecord:
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
    admin: UserRecord = Depends(require_admin),
    store: DynamoStore = Depends(get_store_dep)
):
    """
    List all users (admin only).
    
    Args:
        admin: Current admin user
        store: Database store
        
    Returns:
        List of all users
    """
    logger.info(f"Admin {admin.username} listing all users")
    
    try:
        users = store.list_users()
        
        return [
            UserResponse(
                id=user.user_id,
                username=user.username,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at.isoformat()
            )
            for user in users
        ]
    except Exception as e:
        logger.error(f"Error listing users: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list users: {str(e)}"
        )


@router.post("/admin/users", response_model=CreateUserResponse)
async def create_user(
    user_data: CreateUserRequest,
    admin: UserRecord = Depends(require_admin),
    store: DynamoStore = Depends(get_store_dep)
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
                # If the user already exists in Cognito, sync password and proceed to local creation
                if cognito.last_error and "UsernameExistsException" in cognito.last_error:
                    logger.info(f"Cognito user already exists; syncing local record for {user_data.username}")
                    if not cognito.set_permanent_password(user_data.username, user_data.password):
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to sync existing Cognito user password: {cognito.last_error}"
                        )
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to create user in Cognito: {cognito.last_error or 'Unknown error'}"
                    )
            else:
                logger.info(f"✓ User created in Cognito: {user_data.username}")
    
    # Check if username already exists in local database
    existing_user = store.get_user(user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Username '{user_data.username}' already exists"
        )
    
    # Hash password
    hashed_password = get_password_hash(user_data.password)
    
    # Create new user with admin flag from request
    try:
        created = store.create_user(
            username=user_data.username,
            hashed_password=hashed_password,
            email=user_data.email,
            is_admin=user_data.is_admin,
        )

        logger.info(f"✓ User created successfully: {created.username} (id: {created.user_id})")

        return CreateUserResponse(
            success=True,
            message=f"User '{created.username}' created successfully",
            user=UserResponse(
                id=created.user_id,
                username=created.username,
                email=created.email,
                is_active=created.is_active,
                is_admin=created.is_admin,
                created_at=created.created_at.isoformat()
            )
        )
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.patch("/admin/users/{user_id}", response_model=UpdateUserResponse)
async def update_user(
    user_id: int,
    update_data: UpdateUserRequest,
    admin: UserRecord = Depends(require_admin),
    store: DynamoStore = Depends(get_store_dep)
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
    if not update_data.email and not update_data.password and update_data.is_admin is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field (email, password, or is_admin) must be provided"
        )
    
    # Get the user
    user = store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    try:
        hashed_password = get_password_hash(update_data.password) if update_data.password else None
        updated = store.update_user(
            user_id, 
            email=update_data.email, 
            hashed_password=hashed_password,
            is_admin=update_data.is_admin
        )
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )

        logger.info(f"✓ User updated successfully: {updated.username} (id: {updated.user_id})")

        return UpdateUserResponse(
            success=True,
            message=f"User '{updated.username}' updated successfully",
            user=UserResponse(
                id=updated.user_id,
                username=updated.username,
                email=updated.email,
                is_active=updated.is_active,
                is_admin=updated.is_admin,
                created_at=updated.created_at.isoformat()
            )
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )

class DeleteUserResponse(BaseModel):
    """Response model for user deletion."""
    success: bool
    message: str


@router.delete("/admin/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(
    user_id: int,
    admin: UserRecord = Depends(require_admin),
    store: DynamoStore = Depends(get_store_dep)
):
    """
    Delete a user (admin only).
    
    Cannot delete:
    - Yourself (the current admin)
    - Admin users (to prevent accidental lockout)
    
    Args:
        user_id: ID of the user to delete
        admin: Current admin user
        store: Database store
        
    Returns:
        Success message
    """
    logger.info(f"Admin {admin.username} attempting to delete user {user_id}")
    
    # Get the user
    user = store.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found"
        )
    
    # Cannot delete yourself
    if user.user_id == admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )
    
    # Cannot delete admin users (to prevent lockout)
    if user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete admin users"
        )
    
    try:
        # Delete from Cognito if enabled
        if USE_COGNITO:
            cognito = get_cognito_auth()
            if not cognito.delete_user(user.username):
                logger.warning(f"Failed to delete user from Cognito: {cognito.last_error}")
                # Continue anyway - DynamoDB is source of truth
        
        # Delete from DynamoDB
        if not store.delete_user(user_id):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found"
            )

        logger.info(f"✓ User deleted successfully: {user.username} (id: {user_id})")

        return DeleteUserResponse(
            success=True,
            message=f"User '{user.username}' deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )