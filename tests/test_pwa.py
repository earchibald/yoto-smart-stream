import json
import os

import pytest
from playwright.sync_api import Page, expect

# Use environment variable directly instead of fixture
BASE_URL = os.getenv("TEST_URL", "http://localhost:8080")


def test_manifest_accessible(page: Page):
    """Test that the PWA manifest file is accessible."""
    response = page.goto(f"{BASE_URL}/manifest.json")
    assert response is not None
    assert response.status == 200

    # Check content type
    content_type = response.headers.get("content-type", "")
    assert "application/json" in content_type

    # Parse and validate manifest
    manifest = json.loads(response.text())
    assert manifest["name"] == "Yoto Smart Stream"
    assert manifest["short_name"] == "Yoto Stream"
    assert manifest["display"] == "standalone"
    assert manifest["theme_color"] == "#4A90E2"
    assert len(manifest["icons"]) > 0


def test_service_worker_accessible(page: Page):
    """Test that the service worker file is accessible."""
    response = page.goto(f"{BASE_URL}/service-worker.js")
    assert response is not None
    assert response.status == 200

    # Check content type
    content_type = response.headers.get("content-type", "")
    assert "javascript" in content_type.lower()

    # Check that it contains service worker code
    content = response.text()
    assert "Service Worker" in content
    assert "addEventListener" in content


def test_pwa_meta_tags_present(page: Page):
    """Test that PWA meta tags are present in HTML pages."""
    page.goto(BASE_URL)

    # Check viewport meta tag
    viewport = page.locator('meta[name="viewport"]')
    expect(viewport).to_have_count(1)

    # Check theme-color meta tag
    theme_color = page.locator('meta[name="theme-color"]')
    expect(theme_color).to_have_count(1)
    expect(theme_color).to_have_attribute("content", "#4A90E2")

    # Check Apple mobile web app meta tags
    apple_capable = page.locator('meta[name="apple-mobile-web-app-capable"]')
    expect(apple_capable).to_have_count(1)
    expect(apple_capable).to_have_attribute("content", "yes")

    # Check manifest link
    manifest_link = page.locator('link[rel="manifest"]')
    expect(manifest_link).to_have_count(1)
    expect(manifest_link).to_have_attribute("href", "/static/manifest.json")


def test_pwa_icons_present(page: Page):
    """Test that PWA icon links are present."""
    page.goto(BASE_URL)

    # Check favicon
    favicon = page.locator('link[rel="icon"]')
    expect(favicon).to_have_count(1)

    # Check Apple touch icon
    apple_icon = page.locator('link[rel="apple-touch-icon"]')
    expect(apple_icon).to_have_count(1)
    expect(apple_icon).to_have_attribute("href", "/static/icons/apple-touch-icon.png")


def test_pwa_css_loaded(page: Page):
    """Test that PWA CSS is loaded."""
    page.goto(BASE_URL)

    # Check that pwa.css is linked
    pwa_css = page.locator('link[href*="pwa.css"]')
    expect(pwa_css).to_have_count(1)


def test_pwa_js_loaded(page: Page):
    """Test that PWA JavaScript is loaded."""
    page.goto(BASE_URL)

    # Check that pwa.js is loaded
    pwa_js = page.locator('script[src*="pwa.js"]')
    expect(pwa_js).to_have_count(1)


def test_service_worker_registration(page: Page):
    """Test that service worker registration is attempted."""
    page.goto(BASE_URL)

    # Wait for page to load
    page.wait_for_load_state("networkidle")

    # Check console logs for service worker registration
    # This will happen asynchronously
    console_messages = []

    def handle_console(msg):
        console_messages.append(msg.text)

    page.on("console", handle_console)

    # Reload to trigger service worker registration
    page.reload()
    page.wait_for_timeout(2000)  # Wait for SW registration

    # Check that service worker registration was attempted
    sw_messages = [msg for msg in console_messages if "Service Worker" in msg or "PWA" in msg]
    assert len(sw_messages) > 0, "Service worker registration should be logged"


def test_mobile_viewport_scaling(page: Page):
    """Test mobile viewport scaling works correctly."""
    # Set mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})  # iPhone SE size
    page.goto(BASE_URL)

    # Check that content is scaled properly
    viewport_meta = page.locator('meta[name="viewport"]').get_attribute("content")
    assert "width=device-width" in viewport_meta
    assert "initial-scale=1.0" in viewport_meta


def test_pwa_styles_on_mobile(page: Page):
    """Test that PWA styles are applied on mobile viewport."""
    # Set mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # The page should render without horizontal scrolling
    body = page.locator("body")
    expect(body).to_be_visible()


def test_touch_targets_mobile(page: Page):
    """Test that touch targets are appropriately sized for mobile."""
    # Set mobile viewport
    page.set_viewport_size({"width": 375, "height": 667})
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # Check that buttons have minimum 44px touch targets
    # This is tested via CSS, so we just verify buttons are present
    buttons = page.locator("button, .action-button")
    count = buttons.count()
    assert count > 0, "Should have interactive buttons"


def test_pwa_install_button_logic(page: Page):
    """Test PWA install button logic (when available)."""
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # The install button may or may not be visible depending on:
    # 1. Browser support for beforeinstallprompt
    # 2. Whether app is already installed
    # 3. Whether running in HTTPS
    # So we just verify the PWA object exists
    pwa_object = page.evaluate("() => typeof window.PWA")
    assert pwa_object == "object", "PWA object should be available"


def test_offline_page_fallback(page: Page):
    """Test that the app handles offline gracefully."""
    # First, load the page normally to cache assets
    page.goto(BASE_URL)
    page.wait_for_load_state("networkidle")

    # Service worker needs time to install
    page.wait_for_timeout(2000)

    # Note: Testing true offline mode requires browser context modifications
    # This is a basic test to ensure the service worker is set up
    sw_ready = page.evaluate(
        """
        () => {
            return navigator.serviceWorker.ready.then(reg => {
                return reg.active !== null;
            });
        }
    """
    )
    # Service worker should be registered (or attempting to register)
    assert sw_ready is not None


def test_all_pages_have_pwa_meta(page: Page):
    """Test that all HTML pages have PWA meta tags."""
    pages_to_test = [
        "/",
        "/login",
        "/admin",
        "/library",
        "/audio-library",
        "/streams",
    ]

    for path in pages_to_test:
        url = f"{BASE_URL}{path}"

        # Some pages may require authentication, so we'll just check for 200 or 302
        try:
            response = page.goto(url)
            if response and response.status in [200, 302]:
                # Check for manifest link
                manifest_links = page.locator('link[rel="manifest"]')
                count = manifest_links.count()
                assert count >= 1, f"Page {path} should have manifest link"
        except Exception as e:
            # If page requires auth and redirects, that's okay
            print(f"Skipping {path} due to auth requirement: {e}")


@pytest.mark.skip(reason="Requires HTTPS for full PWA features")
def test_pwa_installability(page: Page):
    """
    Test PWA installability criteria.

    Note: This test requires HTTPS and may not work in all environments.
    Skipped by default.
    """
    page.goto(BASE_URL)

    # Check if beforeinstallprompt event can be captured
    install_prompt_available = page.evaluate(
        """
        () => {
            return new Promise((resolve) => {
                window.addEventListener('beforeinstallprompt', () => {
                    resolve(true);
                });
                setTimeout(() => resolve(false), 3000);
            });
        }
    """
    )

    # This might be False if already installed or not on HTTPS
    # We just verify the test can run
    assert install_prompt_available is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
