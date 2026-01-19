> **⚠️ DEPRECATED**: This documentation has been consolidated into the [yoto-smart-stream skill](../.github/skills/yoto-smart-stream/SKILL.md). Please refer to the skill for current information.
>
> **New location:** `.github/skills/yoto-smart-stream/reference/dynamic_streaming.md`

---

# Dynamic Audio Streaming

This guide explains how to use the dynamic audio streaming feature to create server-controlled playlists that stream multiple audio files sequentially to clients.

## Overview

The dynamic audio streaming feature allows you to:
- Create named stream queues with multiple audio files
- Add, remove, and reorder files in the queue
- Stream all files in sequence as a continuous MP3 to clients
- Manage multiple independent queues simultaneously
- Control queues via REST API or scripts

To the client (Yoto player), the stream appears as a single continuous MP3 file, but the server actually streams multiple files in sequence.

## Key Concepts

### Stream Queue
A named collection of audio files that will be played sequentially. Each queue is independent and can have different files.

### Sequential Streaming
When a client connects to a stream endpoint, they receive all files in the queue played one after another as a continuous audio stream.

### Queue Snapshot
Each connecting client gets a snapshot of the queue at connection time, so changes to the queue don't affect already-connected clients.

## API Endpoints

### List All Queues
```bash
GET /api/streams/queues
```

Returns a list of all stream queues.

**Response:**
```json
{
  "queues": ["my-playlist", "bedtime-stories"],
  "count": 2
}
```

### Get Queue Information
```bash
GET /api/streams/{stream_name}/queue
```

Get details about a specific queue.

**Response:**
```json
{
  "name": "my-playlist",
  "files": ["1.mp3", "2.mp3", "3.mp3"],
  "loop": false,
  "file_count": 3
}
```

### Add Files to Queue
```bash
POST /api/streams/{stream_name}/queue
Content-Type: application/json

{
  "files": ["1.mp3", "2.mp3", "3.mp3"]
}
```

Adds files to the end of the queue. Files must exist in the `audio_files` directory.

**Response:**
```json
{
  "success": true,
  "message": "Added 3 file(s) to stream 'my-playlist'",
  "queue": {
    "name": "my-playlist",
    "files": ["1.mp3", "2.mp3", "3.mp3"],
    "file_count": 3
  }
}
```

### Remove File from Queue
```bash
DELETE /api/streams/{stream_name}/queue/{file_index}
```

Remove a file at the specified index (0-based).

**Example:**
```bash
# Remove the second file (index 1)
DELETE /api/streams/my-playlist/queue/1
```

**Response:**
```json
{
  "success": true,
  "message": "Removed '2.mp3' from stream 'my-playlist'",
  "queue": {
    "name": "my-playlist",
    "files": ["1.mp3", "3.mp3"],
    "file_count": 2
  }
}
```

### Clear Queue
```bash
DELETE /api/streams/{stream_name}/queue
```

Remove all files from the queue.

**Response:**
```json
{
  "success": true,
  "message": "Cleared all files from stream 'my-playlist'",
  "queue": {
    "name": "my-playlist",
    "files": [],
    "file_count": 0
  }
}
```

### Reorder Queue
```bash
PUT /api/streams/{stream_name}/queue/reorder
Content-Type: application/json

{
  "old_index": 0,
  "new_index": 2
}
```

Move a file from one position to another.

**Response:**
```json
{
  "success": true,
  "message": "Reordered queue 'my-playlist'",
  "queue": {
    "name": "my-playlist",
    "files": ["2.mp3", "3.mp3", "1.mp3"],
    "file_count": 3
  }
}
```

### Delete Queue
```bash
DELETE /api/streams/{stream_name}
```

Delete a queue entirely.

**Response:**
```json
{
  "success": true,
  "message": "Deleted stream queue 'my-playlist'"
}
```

### Stream Audio
```bash
GET /api/streams/{stream_name}/stream.mp3
```

