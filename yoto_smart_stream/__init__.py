"""
Yoto Smart Stream - Audio streaming service for Yoto devices.

This package provides functionality for streaming audio to Yoto devices,
monitoring events via MQTT, and managing interactive audio experiences.

Device Compatibility:
- Yoto Player (original): No display screen, no microphone
- Yoto Mini: 16x16 pixel display, no microphone

Note: Voice control features are not supported as Yoto devices do not have microphones.
"""

__version__ = "0.2.1+mysql"

from .api import app, create_app
from .config import Settings, get_settings
from .core import YotoClient

__all__ = ["app", "create_app", "get_settings", "Settings", "YotoClient", "__version__"]
