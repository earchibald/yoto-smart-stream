#!/usr/bin/env python3
"""
Test Yoto OAuth flow with Playwright automation
"""
import os
import sys
import json
import time
import requests
from playwright.sync_api import sync_playwright, expect

# Get environment variables
YOTO_USERNAME = os.environ.get('YOTO_USERNAME')
YOTO_PASSWORD = os.environ.get('YOTO_PASSWORD')
API_URL = "https://d8vwiy1z0j.execute-api.us-east-1.amazonaws.com"

if not YOTO_USERNAME or not YOTO_PASSWORD:
    print("❌ ERROR: YOTO_USERNAME and YOTO_PASSWORD environment variables required")
    sys.exit(1)

print("🚀 Starting OAuth flow test...")
print(f"Using Yoto username: {YOTO_USERNAME}")

# Step 1: Start OAuth device flow
print("\n📱 Step 1: Starting OAuth device flow...")
response = requests.post(f"{API_URL}/api/auth/start")
auth_data = response.json()
print(f"✓ Device code: {auth_data['device_code']}")
print(f"✓ User code: {auth_data['user_code']}")
print(f"✓ Verification URL: {auth_data['verification_uri_complete']}")

device_code = auth_data['device_code']
verification_url = auth_data['verification_uri_complete']

