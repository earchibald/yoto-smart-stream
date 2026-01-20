#!/usr/bin/env python3
"""Test settings env var override functionality."""

import json
import requests

BASE_URL = "https://yoto-smart-stream-develop.up.railway.app"

def test_settings_env_override():
    """Test that env var override is properly detected and displayed."""
    
    # Login
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/user/login",
        json={"username": "admin", "password": "yoto"}
    )
    assert response.ok, f"Login failed: {response.text}"
    print("✅ Login successful")
    
    # Get settings
    response = session.get(f"{BASE_URL}/api/settings")
    assert response.ok, f"Get settings failed: {response.text}"
    
    data = response.json()
    settings = data["settings"]
    transcription_setting = next(s for s in settings if s["key"] == "transcription_enabled")
    
    print("\n📊 Current Settings State:")
    print(f"  Key: {transcription_setting['key']}")
    print(f"  Value (effective): {transcription_setting['value']}")
    print(f"  Env Var Override: {transcription_setting['env_var_override']}")
    print(f"  Is Overridden: {transcription_setting['is_overridden']}")
    
    # Verify env var is detected
    assert transcription_setting["is_overridden"], "❌ Env var override not detected!"
    assert transcription_setting["env_var_override"] == "true", f"❌ Unexpected env var value: {transcription_setting['env_var_override']}"
    assert transcription_setting["value"] == "true", f"❌ Effective value should be 'true' from env var, got: {transcription_setting['value']}"
    print("\n✅ Env var override correctly detected!")
    
    # Try to update setting (should update DB but effective value stays from env var)
    print("\n🔄 Updating database setting to 'false'...")
    response = session.put(
        f"{BASE_URL}/api/settings/transcription_enabled",
        json={"value": "false"}
    )
    assert response.ok, f"Update failed: {response.text}"
    
    updated = response.json()
    print(f"  Response value (effective): {updated['value']}")
    print(f"  Response is_overridden: {updated['is_overridden']}")
    
    # Effective value should still be 'true' from env var
    assert updated["value"] == "true", f"❌ Effective value should still be 'true', got: {updated['value']}"
    assert updated["is_overridden"], "❌ Should still be overridden!"
    print("✅ Database updated but env var still takes precedence!")
    
    # Get settings again to verify persistence
    response = session.get(f"{BASE_URL}/api/settings")
    data = response.json()
    transcription_setting = next(s for s in data["settings"] if s["key"] == "transcription_enabled")
    
    print(f"\n📊 After Update:")
    print(f"  Value (effective): {transcription_setting['value']}")
    print(f"  Still overridden: {transcription_setting['is_overridden']}")
    
    assert transcription_setting["value"] == "true", "❌ Effective value changed!"
    assert transcription_setting["is_overridden"], "❌ Override flag cleared!"
    print("✅ State persisted correctly!")
    
    print("\n🎉 All tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_settings_env_override()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