Stream all files in the queue sequentially as a continuous MP3.

**Response Headers:**
```
Content-Type: audio/mpeg
X-Stream-Name: my-playlist
X-File-Count: 3
Cache-Control: no-cache, no-store, must-revalidate
Accept-Ranges: none
```

**Response Body:** Continuous audio stream

## Usage Examples

### Example 1: Create a Simple Playlist

```bash
# 1. Add files to create a playlist
curl -X POST http://localhost:8080/api/streams/morning-playlist/queue \
  -H "Content-Type: application/json" \
  -d '{"files": ["morning-story.mp3", "wake-up-song.mp3", "breakfast-music.mp3"]}'

# 2. Stream the playlist
curl http://localhost:8080/api/streams/morning-playlist/stream.mp3 -o morning-stream.mp3

# Or point your Yoto card to:
# https://your-server.com/api/streams/morning-playlist/stream.mp3
```

### Example 2: Create a Bedtime Story Sequence

```bash
# Create a bedtime sequence
curl -X POST http://localhost:8080/api/streams/bedtime/queue \
  -H "Content-Type: application/json" \
  -d '{"files": ["intro.mp3", "story-chapter-1.mp3", "story-chapter-2.mp3", "goodnight.mp3"]}'

# View the queue
curl http://localhost:8080/api/streams/bedtime/queue

# Stream to Yoto player at:
# https://your-server.com/api/streams/bedtime/stream.mp3
```

### Example 3: Dynamic Queue Management

```bash
# Start with a base playlist
curl -X POST http://localhost:8080/api/streams/kids-radio/queue \
  -H "Content-Type: application/json" \
  -d '{"files": ["song1.mp3", "song2.mp3", "song3.mp3"]}'

# Add more songs later
curl -X POST http://localhost:8080/api/streams/kids-radio/queue \
  -H "Content-Type: application/json" \
  -d '{"files": ["song4.mp3", "song5.mp3"]}'

# Remove the second song (index 1)
curl -X DELETE http://localhost:8080/api/streams/kids-radio/queue/1

# Reorder: Move first song to the end
curl -X PUT http://localhost:8080/api/streams/kids-radio/queue/reorder \
  -H "Content-Type: application/json" \
  -d '{"old_index": 0, "new_index": 3}'

# Check the current queue
curl http://localhost:8080/api/streams/kids-radio/queue
```

### Example 4: Using with Yoto MYO Cards

Create a MYO card that points to your dynamic stream:

```python
import requests

# Your Yoto API token
token = "your_yoto_access_token"

# Create a card pointing to your stream
card_data = {
    "title": "Dynamic Playlist",
    "description": "Server-controlled playlist that updates automatically",
    "author": "Your Name",
    "content": {
        "chapters": [{
            "key": "01",
            "title": "Playlist",
            "tracks": [{
                "key": "01",
                "title": "Dynamic Stream",
                "format": "mp3",
                "channels": "mono",
                "url": "https://your-server.com/api/streams/kids-radio/stream.mp3"
            }]
        }]
    }
}

response = requests.post(
    "https://api.yotoplay.com/card",
    headers={"Authorization": f"Bearer {token}"},
    json=card_data
)

print(f"Card created: {response.json()['cardId']}")
```

Now you can update the playlist on the server, and the card will play the updated content next time it's inserted!

## Python Script Example

