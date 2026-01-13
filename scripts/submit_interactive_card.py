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
        "title": "3 Interactive Sandbox (LLM Test)",
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
  "cover": {
    "imageL": "https://card-content.yotoplay.com/yoto/pub/qcaZsFg30wxKMfWKCS8-9S5xOpQ9gmssn7b7MN3ZmWQ"
  },
  "playbackType": "interactive",
  "editSettings": {
    "autoOverlayLabels": "chapters",
    "editKeys": False,
    "interactiveContent": True
  },
  "chapters": [
    {
      "title": "01 Credits ",
      "key": "01 Credits",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 772551,
      "duration": 48,
      "tracks": [
        {
          "key": "01 Credits",
          "title": "01 Credits",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 772551,
          "duration": 48,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/Xwgu8BQP_sPXb-t0xDPowo8Eth4nodVTXupyyClinac?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vWHdndThCUVBfc1BYYi10MHhEUG93bzhFdGg0bm9kVlRYdXB5eUNsaW5hYyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=q7X%7EzX1BKk%7E4Q5OxUSYDvWYtDr50CbgYLlCRfZmPCn9nR4fmqh1P2qEsr%7E7-CIfHO4B61Xz0Wb5w25Z6NJToNaNqWrNJqdSBnCBlsj0Q99tSJ2ViKckNSZkSq4igyspi3OjTe4tiZWx9olTvTsFLla0tcdJsP2FXSVy37jUo0lqjJPQsATflxh6xTWnrTtCh19-vNw5-RazVU2nBk-ylf7gJWiHC2pMNSHeQ7oB%7EO%7EuQGjl%7Eax2kS-TxMUlilxDjdZHrDSyMaTzo6OhFh8Ry06uphSRNlT18%7E5nQ984rdJVWIe6nmrCM2dLJx9NcVQ6nqLbhctqigkxq%7E7E-2cM6ew__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=Xwgu8BQP_sPXb-t0xDPowo8Eth4nodVTXupyyClinac",
          "events": {
            "onLhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "02 Start",
                "trackKey": "02 Start"
              }
            },
            "onRhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "02 Start",
                "trackKey": "02 Start"
              }
            },
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "02 Start",
                "trackKey": "02 Start"
              }
            }
          }
        }
      ]
    },
    {
      "title": "02 Start ",
      "key": "02 Start",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 619339,
      "duration": 38,
      "tracks": [
        {
          "key": "02 Start",
          "title": "02 Start",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 619339,
          "duration": 38,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/KVRFV4bXml23wILXoVN_heHlc2t87SnUFkN1N_hSzVY?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vS1ZSRlY0YlhtbDIzd0lMWG9WTl9oZUhsYzJ0ODdTblVGa04xTl9oU3pWWSIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=IEYnHeeK9CGSe7M83xKvHEP6aG1FOn2Kdd1Uu1oLERxVoOXi2d7sacEgyShAGbJWeXM2K8ncweZ21P1oFz6MQrSJFXp7Ezf2OEq%7EHGF3n0kL9mMlw%7EDC1CNdUr2sxrEzAozfF3H8vOzwZEI2N2KmEqoOR3x%7E0SPRryKY7sdalTSpYMAKhmBkItlOV%7Ehps9anrfrrr5cL-WJQmtsZ8R3SNXg7MkGxabTpgQIaBroEuRxoYsZeXb7JIYz93VeFJAUb37f7smKsk25YILo8lkUSUzd4sOQNVbfTXu4Odxzc2Nd5HhEqilcyWO1L5aiQUDtzxDfmczOostQgRYUOTF%7EZAQ__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=KVRFV4bXml23wILXoVN_heHlc2t87SnUFkN1N_hSzVY",
          "events": {
            "onEnd": {
              "cmd": "stop"
            },
            "onLhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "03 Marketplace",
                "trackKey": "03 Marketplace"
              }
            },
            "onRhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "03 Marketplace",
                "trackKey": "03 Marketplace"
              }
            }
          }
        }
      ]
    },
    {
      "title": "03 Marketplace [Edited]",
      "key": "03 Marketplace",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 1919402,
      "duration": 119,
      "tracks": [
        {
          "key": "03 Marketplace",
          "title": "03 Marketplace",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 1919402,
          "duration": 119,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/6fTOk05cN6T6_kGI5ASo9be1Ahcsr3s5eQet8V1zBTs?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vNmZUT2swNWNONlQ2X2tHSTVBU285YmUxQWhjc3IzczVlUWV0OFYxekJUcyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=MkTymwDy2HlbpddPRAKbC-vlMq1Dn7CQbY0rMcMDFaYCSR1RaVyP8dFWVt0S9E6GXP0SBrT9wbXkpsxN3RbzJzWoIvefUWknpb8fOy-N4hAQsdpmF-L-3BFQ%7Ew1%7EZhJMNu5VNDSpfIW-nGw6oBTCOxQ9SsaY%7E0YQq6Dg8T934Fd9Dvtl3lkoCJMlwLRy2mCNmP%7EqCfGmcrZVtA5sekLoP2BfB3bzDp-3U5B5PQDxZfeS0duE%7El4x4naRZ-lyQuU-XUlRiBpICLcjOhwo%7EZFYwMPwLHz%7EQoYUDibJRXvEgutYwWujQapQkPvSFH4gsCUI0uQolOS7nLG7E-XOw3Y1EA__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=6fTOk05cN6T6_kGI5ASo9be1Ahcsr3s5eQet8V1zBTs",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "04 Class Choice",
                "trackKey": "04 Class Choice"
              }
            }
          }
        }
      ]
    },
    {
      "title": "04 Class Choice [Choice]",
      "key": "04 Class Choice",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 437212,
      "duration": 27,
      "tracks": [
        {
          "key": "04 Class Choice",
          "title": "04 Class Choice",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 437212,
          "duration": 27,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/Fvc7xJU0pQUAyPL2HDEnogLIOLvB_haSXLQ0CqidKcQ?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vRnZjN3hKVTBwUVVBeVBMMkhERW5vZ0xJT0x2Ql9oYVNYTFEwQ3FpZEtjUSIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=VrUFBcQ6He%7EdKw6S1COZTwAp7Sg9AJ%7EfuEKHW9yOqknHkfd7ek-hHKZ5dM8DpPcoK1AM71FYxgYju7HxIGc%7EPuL5ew0w078S5Z9iMqL7e5WxOt5gcucFQR8GkhbcbwpXVZpf3tNiES7UJ05AT8Fu1Q7ONKnY0zn4jMSQ4tgqkjNze7%7EyIqkWjwLnJ-HkA4ac6DVu74V6DQkfoJXlUh5KlRfSj-kWectsPTcfLSSXTZXJjiAfD6s-Yer9H0r%7EpC%7E1KLfVml%7EmyzCYKCNE2hoi-M6RuntMjIYFFiyxqc9BvrFeWYSpgFZSbeIPM7cCpF9h5bGnmh32o4no3QjQcSlVKw__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=Fvc7xJU0pQUAyPL2HDEnogLIOLvB_haSXLQ0CqidKcQ",
          "events": {
            "onLhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "05 Wizard",
                "trackKey": "05 Wizard"
              }
            },
            "onRhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "09 Fighter",
                "trackKey": "09 Fighter"
              }
            },
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "04 Class Choice",
                "trackKey": "04 Class Choice"
              }
            }
          }
        }
      ]
    },
    {
      "title": "05 Wizard ",
      "key": "05 Wizard",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 572860,
      "duration": 35,
      "tracks": [
        {
          "key": "05 Wizard",
          "title": "05 Wizard",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 572860,
          "duration": 35,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/6yl6w-_5AAxtUcJyAmcxeql4BwFM4rve1KLLyrl0hJQ?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vNnlsNnctXzVBQXh0VWNKeUFtY3hlcWw0QndGTTRydmUxS0xMeXJsMGhKUSIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=BhL-zJXdd0uXELLarr8pKtzZ0%7E0HJZsMBcOrvlmK9wg0X%7ExSzWBeZCiAOat4RzrS2nK7%7EzhhuvINe9SoiUP2uYZq6OBWyW9bwvK-YNcYpFrE3hIcmq%7E3A8WhGl8c7v4eUwZJwRDcYBximKsKXww4GFbDj9jgcgTLWix8VrbPeCs8cDrAuiVTiNgFIbvVQR1yzUM7GngiwMclphND2rBieHzfBpdHGjZT1ouAml5ZJ5cW%7EFdUBZkqCy2lSiDEB2YMALrtJKjxOng5l5NeddeJnVajo4Pwnu-wwoooBStf1VK0%7EjAl-JiyN78bnRVhblqV7evUGnfSfyF7WgYXU90SCg__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=6yl6w-_5AAxtUcJyAmcxeql4BwFM4rve1KLLyrl0hJQ",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "06 Wizard Choice",
                "trackKey": "06 Wizard Choice"
              }
            }
          }
        }
      ]
    },
    {
      "title": "06 Wizard Choice [Choice]",
      "key": "06 Wizard Choice",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 437212,
      "duration": 27,
      "tracks": [
        {
          "key": "06 Wizard Choice",
          "title": "06 Wizard Choice",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 437212,
          "duration": 27,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/8JgziseMPjYYxUieaFJbMBZKMlO5c5uxN11p04C_M4k?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vOEpnemlzZU1QallZeFVpZWFGSmJNQlpLTWxPNWM1dXhOMTFwMDRDX000ayIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=VBtGk6ZuGVEUkuJ1Gx3akuQLmIvjXVul%7E6tFEbQtwmE1%7EqMHL1eSyIcQsQ27Kd7kOlGp7N3K91hxMilLe2tz7SCYYaaE6V2bFx-y4kkFK7uFWrJczEuIgKNzrV4y%7EhQtntQGWuKPEkYfw0vorpHk7nvw7Vy2GBEGNAG6Are3g5XK7pi7bPW3VqEXPyacRcN-3ZeLxtnTs1pB6g0TjWkGRe3muUA9OC4Ac7mdPuJ2ou6zPTyPFWhSxkPZyyc9h0SDpLiiK8KGWVsyAhRSnROisNuRCvOLOMlzxCLtKJ13GPE0gmegxs-M4hpWZ-pBvAr2vffwStfgGvD25mndzADLdQ__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=8JgziseMPjYYxUieaFJbMBZKMlO5c5uxN11p04C_M4k",
          "events": {
            "onLhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "07 Mage Hand",
                "trackKey": "07 Mage Hand"
              }
            },
            "onRhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "08 Mold Earth",
                "trackKey": "08 Mold Earth"
              }
            },
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "06 Wizard Choice",
                "trackKey": "06 Wizard Choice"
              }
            }
          }
        }
      ]
    },
    {
      "title": "07 Mage Hand ",
      "key": "07 Mage Hand",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 605571,
      "duration": 37,
      "tracks": [
        {
          "key": "07 Mage Hand",
          "title": "07 Mage Hand",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 605571,
          "duration": 37,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/vHYWizHc38kXcTj3JM5grtv-K62CunDvqRFJwoWnVy0?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vdkhZV2l6SGMzOGtYY1RqM0pNNWdydHYtSzYyQ3VuRHZxUkZKd29XblZ5MCIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=aimOHELA7RvVy7N2qkaNSVrebgp7wC46DVy02c-Uf3yW9AuCiLrKF4vUwkKbBXUJvWXcmLZpO9A%7ED6J0V39QcEpIA6c6gzbVCVIW-hGYErPnAnC4Nb47T1QYZCV14EMI6W56wzUz08XOQfJ-rGdJH48TZIA8qRByk2elFr7Ycc5aTN7xJx-G%7Er9OIHaL1BNVsX2EXlAUp26f8kxIMRXbl4rsX7Px87lmmtMjcr1WjvpOacsxd8Px-DgRGmAUD0gup-QAcu-XqzYJKWfNgd0Uny5bH7Cmn5GN1ZZWDH-C8eQHqTYwjfWCKoXtikEfiRgi%7EQ2JdlXhui23uBjyDW89Sw__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=vHYWizHc38kXcTj3JM5grtv-K62CunDvqRFJwoWnVy0",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "13W Fire",
                "trackKey": "13W Fire"
              }
            }
          }
        }
      ]
    },
    {
      "title": "08 Mold Earth ",
      "key": "08 Mold Earth",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 503385,
      "duration": 31,
      "tracks": [
        {
          "key": "08 Mold Earth",
          "title": "08 Mold Earth",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 503385,
          "duration": 31,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/TNVTFKJHZKxQEITbP0tqFxkj9BRUHV7VSujLAkWNlrc?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vVE5WVEZLSkhaS3hRRUlUYlAwdHFGeGtqOUJSVUhWN1ZTdWpMQWtXTmxyYyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=lXrLbTiYwe1vWw1SkU-Eu28mbtv0InOIbHgUNQrQmf8aKMMVSAGVmW0XKFsMREFWP7fw5FHEm7mSJbwHyJZIhlnaQmP2oTkj8b65XQs%7Eb8yd2j-l2lZQt%7EnNOQ7HQO89IYJRdDZuZn0inhkZiFIL35uNf8tDVGq10HixOxI4E6SmbX8LwfV5AtAZaonjB1Dk0J7SiajLly8GN4Yi%7E%7EUD0TVotIndA2WaP%7ECIpsUB9saY2XgTJKFsjH0GSHJx9gtTzTuoMcCNXpypUF8Q7dTpAJGsecinXJlFWOapb6K-1q5k8qWrWof6SgPhrM2FdjyHgaU5TmDdYqGC9FYVVRtRkg__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=TNVTFKJHZKxQEITbP0tqFxkj9BRUHV7VSujLAkWNlrc",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "13W Fire",
                "trackKey": "13W Fire"
              }
            }
          }
        }
      ]
    },
    {
      "title": "09 Fighter ",
      "key": "09 Fighter",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 526585,
      "duration": 32,
      "tracks": [
        {
          "key": "09 Fighter",
          "title": "09 Fighter",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 526585,
          "duration": 32,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/lwgJII7TBtfDczJfbSDclUG8rgpFhPHTiJtvvYsQtsA?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vbHdnSklJN1RCdGZEY3pKZmJTRGNsVUc4cmdwRmhQSFRpSnR2dllzUXRzQSIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=SxggdUzirf8xkv3x%7E0u3EOeoFwqzg8pGv0yT-lwR-KScJUzCSDgOR-W3%7EzUkJbMsTAQ86uAloMF7PlsOI87cqweFlzXfUJwK7u6vP20C2IiFYqe0XKefMKovOVaUe%7E1EHlqTSbCJrmfBklKmnxd7RyFS5EzybimhbFt5X0ij5HgErA4b7M8Z5fwNYaPAJ9Mbp%7ElSwQs%7Ex4kexRdXlWOqKSaWdQMULg17xSopRiCLtNfStP0a0NF5M%7ELPE%7Eg-T3POuRkqhfQzXbRAyfgAs9lozL74-t5Lbu2NsQf8MaRt6pMExfGmhJcwUWvn8tRh92HJAC5XayJ2zDrxpsliwLGoWA__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=lwgJII7TBtfDczJfbSDclUG8rgpFhPHTiJtvvYsQtsA",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "10 Fighter Choice",
                "trackKey": "10 Fighter Choice"
              }
            }
          }
        }
      ]
    },
    {
      "title": "10 Fighter Choice [Choice]",
      "key": "10 Fighter Choice",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 437212,
      "duration": 27,
      "tracks": [
        {
          "key": "10 Fighter Choice",
          "title": "10 Fighter Choice",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 437212,
          "duration": 27,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/Zs5RLQBd-Lv8ZYMwU1cLFw36tuHPBKuQaYTQvTBEJcg?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vWnM1UkxRQmQtTHY4WllNd1UxY0xGdzM2dHVIUEJLdVFhWVRRdlRCRUpjZyIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=BVFFqGQ9uvtMbB8jlFRYdWvK3qaEQ62awVyKyIYmZ8oMDLuuOewS2oyXC4e4JG6u6BoceJ5Ws-HRRU3Jq1DzqTDlQ510maoiigpEUFnnAHEbw-%7EXWomjFD%7EghF05YLPhpHqZO-riiCPYj5lvc6GiiobHuRwdMx83iaOBl28ZZTylLHiCIOvZlLwy1P5AJrL5Pi%7EhUdzVAb6bkBYub2J-lmLoHQM1Gm%7E38N5qiI56umTM3dvlZZbji7ePEeYwcMqoZV5MgPvRGjB0jAe3q0Bi1sCDfHz%7EEkWVynBDxu7w4SJ7S5EQWunn76oZyCQa-z%7Erb-mkvf%7EtEKhFVeuL55k5Kw__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=Zs5RLQBd-Lv8ZYMwU1cLFw36tuHPBKuQaYTQvTBEJcg",
          "events": {
            "onLhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "11 Shield",
                "trackKey": "11 Shield"
              }
            },
            "onRhb": {
              "cmd": "goto",
              "params": {
                "chapterKey": "12 Rope",
                "trackKey": "12 Rope"
              }
            },
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "10 Fighter Choice",
                "trackKey": "10 Fighter Choice"
              }
            }
          }
        }
      ]
    },
    {
      "title": "11 Shield ",
      "key": "11 Shield",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 497671,
      "duration": 31,
      "tracks": [
        {
          "key": "11 Shield",
          "title": "11 Shield",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 497671,
          "duration": 31,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/qRI--b8VoDbm3YImYV6AWhtWnF-VnuxUS85D0W85eyE?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vcVJJLS1iOFZvRGJtM1lJbVlWNkFXaHRXbkYtVm51eFVTODVEMFc4NWV5RSIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=E3yL7Ny8jrlAlMTCGrDrqJwutvEQOtUUNetcinCGMpvwqyntHXVxiB%7ElHuBF0Ppa1cResvjF6l3G1HJn3apYE2Ndo-XkHRkij1s1w0L9wGSVnjWkS56XP88nTaSOJjNsdJDji62g4jKbCz4Aywcior%7E2rBE7-jnsf9iWGCxBiztN%7E%7EoM0FzIzadiMA--Bo-t48N5%7EKVimfQufuoLw-vcMjC9KZGV3I2%7ErcDr273gtJT5Nz9FQUk8RF-XQm5fgH7G%7Ed1eIMzWG3id%7E91JH7E8y%7EnCX6SiCZpMJknX%7E2leJPLrfXJAG6IF7iRGk0-xCSH7XWkbicutz7O4pPB4tOXTaQ__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=qRI--b8VoDbm3YImYV6AWhtWnF-VnuxUS85D0W85eyE",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "13F Fire",
                "trackKey": "13F Fire"
              }
            }
          }
        }
      ]
    },
    {
      "title": "12 Rope ",
      "key": "12 Rope",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 575027,
      "duration": 35,
      "tracks": [
        {
          "key": "12 Rope",
          "title": "12 Rope",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 575027,
          "duration": 35,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/M_Y_mGnRVp1711ek1ewaoB1dRPv-0BrZTGTuFfnXSk0?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vTV9ZX21HblJWcDE3MTFlazFld2FvQjFkUlB2LTBCclpUR1R1RmZuWFNrMCIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=uqKjdtB958RrCiJw13stR7YygfF5Jaass2kGwn4qij4uoe4-2Fgtd8NMKgPBOQlluNVbWwlfJiDWcinVrT4bkbMo58uOPPPE8sN5yUP-wEeiQ1rXgMTFDF2mhbhI5JBHzV6DolgXg-n888lGWs5Ug0zAAGJf4yLy5r%7Eycj%7ExtqGw2E8Ja5W6fP13hz1pe1IJzoKMEwvDf4KcRxbJeMf-dnfpeZIWNVVFgKevukzWESp710SGCWpuYMUEOF7UawHW%7El9ejpk-o1VbrrIuaqGmniSBGc2%7Evg8tFN3%7EmBX-OusdInTbe7ZcmLsCE7DYVODwey5i1Zv-k8dzeXKXqQxmWw__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=M_Y_mGnRVp1711ek1ewaoB1dRPv-0BrZTGTuFfnXSk0",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "13F Fire",
                "trackKey": "13F Fire"
              }
            }
          }
        }
      ]
    },
    {
      "title": "13F Fire ",
      "key": "13F Fire",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 1384288,
      "duration": 85,
      "tracks": [
        {
          "key": "13F Fire",
          "title": "13F Fire",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 1384288,
          "duration": 85,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/RguqYkqpWpUPJfEy-gLV59kfscdGjB1IPHr-4QzfUC0?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vUmd1cVlrcXBXcFVQSmZFeS1nTFY1OWtmc2NkR2pCMUlQSHItNFF6ZlVDMCIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=W8hAlWxDU-f9TaD5rZ0NmxNI0kqBOVxUHrr1ZezxhvYQ1tawOb58cUQLVI4wY7jADg6sxHPU7AxDfzm4WpYy85EaQSgZaAVDRx0i%7ExY6JMj%7EiFR1OD2SGQDSqHQMpcSng7vkAE07FTbvCj6AuVMYWlUrucfqECCI1ZD8ALq1bif3nspoAGtUn10pOERrlb5KzG0xXLfb1bwUzFpdr84oh9A8eJea89ZhZokPbavoxZbnjx9w8B756AKQJfWIFqv25UKn7QFdaX6EmjPX74CXdotTtuwPjEyF7CND%7ELAz4L4yGA4oVuU0ztNDx%7EZaxGEkMztri9z06skusDHjZ2f0IQ__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=RguqYkqpWpUPJfEy-gLV59kfscdGjB1IPHr-4QzfUC0",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "13F Fire2",
                "trackKey": "13F Fire2"
              }
            }
          }
        }
      ]
    },
    {
      "title": "13F Fire2 ",
      "key": "13F Fire2",
      "availableFrom": None,
      "ambient": None,
      "defaultTrackDisplay": None,
      "defaultTrackAmbient": None,
      "fileSize": 2738050,
      "duration": 169,
      "tracks": [
        {
          "key": "13F Fire2",
          "title": "13F Fire2",
          "type": "audio",
          "format": "aac",
          "display": None,
          "ambient": None,
          "fileSize": 2738050,
          "duration": 169,
          "trackUrl": "https://secure-media.yotoplay.com/yoto/UN4jEEnZGFLeNJFs8HfGEBMYL07hWM0t2yq5P_0hbck?Expires=1768289566&Policy=eyJTdGF0ZW1lbnQiOlt7IlJlc291cmNlIjoiaHR0cHM6Ly9zZWN1cmUtbWVkaWEueW90b3BsYXkuY29tL3lvdG8vVU40akVFblpHRkxlTkpGczhIZkdFQk1ZTDA3aFdNMHQyeXE1UF8waGJjayIsIkNvbmRpdGlvbiI6eyJEYXRlTGVzc1RoYW4iOnsiQVdTOkVwb2NoVGltZSI6MTc2ODI4OTU2Nn19fV19&Signature=LRYTsZyJ1CjFwqNihlKHk3JzObg44Y-2R16RUuluu2R8BUYOT3fmOouTZufcPC1c1eIs-8WxIYG98%7EKVVf8e9iB1JHEtlvKPenNywUpWHmGuIQtYXZs6lshco%7EMyczm8FfP4FUjf3NnC0HRqwOxP3qdorJKhkUqI1Pt13V9tP5enr8Xesuph%7ERKztHyHGe1RzGmITDQIv6x6UUKUQx9b6jNHWFi9B2-NJLv%7E31Z-4GwZ8zFK9K8hHeUPOEW2cg03IaIPSsPuGV9xsZoVkTpbBtfQ327acIzRPErbbwfLoeyxDNLKEEbF2HZ%7EBSCQZ8YGgZQVVf2eqWa%7EjY5CpggO8Q__&Key-Pair-Id=K11LSW6MOXJ7KP#sha256=UN4jEEnZGFLeNJFs8HfGEBMYL07hWM0t2yq5P_0hbck",
          "events": {
            "onEnd": {
              "cmd": "goto",
              "params": {
                "chapterKey": "17F Story",
                "trackKey": "17F Story"
              }
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
