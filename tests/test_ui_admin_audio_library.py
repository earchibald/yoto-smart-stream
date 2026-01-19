"""
Playwright tests for Admin UI and Audio Library pages.

These tests verify:
1. Authentication and navigation
2. Audio Library functionality
3. Admin user management
"""

import os
import re
import pytest
from playwright.sync_api import Page, expect


# Get PR ID from environment or use default
PR_ID = os.getenv("PR_ID", "0")
BASE_URL = f"https://yoto-smart-stream-yoto-smart-stream-pr-{PR_ID}.up.railway.app" if PR_ID != "0" else "http://localhost:8000"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser context with longer timeout."""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
    }


def login(page: Page, username: str = "admin", password: str = "yoto"):
    """Helper function to log in to the application."""
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", username)
    page.fill("input[name='password']", password)
    page.click("button[type='submit']")
    # Wait for navigation to dashboard
    page.wait_for_url(f"{BASE_URL}/", timeout=10000)


def test_login_page(page: Page):
    """Test login page loads and authentication works."""
    page.goto(f"{BASE_URL}/login")
    
    # Check login page elements
    expect(page.locator("h1")).to_contain_text("Yoto Smart Stream")
    expect(page.locator("input[name='username']")).to_be_visible()
    expect(page.locator("input[name='password']")).to_be_visible()
    expect(page.locator("button[type='submit']")).to_contain_text("Sign In")
    
    # Test login with correct credentials
    login(page)
    
    # Should be redirected to dashboard
    expect(page).to_have_url(f"{BASE_URL}/")
    expect(page.locator("h2")).to_contain_text("Dashboard")


def test_navigation_links(page: Page):
    """Test that all navigation links are present and working."""
    login(page)
    
    # Check all navigation links are present
    nav_menu = page.locator(".nav-menu")
    expect(nav_menu.locator("a[href='/']")).to_contain_text("Dashboard")
    expect(nav_menu.locator("a[href='/streams']")).to_contain_text("Smart Streams")
    expect(nav_menu.locator("a[href='/library']")).to_contain_text("Yoto Library")
    expect(nav_menu.locator("a[href='/audio-library']")).to_contain_text("Audio Library")
    expect(nav_menu.locator("a[href='/admin']")).to_contain_text("Admin")
    
    # Verify MQTT Analyzer button is NOT in navigation
    expect(nav_menu.locator("button").filter(has_text="MQTT Analyzer")).not_to_be_visible()
    
    # Test navigation to Audio Library
    page.click("a[href='/audio-library']")
    expect(page).to_have_url(f"{BASE_URL}/audio-library")
    expect(page.locator("h2")).to_contain_text("Audio Library")
    
    # Test navigation to Admin
    page.click("a[href='/admin']")
    expect(page).to_have_url(f"{BASE_URL}/admin")
    expect(page.locator("h2")).to_contain_text("Admin")
    
    # Test navigation back to Dashboard
    page.click("a[href='/']")
    expect(page).to_have_url(f"{BASE_URL}/")
    expect(page.locator("h2")).to_contain_text("Dashboard")


def test_audio_library_page(page: Page):
    """Test Audio Library page elements and TTS form."""
    login(page)
    page.goto(f"{BASE_URL}/audio-library")
    
    # Check page header
    expect(page.locator("h2")).to_contain_text("Audio Library")
    
    # Check Audio Files section exists
    expect(page.locator("h3").filter(has_text="Audio Files")).to_be_visible()
    expect(page.locator("#audio-list")).to_be_visible()
    
    # Check Upload Audio File section
    expect(page.locator("h3").filter(has_text="Upload Audio File")).to_be_visible()
    expect(page.locator("#upload-form")).to_be_visible()
    
    # Check upload form elements
    expect(page.locator("#upload-file")).to_be_visible()
    expect(page.locator("#upload-filename")).to_be_visible()
    expect(page.locator("#upload-description")).to_be_visible()
    expect(page.locator("#upload-submit-btn")).to_be_visible()
    
    # Test upload filename preview updates
    page.fill("#upload-filename", "test-upload")
    expect(page.locator("#upload-filename-preview")).to_contain_text("test-upload.mp3")
    
    # Check TTS Generator section
    expect(page.locator("h3").filter(has_text="Generate Text-to-Speech Audio")).to_be_visible()
    expect(page.locator("#tts-form")).to_be_visible()
    
    # Check TTS form elements
    expect(page.locator("#tts-filename")).to_be_visible()
    expect(page.locator("#tts-text")).to_be_visible()
    expect(page.locator("#tts-submit-btn")).to_be_visible()
    
    # Test filename preview updates
    page.fill("#tts-filename", "test-audio")
    expect(page.locator("#filename-preview")).to_contain_text("test-audio.mp3")
    
    # Test character counter
    page.fill("#tts-text", "Hello World")
    expect(page.locator("#text-length")).to_contain_text("11 characters")


def test_audio_upload_form_validation(page: Page):
    """Test audio upload form validation."""
    login(page)
    page.goto(f"{BASE_URL}/audio-library")
    
    # Try to submit empty form
    page.click("#upload-submit-btn")
    
    # HTML5 validation should prevent submission
    expect(page.locator("#upload-form")).to_be_visible()
    
    # Fill in filename but not file
    page.fill("#upload-filename", "testfile")
    page.click("#upload-submit-btn")
    
    # Should still be on the form (file required)
    expect(page.locator("#upload-form")).to_be_visible()


def test_admin_page_access(page: Page):
    """Test Admin page access for admin user."""
    """Test Admin page access for admin user."""
    login(page)
    page.goto(f"{BASE_URL}/admin")
    
    # Check page header
    expect(page.locator("h2")).to_contain_text("Admin")
    
    # Check admin content is visible (not access denied)
    expect(page.locator("#admin-content")).to_be_visible()
    expect(page.locator("#access-denied")).not_to_be_visible()
    
    # Check System Administration section
    expect(page.locator("h3").filter(has_text="System Administration")).to_be_visible()
    expect(page.locator("button").filter(has_text="Refresh Data")).to_be_visible()
    
    # Check MQTT Analyzer button is in Admin page
    expect(page.locator("button").filter(has_text="MQTT Analyzer")).to_be_visible()
    
    # Check User Management section
    expect(page.locator("h3").filter(has_text="User Management")).to_be_visible()
    expect(page.locator("#users-list")).to_be_visible()
    
    # Check Create User Form
    expect(page.locator("#create-user-form")).to_be_visible()
    expect(page.locator("#username")).to_be_visible()
    expect(page.locator("#password")).to_be_visible()
    expect(page.locator("#email")).to_be_visible()
    expect(page.locator("#create-user-btn")).to_be_visible()


def test_admin_user_list(page: Page):
    """Test that admin can see user list."""
    login(page)
    page.goto(f"{BASE_URL}/admin")
    
    # Wait for users list to load
    page.wait_for_selector("#users-list .list-item", timeout=10000)
    
    # Check that at least the admin user is visible
    users_list = page.locator("#users-list")
    expect(users_list.locator(".list-item")).to_have_count(1)  # At least admin user
    
    # Check admin user is marked as admin
    admin_item = users_list.locator(".list-item").first
    expect(admin_item).to_contain_text("admin")
    expect(admin_item).to_contain_text("Admin")


def test_create_user_form_validation(page: Page):
    """Test create user form validation."""
    login(page)
    page.goto(f"{BASE_URL}/admin")
    
    # Try to submit empty form
    page.click("#create-user-btn")
    
    # HTML5 validation should prevent submission
    expect(page.locator("#create-user-form")).to_be_visible()
    
    # Fill in username but not password
    page.fill("#username", "testuser")
    page.click("#create-user-btn")
    
    # Should still be on the form
    expect(page.locator("#create-user-form")).to_be_visible()


def test_dashboard_no_audio_library(page: Page):
    """Test that Dashboard no longer has Audio Library section."""
    login(page)
    page.goto(f"{BASE_URL}/")
    
    # Check that Audio Library section is NOT present
    expect(page.locator("h3").filter(has_text="Audio Library")).not_to_be_visible()
    
    # Check that Quick Actions no longer has TTS button
    quick_actions = page.locator(".section").filter(has_text="Quick Actions")
    expect(quick_actions).to_be_visible()
    expect(quick_actions.locator("button").filter(has_text="Generate TTS")).not_to_be_visible()
    
    # Check that API Documentation link is removed
    expect(quick_actions.locator("a[href='/api/docs']")).not_to_be_visible()
    
    # Check that View Streams link is removed
    expect(quick_actions.locator("a[href='/streams']")).not_to_be_visible()


def test_tooltips_present(page: Page):
    """Test that tooltips are present on relevant elements."""
    login(page)
    
    # Test Admin page tooltips
    page.goto(f"{BASE_URL}/admin")
    expect(page.locator("button[title*='Refresh']")).to_be_visible()
    expect(page.locator("input#username[title]")).to_be_visible()
    expect(page.locator("input#password[title]")).to_be_visible()
    
    # Test Audio Library page tooltips
    page.goto(f"{BASE_URL}/audio-library")
    expect(page.locator("label[title]")).to_have_count(2)  # Filename and Text labels


def test_admin_user_edit_button(page: Page):
    """Test that edit button appears for users and opens modal."""
    login(page)
    page.goto(f"{BASE_URL}/admin")
    
    # Wait for users list to load
    page.wait_for_selector("#users-list .list-item", timeout=10000)
    
    # Check that edit button exists
    expect(page.locator(".edit-user-btn").first).to_be_visible()
    
    # Click edit button
    page.locator(".edit-user-btn").first.click()
    
    # Check modal opens
    expect(page.locator("#edit-user-modal")).to_be_visible()
    expect(page.locator("#edit-username")).to_be_visible()
    expect(page.locator("#edit-email")).to_be_visible()
    expect(page.locator("#edit-password")).to_be_visible()


def test_keyboard_shortcut_library(page: Page):
    """Test that '/' key focuses the filter input in Yoto Library."""
    login(page)
    page.goto(f"{BASE_URL}/library")
    
    # Wait for page to load
    page.wait_for_timeout(1000)
    
    # Press '/' key
    page.keyboard.press("/")
    
    # Check that filter input is focused (either cards or playlists)
    cards_filter = page.locator("#cards-filter")
    playlists_filter = page.locator("#playlists-filter")
    
    # At least one should be focused
    is_focused = cards_filter.is_focused() or playlists_filter.is_focused()
    assert is_focused, "Neither filter input is focused after pressing '/'"


def test_static_audio_badges(page: Page):
    """Test that static audio files (1.mp3-10.mp3) have badges."""
    login(page)
    page.goto(f"{BASE_URL}/audio-library")
    
    # Wait for audio list to load
    page.wait_for_selector("#audio-list", timeout=10000)
    
    # Check for static badges
    static_badges = page.locator(".badge").filter(has_text="Static")
    
    # Should have at least one static file badge
    expect(static_badges.first).to_be_visible()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
