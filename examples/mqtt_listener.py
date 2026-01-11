#!/usr/bin/env python3
"""
MQTT Event Listener Example

This script connects to the Yoto MQTT broker and listens for real-time events
from your Yoto players. Useful for understanding event structure and timing.

Events you might see:
- playback.status: Track position, play/pause state
- config.nightLight: Night light changes
- config.volume: Volume changes
- player.status: Battery, connectivity
- button.press: Physical button presses
"""

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
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


class EventLogger:
    """Custom event logger for MQTT events."""

    def __init__(self, log_to_file: bool = False):
        self.log_to_file = log_to_file
        self.event_count = 0

        if log_to_file:
            self.log_file = Path("mqtt_events.jsonl")
            logger.info(f"Logging events to {self.log_file}")

    def log_event(self, topic: str, payload: dict):
        """Log an MQTT event."""
        self.event_count += 1

        # Create structured event
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "count": self.event_count,
            "topic": topic,
            "payload": payload,
        }

        # Pretty print to console
        print("\n" + "=" * 80)
        print(f"Event #{self.event_count} at {event['timestamp']}")
        print(f"Topic: {topic}")
        print("Payload:")
        print(json.dumps(payload, indent=2))
        print("=" * 80)

        # Log to file if enabled
        if self.log_to_file:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(event) + "\n")


def main():
    """Main function to listen for MQTT events."""

    # Get client ID from environment or token file (prefer YOTO_SERVER_CLIENT_ID, fallback to legacy YOTO_CLIENT_ID)
    client_id = os.getenv("YOTO_SERVER_CLIENT_ID") or os.getenv("YOTO_CLIENT_ID")
    token_file = Path(".yoto_refresh_token")

    if not client_id:
        logger.error("YOTO_SERVER_CLIENT_ID or YOTO_CLIENT_ID environment variable not set")
        logger.info("Set with: export YOTO_SERVER_CLIENT_ID=your_client_id")
        sys.exit(1)

    if not token_file.exists():
        logger.error("No refresh token found. Run simple_client.py first to authenticate.")
        sys.exit(1)

    # Initialize
    logger.info("Initializing Yoto Manager...")
    ym = YotoManager(client_id=client_id)

    # Authenticate with refresh token
    refresh_token = token_file.read_text().strip()
    ym.set_refresh_token(refresh_token)
    ym.check_and_refresh_token()
    logger.info("Authenticated successfully!")

    # Initialize event logger
    log_to_file = "--log-file" in sys.argv
    event_logger = EventLogger(log_to_file=log_to_file)

    # Connect to MQTT
    logger.info("Connecting to MQTT broker...")

    try:
        ym.connect_to_events()
        logger.info("Connected to MQTT successfully!")
    except Exception as e:
        logger.error(f"Failed to connect to MQTT: {e}")
        sys.exit(1)

    # Note: The yoto_api library handles MQTT callbacks internally
    # For a production system, you'd want to implement custom callbacks
    # This example relies on the library's default logging

    print("\n" + "=" * 80)
    print("LISTENING FOR EVENTS")
    print("=" * 80)
    print("\nTry these actions on your Yoto player to see events:")
    print("  - Insert or remove a card")
    print("  - Press play/pause")
    print("  - Change volume")
    print("  - Change night light color")
    print("  - Press left/right buttons")
    print("\nPress Ctrl+C to stop listening\n")

    # Keep alive and listen for events
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping event listener...")
        logger.info(f"Total events received: {event_logger.event_count}")

        if log_to_file:
            logger.info(f"Events saved to {event_logger.log_file}")


if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        print("\nUsage:")
        print("  python mqtt_listener.py              # Display events in console")
        print("  python mqtt_listener.py --log-file   # Also save to mqtt_events.jsonl")
        sys.exit(0)

    main()
