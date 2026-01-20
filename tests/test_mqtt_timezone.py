"""Test MQTT event timezone handling."""

import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add the parent directory to the path to allow direct import
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import directly from the module file to avoid app initialization
spec = importlib.util.spec_from_file_location(
    "mqtt_event_store",
    Path(__file__).parent.parent / "yoto_smart_stream" / "api" / "mqtt_event_store.py",
)
assert spec is not None and spec.loader is not None
mqtt_module: Any = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mqtt_module)

MQTTEvent = mqtt_module.MQTTEvent
StreamRequestEvent = mqtt_module.StreamRequestEvent


def test_mqtt_event_timestamp_includes_utc_indicator():
    """Test that MQTT event timestamps include 'Z' UTC indicator."""
    # Create an event with a known UTC time
    test_time = datetime(2026, 1, 20, 5, 53, 0)  # UTC time
    event = MQTTEvent(
        timestamp=test_time,
        device_id="test-device",
        playback_status="playing",
        volume=50,
        volume_max=100,
    )

    # Convert to dict
    event_dict = event.to_dict()

    # Verify timestamp has 'Z' suffix indicating UTC
    assert event_dict["timestamp"].endswith(
        "Z"
    ), f"Timestamp should end with 'Z' to indicate UTC, got: {event_dict['timestamp']}"

    # Verify the timestamp can be parsed correctly
    timestamp_str = event_dict["timestamp"]
    # Remove 'Z' for Python's datetime parser
    parsed = datetime.fromisoformat(timestamp_str.rstrip("Z"))
    assert parsed == test_time


def test_stream_request_timestamp_includes_utc_indicator():
    """Test that stream request timestamps include 'Z' UTC indicator."""
    # Create a stream request with a known UTC time
    test_time = datetime(2026, 1, 20, 5, 53, 0)  # UTC time
    request = StreamRequestEvent(
        timestamp=test_time,
        stream_name="test-stream",
        device_ip="192.168.1.100",
    )

    # Convert to dict
    request_dict = request.to_dict()

    # Verify timestamp has 'Z' suffix indicating UTC
    assert request_dict["timestamp"].endswith(
        "Z"
    ), f"Timestamp should end with 'Z' to indicate UTC, got: {request_dict['timestamp']}"

    # Verify the timestamp can be parsed correctly
    timestamp_str = request_dict["timestamp"]
    # Remove 'Z' for Python's datetime parser
    parsed = datetime.fromisoformat(timestamp_str.rstrip("Z"))
    assert parsed == test_time


def test_mqtt_event_with_preceding_events():
    """Test that preceding MQTT events in stream requests also have UTC timestamps."""
    test_time = datetime(2026, 1, 20, 5, 53, 0)  # UTC time

    # Create MQTT events
    mqtt_event = MQTTEvent(
        timestamp=test_time,
        device_id="test-device",
        playback_status="playing",
    )

    # Create stream request with preceding events
    request = StreamRequestEvent(
        timestamp=test_time,
        stream_name="test-stream",
        preceding_mqtt_events=[mqtt_event],
    )

    # Convert to dict
    request_dict = request.to_dict()

    # Verify main timestamp
    assert request_dict["timestamp"].endswith("Z")

    # Verify preceding event timestamp
    assert len(request_dict["preceding_mqtt_events"]) == 1
    preceding = request_dict["preceding_mqtt_events"][0]
    assert preceding["timestamp"].endswith(
        "Z"
    ), f"Preceding event timestamp should have 'Z' suffix, got: {preceding['timestamp']}"


def test_json_serialization_with_utc_timestamps():
    """Test that timestamps can be serialized to JSON and maintain UTC indicator."""
    test_time = datetime(2026, 1, 20, 5, 53, 0)  # UTC time
    event = MQTTEvent(
        timestamp=test_time,
        device_id="test-device",
        playback_status="playing",
        volume=50,
    )

    # Convert to dict and serialize to JSON
    event_dict = event.to_dict()
    json_str = json.dumps(event_dict)

    # Parse back from JSON
    parsed_dict = json.loads(json_str)

    # Verify 'Z' suffix is preserved in JSON
    assert parsed_dict["timestamp"].endswith("Z")
    assert "2026-01-20T05:53:00Z" == parsed_dict["timestamp"]
