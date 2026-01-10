# Creating Yoto MYO (Make Your Own) Cards

This guide explains the complete procedure for creating custom Yoto MYO Cards using the Yoto API. MYO Cards allow you to create your own audio content that can be played on Yoto devices.

## Overview

A Yoto MYO Card is custom audio content that you create and upload to your Yoto account. Once created, you can play this content on any Yoto Player in your family by scanning a physical Yoto card or using the Yoto app.

## Prerequisites

Before you begin, ensure you have:

1. **Yoto Account**: An active Yoto account with at least one registered Yoto Player
2. **Yoto API Credentials**: A Client ID from [yoto.dev](https://yoto.dev/get-started/start-here/)
3. **Authentication Token**: Valid access token and refresh token (see [Authentication](#authentication))
4. **Audio Files**: Your audio content in a supported format (MP3, WAV, OGG, FLAC)
5. **Cover Image** (optional): An image file for your card's cover art

## Complete Procedure

### Step 1: Authenticate with Yoto API

First, authenticate to obtain access tokens:

```python
from yoto_api import YotoManager
import time

# Initialize with your Client ID
ym = YotoManager(client_id="YOUR_CLIENT_ID")

# Start device code flow
device_info = ym.device_code_flow_start()
print(f"Visit: {device_info['verification_uri']}")
print(f"Enter code: {device_info['user_code']}")

# Wait for user authorization
time.sleep(15)

# Complete authentication
ym.device_code_flow_complete()

# Save refresh token for future use
refresh_token = ym.token.refresh_token
# Store this securely!
```

For subsequent runs:

```python
# Use saved refresh token
ym = YotoManager(client_id="YOUR_CLIENT_ID")
ym.set_refresh_token(refresh_token)
ym.check_and_refresh_token()
```

### Step 2: Prepare Your Audio Files

Ensure your audio files meet Yoto's requirements:

- **Supported formats**: MP3, AAC, WAV, OGG, FLAC
- **Recommended format**: MP3, mono channel, 128-192 kbps
- **File naming**: Use descriptive names (e.g., `chapter_01_intro.mp3`)

Calculate the SHA-256 hash of your audio file:

```python
import hashlib

def calculate_sha256(file_path):
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Calculate hash for your audio file
audio_hash = calculate_sha256("path/to/your/audio.mp3")
print(f"SHA-256: {audio_hash}")
```

### Step 3: Get Audio Upload URL

Request a signed upload URL from the Yoto API:

```http
POST https://api.yotoplay.com/media/audio/upload-url
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "sha256": "your_file_sha256_hash",
  "filename": "your_audio_file.mp3"
}
```

**Response:**

```json
{
  "uploadId": "unique_upload_id",
  "uploadUrl": "https://signed-s3-url-for-upload",
  "exists": false
}
```

**Note**: If `exists: true`, the file is already uploaded and you can skip Step 4.

### Step 4: Upload Audio File

Upload your audio file to the signed URL:

```python
import requests

def upload_audio_file(upload_url, file_path):
    """Upload audio file to signed S3 URL"""
    with open(file_path, 'rb') as f:
        response = requests.put(
            upload_url,
            data=f,
            headers={'Content-Type': 'audio/mpeg'}
        )
    return response.status_code == 200

# Upload the file
success = upload_audio_file(upload_url, "path/to/your/audio.mp3")
print(f"Upload successful: {success}")
```

### Step 5: Upload Cover Image (Optional)

Upload a cover image for your card:

```http
POST https://api.yotoplay.com/media/cover-image
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: multipart/form-data

image: [binary data]
coverType: default
autoConvert: true
```

**Response:**

```json
{
  "imageId": "unique_image_id",
  "imageUrl": "https://url-to-uploaded-image"
}
```

Python example:

```python
def upload_cover_image(access_token, image_path):
    """Upload cover image for card"""
    url = "https://api.yotoplay.com/media/cover-image"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    with open(image_path, 'rb') as f:
        files = {'image': f}
        data = {
            'coverType': 'default',
            'autoConvert': 'true'
        }
        response = requests.post(url, headers=headers, files=files, data=data)
    
    return response.json()

# Upload image
image_response = upload_cover_image(access_token, "path/to/cover.jpg")
image_id = image_response['imageId']
```

### Step 6: Create the MYO Card

Create the card with your uploaded content:

```http
POST https://api.yotoplay.com/card
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "title": "My Custom Story",
  "description": "A wonderful bedtime story",
  "author": "Your Name",
  "metadata": {
    "cover": {
      "imageId": "your_image_id"
    }
  },
  "content": {
    "chapters": [
      {
        "key": "01",
        "title": "Chapter 1",
        "display": {
          "icon16x16": "icon_id_optional"
        },
        "tracks": [
          {
            "key": "01",
            "title": "Introduction",
            "format": "aac",
            "channels": "mono",
            "uploadId": "your_upload_id_from_step3"
          }
        ]
      }
    ]
  }
}
```

**Response:**

```json
{
  "cardId": "generated_card_id",
  "card": {
    "cardId": "generated_card_id",
    "title": "My Custom Story",
    "metadata": { ... },
    "content": { ... }
  }
}
```

### Step 7: Verify Card Creation

Retrieve your newly created card to verify:

```http
GET https://api.yotoplay.com/card/{cardId}
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Or get all your MYO cards:

```http
GET https://api.yotoplay.com/card/mine
Authorization: Bearer YOUR_ACCESS_TOKEN
```

### Step 8: Play the Card on Your Device

#### Option A: Via MQTT Commands

```python
# Connect to MQTT
ym.connect_to_events()

# Play the card on a specific device
device_id = "your_device_id"
card_id = "your_new_card_id"

# Send play command
ym.play_card(device_id, card_id, chapter_key="01", track_key="01")
```

#### Option B: Via REST API

```http
POST https://api.yotoplay.com/device-v2/{deviceId}/command
Authorization: Bearer YOUR_ACCESS_TOKEN
Content-Type: application/json

{
  "card": {
    "cardId": "your_card_id",
    "chapterKey": "01",
    "trackKey": "01"
  }
}
```

## Complete Python Example

Here's a complete example that creates a MYO card:

```python
from yoto_api import YotoManager
import hashlib
import requests
import time

def create_myo_card(
    client_id,
    refresh_token,
    audio_file_path,
    cover_image_path,
    title,
    description,
    author
):
    """Complete workflow to create a Yoto MYO card"""
    
    # Step 1: Authenticate
    ym = YotoManager(client_id=client_id)
    ym.set_refresh_token(refresh_token)
    ym.check_and_refresh_token()
    access_token = ym.token.access_token
    
    # Step 2: Calculate SHA-256 hash
    sha256_hash = hashlib.sha256()
    with open(audio_file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    file_hash = sha256_hash.hexdigest()
    
    # Step 3: Get upload URL
    upload_response = requests.post(
        "https://api.yotoplay.com/media/audio/upload-url",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={
            "sha256": file_hash,
            "filename": audio_file_path.split('/')[-1]
        }
    )
    upload_data = upload_response.json()
    upload_id = upload_data['uploadId']
    
    # Step 4: Upload audio if needed
    if not upload_data.get('exists', False):
        with open(audio_file_path, 'rb') as f:
            requests.put(
                upload_data['uploadUrl'],
                data=f,
                headers={'Content-Type': 'audio/mpeg'}
            )
    
    # Step 5: Upload cover image
    with open(cover_image_path, 'rb') as f:
        image_response = requests.post(
            "https://api.yotoplay.com/media/cover-image",
            headers={"Authorization": f"Bearer {access_token}"},
            files={'image': f},
            data={'coverType': 'default', 'autoConvert': 'true'}
        )
    image_id = image_response.json()['imageId']
    
    # Step 6: Create the card
    card_response = requests.post(
        "https://api.yotoplay.com/card",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        },
        json={
            "title": title,
            "description": description,
            "author": author,
            "metadata": {
                "cover": {"imageId": image_id}
            },
            "content": {
                "chapters": [{
                    "key": "01",
                    "title": "Chapter 1",
                    "tracks": [{
                        "key": "01",
                        "title": title,
                        "format": "aac",
                        "channels": "mono",
                        "uploadId": upload_id
                    }]
                }]
            }
        }
    )
    
    card_data = card_response.json()
    return card_data['cardId']

# Usage
card_id = create_myo_card(
    client_id="YOUR_CLIENT_ID",
    refresh_token="YOUR_REFRESH_TOKEN",
    audio_file_path="./my_story.mp3",
    cover_image_path="./cover.jpg",
    title="My Bedtime Story",
    description="A soothing story for bedtime",
    author="Parent"
)

print(f"Card created successfully! Card ID: {card_id}")
```

## Multi-Chapter Cards

For cards with multiple chapters or tracks:

```json
{
  "title": "Complete Story Collection",
  "content": {
    "chapters": [
      {
        "key": "01",
        "title": "Chapter 1: The Beginning",
        "tracks": [
          {
            "key": "01",
            "title": "Part 1",
            "uploadId": "upload_id_1"
          }
        ]
      },
      {
        "key": "02",
        "title": "Chapter 2: The Journey",
        "tracks": [
          {
            "key": "01",
            "title": "Part 2",
            "uploadId": "upload_id_2"
          }
        ]
      },
      {
        "key": "03",
        "title": "Chapter 3: The End",
        "tracks": [
          {
            "key": "01",
            "title": "Part 3",
            "uploadId": "upload_id_3"
          }
        ]
      }
    ]
  }
}
```

## Common Issues and Troubleshooting

### Issue: Upload URL Request Fails

**Symptom**: 401 Unauthorized error

**Solution**: 
- Check that your access token is valid
- Refresh your token using `ym.check_and_refresh_token()`
- Ensure your Client ID is correct

### Issue: File Upload Fails

**Symptom**: Upload to signed URL returns error

**Solution**:
- Verify the SHA-256 hash is calculated correctly
- Ensure file size is reasonable (< 500MB recommended)
- Check that the file is not corrupted

### Issue: Card Not Appearing

**Symptom**: Card created but not visible in library

**Solution**:
- Wait a few minutes for processing
- Check the card using `GET /card/{cardId}`
- Verify the card is in your MYO library: `GET /card/mine`

### Issue: Card Won't Play

**Symptom**: Card created but won't play on device

**Solution**:
- Verify audio format is supported
- Check that uploadId references a successful upload
- Ensure device is online and connected
- Try playing via MQTT instead of physical card

## Best Practices

1. **Audio Quality**: Use MP3 format, mono channel, 128-192 kbps for best compatibility
2. **File Naming**: Use descriptive, sequential names for easy organization
3. **Cover Images**: Use square images (minimum 300x300px) for best display
4. **Testing**: Always test playback before sharing with others
5. **Token Storage**: Store refresh tokens securely (e.g., in environment variables or secure storage)
6. **Error Handling**: Implement proper error handling and retries for network operations
7. **Rate Limiting**: Be respectful of API rate limits
8. **Metadata**: Include complete metadata (title, author, description) for better organization

## Advanced Topics

### Interactive Cards (Choose Your Own Adventure)

For interactive stories that respond to button presses, see [ARCHITECTURE.md](ARCHITECTURE.md) for the complete interactive card implementation guide.

### Audio Conversion

For automatic audio conversion to Yoto-compatible formats:

```python
from pydub import AudioSegment

def convert_to_yoto_format(input_file, output_file):
    """Convert audio to Yoto-optimized format"""
    audio = AudioSegment.from_file(input_file)
    
    # Convert to mono
    audio = audio.set_channels(1)
    
    # Set sample rate to 44.1kHz
    audio = audio.set_frame_rate(44100)
    
    # Export as MP3 at 192kbps
    audio.export(
        output_file,
        format="mp3",
        bitrate="192k",
        parameters=["-ac", "1"]
    )
    
    return output_file
```

### Batch Upload

For uploading multiple cards at once, see the examples in the repository.

## API Reference

For complete API documentation, see:
- [Yoto API Reference](YOTO_API_REFERENCE.md)
- [Official Yoto API Documentation](https://yoto.dev/api/)

## Related Guides

- [Getting Started Guide](GETTING_STARTED.md)
- [Architecture Guide](ARCHITECTURE.md)
- [MQTT Reference](yoto-mqtt-reference.md)

## Support

If you encounter issues:
1. Check the [troubleshooting section](#common-issues-and-troubleshooting)
2. Review the [Yoto Developer Portal](https://yoto.dev/)
3. Open an issue on the [GitHub repository](https://github.com/earchibald/yoto-smart-stream/issues)

---

*Last updated: January 2026*
