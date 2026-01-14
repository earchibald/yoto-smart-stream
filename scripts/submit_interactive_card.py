#!/usr/bin/env python3
"""Submit a minimal interactive card payload to Yoto API.

This script is intentionally verbose for iteration by an LLM agent. It:
- Loads YOTO_CLIENT_ID from the environment
- Reuses a cached refresh token if available (.yoto_refresh_token)
- Falls back to device code flow and caches the refresh token on success
- Submits a tiny interactive card schema with one choice and state updates
- Prints request/response details for further permutation

Usage:
    python scripts/submit_interactive_card.py

Prerequisites:
    pip install yoto_api requests
    export YOTO_CLIENT_ID=...   # from https://yoto.dev/
"""

from __future__ import annotations

COUNT = 12

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from yoto_api import YotoManager

TOKEN_CACHE = Path(".yoto_refresh_token")
CONTENT_URL = "https://api.yotoplay.com/content"  # For streaming/interactive cards
CARD_URL = "https://api.yotoplay.com/card"       # Legacy endpoint

# Sample audio tracks (public)
SAMPLE_MP3 = "https://samplelib.com/lib/preview/mp3/sample-3s.mp3"
SAMPLE_MP3_2 = "https://download.samplelib.com/mp3/sample-12s.mp3"
SAMPLE_MP3_3 = "https://download.samplelib.com/mp3/sample-9s.mp3"


def load_client_id() -> str:
    client_id = os.getenv("YOTO_CLIENT_ID")
    if not client_id:
        print("ERROR: YOTO_CLIENT_ID is not set in the environment.")
        sys.exit(1)
    return client_id


def init_manager(client_id: str) -> YotoManager:
    return YotoManager(client_id=client_id)


def refresh_with_cached_token(manager: YotoManager) -> bool:
    """Always attempt a refresh before using any cached token.

    This avoids relying on a possibly-expired access token and forces a new
    access token on startup. If refresh fails, caller should fall back to
    device code flow.
    """
    if not TOKEN_CACHE.exists():
        return False

    token = TOKEN_CACHE.read_text().strip()
    if not token:
        return False

    try:
        manager.set_refresh_token(token)
        # Force a refresh immediately rather than assuming validity
        manager.check_and_refresh_token()
        print("✅ Refreshed using cached refresh token (new access token acquired)")
        return True
    except Exception as exc:  # pragma: no cover - best effort
        print(f"⚠️  Cached token unusable: {exc}")
        return False


def device_flow_auth(manager: YotoManager) -> None:
    info = manager.device_code_flow_start()
    verification_uri = info.get("verification_uri", "https://login.yotoplay.com/activate")
    user_code = info.get("user_code", "")
    # Prefer provider-supplied deep link, else build a convenience link with the code prefilled
    one_click = info.get("verification_uri_complete") or f"{verification_uri}?user_code={user_code}"
    print("\n== Device Code Flow ==")
    print(f"Visit: {one_click}")
    print(f"Code:  {user_code}")
    interval = info.get("interval", 5)

    # Poll until success or timeout (3 minutes)
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            time.sleep(interval)
            manager.device_code_flow_complete()
            print("✅ Device code auth completed")
            return
        except Exception as exc:  # pragma: no cover - network/UX dependent
            if "authorization_pending" in str(exc):
                print("… waiting for user approval …")
                continue
            if "slow_down" in str(exc):
                interval = min(interval + 2, 15)
                print("… asked to slow down, increasing interval …")
                continue
            print(f"⚠️  Poll error: {exc}")
    print("ERROR: Device flow timed out after 3 minutes")
    sys.exit(1)


def cache_refresh_token(manager: YotoManager) -> None:
    token = getattr(manager, "token", None)
    refresh = getattr(token, "refresh_token", None)
    if not refresh:
        print("⚠️  No refresh token returned; cannot cache")
        return
    TOKEN_CACHE.write_text(refresh)
    print(f"💾 Cached refresh token to {TOKEN_CACHE}")


