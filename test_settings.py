#!/usr/bin/env python3
"""Test the settings management feature on the admin page."""

import os
import time
from playwright.sync_api import sync_playwright

# Get credentials from environment
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "yoto")  # Default password
BASE_URL = "https://yoto-smart-stream-develop.up.railway.app"

def test_settings():
    """Test settings management functionality."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # 1. Navigate to admin page
            print(f"🌐 Navigating to {BASE_URL}/admin")
            page.goto(f"{BASE_URL}/admin", wait_until="networkidle")
            
            # Check if we need to log in
            if "/login" in page.url or "Login" in page.content():
                print("🔐 Logging in as admin...")
                page.fill('input[name="username"]', ADMIN_USERNAME)
                page.fill('input[name="password"]', ADMIN_PASSWORD)
                page.click('button[type="submit"]')
                page.wait_for_load_state("networkidle")
                
                # Wait a bit and check if we're redirected
                time.sleep(2)
                print(f"📍 Current URL after login: {page.url}")
                
                if "/login" in page.url or "Login" in page.content():
                    print("❌ Login failed - still on login page")
                    page.screenshot(path="/tmp/login_failed.png", full_page=True)
                    print("📸 Login failure screenshot saved: /tmp/login_failed.png")
                    return False
                print("✅ Logged in successfully")
            
            # Take screenshot of admin page
            page.screenshot(path="/tmp/admin_page.png", full_page=True)
            print("📸 Screenshot saved: /tmp/admin_page.png")
            
            # 2. Check if settings section is visible
            print("\n🔍 Checking for settings section...")
            settings_section = page.locator("h2:has-text('Settings')")
            if settings_section.is_visible():
                print("✅ Settings section found")
            else:
                print("❌ Settings section not found")
                print("Page content:")
                print(page.content()[:500])
                return False
            
            # 3. Check if transcription_enabled setting is present
            print("\n🔍 Looking for transcription_enabled setting...")
            setting_item = page.locator('.setting-item:has-text("Transcription Enabled")')
            if setting_item.count() > 0:
                print("✅ Transcription setting found")
                
                # Take screenshot of settings section
                setting_item.screenshot(path="/tmp/settings_section.png")
                print("📸 Settings screenshot saved: /tmp/settings_section.png")
                
                # Check if toggle switch is present
                toggle = setting_item.locator('.toggle-switch input[type="checkbox"]')
                if toggle.count() > 0:
                    print("✅ Toggle switch found")
                    
                    # Get current state
                    is_checked = toggle.is_checked()
                    print(f"📊 Current state: {'ON' if is_checked else 'OFF'}")
                    
                    # Toggle the setting
                    print("\n🔄 Toggling setting...")
                    toggle.click()
                    
                    # Wait for API call to complete
                    time.sleep(2)
                    
                    # Check new state
                    new_state = toggle.is_checked()
                    print(f"📊 New state: {'ON' if new_state else 'OFF'}")
                    
                    if new_state != is_checked:
                        print("✅ Toggle changed successfully")
                        
                        # Toggle back to original state
                        print("\n🔄 Toggling back to original state...")
                        toggle.click()
                        time.sleep(2)
                        final_state = toggle.is_checked()
                        
                        if final_state == is_checked:
                            print("✅ Successfully toggled back to original state")
                        else:
                            print("⚠️  State didn't restore correctly")
                    else:
                        print("❌ Toggle didn't change")
                else:
                    print("❌ Toggle switch not found")
                    return False
            else:
                print("❌ Transcription setting not found")
                print("\nAvailable content:")
                print(page.locator(".settings-container").inner_text())
                return False
            
            # 4. Check API endpoint directly
            print("\n🔌 Testing API endpoint...")
            response = page.request.get(f"{BASE_URL}/api/settings")
            if response.ok:
                settings_data = response.json()
                print("✅ API endpoint working")
                print(f"📊 Settings data: {settings_data}")
            else:
                print(f"❌ API endpoint failed: {response.status}")
                return False
            
            print("\n✅ All tests passed!")
            return True
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            # Take screenshot on error
            page.screenshot(path="/tmp/error.png", full_page=True)
            print("📸 Error screenshot saved: /tmp/error.png")
            return False
        finally:
            browser.close()

if __name__ == "__main__":
    success = test_settings()
    exit(0 if success else 1)
