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
        "title": "4 Interactive Sandbox (LLM Test)",
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
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "tracks": [
        {
          "key": "01 Chapter 1",
          "title": "01 Chapter 1",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/Xwgu8BQP_sPXb-t0xDPowo8Eth4nodVTXupyyClinac?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vWHdndThCUVBfc1BYYi10MHhEUG93bzhFdGg0bm9kVlRYdXB5eUNsaW5hYyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=q7X%7EzX1BKk%7E4Q5OxUSYDvWYtDr50CbgYLlCRfZmPCn9nR4fmqh1P2qEsr%7E7-CIfHO4B61Xz0Wb5w25Z6NJToNaNqWrNJqdSBnCBlsj0Q99tSJ2ViKckNSZkSq4igyspi3OjTe4tiZWx9olTvTsFLla0tcdJsP2FXSVy37jUo0lqjJPQsATflxh6xTWnrTtCh19-vNw5-RazVU2nBk-ylf7gJWiHC2pMNSHeQ7oB%7EO%7EuQGjl%7Eax2kS-TxMUlilxDjdZHrDSyMaTzo6OhFh8Ry06uphSRNlT18%7E5nQ984rdJVWIe6nmrCM2dLJx9NcVQ6nqLbhctqigkxq%7E7E-2cM6ew__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=Xwgu8BQP_sPXb-t0xDPowo8Eth4nodVTXupyyClinac",
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
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "02 Chapter 2",
                "trackKey": "02 Chapter 2"
              }
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
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/KVRFV4bXml23wILXoVN_heHlc2t87SnUFkN1N_hSzVY?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vS1ZSRlY0YlhtbDIzd0lMWG9WTl9oZUhsYzJ0ODdTblVGa04xTl9oU3pWWSIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=IEYnHeeK9CGSe7M83xKvHEP6aG1FOn2Kdd1Uu1oLERxVoOXi2d7sacEgyShAGbJWeXM2K8ncweZ21P1oFz6MQrSJFXp7Ezf2OEq%7EHGF3n0kL9mMlw%7EDC1CNdUr2sxrEzAozfF3H8vOzwZEI2N2KmEqoOR3x%7E0SPRryKY7sdalTSpYMAKhmBkItlOV%7Ehps9anrfrrr5cL-WJQmtsZ8R3SNXg7MkGxabTpgQIaBroEuRxoYsZeXb7JIYz93VeFJAUb37f7smKsk25YILo8lkUSUzd4sOQNVbfTXu4Odxzc2Nd5HhEqilcyWO1L5aiQUDtzxDfmczOostQgRYUOTF%7EZAQ__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=KVRFV4bXml23wILXoVN_heHlc2t87SnUFkN1N_hSzVY",
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
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/6fTOk05cN6T6_kGI5ASo9be1Ahcsr3s5eQet8V1zBTs?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vNmZUT2swNWNONlQ2X2tHSTVBU285YmUxQWhjc3IzczVlUWV0OFYxekJUcyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=MkTymwDy2HlbpddPRAKbC-vlMq1Dn7CQbY0rMcMDFaYCSR1RaVyP8dFWVt0S9E6GXP0SBrT9wbXkpsxN3RbzJzWoIvefUWknpb8fOy-N4hAQsdpmF-L-3BFQ%7Ew1%7EZhJMNu5VNDSpfIW-nGw6oBTCOxQ9SsaY%7E0YQq6Dg8T934Fd9Dvtl3lkoCJMlwLRy2mCNmP%7EqCfGmcrZVtA5sekLoP2BfB3bzDp-3U5B5PQDxZfeS0duE%7El4x4naRZ-lyQuU-XUlRiBpICLcjOhwo%7EZFYwMPwLHz%7EQoYUDibJRXvEgutYwWujQapQkPvSFH4gsCUI0uQolOS7nLG7E-XOw3Y1EA__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=6fTOk05cN6T6_kGI5ASo9be1Ahcsr3s5eQet8V1zBTs",
          "events": {
            "onEnd": {
              "cmd": "stop"
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
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/Fvc7xJU0pQUAyPL2HDEnogLIOLvB_haSXLQ0CqidKcQ?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vRnZjN3hKVTBwUVVBeVBMMkhERW5vZ0xJT0x2Ql9oYVNYTFEwQ3FpZEtjUSIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=VrUFBcQ6He%7EdKw6S1COZTwAp7Sg9AJ%7EfuEKHW9yOqknHkfd7ek-hHKZ5dM8DpPcoK1AM71FYxgYju7HxIGc%7EPuL5ew0w078S5Z9iMqL7e5WxOt5gcucFQR8GkhbcbwpXVZpf3tNiES7UJ05AT8Fu1Q7ONKnY0zn4jMSQ4tgqkjNze7%7EyIqkWjwLnJ-HkA4ac6DVu74V6DQkfoJXlUh5KlRfSj-kWectsPTcfLSSXTZXJjiAfD6s-Yer9H0r%7EpC%7E1KLfVml%7EmyzCYKCNE2hoi-M6RuntMjIYFFiyxqc9BvrFeWYSpgFZSbeIPM7cCpF9h5bGnmh32o4no3QjQcSlVKw__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=Fvc7xJU0pQUAyPL2HDEnogLIOLvB_haSXLQ0CqidKcQ",
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
    streaming_payload = build_simple_streaming_payload()
    submit_card(manager, streaming_payload, label="Baseline Streaming Card", endpoint=CONTENT_URL)

    # Submit interactive card using /content endpoint
    interactive_payload = build_interactive_payload()
    submit_card(manager, interactive_payload, label="Interactive Card", endpoint=CONTENT_URL)


if __name__ == "__main__":
    main()
