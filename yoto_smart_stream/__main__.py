#!/usr/bin/env python3
"""
Command-line entry point for Yoto Smart Stream server.

This script starts the production server with proper configuration.
"""

import os
import sys
import time
from pathlib import Path

import uvicorn

from yoto_smart_stream.config import get_settings


def log_environment_variables():
    """Log all environment variables for debugging Railway variable initialization."""
    print("\n" + "=" * 80)
    print("Environment Variables:")
    print("=" * 80)

    # Get all environment variables and sort them for easier reading
    env_vars = sorted(os.environ.items())

    # Mask sensitive values
    sensitive_keys = {
        'TOKEN', 'SECRET', 'PASSWORD', 'KEY', 'CREDENTIAL',
        'AUTH', 'API_KEY', 'REFRESH_TOKEN', 'ACCESS_TOKEN'
    }

    for key, value in env_vars:
        # Check if key contains sensitive information
        is_sensitive = any(sensitive in key.upper() for sensitive in sensitive_keys)

        if is_sensitive:
            # Show only first and last 4 characters for sensitive values
            if len(value) > 8:
                masked_value = f"{value[:4]}...{value[-4:]}"
            else:
                masked_value = "***"
            print(f"  {key}={masked_value}")
        else:
            print(f"  {key}={value}")

    print("=" * 80 + "\n")


def main():
    """Main entry point for the server."""
    settings = get_settings()

    # Wait for Railway shared variables to initialize if configured
    if settings.railway_startup_wait_seconds > 0:
        print(f"\n⏳ Waiting {settings.railway_startup_wait_seconds} seconds for Railway variables to initialize...")
        time.sleep(settings.railway_startup_wait_seconds)
        print("✓ Startup wait complete\n")

    # Log environment variables if configured
    if settings.log_env_on_startup:
        log_environment_variables()

    print("\n" + "=" * 80)
    print(f"Starting {settings.app_name} v{settings.app_version}")
    print("=" * 80)
    print(f"\n🌍 Environment: {settings.environment}")
    print(f"📚 Documentation: http://{settings.host}:{settings.port}/docs")
    print(f"🎵 Audio files: {settings.audio_files_dir.absolute()}")
    print(f"🔌 MQTT enabled: {settings.mqtt_enabled}")

    if not settings.public_url:
        print("\n⚠️  PUBLIC_URL not set - card creation will not work")
        print("   Set PUBLIC_URL environment variable for audio streaming")
    else:
        print(f"\n🌐 Public URL: {settings.public_url}")

    if not Path(settings.yoto_refresh_token_file).exists():
        print("\n⚠️  Yoto refresh token not found")
        print("   Run: python examples/simple_client.py")
        print("   Some features may not work until authenticated")

    print("=" * 80 + "\n")

    # Start server
    uvicorn.run(
        "yoto_smart_stream.api:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    sys.exit(main())