# Step 2: Navigate to Yoto authorization page with Playwright
print("\n🌐 Step 2: Navigating to Yoto authorization page...")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context()
    page = context.new_page()
    
    try:
        # Navigate to verification URL
        print(f"Navigating to: {verification_url}")
        page.goto(verification_url, wait_until="networkidle", timeout=30000)
        time.sleep(2)
        
        # Take screenshot for debugging
        page.screenshot(path="/tmp/oauth_step1.png")
        print("✓ Page loaded, screenshot saved to /tmp/oauth_step1.png")
        
        # Check if we need to log in
        print("\n🔐 Step 3: Checking page state...")
        page_content = page.content()
        
        if "device confirmation" in page_content.lower() or "confirm this is the code" in page_content.lower():
            print("✓ Already on device confirmation page, skipping login for now")
        elif "login" in page_content.lower() or "email" in page_content.lower() or "password" in page_content.lower():
            print("Login page detected. Entering credentials...")
            
            # For Yoto, it's username not email
            try:
                username_selector = 'input[type="text"], input[name="username"], input[id="username"], input[name="email"], input[id="email"]'
                page.wait_for_selector(username_selector, timeout=5000)
                page.fill(username_selector, YOTO_USERNAME)
                print(f"✓ Entered username: {YOTO_USERNAME}")
            except Exception as e:
                print(f"⚠️  Could not find username field: {e}")
                print("Page title:", page.title())
                print("Page URL:", page.url)
            
            # Wait for and fill password field
            try:
                password_selector = 'input[type="password"], input[name="password"], input[id="password"]'
                page.wait_for_selector(password_selector, timeout=5000)
                page.fill(password_selector, YOTO_PASSWORD)
                print("✓ Entered password")
            except Exception as e:
                print(f"⚠️  Could not find password field: {e}")
            
            # Take screenshot before submit
            page.screenshot(path="/tmp/oauth_step2_credentials.png")
            print("✓ Screenshot saved: /tmp/oauth_step2_credentials.png")
            
            # Click login/submit button
            try:
                submit_selectors = [
                    'button:has-text("Log in")',
                    'button:has-text("log in")',
                    'button:has-text("Sign in")',
                    'button:has-text("Continue")',
                    'button[type="submit"]',
                    'input[type="submit"]'
                ]
                
                for selector in submit_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            print(f"Found submit button with selector: {selector}")
                            page.click(selector)
                            print("✓ Clicked login button")
                            break
                    except:
                        continue
                
                # Wait for navigation
                page.wait_for_load_state("networkidle", timeout=10000)
                time.sleep(2)
                
            except Exception as e:
                print(f"⚠️  Could not click submit button: {e}")
        else:
            print("✓ Page state unclear, proceeding to next step")
        
        # Take screenshot after login check
        page.screenshot(path="/tmp/oauth_step2_after_check.png")
        print("✓ Screenshot saved: /tmp/oauth_step2_after_check.png")
        
        # Step 4: Look for and click authorization/confirmation button
        print("\n✅ Step 4: Looking for authorization button...")
        page_content = page.content().lower()
        page_text = page.inner_text('body').lower()
        
        print(f"Page title: {page.title()}")
        print(f"Page URL: {page.url}")
        
        # Check if we're on the success page
        if "congratulations" in page_text or "you're all set" in page_text or "success" in page_text:
            print("✓ Already on success page!")
        else:
            # Look for Confirm button specifically (Device Confirmation page)
            auth_button_selectors = [
                'button:has-text("Confirm")',
                'button:has-text("Allow")',
                'button:has-text("Authorize")',
                'button:has-text("Accept")',
                'button:has-text("Continue")'
            ]
            
            button_clicked = False
            for selector in auth_button_selectors:
                try:
                    locator = page.locator(selector)
                    if locator.count() > 0:
                        print(f"Found authorization button with selector: {selector}")
                        button_text = locator.first.inner_text()
                        print(f"Button text: {button_text}")
                        
                        # Only click if it's not Cancel
                        if "cancel" not in button_text.lower():
                            locator.first.click()
                            print("✓ Clicked authorization button")
                            button_clicked = True
                            
                            # Wait for navigation
                            page.wait_for_load_state("networkidle", timeout=10000)
                            time.sleep(2)
                            break
                except Exception as e:
                    print(f"  Error with selector {selector}: {e}")
                    continue
            
            if not button_clicked:
                print("⚠️  No authorization button found on page")
                # Print all buttons on page for debugging
                all_buttons = page.locator('button').all()
                print(f"All buttons on page ({len(all_buttons)}):")
                for btn in all_buttons:
                    try:
                        print(f"  - {btn.inner_text()}")
                    except:
                        pass
        
        # Take screenshot after clicking Confirm
        page.screenshot(path="/tmp/oauth_step4_after_confirm.png")
        print("✓ Screenshot saved: /tmp/oauth_step4_after_confirm.png")
        
        # Step 5: Check if we were redirected to login page after clicking Confirm
        print("\n🔐 Step 5: Checking if login is required after confirmation...")
        page_content = page.content().lower()
        page_text = page.inner_text('body').lower()
        
        if "log in" in page_text or "login" in page_text or "sign in" in page_text:
            print("Login page detected after confirmation. Entering credentials...")
            
            # For Yoto, it's username not email
            try:
                # Look for the first visible text input
                username_selectors = [
                    'input[type="text"]:visible',
                    'input[name="username"]',
                    'input[id="username"]',
                    'input[name="email"]',
                    'input[placeholder*="email" i]'
                ]
                
                for selector in username_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            page.fill(selector, YOTO_USERNAME)
                            print(f"✓ Entered username: {YOTO_USERNAME} (selector: {selector})")
                            break
                    except:
                        continue
                        
            except Exception as e:
                print(f"⚠️  Could not find username field: {e}")
            
            # Wait for and fill password field
            try:
                password_selector = 'input[type="password"]'
                page.wait_for_selector(password_selector, timeout=5000)
                page.fill(password_selector, YOTO_PASSWORD)
                print("✓ Entered password")
            except Exception as e:
                print(f"⚠️  Could not find password field: {e}")
            
            # Take screenshot before submit
            page.screenshot(path="/tmp/oauth_step5_login_filled.png")
            print("✓ Screenshot saved: /tmp/oauth_step5_login_filled.png")
            
            # Click login button
            try:
                login_selectors = [
                    'button:has-text("log in")',
                    'button:has-text("Log in")',
                    'button:has-text("Sign in")',
                    'button[type="submit"]'
                ]
                
                for selector in login_selectors:
                    try:
                        if page.locator(selector).count() > 0:
                            print(f"Found login button with selector: {selector}")
                            page.click(selector)
                            print("✓ Clicked login button")
                            
                            # Wait for navigation
                            page.wait_for_load_state("networkidle", timeout=10000)
                            time.sleep(2)
                            break
                    except:
                        continue
                
            except Exception as e:
                print(f"⚠️  Could not click login button: {e}")
        else:
            print("✓ No login required after confirmation")
        
        # Take final screenshot
        page.screenshot(path="/tmp/oauth_step6_final.png")
        print("✓ Screenshot saved: /tmp/oauth_step6_final.png")
        
        # Check for success message
        final_content = page.inner_text('body').lower()
        if "congratulations" in final_content or "you're all set" in final_content or "success" in final_content:
            print("\n🎉 SUCCESS: Authorization completed!")
            print(f"Final page: {page.url}")
        else:
            print("\n⚠️  Status unclear - checking final page content...")
            print(f"Final page: {page.url}")
            print(f"Page title: {page.title()}")
            if "denied" in final_content or "error" in final_content:
                print("❌ Authorization was denied or encountered an error")
            else:
                print(f"Page content preview: {final_content[:300]}...")
        
    except Exception as e:
        print(f"\n❌ ERROR during OAuth flow: {e}")
        import traceback
        traceback.print_exc()
        page.screenshot(path="/tmp/oauth_error.png")
        print("Error screenshot saved: /tmp/oauth_error.png")
    
    finally:
        browser.close()

# Step 6: Poll the API to check authorization status
print("\n🔄 Step 6: Polling API for authorization status...")
max_attempts = 10
for attempt in range(max_attempts):
    print(f"Attempt {attempt + 1}/{max_attempts}...")
    
    poll_response = requests.post(
        f"{API_URL}/api/auth/poll",
        json={"device_code": device_code}
    )
    poll_data = poll_response.json()
    
    print(f"  Status: {poll_data.get('status')}")
    
    if poll_data.get('status') == 'success':
        print("\n✅ OAuth authorization SUCCESSFUL!")
        print(f"Authenticated: {poll_data.get('authenticated')}")
        if poll_data.get('players_count') is not None:
            print(f"Players found: {poll_data.get('players_count')}")
        break
    elif poll_data.get('status') == 'expired':
        print("\n❌ OAuth authorization EXPIRED")
        break
    elif poll_data.get('status') == 'pending':
        print("  Still pending, waiting 5 seconds...")
        time.sleep(5)
    else:
        print(f"  Unknown status: {poll_data}")
        time.sleep(5)
else:
    print("\n⏱️  Timeout: Authorization not completed within polling window")

print("\n✅ OAuth flow test completed!")
