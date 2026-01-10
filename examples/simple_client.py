#!/usr/bin/env python3
"""
Simple example of connecting to the Yoto API and controlling a player.

This demonstrates:
1. Authentication using device code flow
2. Getting player status
3. Basic player control (pause)

Requirements:
- yoto_api library installed
- YOTO_CLIENT_ID environment variable set
"""

import logging
import os
import sys
import time
from pathlib import Path

try:
    from yoto_api import YotoManager
except ImportError:
    print("Error: yoto_api library not found.")
    print("Install it with: pip install yoto_api")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main function to demonstrate Yoto API usage."""

    # Get client ID from environment
    client_id = os.getenv("YOTO_CLIENT_ID")
    if not client_id:
        logger.error("YOTO_CLIENT_ID environment variable not set")
        logger.info("Get your client ID from: https://yoto.dev/get-started/start-here/")
        sys.exit(1)

    # Initialize Yoto Manager
    logger.info("Initializing Yoto Manager...")
    ym = YotoManager(client_id=client_id)

    # Check for stored refresh token
    token_file = Path(".yoto_refresh_token")
    refresh_token = None

    if token_file.exists():
        refresh_token = token_file.read_text().strip()
        logger.info("Found stored refresh token, attempting to use it...")

        try:
            ym.set_refresh_token(refresh_token)
            ym.check_and_refresh_token()
            logger.info("Successfully authenticated with stored token!")
        except Exception as e:
            logger.warning(f"Stored token failed: {e}")
            logger.info("Will perform device code flow authentication...")
            refresh_token = None

    # If no valid token, do device code flow
    if not refresh_token:
        logger.info("Starting device code flow authentication...")
        device_info = ym.device_code_flow_start()

        print("\n" + "=" * 60)
        print("AUTHENTICATION REQUIRED")
        print("=" * 60)
        print(f"\n1. Go to: {device_info['verification_uri']}")
        print(f"2. Enter code: {device_info['user_code']}")
        print("\nWaiting for authorization...")
        print("(This typically takes 15-30 seconds after you approve)\n")

        # Wait for user to complete authorization
        time.sleep(20)

        try:
            ym.device_code_flow_complete()
            logger.info("Authentication successful!")

            # Save refresh token for future use
            if hasattr(ym.token, "refresh_token"):
                token_file.write_text(ym.token.refresh_token)
                logger.info(f"Refresh token saved to {token_file}")

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            sys.exit(1)

    # Get and display player information
    logger.info("Fetching player status...")
    ym.update_player_status()

    if not ym.players:
        logger.warning("No players found on your account")
        return

    print("\n" + "=" * 60)
    print("YOTO PLAYERS")
    print("=" * 60 + "\n")

    for player_id, player in ym.players.items():
        print(f"Player: {player.name}")
        print(f"  ID: {player_id}")
        print(f"  Online: {player.online}")
        print(f"  Volume: {player.volume}/16")

        if hasattr(player, "playing") and player.playing:
            print("  Status: Playing")
        else:
            print("  Status: Not playing")

        if hasattr(player, "battery_level"):
            print(f"  Battery: {player.battery_level}%")
        print()

    # Connect to MQTT for real-time events
    logger.info("Connecting to MQTT for real-time events...")
    try:
        ym.connect_to_events()
        logger.info("Connected to MQTT successfully!")
    except Exception as e:
        logger.error(f"Failed to connect to MQTT: {e}")
        return

    # Example: Pause the first player
    first_player_id = next(iter(ym.players.keys()))
    print(f"\nExample: Pausing player {ym.players[first_player_id].name}...")

    try:
        ym.pause_player(first_player_id)
        logger.info("Pause command sent!")
    except Exception as e:
        logger.error(f"Failed to pause player: {e}")

    # Keep alive to receive MQTT events
    print("\nListening for events for 30 seconds...")
    print("(Try interacting with your Yoto player to see events)\n")

    try:
        time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")

    logger.info("Example complete!")


if __name__ == "__main__":
    main()