```python
import requests

BASE_URL = "http://localhost:8080/api"

class DynamicStreamManager:
    """Helper class for managing dynamic streams."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def create_stream(self, name: str, files: list[str]):
        """Create a new stream with files."""
        response = requests.post(
            f"{self.base_url}/streams/{name}/queue",
            json={"files": files}
        )
        return response.json()
    
    def add_files(self, name: str, files: list[str]):
        """Add files to an existing stream."""
        response = requests.post(
            f"{self.base_url}/streams/{name}/queue",
            json={"files": files}
        )
        return response.json()
    
    def get_queue(self, name: str):
        """Get queue information."""
        response = requests.get(f"{self.base_url}/streams/{name}/queue")
        return response.json()
    
    def remove_file(self, name: str, index: int):
        """Remove a file from the queue."""
        response = requests.delete(f"{self.base_url}/streams/{name}/queue/{index}")
        return response.json()
    
    def clear_queue(self, name: str):
        """Clear all files from the queue."""
        response = requests.delete(f"{self.base_url}/streams/{name}/queue")
        return response.json()
    
    def list_queues(self):
        """List all queues."""
        response = requests.get(f"{self.base_url}/streams/queues")
        return response.json()
    
    def get_stream_url(self, name: str):
        """Get the streaming URL for a queue."""
        return f"{self.base_url}/streams/{name}/stream.mp3"


# Usage
manager = DynamicStreamManager(BASE_URL)

# Create a morning playlist
manager.create_stream("morning-playlist", [
    "wake-up.mp3",
    "morning-news.mp3",
    "motivational-quote.mp3"
])

# Add more content
manager.add_files("morning-playlist", ["exercise-music.mp3"])

# Check the queue
queue = manager.get_queue("morning-playlist")
print(f"Queue has {queue['file_count']} files: {queue['files']}")

# Get the stream URL
stream_url = manager.get_stream_url("morning-playlist")
print(f"Stream at: {stream_url}")
```

## Advanced Usage

### Scheduled Queue Updates

You can create a script that updates queues based on time or events:

```python
import schedule
import time
from datetime import datetime

def update_daily_playlist():
    """Update the daily playlist with fresh content."""
    manager = DynamicStreamManager("http://localhost:8080/api")
    
    # Clear old content
    manager.clear_queue("daily-stream")
    
    # Add today's content based on the day
    day = datetime.now().strftime("%A")
    files = get_files_for_day(day)  # Your custom logic
    manager.add_files("daily-stream", files)
    
    print(f"Updated daily stream for {day}")

# Schedule updates
schedule.every().day.at("06:00").do(update_daily_playlist)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Event-Driven Queue Management

Respond to external events (e.g., MQTT messages, webhooks) to update queues:

```python
import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    """Handle MQTT messages to update playlists."""
    if msg.topic == "yoto/button_press":
        # User pressed a button, add requested content
        manager = DynamicStreamManager("http://localhost:8080/api")
        manager.add_files("interactive-stream", ["bonus-content.mp3"])

client = mqtt.Client()
client.on_message = on_message
client.connect("mqtt.example.com", 1883)
client.subscribe("yoto/#")
client.loop_forever()
```

## Best Practices

1. **File Validation**: Always ensure files exist before adding them to a queue
2. **Queue Names**: Use descriptive names like "morning-playlist" or "bedtime-stories"
3. **Concurrent Access**: The system handles concurrent operations safely with locks
4. **Client Snapshots**: Each client gets a snapshot of the queue when they connect
5. **Error Handling**: Check response status codes and handle errors appropriately
6. **Memory Management**: Queues are stored in memory, so restart will clear them

## Limitations

- Queues are stored in memory and will be lost on server restart
- Seeking within the stream is not supported (Accept-Ranges: none)
- File changes during streaming won't affect already-connected clients
- No built-in persistence (implement database storage if needed)

## Troubleshooting

### Files Not Found
Make sure audio files are in the `audio_files` directory:
```bash
ls -la audio_files/
```

### Empty Stream
Check that the queue has files:
```bash
curl http://localhost:8080/api/streams/my-playlist/queue
```

### Stream Not Playing
- Verify the stream URL is correct
- Check that files are valid MP3 format
- Ensure the server is accessible from the Yoto device

## Next Steps

- Implement queue persistence with a database
- Add support for loop mode
- Create a web UI for queue management
- Add webhook notifications for queue changes
- Implement scheduling and automation tools
