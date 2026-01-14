#!/usr/bin/env python3
"""
Delete library entries containing a match string using the server API only.

This script logs into the FastAPI service, lists the library, and deletes any
cards or playlists whose title contains the requested match text. It does not
call Yoto APIs directly.
"""

import argparse
import os
import sys
from getpass import getpass
from typing import Dict, List, Optional

import requests


DEFAULT_BASE_URL = os.getenv("YOTO_API_BASE_URL") or os.getenv("SERVER_API_BASE_URL")
DEFAULT_USERNAME = os.getenv("YOTO_API_USERNAME", "admin")
DEFAULT_PASSWORD = os.getenv("YOTO_API_PASSWORD")
DEFAULT_MATCH = os.getenv("YOTO_DELETE_MATCH", "LLM Test")


def authenticate(session: requests.Session, base_url: str, username: str, password: str) -> None:
    """Authenticate against the server and persist the session cookie."""
    response = session.post(
        f"{base_url}/user/login",
        json={"username": username, "password": password},
        timeout=15,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success"):
        raise RuntimeError(f"Login failed: {payload.get('message', 'unknown error')}")


def fetch_library(session: requests.Session, base_url: str) -> dict:
    """Fetch the library payload from the server."""
    response = session.get(f"{base_url}/library", timeout=30)
    response.raise_for_status()
    return response.json()


def normalize_base_url(raw_base_url: Optional[str]) -> str:
    """Ensure we have a usable API base URL."""
    if not raw_base_url:
        return "https://yoto-smart-stream-develop.up.railway.app/api"
    return raw_base_url.rstrip("/")


def find_targets(library_payload: dict, match_text: str) -> List[Dict[str, str]]:
    """Find cards or playlists whose title/name contains match_text (case-insensitive)."""
    targets: List[Dict[str, str]] = []
    needle = match_text.lower()

    def collect_items(items, source_label: str):
        for item in items:
            title = item.get("title") or item.get("name") or ""
            if needle not in title.lower():
                continue

            content_id = item.get("contentId") or item.get("id") or item.get("cardId")
            if not content_id:
                continue

            targets.append(
                {
                    "title": title,
                    "contentId": content_id,
                    "source": source_label,
                }
            )

    collect_items(library_payload.get("cards", []), "card")
    collect_items(library_payload.get("playlists", []), "playlist")
    return targets


def delete_target(session: requests.Session, base_url: str, target: dict) -> tuple[bool, str]:
    """Delete a single target by contentId via the server endpoint."""
    content_id = target["contentId"]
    response = session.delete(f"{base_url}/library/{content_id}", timeout=30)

    if response.status_code in (200, 204):
        return True, "deleted"
    if response.status_code == 404:
        return False, "not found"
    return False, f"failed ({response.status_code}: {response.text[:200]})"


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete library items matching text via server API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL (default: Railway develop)")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="Server username (default: admin)")
    parser.add_argument("--password", help="Server password (prompted if not provided)")
    parser.add_argument("--match", default=DEFAULT_MATCH, help="Substring to match in title/name (default: 'LLM Test')")
    parser.add_argument("--auto-confirm", action="store_true", help="Skip interactive confirmation")
    parser.add_argument("--dry-run", action="store_true", help="List matches without deleting")
    args = parser.parse_args()

    base_url = normalize_base_url(args.base_url)
    username = args.username
    password = args.password or DEFAULT_PASSWORD or getpass("Password: ")

    session = requests.Session()

    print(f"Using API base: {base_url}")
    print("Authenticating against server...")
    try:
        authenticate(session, base_url, username, password)
        print(f"Authenticated as {username}")
    except Exception as exc:
        print(f"Authentication failed: {exc}")
        return 1

    print("Fetching library...")
    try:
        library_payload = fetch_library(session, base_url)
    except Exception as exc:
        print(f"Failed to fetch library: {exc}")
        return 1

    targets = find_targets(library_payload, args.match)
    if not targets:
        print(f"No items found containing '{args.match}'.")
        return 0

    print(f"Found {len(targets)} item(s) matching '{args.match}':")
    for target in targets:
        print(f"  - {target['title']} (source={target['source']}, contentId={target['contentId']})")

    if args.dry_run:
        print("Dry run requested; no deletions performed.")
        return 0

    if not args.auto_confirm:
        confirm = input("Proceed with deletion? (yes/no): ").strip().lower()
        if confirm not in {"yes", "y"}:
            print("Cancelled.")
            return 0
    else:
        print("Auto-confirm enabled; proceeding with deletion.")

    failures = 0
    for target in targets:
        success, message = delete_target(session, base_url, target)
        status = "ok" if success else "fail"
        print(f"[{status}] {target['title']} -> {message}")
        if not success:
            failures += 1

    if failures:
        print(f"Completed with {failures} failure(s).")
        return 1

    print("Deletion complete with no failures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