def build_interactive_payload() -> Dict[str, Any]:
    """Return a minimal interactive card schema with a single choice."""
    payload: Dict[str, Any] = {
        "title": f"{COUNT} Interactive Sandbox (LLM Test)",
        "metadata": {
            "description": "Minimal interactive card with one branching choice.",
            "author": "LLM Sandbox",
        },
        "content": {
            "version": "1",
            "activity": "yoto_Player",
            "config": {
                "resumeTimeout": 2592000,
                "disableTrackNav": True,
                "disableChapterNav": True,
                "autoadvance": "none"
            },
            "availability": "",
            "playbackType": "interactive",
            "editSettings": {
                "autoOverlayLabels": "chapters",
                "editKeys": False,
                "interactiveContent": True
            },
            "chapters": [
                {
                    "title": "01 Chapter 1 ",
                    "key": "01 Chapter 1",
                    "tracks": [
                        {
                            "key": "01 Chapter 1",
                            "title": "01 Chapter 1",
                            "type": "stream",
                            "format": "mp3",
                            "display": None,
                            "ambient": None,
                            "trackUrl": "https://yoto-smart-stream-develop.up.railway.app/api/audio/ch1.mp3",
                            "events": {
                                "onLhb": {
                                    "cmd": "goto",
                                    "params": {
                                        "chapterKey": "02 Chapter 2",
                                        "trackKey": "02 Chapter 2"
                                    }
                                },
                                "onRhb": {
                                    "cmd": "goto",
                                    "params": {
                                        "chapterKey": "02 Chapter 2",
                                        "trackKey": "02 Chapter 2"
                                    }
                                },
                                "onEnd":
                                {
                                    "cmd": "stop"
                                }
                            }
                        }
                    ]
                },
                {
                    "title": "02 Chapter 2 ",
                    "key": "02 Chapter 2",
                    "availableFrom": None,
                    "ambient": None,
                    "defaultTrackDisplay": None,
                    "defaultTrackAmbient": None,
                    "tracks": [
                        {
                            "key": "02 Chapter 2",
                            "title": "02 Chapter 2",
                            "type": "stream",
                            "format": "mp3",
                            "display": None,
                            "ambient": None,
                            "trackUrl": "https://yoto-smart-stream-develop.up.railway.app/api/audio/ch2.mp3",
                            "events": {
                                "onEnd": {
                                    "cmd": "stop"
                                },
                                "onLhb": {
                                    "cmd": "goto",
                                    "params": {
                                        "chapterKey": "03 Chapter 3",
                                        "trackKey": "03 Chapter 3"
                                    }
                                },
                                "onRhb": {
                                    "cmd": "goto",
                                    "params": {
                                        "chapterKey": "04 Chapter 4",
                                        "trackKey": "04 Chapter 4"
                                    }
                                }
                            }
                        }
                    ]
                },
                {
                    "title": "03 Chapter 3",
                    "key": "03 Chapter 3",
                    "availableFrom": None,
                    "ambient": None,
                    "defaultTrackDisplay": None,
                    "defaultTrackAmbient": None,
                    "tracks": [
                        {
                            "key": "03 Chapter 3",
                            "title": "03 Chapter 3",
                            "type": "stream",
                            "format": "mp3",
                            "display": None,
                            "ambient": None,
                            "trackUrl": "https://yoto-smart-stream-develop.up.railway.app/api/audio/ch3.mp3",
                            "events": {
                                "onEnd": {
                                "cmd": "stop"
                                },
                                "onLhb": {
                                    "cmd": "goto",
                                    "params": {
                                        "chapterKey": "01 Chapter 1",
                                        "trackKey": "01 Chapter 1"
                                    }
                                }
                            }
                        }
                    ]
                },
                {
                    "title": "04 Chapter 4 ",
                    "key": "04 Chapter 4",
                    "availableFrom": None,
                    "ambient": None,
                    "defaultTrackDisplay": None,
                    "defaultTrackAmbient": None,
                    "tracks": [
                        {
                            "key": "04 Chapter 4",
                            "title": "04 Chapter 4",
                            "type": "stream",
                            "format": "mp3",
                            "display": None,
                            "ambient": None,
                            "trackUrl": "https://yoto-smart-stream-develop.up.railway.app/api/audio/ch4.mp3",
                            "events": {
                                "onEnd": {
                                "cmd": "stop"
                                },
                                "onLhb": {
                                    "cmd": "goto",
                                    "params": {
                                        "chapterKey": "01 Chapter 1",
                                        "trackKey": "01 Chapter 1"
                                    }
                                },
                            }
                        }
                    ]
                },
                {
                "title": "04 Chapter 5",
                "key": "04 Chapter 5",
                "availableFrom": None,
                "ambient": None,
                "defaultTrackDisplay": None,
                "defaultTrackAmbient": None,
                    "tracks": [
                        {
                            "key": "04 Chapter 5",
                            "title": "04 Chapter 5",
                            "type": "stream",
                            "format": "mp3",
                            "display": None,
                            "ambient": None,
                            "trackUrl": "https://yoto-smart-stream-develop.up.railway.app/api/audio/ch4.mp3",
                            "events": {
                                "onEnd": {
                                    "cmd": "stop"
                                }
                            }
                        }
                    ]
                }
            ]
        }
}
    return payload


def submit_card(manager: YotoManager, payload: Dict[str, Any], label: str, endpoint: str = CONTENT_URL) -> requests.Response:
    """Submit a card payload to the Yoto API.
    
    Args:
        manager: Authenticated YotoManager instance
        payload: Card payload to submit
        label: Display label for logging
        endpoint: API endpoint URL (default: CONTENT_URL)
    
    Returns:
        Response object from the API
    """
    access_token = manager.token.access_token  # type: ignore[attr-defined]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    print(f"\n== Submitting {label} ==")
    print(f"Endpoint: {endpoint}")
    print("Payload:")
    print(json.dumps(payload, indent=2))

    resp = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    print("\n== Response ==")
    print(f"Status: {resp.status_code}")
    try:
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print(resp.text)
    return resp


def build_simple_streaming_payload() -> Dict[str, Any]:
    """Baseline non-interactive streaming card using correct Yoto schema."""
    payload: Dict[str, Any] = {
        "title": "Baseline Streaming Card (LLM Test)",
        "metadata": {
            "description": "Single-track streaming card for control test.",
        },
        "content": {
            "chapters": [
                {
                    "key": "01",
                    "title": "Chapter 1",
                    "tracks": [
                        {
                            "key": "01",
                            "type": "stream",
                            "format": "mp3",
                            "title": "Track 1",
                            "trackUrl": "https://samplelib.com/lib/preview/mp3/sample-3s.mp3",
                        }
                    ],
                }
            ]
        },
    }
    return payload


def main() -> None:
    client_id = load_client_id()
    manager = init_manager(client_id)

    authed = refresh_with_cached_token(manager)
    if not authed:
        device_flow_auth(manager)
        cache_refresh_token(manager)

    # Submit baseline streaming card using /content endpoint
    # streaming_payload = build_simple_streaming_payload()
    # submit_card(manager, streaming_payload, label="Baseline Streaming Card", endpoint=CONTENT_URL)

    # Submit interactive card using /content endpoint
    interactive_payload = build_interactive_payload()
    submit_card(manager, interactive_payload, label="Interactive Card", endpoint=CONTENT_URL)


if __name__ == "__main__":
    main()
