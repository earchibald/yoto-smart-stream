#!/usr/bin/env python3
"""
Test card creation and deletion utility for yoto-smart-stream service.

This script:
- Authenticates to the yoto-smart-stream server
- Creates a simple 1-chapter, 1-track streaming card
- Validates the card was created successfully
- Summarizes card information
- Optionally cleans up (deletes) the created card

Usage:
    python scripts/test_card_creation.py
    python scripts/test_card_creation.py --no-delete
    python scripts/test_card_creation.py --base-url https://example.com
"""

import argparse
import os
import sys
import time
from typing import Optional

import requests

# Default values from environment or hardcoded
DEFAULT_BASE_URL = os.getenv("SERVER_API_BASE_URL", "http://localhost:8000")
DEFAULT_USERNAME = os.getenv("YOTO_API_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("YOTO_API_PASSWORD", "yoto")
DEFAULT_MATCH = "Test Card Creation"

# Sample MP3 URL for testing
SAMPLE_MP3_URL = "https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3"


def normalize_base_url(raw_base_url: Optional[str]) -> str:
    """Ensure we have a usable API base URL."""
    if not raw_base_url:
        print("ERROR: Base URL is required. Set SERVER_API_BASE_URL or use --base-url")
        sys.exit(1)
    return raw_base_url.rstrip("/")


def authenticate(session: requests.Session, base_url: str, username: str, password: str) -> None:
    """Authenticate against the server and persist the session cookie."""
    try:
        response = session.post(
            f"{base_url}/user/login",
            json={"username": username, "password": password},
            timeout=15,
        )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("success"):
            raise RuntimeError(f"Login failed: {payload.get('message', 'unknown error')}")
        print(f"✅ Authenticated as {username}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Authentication request failed: {e}") from e


def create_streaming_card(
    session: requests.Session,
    base_url: str,
    title: str,
    audio_url: str,
    description: str = "",
) -> dict:
    """
    Create a streaming card via the server API.

    Args:
        session: Authenticated requests session
        base_url: API base URL
        title: Card title
        audio_url: URL of the audio file to stream
        description: Card description

    Returns:
        Dictionary with card creation response
    """
    card_payload = {
        "title": title,
        "description": description,
        "author": "Test Script",
        "audio_url": audio_url,
    }

    print(f"\n📝 Creating card: '{title}'")
    print(f"   Audio URL: {audio_url}")

    try:
        response = session.post(
            f"{base_url}/api/cards/create-streaming-url",
            json=card_payload,
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()

        if result.get("success"):
            print("✅ Card created successfully!")
            print(f"   Card ID: {result.get('card_id')}")
            print(f"   Content ID: {result.get('content_id')}")
            return result
        else:
            raise RuntimeError(f"Card creation failed: {result.get('message', 'unknown error')}")

    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Card creation request failed: {e}") from e


def get_library(session: requests.Session, base_url: str) -> dict:
    """Fetch the library from the server."""
    try:
        response = session.get(f"{base_url}/api/library?fresh=1", timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to fetch library: {e}") from e


def validate_card_in_library(
    session: requests.Session,
    base_url: str,
    card_id: str,
    title: str,
) -> bool:
    """
    Validate that the created card appears in the library.

    Args:
        session: Authenticated requests session
        base_url: API base URL
        card_id: Expected card ID
        title: Expected card title

    Returns:
        True if card found in library, False otherwise
    """
    print("\n🔍 Validating card in library...")

    try:
        library = get_library(session, base_url)

        # Check in cards list
        cards = library.get("cards", [])
        for card in cards:
            if card.get("cardId") == card_id or card.get("id") == card_id:
                print("✅ Card found in library!")
                print(f"   Title: {card.get('title')}")
                print(f"   ID: {card.get('id')}")
                print(f"   Content ID: {card.get('contentId')}")
                return True

        # Check in playlists list
        playlists = library.get("playlists", [])
        for playlist in playlists:
            playlist_title = playlist.get("name") or playlist.get("title")
            if title.lower() in playlist_title.lower():
                print("✅ Card found in playlists!")
                print(f"   Title: {playlist_title}")
                print(f"   ID: {playlist.get('id')}")
                print(f"   Content ID: {playlist.get('contentId')}")
                return True

        print("⚠️  Card not found in library (may take a moment to sync)")
        return False

    except Exception as e:
        print(f"⚠️  Could not validate card in library: {e}")
        return False


def delete_card(
    session: requests.Session,
    base_url: str,
    content_id: str,
) -> bool:
    """
    Delete a card by content ID.

    Args:
        session: Authenticated requests session
        base_url: API base URL
        content_id: Content ID to delete

    Returns:
        True if deletion successful, False otherwise
    """
    try:
        response = session.delete(
            f"{base_url}/api/library/{content_id}",
            timeout=30,
        )

        if response.status_code in (200, 204):
            print("✅ Card deleted successfully")
            return True
        elif response.status_code == 404:
            print("⚠️  Card not found (may have been already deleted)")
            return False
        else:
            print(f"❌ Failed to delete card: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to delete card: {e}")
        return False


def summarize_results(
    card_data: dict,
    validation_success: bool,
    deleted: bool,
) -> None:
    """Print a summary of the test results."""
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Card Title:      {card_data.get('title', 'N/A')}")
    print(f"Card ID:         {card_data.get('card_id', 'N/A')}")
    print(f"Content ID:      {card_data.get('content_id', 'N/A')}")
    print(f"Streaming URL:   {card_data.get('streaming_url', 'N/A')}")
    print(f"Creation:        {'✅ Success' if card_data.get('success') else '❌ Failed'}")
    print(f"Validation:      {'✅ Found in library' if validation_success else '⚠️  Not found'}")
    print(f"Cleanup:         {'✅ Deleted' if deleted else '⏭️  Skipped (--no-delete)'}")
    print("=" * 60)


def main() -> int:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Test card creation and deletion for yoto-smart-stream service"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Server base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--username",
        default=DEFAULT_USERNAME,
        help=f"Server username (default: {DEFAULT_USERNAME})",
    )
    parser.add_argument(
        "--password",
        default=DEFAULT_PASSWORD,
        help=f"Server password (default: {DEFAULT_PASSWORD})",
    )
    parser.add_argument(
        "--no-delete",
        action="store_true",
        help="Skip cleanup (don't delete the created card)",
    )
    parser.add_argument(
        "--title",
        default=DEFAULT_MATCH,
        help=f"Card title (default: {DEFAULT_MATCH})",
    )
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    session = requests.Session()

    print("=" * 60)
    print("YOTO SMART STREAM - CARD CREATION TEST")
    print("=" * 60)
    print(f"Server: {base_url}")
    print(f"User:   {args.username}")

    # Step 1: Authenticate
    try:
        authenticate(session, base_url, args.username, args.password)
    except Exception as e:
        print(f"\n❌ Authentication failed: {e}")
        return 1

    # Step 2: Create card
    card_data = {}
    try:
        card_data = create_streaming_card(
            session,
            base_url,
            args.title,
            SAMPLE_MP3_URL,
            "Test card created by automated testing script",
        )
    except Exception as e:
        print(f"\n❌ Card creation failed: {e}")
        return 1

    # Step 3: Validate card exists
    # Wait a moment for the card to sync
    time.sleep(2)
    validation_success = validate_card_in_library(
        session,
        base_url,
        card_data.get("card_id", ""),
        args.title,
    )

    # Step 4: Delete card (unless --no-delete)
    deleted = False
    if args.no_delete:
        print("\n⏭️  Skipping cleanup (--no-delete flag set)")
    else:
        print("\n🗑️  Cleaning up...")
        content_id = card_data.get("content_id") or card_data.get("card_id")
        if content_id:
            deleted = delete_card(session, base_url, content_id)
        else:
            print("⚠️  No content ID available for deletion")

    # Step 5: Summary
    summarize_results(card_data, validation_success, deleted)

    # Return success if card was created successfully
    return 0 if card_data.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
