"""MQTT event tracking and correlation with stream requests."""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class MQTTEvent:
    """Represents a single MQTT event from a Yoto device."""

    timestamp: datetime
    device_id: Optional[str] = None
    raw_payload: Dict = field(default_factory=dict)
    
    # Common fields from payload
    volume: Optional[int] = None
    volume_max: Optional[int] = None
    card_id: Optional[str] = None
    playback_status: Optional[str] = None
    streaming: Optional[bool] = None
    playback_wait: Optional[bool] = None
    sleep_timer_active: Optional[bool] = None
    repeat_all: Optional[bool] = None
    
    # Button events
    button_left_clicked: bool = False
    button_right_clicked: bool = False
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "device_id": self.device_id,
            "volume": self.volume,
            "volume_max": self.volume_max,
            "card_id": self.card_id,
            "playback_status": self.playback_status,
            "streaming": self.streaming,
            "playback_wait": self.playback_wait,
            "sleep_timer_active": self.sleep_timer_active,
            "repeat_all": self.repeat_all,
            "button_left_clicked": self.button_left_clicked,
            "button_right_clicked": self.button_right_clicked,
        }


@dataclass
class StreamRequestEvent:
    """Represents a stream request with context."""
    
    timestamp: datetime
    stream_name: str
    device_ip: Optional[str] = None
    user_agent: Optional[str] = None
    preceding_mqtt_events: List[MQTTEvent] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "stream_name": self.stream_name,
            "device_ip": self.device_ip,
            "user_agent": self.user_agent,
            "preceding_mqtt_events": [e.to_dict() for e in self.preceding_mqtt_events],
        }


class MQTTEventStore:
    """Stores and manages MQTT events with correlation to stream requests."""
    
    def __init__(self, max_events: int = 500, device_id: Optional[str] = None):
        """
        Initialize the MQTT event store.
        
        Args:
            max_events: Maximum number of events to keep in memory
            device_id: Optional device identifier for filtering
        """
        self.max_events = max_events
        self.device_id = device_id
        self.events: List[MQTTEvent] = []
        self.stream_requests: List[StreamRequestEvent] = []
        
    def add_event(self, event: MQTTEvent) -> None:
        """Add an MQTT event to the store."""
        self.events.append(event)
        
        # Trim to max_events
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        logger.debug(
            f"MQTT Event stored: {event.device_id} - "
            f"status={event.playback_status}, volume={event.volume}/{event.volume_max}, "
            f"streaming={event.streaming}"
        )
    
    def add_stream_request(
        self,
        stream_name: str,
        device_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        lookback_seconds: int = 30,
    ) -> StreamRequestEvent:
        """
        Add a stream request with preceding MQTT events.
        
        Args:
            stream_name: Name of the stream being requested
            device_ip: IP address of requesting device
            user_agent: User-Agent header from request
            lookback_seconds: How far back to include MQTT events
            
        Returns:
            StreamRequestEvent with correlated MQTT events
        """
        now = datetime.now()
        cutoff = datetime.fromtimestamp(now.timestamp() - lookback_seconds)
        
        # Find recent MQTT events
        recent_events = [e for e in self.events if e.timestamp >= cutoff]
        
        request = StreamRequestEvent(
            timestamp=now,
            stream_name=stream_name,
            device_ip=device_ip,
            user_agent=user_agent,
            preceding_mqtt_events=recent_events,
        )
        
        self.stream_requests.append(request)
        
        # Trim stream requests
        if len(self.stream_requests) > self.max_events:
            self.stream_requests = self.stream_requests[-self.max_events:]
        
        return request
    
    def get_device_state(self) -> Optional[MQTTEvent]:
        """Get the most recent device state event."""
        if self.events:
            return self.events[-1]
        return None
    
    def get_recent_events(self, count: int = 20) -> List[MQTTEvent]:
        """Get the most recent N events."""
        return self.events[-count:]
    
    def get_events_since(self, seconds_ago: int = 60) -> List[MQTTEvent]:
        """Get all events from the last N seconds."""
        cutoff = datetime.fromtimestamp(datetime.now().timestamp() - seconds_ago)
        return [e for e in self.events if e.timestamp >= cutoff]
    
    def get_stream_requests_since(self, seconds_ago: int = 60) -> List[StreamRequestEvent]:
        """Get all stream requests from the last N seconds."""
        cutoff = datetime.fromtimestamp(datetime.now().timestamp() - seconds_ago)
        return [r for r in self.stream_requests if r.timestamp >= cutoff]
    
    def to_dict(self) -> dict:
        """Export store state as dictionary."""
        current_state = self.get_device_state()
        return {
            "device_id": self.device_id,
            "events_count": len(self.events),
            "stream_requests_count": len(self.stream_requests),
            "current_device_state": current_state.to_dict() if current_state else None,
            "recent_events": [e.to_dict() for e in self.get_recent_events(10)],
            "recent_stream_requests": [r.to_dict() for r in self.stream_requests[-5:]],
        }


# Global event store instance
_event_store: Optional[MQTTEventStore] = None


def get_mqtt_event_store() -> MQTTEventStore:
    """Get or create the global MQTT event store."""
    global _event_store
    if _event_store is None:
        _event_store = MQTTEventStore()
    return _event_store


def set_mqtt_event_store(store: MQTTEventStore) -> None:
    """Set a custom MQTT event store (for testing)."""
    global _event_store
    _event_store = store
