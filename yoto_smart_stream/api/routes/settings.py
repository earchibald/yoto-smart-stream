"""Settings management endpoints for admin configuration."""

import logging
import os
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...database import get_db
from ...models import Setting
from ..routes.user_auth import require_auth
from ...models import User

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models
class SettingResponse(BaseModel):
    """Setting response model."""

    key: str
    value: str
    description: Optional[str] = None
    env_var_override: Optional[str] = None
    is_overridden: bool = False


class SettingUpdateRequest(BaseModel):
    """Setting update request model."""

    value: str = Field(..., description="The setting value")


class SettingsListResponse(BaseModel):
    """Settings list response model."""

    settings: List[SettingResponse]


# Define available settings with their environment variable names
AVAILABLE_SETTINGS = {
    "transcription_enabled": {
        "env_var": "transcription_enabled",  # Pydantic reads both upper and lowercase
        "description": "Enable or disable automatic transcription of uploaded audio files",
        "default": "false",
    },
}


def get_env_var_value(env_var_name: str) -> Optional[str]:
    """Get environment variable value if set (checks both cases)."""
    # Check both uppercase and lowercase versions
    value = os.getenv(env_var_name.upper()) or os.getenv(env_var_name.lower())
    if value is not None:
        return str(value).lower()  # Normalize to lowercase for boolean comparison
    return None


def get_setting_value(key: str, db: Session) -> tuple[str, Optional[str], bool]:
    """
    Get setting value, checking both database and environment variables.
    
    Returns:
        tuple: (effective_value, env_var_value, is_overridden)
    """
    config = AVAILABLE_SETTINGS.get(key)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    
    # Check environment variable first
    env_var_name = config["env_var"]
    env_var_value = get_env_var_value(env_var_name)
    
    # Get database value
    setting = db.query(Setting).filter(Setting.key == key).first()
    db_value = str(setting.value) if setting else config["default"]
    
    # Determine if overridden
    is_overridden = env_var_value is not None
    effective_value = env_var_value if is_overridden else db_value
    
    return str(effective_value), env_var_value, is_overridden


@router.get("/settings", response_model=SettingsListResponse)
async def list_settings(
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    List all available settings with their values and override status.
    
    Requires admin authentication.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logger.info(f"User {user.username} listing settings")
    
    settings_list = []
    
    for key, config in AVAILABLE_SETTINGS.items():
        value, env_override, is_overridden = get_setting_value(key, db)
        
        settings_list.append(SettingResponse(
            key=key,
            value=value,
            description=config["description"],
            env_var_override=env_override,
            is_overridden=is_overridden
        ))
    
    return SettingsListResponse(settings=settings_list)


@router.get("/settings/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Get a specific setting value.
    
    Requires admin authentication.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    logger.info(f"User {user.username} getting setting: {key}")
    
    config = AVAILABLE_SETTINGS.get(key)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    
    value, env_override, is_overridden = get_setting_value(key, db)
    
    return SettingResponse(
        key=key,
        value=value,
        description=config["description"],
        env_var_override=env_override,
        is_overridden=is_overridden
    )


@router.put("/settings/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    request: SettingUpdateRequest,
    user: User = Depends(require_auth),
    db: Session = Depends(get_db)
):
    """
    Update a setting value in the database.
    
    Note: If an environment variable override is set, it will take precedence
    over the database value.
    
    Requires admin authentication.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    config = AVAILABLE_SETTINGS.get(key)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    
    logger.info(f"User {user.username} updating setting {key} to: {request.value}")
    
    # Get or create setting
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = request.value
    else:
        setting = Setting(
            key=key,
            value=request.value,
            description=config["description"]
        )
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    
    # Get current effective value
    value, env_override, is_overridden = get_setting_value(key, db)
    
    return SettingResponse(
        key=key,
        value=value,
        description=config["description"],
        env_var_override=env_override,
        is_overridden=is_overridden
    )
