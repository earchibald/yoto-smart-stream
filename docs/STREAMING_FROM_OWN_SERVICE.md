> **⚠️ DEPRECATED**: This documentation has been consolidated into the [yoto-smart-stream skill](../.github/skills/yoto-smart-stream/SKILL.md). Please refer to the skill for current information.
>
> **New location:** `.github/skills/yoto-smart-stream/reference/streaming_patterns.md`

---

# Streaming Audio from Your Own Service

This guide explains how to create Yoto MYO Cards that stream audio directly from your own server instead of uploading files to Yoto's servers.

## Overview

Instead of the traditional MYO card workflow where you upload audio files to Yoto's servers, you can configure cards to stream audio from your own service. This approach gives you complete control over:

- **Content Management**: Update audio content without recreating cards
- **Dynamic Content**: Serve different audio based on time, user, or other factors
- **Storage Control**: Keep audio files on your own infrastructure
- **Bandwidth**: Control and monitor your own bandwidth usage

## Key Difference: `url` vs `uploadId`

### Traditional Approach (Upload to Yoto)
```json
{
  "tracks": [{
    "key": "01",
    "title": "Introduction",
    "format": "aac",
    "channels": "mono",
    "uploadId": "abc123"  // Points to Yoto's servers
  }]
}
```

### Streaming Approach (Your Server)
```json
{
  "tracks": [{
    "key": "01",
    "title": "Introduction",
    "format": "mp3",
    "channels": "mono",
    "url": "https://your-server.com/audio/story.mp3"  // Points to YOUR server!
  }]
}
```

## Prerequisites

1. **Web Server**: A publicly accessible web server (or ngrok for testing)
2. **Audio Files**: Your audio content in MP3 or AAC format
3. **Yoto Account**: Active Yoto account with API credentials
4. **HTTPS**: Your streaming endpoint should use HTTPS (required by Yoto)

## Step-by-Step Guide

### Step 1: Set Up Your Audio Streaming Endpoint

Create an endpoint that serves audio files with proper headers:

```python
from fastapi import FastAPI
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI()

@app.get("/audio/{filename}")
async def stream_audio(filename: str):
    """Stream audio file with proper headers"""
    audio_path = Path("audio_files") / filename
    
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600"
        }
    )
```

**Important Headers:**
- `Accept-Ranges: bytes` - Enables seeking in audio
- `Content-Type: audio/mpeg` or `audio/aac` - Proper MIME type
- `Cache-Control` - Optional, for performance

### Step 2: Make Your Server Publicly Accessible

#### Option A: Production Server
Deploy your server to a cloud provider with a public URL:
- Heroku, Railway, Fly.io
- AWS, GCP, Azure
- Your own VPS with domain

#### Option B: Testing with ngrok
For local testing, use ngrok:

```bash
# Start your server
uvicorn your_server:app --port 8080

# In another terminal, expose it publicly
ngrok http 8000
```

You'll get a public URL like: `https://abc123.ngrok.io`

### Step 3: Authenticate with Yoto API

```python
from yoto_api import YotoManager

# Initialize and authenticate
ym = YotoManager(client_id="YOUR_CLIENT_ID")
ym.set_refresh_token("YOUR_REFRESH_TOKEN")
ym.check_and_refresh_token()

access_token = ym.token.access_token
```

### Step 4: Create Card with Streaming URL

```python
import requests

def create_streaming_card(
    access_token: str,
    title: str,
    audio_url: str,
    cover_image_id: str = None
):
    """Create a MYO card that streams from your server"""
    
    card_data = {
        "title": title,
        "description": "Streaming from my own service",
        "author": "Your Name",
        "metadata": {},
        "content": {
            "chapters": [{
                "key": "01",
                "title": "Chapter 1",
                "tracks": [{
                    "key": "01",
                    "title": title,
                    "format": "mp3",  # or "aac"
                    "channels": "mono",
                    "url": audio_url  # YOUR streaming URL!
                }]
            }]
        }
    }
    
    # Add cover image if provided
    if cover_image_id:
        card_data["metadata"]["cover"] = {"imageId": cover_image_id}
    
    # Create the card
    response = requests.post(
        "https://api.yotoplay.com/card",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json=card_data
    )
    
    response.raise_for_status()
    return response.json()

# Usage
card = create_streaming_card(
    access_token=access_token,
    title="My Streaming Story",
    audio_url="https://your-server.com/audio/story.mp3"
)

print(f"Card created! ID: {card['cardId']}")
```

### Step 5: Update Card Content Dynamically

The beauty of streaming from your own service is that you can change the audio without recreating the card:

```python
@app.get("/audio/dynamic-story.mp3")
async def dynamic_story():
    """Serve different content based on time of day"""
    from datetime import datetime
    
    hour = datetime.now().hour
    
    if 6 <= hour < 12:
        audio_file = "morning-story.mp3"
    elif 12 <= hour < 18:
        audio_file = "afternoon-story.mp3"
    else:
        audio_file = "bedtime-story.mp3"
    
    return FileResponse(
        Path("audio_files") / audio_file,
        media_type="audio/mpeg"
    )
```

## Complete Example

Here's a complete working example:

