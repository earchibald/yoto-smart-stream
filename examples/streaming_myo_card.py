#!/usr/bin/env python3
"""
Example: Create a Yoto MYO card that streams from your own service

This example demonstrates how to:
1. Set up an audio streaming endpoint
2. Create a MYO card that points to YOUR streaming URL (not Yoto's servers)
3. Update content dynamically without recreating cards

Run the server with:
    python streaming_myo_card.py

Then in another terminal, create the card:
    python streaming_myo_card.py --create-card
"""

import argparse
import os
from datetime import datetime
from pathlib import Path

import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

try:
    from yoto_api import YotoManager
except ImportError:
    print("Error: yoto_api library not found.")
    print("Install with: pip install yoto_api")
    exit(1)


# === PART 1: Audio Streaming Server ===

app = FastAPI(
    title="Yoto Audio Streaming Service",
    description="Stream audio to Yoto devices from your own service",
    version="1.0.0",
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Yoto Audio Streaming",
        "status": "running",
        "endpoints": {
            "static": "/audio/{filename}",
            "dynamic": "/audio/dynamic-story.mp3",
            "time_based": "/audio/time-based.mp3",
        },
    }


@app.get("/audio/{filename}")
async def stream_static_audio(filename: str):
    """
    Stream a static audio file
    
    Example: /audio/my-story.mp3
    """
    # In production, use a proper audio_files directory
    audio_path = Path("audio_files") / filename

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"Audio file not found: {filename}")

    # Determine media type from file extension
    media_type = "audio/mpeg" if filename.endswith(".mp3") else "audio/aac"

    return FileResponse(
        audio_path,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",  # Enable seeking
            "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
        },
    )


@app.get("/audio/dynamic-story.mp3")
async def stream_dynamic_audio():
    """
    Stream different content based on time of day
    
    This demonstrates how you can serve different audio
    without recreating the Yoto card!
    """
    hour = datetime.now().hour

    # Serve different audio based on time of day
    if 6 <= hour < 12:
        audio_file = "morning-story.mp3"
        print(f"[{datetime.now()}] Serving morning story")
    elif 12 <= hour < 18:
        audio_file = "afternoon-story.mp3"
        print(f"[{datetime.now()}] Serving afternoon story")
    else:
        audio_file = "bedtime-story.mp3"
        print(f"[{datetime.now()}] Serving bedtime story")

    audio_path = Path("audio_files") / audio_file

    if not audio_path.exists():
        # Fallback to a default file if time-specific file doesn't exist
        print(f"Warning: {audio_file} not found, using default")
        audio_path = Path("audio_files") / "default-story.mp3"

    if not audio_path.exists():
        raise HTTPException(
            status_code=404, detail="No audio files found. Please add MP3 files to audio_files/"
        )

    return FileResponse(
        audio_path,
        media_type="audio/mpeg",
        headers={"Accept-Ranges": "bytes", "Cache-Control": "no-cache"},  # Don't cache dynamic content
    )


@app.get("/audio/time-based.mp3")
async def stream_time_based():
    """Another example of dynamic content based on time"""
    hour = datetime.now().hour

    # Morning greeting (6 AM - 12 PM)
    if 6 <= hour < 12:
        return await stream_static_audio("morning-greeting.mp3")
    # Afternoon content (12 PM - 6 PM)
    elif 12 <= hour < 18:
        return await stream_static_audio("afternoon-content.mp3")
    # Evening/night content (6 PM - 6 AM)
    else:
        return await stream_static_audio("evening-content.mp3")


# === PART 2: Create Streaming MYO Card ===


