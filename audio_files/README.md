# Audio Files Directory

This directory contains audio files that will be streamed to Yoto devices.

## Getting Started

You can generate sample MP3 files (1.mp3 through 10.mp3) for testing using the provided script. These are minimal MP3 files suitable for testing the streaming infrastructure.

### Generate Sample Files

To create the sample audio files, run:

```bash
python examples/generate_sample_audio.py
```

This will create files 1.mp3 through 10.mp3 in this directory, where each file contains someone saying that number five times (e.g., "one. one. one. one. one.").

**Requirements:** The script requires `gtts` and `pydub` packages. Install with:
```bash
pip install gtts pydub
```

## Adding Your Own Audio

Replace the sample files with your own audio content:

1. **Supported Formats:** MP3 (recommended), AAC
2. **Recommended Settings:**
   - Format: MP3
   - Channels: Mono
   - Bitrate: 128-192 kbps
   - Sample Rate: 44.1 kHz

## File Organization

- `1.mp3` through `10.mp3` - Sample test files
- Add your own files with descriptive names (e.g., `bedtime-story.mp3`)

## Using These Files

### 1. Stream Static Audio

Access files via the streaming endpoint:
```
http://localhost:8080/audio/1.mp3
```

### 2. Create MYO Cards

Use the API to create cards that stream from these files:

```bash
curl -X POST http://localhost:8080/api/cards/create-streaming \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Story",
    "audio_filename": "1.mp3",
    "description": "A test story"
  }'
```

### 3. List Available Files

```bash
curl http://localhost:8080/audio/list
```

## Dynamic Content

For time-based dynamic content, create special files:
- `morning-story.mp3` - Played 6 AM - 12 PM
- `afternoon-story.mp3` - Played 12 PM - 6 PM
- `bedtime-story.mp3` - Played 6 PM - 6 AM

These will automatically be served by the `/audio/dynamic/{card_id}.mp3` endpoint.

## Custom Audio Generation

You can also use `examples/generate_sample_audio.py` to generate custom spoken audio files. The script uses Google Text-to-Speech (gTTS) and requires an internet connection.

## Note

These files are not committed to git (excluded by .gitignore). Each deployment needs its own audio files.