```python
#!/usr/bin/env python3
"""
Complete example: Create a Yoto MYO card that streams from your own service
"""

import requests
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from yoto_api import YotoManager

# === PART 1: Audio Streaming Server ===

app = FastAPI()

@app.get("/audio/{filename}")
async def stream_audio(filename: str):
    """Stream audio files"""
    audio_path = Path("audio_files") / filename
    
    if not audio_path.exists():
        raise HTTPException(status_code=404)
    
    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes"}
    )

# === PART 2: Create Streaming MYO Card ===

def create_streaming_myo_card():
    """Create a card that streams from our server"""
    
    # 1. Authenticate with Yoto
    ym = YotoManager(client_id="YOUR_CLIENT_ID")
    ym.set_refresh_token("YOUR_REFRESH_TOKEN")
    ym.check_and_refresh_token()
    
    # 2. Define your streaming URL
    # Replace with your actual server URL
    streaming_url = "https://your-server.com/audio/story.mp3"
    
    # 3. Create the card
    card_data = {
        "title": "My Streaming Story",
        "description": "Streams from my own service",
        "author": "Me",
        "content": {
            "chapters": [{
                "key": "01",
                "title": "Chapter 1",
                "tracks": [{
                    "key": "01",
                    "title": "My Story",
                    "format": "mp3",
                    "channels": "mono",
                    "url": streaming_url  # Stream from YOUR server!
                }]
            }]
        }
    }
    
    # 4. Send to Yoto API
    response = requests.post(
        "https://api.yotoplay.com/card",
        headers={
            "Authorization": f"Bearer {ym.token.access_token}",
            "Content-Type": "application/json"
        },
        json=card_data
    )
    
    response.raise_for_status()
    card = response.json()
    
    print(f"✓ Card created: {card['cardId']}")
    print(f"✓ Streams from: {streaming_url}")
    
    return card

if __name__ == "__main__":
    import uvicorn
    
    # Start the streaming server
    # Run create_streaming_myo_card() separately after server is running
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Audio Format Requirements

Your streaming endpoint should serve audio in formats supported by Yoto:

- **MP3**: Most compatible, recommended
  - Mono or stereo
  - 128-192 kbps recommended
  - Sample rate: 44.1 kHz or 48 kHz

- **AAC**: Also supported
  - Same recommendations as MP3

## Important Considerations

### 1. Server Reliability
- Your server must be available whenever the card is played
- Implement proper error handling and logging
- Consider using a CDN for better performance

### 2. HTTPS Required
- Yoto players require HTTPS for streaming URLs
- Use Let's Encrypt for free SSL certificates
- ngrok provides HTTPS automatically for testing

### 3. Bandwidth
- Monitor bandwidth usage, especially with multiple players
- Consider file size optimization (lower bitrate, mono audio)
- Implement caching headers to reduce repeated downloads

### 4. Range Requests
- Support HTTP range requests for seeking
- Most frameworks handle this automatically (FastAPI, Flask, etc.)

### 5. CORS Headers (Optional)
Only needed if you're accessing the audio from a web player:

```python
headers={
    "Access-Control-Allow-Origin": "*",
    "Accept-Ranges": "bytes"
}
```

## Troubleshooting

### Card Won't Play
1. **Check URL is accessible**: Test in browser or with curl
2. **Verify HTTPS**: Yoto requires secure connections
3. **Check audio format**: Ensure MP3 or AAC format
4. **Inspect headers**: Must include `Content-Type: audio/mpeg`

### Audio Doesn't Seek Properly
- Add `Accept-Ranges: bytes` header
- Ensure your server supports HTTP range requests

### Server Not Accessible
- Verify firewall settings
- Check if port is open
- For local testing, use ngrok

### Card Creates But Shows Error
- Check Yoto API response for error details
- Verify authentication token is valid
- Ensure URL is publicly accessible

## Advanced: Dynamic Content

### Example: Time-Based Stories

```python
@app.get("/audio/time-based.mp3")
async def time_based_audio():
    hour = datetime.now().hour
    audio_file = "morning.mp3" if 6 <= hour < 18 else "evening.mp3"
    return FileResponse(Path("audio") / audio_file, media_type="audio/mpeg")
```

### Example: User-Specific Content

```python
@app.get("/audio/{user_id}/story.mp3")
async def user_story(user_id: str):
    # Serve personalized content per user/player
    audio_file = f"user_{user_id}_story.mp3"
    return FileResponse(Path("audio") / audio_file, media_type="audio/mpeg")
```

### Example: Interactive Stories

For Choose Your Own Adventure style stories, see [ARCHITECTURE.md](ARCHITECTURE.md) for details on using MQTT button events to dynamically serve different audio tracks.

## Benefits of Streaming from Your Service

✅ **No Upload Limits**: No file size restrictions from Yoto  
✅ **Dynamic Content**: Change audio without recreating cards  
✅ **Control**: Full control over content and access  
✅ **Flexibility**: Serve different content based on context  
✅ **Cost**: No storage costs on Yoto's servers  
✅ **Privacy**: Audio stays on your infrastructure  

## Comparison: Upload vs Stream

| Feature | Upload to Yoto | Stream from Own Service |
|---------|---------------|------------------------|
| Setup Complexity | Simple | Moderate |
| Requires Server | No | Yes |
| Dynamic Content | No | Yes |
| File Size Limits | Yes | No |
| Bandwidth Cost | Yoto pays | You pay |
| Offline Play | Better | Depends on connection |
| Content Control | Limited | Complete |

## Next Steps

1. Set up your streaming server (see `examples/basic_server.py`)
2. Deploy to production or use ngrok for testing
3. Create your first streaming MYO card
4. Test playback on your Yoto device
5. Implement dynamic content features

## Related Documentation

- [Creating MYO Cards](CREATING_MYO_CARDS.md) - Traditional upload approach
- [Architecture Guide](ARCHITECTURE.md) - System design and interactive cards
- [Yoto API Reference](YOTO_API_REFERENCE.md) - Complete API documentation
- [Quick Start Guide](QUICK_START.md) - Getting started with the project

## Support

If you encounter issues:
1. Check the [troubleshooting section](#troubleshooting)
2. Review server logs for errors
3. Test URL accessibility with curl
4. Open an issue on [GitHub](https://github.com/earchibald/yoto-smart-stream/issues)

---

*Last updated: January 2026*
