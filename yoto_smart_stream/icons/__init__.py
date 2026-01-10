"""
Icon management module for Yoto Smart Stream.

This module provides functionality for managing display icons for Yoto devices,
particularly for the Yoto Mini which has a 16x16 pixel display.

Key features:
- Access to public icon repository via Yoto API
- Custom icon upload and management
- Icon selection and assignment to chapters/tracks

Device Compatibility:
- Icons only display on Yoto Mini (16x16 pixel display)
- Original Yoto Player does not have a display screen
"""

from .client import IconClient
from .models import DisplayIcon, IconCategory, IconListResponse, IconUploadRequest
from .service import IconService

__all__ = [
    "IconClient",
    "DisplayIcon",
    "IconCategory",
    "IconListResponse",
    "IconUploadRequest",
    "IconService",
]