def create_streaming_myo_card(base_url: str, card_type: str = "static"):
    """
    Create a Yoto MYO card that streams from your server
    
    Args:
        base_url: Base URL of your streaming service (e.g., https://your-server.com)
        card_type: Type of card to create ("static" or "dynamic")
    """
    print("\n" + "=" * 80)
    print("Creating Yoto MYO Card with Streaming from Own Service")
    print("=" * 80 + "\n")

    # 1. Get credentials from environment
    client_id = os.getenv("YOTO_CLIENT_ID")
    if not client_id:
        print("Error: YOTO_CLIENT_ID environment variable not set")
        print("Get your Client ID from: https://yoto.dev/get-started/start-here/")
        return

    # 2. Authenticate with Yoto API
    print("Step 1: Authenticating with Yoto API...")
    ym = YotoManager(client_id=client_id)

    # Check for saved refresh token
    token_file = Path(".yoto_refresh_token")
    if not token_file.exists():
        print("\nNo saved refresh token found.")
        print("Please run the authentication flow first:")
        print("  python examples/simple_client.py")
        return

    refresh_token = token_file.read_text().strip()
    ym.set_refresh_token(refresh_token)

    try:
        ym.check_and_refresh_token()
        print("✓ Authentication successful")
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return

    # 3. Define streaming URL
    print("\nStep 2: Configuring streaming URL...")

    if card_type == "dynamic":
        streaming_url = f"{base_url}/audio/dynamic-story.mp3"
        title = "Dynamic Story (Changes by Time)"
        description = "This story changes based on the time of day!"
    else:
        # For static, use a specific file
        streaming_url = f"{base_url}/audio/my-story.mp3"
        title = "My Streaming Story"
        description = "Streams from my own service"

    print(f"  URL: {streaming_url}")

    # 4. Create the card
    print("\nStep 3: Creating MYO card...")

    card_data = {
        "title": title,
        "description": description,
        "author": "Yoto Smart Stream",
        "metadata": {
            # You can add a cover image here if you have one
            # "cover": {"imageId": "your_image_id"}
        },
        "content": {
            "chapters": [
                {
                    "key": "01",
                    "title": "Chapter 1",
                    "tracks": [
                        {
                            "key": "01",
                            "title": title,
                            "format": "mp3",
                            "channels": "mono",
                            "url": streaming_url,  # Stream from YOUR server!
                        }
                    ],
                }
            ]
        },
    }

    # Send to Yoto API
    try:
        response = requests.post(
            "https://api.yotoplay.com/card",
            headers={
                "Authorization": f"Bearer {ym.token.access_token}",
                "Content-Type": "application/json",
            },
            json=card_data,
        )

        response.raise_for_status()
        card = response.json()

        print("\n" + "=" * 80)
        print("✓ SUCCESS! Card created")
        print("=" * 80)
        print(f"  Card ID: {card['cardId']}")
        print(f"  Title: {title}")
        print(f"  Streams from: {streaming_url}")
        print("\nNow you can:")
        print("  1. Open the Yoto app on your phone")
        print("  2. Find the card in 'My Cards'")
        print("  3. Play it on your Yoto device")
        print("\nThe audio will stream from YOUR server, not Yoto's!")
        print("=" * 80 + "\n")

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ Failed to create card: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"\n✗ Error: {e}")


# === MAIN ===


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Yoto Audio Streaming Service and MYO Card Creator"
    )
    parser.add_argument(
        "--create-card", action="store_true", help="Create a streaming MYO card"
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of your streaming service (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--card-type",
        choices=["static", "dynamic"],
        default="static",
        help="Type of card to create (default: static)",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")

    args = parser.parse_args()

    if args.create_card:
        # Create a streaming MYO card
        create_streaming_myo_card(args.base_url, args.card_type)
    else:
        # Start the streaming server
        import uvicorn

        print("\n" + "=" * 80)
        print("Starting Yoto Audio Streaming Service")
        print("=" * 80)
        print(f"\nServer URL: http://{args.host}:{args.port}")
        print(f"API Docs: http://localhost:{args.port}/docs")
        print("\nSetup Instructions:")
        print("  1. Add MP3 files to the 'audio_files/' directory")
        print("  2. Make this server publicly accessible (use ngrok for testing)")
        print("  3. Run with --create-card to create a streaming MYO card")
        print("\nExample:")
        print(f"  python {__file__} --create-card --base-url https://your-server.com")
        print("=" * 80 + "\n")

        # Create audio_files directory if it doesn't exist
        Path("audio_files").mkdir(exist_ok=True)

        uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
