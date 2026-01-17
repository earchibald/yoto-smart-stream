# Quick Start: Streaming from Your Own Service

This guide will get you streaming audio to Yoto devices from your own server in just a few steps.

## What This Does

Instead of uploading audio files to Yoto's servers, your MYO cards will stream directly from YOUR server. This gives you complete control over the audio content.

## Prerequisites

- Yoto account and device
- Yoto API credentials (get from [yoto.dev](https://yoto.dev/get-started/start-here/))
- Python 3.9+ installed

## Step 1: Install Dependencies

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/earchibald/yoto-smart-stream.git
cd yoto-smart-stream

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Step 2: Authenticate with Yoto

```bash
# Set your client ID
export YOTO_CLIENT_ID=your_client_id_here

# Run authentication
python examples/simple_client.py
```

Follow the prompts to complete authentication. Your refresh token will be saved.

## Step 3: Add Audio Files

The repository includes 10 sample MP3 files (1.mp3 through 10.mp3) for testing:

```bash
ls audio_files/
# You should see: 1.mp3 2.mp3 3.mp3 ... 10.mp3
```

To add your own audio:
```bash
# Copy your MP3 files to the audio_files directory
cp /path/to/your/story.mp3 audio_files/
```

## Step 4: Start the Server

```bash
python examples/basic_server.py
```

You should see:
```
Starting Yoto Smart Stream API Server
...
API Documentation: http://localhost:8080/docs
```

## Step 5: Make Server Publicly Accessible

For local testing, use ngrok:

```bash
# In a new terminal
ngrok http 8000
```

You'll get a public URL like: `https://abc123.ngrok.io`

Set this as your PUBLIC_URL:
```bash
export PUBLIC_URL=https://abc123.ngrok.io
```

## Step 6: Create a Streaming MYO Card

### Option A: Using the API

```bash
curl -X POST http://localhost:8080/api/cards/create-streaming \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Streaming Card",
    "audio_filename": "1.mp3",
    "description": "Streams from my own server!"
  }'
```

### Option B: Using the Interactive API Docs

1. Open http://localhost:8080/docs
2. Find `POST /api/cards/create-streaming`
3. Click "Try it out"
4. Fill in:
   - title: "My Test Card"
   - audio_filename: "1.mp3"
   - description: "Testing streaming"
5. Click "Execute"

## Step 7: Play Your Card

1. Open the Yoto app on your phone
2. Go to "My Cards"
3. Find your newly created card
4. Play it on your Yoto device!

The audio will stream from YOUR server! 🎉

## Verify It's Working

Check the server logs - you should see:
```
INFO:     127.0.0.1:xxxxx - "GET /audio/1.mp3 HTTP/1.1" 200 OK
```

This means the Yoto device is streaming from your server!

## Next Steps

### Update Audio Without Recreating Cards

Simply replace the audio file:
```bash
cp /path/to/new/story.mp3 audio_files/1.mp3
```

The card will automatically play the new content!

### Create Dynamic Cards

Create a card that changes based on time of day:

```bash
# Add time-specific audio files
cp morning.mp3 audio_files/morning-story.mp3
cp afternoon.mp3 audio_files/afternoon-story.mp3
cp evening.mp3 audio_files/bedtime-story.mp3

# Create dynamic card
curl -X POST "http://localhost:8080/api/cards/create-dynamic?title=Time%20Based%20Story&card_id=dynamic001"
```

This card will play different audio based on the time of day!

### Monitor Streaming Activity

List available files:
```bash
curl http://localhost:8080/audio/list
```

Check server health:
```bash
curl http://localhost:8080/health
```

## Troubleshooting

### Card Won't Play

1. **Check URL is publicly accessible:**
   ```bash
   curl $PUBLIC_URL/audio/1.mp3
   ```
   Should return audio data.

2. **Verify HTTPS:** Yoto requires HTTPS. ngrok provides this automatically.

3. **Check server logs:** Look for errors in the terminal running the server.

### "PUBLIC_URL not set" Error

Make sure you set the environment variable:
```bash
export PUBLIC_URL=https://your-ngrok-url.ngrok.io
```

### Audio File Not Found

List available files:
```bash
curl http://localhost:8080/audio/list
```

Make sure the filename matches exactly (case-sensitive).

## Complete Example

Here's a complete workflow:

```bash
# 1. Set up environment
export YOTO_CLIENT_ID=your_client_id
export PUBLIC_URL=https://abc123.ngrok.io

# 2. Start server
python examples/basic_server.py &

# 3. Create card
curl -X POST http://localhost:8080/api/cards/create-streaming \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Counting Numbers",
    "audio_filename": "1.mp3",
    "description": "Learn to count"
  }'

# 4. Play on Yoto device via app
```

## Production Deployment

For production use:

1. **Deploy to a cloud provider** (Heroku, Railway, Fly.io, AWS, etc.)
2. **Get a domain name** and SSL certificate
3. **Set PUBLIC_URL** to your domain
4. **Use environment variables** for sensitive data
5. **Monitor** your server logs and bandwidth

See [STREAMING_FROM_OWN_SERVICE.md](STREAMING_FROM_OWN_SERVICE.md) for complete documentation.

## Key Endpoints

- `GET /` - Web UI dashboard
- `GET /api/status` - API information
- `GET /api/health` - Health check
- `GET /api/audio/list` - List audio files
- `GET /api/audio/{filename}` - Stream audio file
- `POST /api/cards/create-streaming` - Create streaming card
- `GET /docs` - Interactive API documentation

## Need Help?

- **Full Documentation:** [STREAMING_FROM_OWN_SERVICE.md](docs/STREAMING_FROM_OWN_SERVICE.md)
- **API Reference:** [YOTO_API_REFERENCE.md](YOTO_API_REFERENCE.md)
- **GitHub Issues:** [Report a problem](https://github.com/earchibald/yoto-smart-stream/issues)

---

**Congratulations!** You're now streaming audio to Yoto devices from your own server! 🎉