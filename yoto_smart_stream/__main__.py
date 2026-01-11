#!/usr/bin/env python3
"""
Command-line entry point for Yoto Smart Stream server.

This script starts the production server with proper configuration.
"""

import sys
import time
from pathlib import Path

import uvicorn

from yoto_smart_stream.config import get_settings
from yoto_smart_stream.utils import log_environment_variables


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
        print()  # Add newline before env vars
        log_environment_variables(print)
        print()  # Add newline after env vars

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
