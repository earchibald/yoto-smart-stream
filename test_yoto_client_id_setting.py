#!/usr/bin/env python3
"""
Simple script to test the YOTO_CLIENT_ID setting functionality.

This script tests:
1. Fetching all settings
2. Getting the yoto_client_id setting
3. Updating the yoto_client_id setting
4. Verifying environment variable override behavior
"""

import os
from typing import Optional

import requests

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "yoto")


def login(base_url: str, username: str, password: str) -> Optional[requests.Session]:
    """Login and return authenticated session."""
    session = requests.Session()

    response = session.post(
        f"{base_url}/api/user/login", json={"username": username, "password": password}
    )

    if response.status_code == 200:
        print(f"✓ Logged in as {username}")
        return session
    else:
        print(f"✗ Login failed: {response.status_code} - {response.text}")
        return None


def test_list_settings(session: requests.Session, base_url: str):
    """Test listing all settings."""
    print("\n📋 Testing list settings...")

    response = session.get(f"{base_url}/api/settings")

    if response.status_code == 200:
        data = response.json()
        print(f"✓ Found {len(data['settings'])} settings")

        for setting in data["settings"]:
            override_indicator = " 🔒 [ENV OVERRIDE]" if setting["is_overridden"] else ""
            print(f"  - {setting['key']}: {setting['value']}{override_indicator}")
            if setting["is_overridden"]:
                print(f"    └─ Environment variable value: {setting['env_var_override']}")

        return True
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
        return False


def test_get_yoto_client_id(session: requests.Session, base_url: str):
    """Test getting yoto_client_id setting."""
    print("\n🔑 Testing get yoto_client_id setting...")

    response = session.get(f"{base_url}/api/settings/yoto_client_id")

    if response.status_code == 200:
        data = response.json()
        print("✓ yoto_client_id setting:")
        print(f"  Value: {data['value']}")
        print(f"  Description: {data['description']}")
        print(f"  Is overridden: {data['is_overridden']}")
        if data["is_overridden"]:
            print(f"  Env var override: {data['env_var_override']}")

        return True
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
        return False


def test_update_yoto_client_id(session: requests.Session, base_url: str, new_value: str):
    """Test updating yoto_client_id setting."""
    print(f"\n✏️  Testing update yoto_client_id setting to: {new_value}...")

    response = session.put(f"{base_url}/api/settings/yoto_client_id", json={"value": new_value})

    if response.status_code == 200:
        data = response.json()
        print("✓ Updated yoto_client_id:")
        print(f"  New value: {data['value']}")
        print(f"  Is overridden: {data['is_overridden']}")
        if data["is_overridden"]:
            print("  ⚠️  Note: Environment variable is overriding this value")
            print(f"     Env var value: {data['env_var_override']}")

        return True
    else:
        print(f"✗ Failed: {response.status_code} - {response.text}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("YOTO_CLIENT_ID SETTING TEST")
    print("=" * 60)
    print(f"Base URL: {BASE_URL}")
    print(f"Username: {ADMIN_USERNAME}")

    # Login
    session = login(BASE_URL, ADMIN_USERNAME, ADMIN_PASSWORD)
    if not session:
        print("\n❌ Cannot proceed without authentication")
        return False

    # Run tests
    success = True
    success &= test_list_settings(session, BASE_URL)
    success &= test_get_yoto_client_id(session, BASE_URL)
    success &= test_update_yoto_client_id(session, BASE_URL, "test_client_id_123")

    # Verify the update
    success &= test_get_yoto_client_id(session, BASE_URL)

    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 60)

    return success


if __name__ == "__main__":
    import sys

    sys.exit(0 if main() else 1)
