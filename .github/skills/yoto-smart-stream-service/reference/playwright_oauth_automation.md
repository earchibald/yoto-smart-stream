# Playwright OAuth Automation for Yoto API

This document describes the automated OAuth flow testing using Playwright for the Yoto Smart Stream service.

## Overview

The Yoto OAuth device flow requires manual authorization on the Yoto website. This can be automated using Playwright for testing and CI/CD purposes.

## OAuth Flow Steps

1. **Start Device Flow**: Call `/api/auth/start` to get device_code and verification_uri_complete
2. **Navigate to Verification URL**: Open the URL in browser (e.g., `https://login.yotoplay.com/activate?user_code=XXXX-XXXX`)
3. **Click Confirm**: On the device confirmation page, click the "Confirm" button
4. **Login** (if required): After clicking Confirm, you'll be redirected to login page
5. **Authorization Success**: After login, you're redirected to success page
6. **Poll API**: Backend polls `/api/auth/poll` with device_code to complete OAuth

## Automated Test Script

See `/tmp/test_oauth_flow.py` for the complete working script.

### Key Selectors

```python
# Device Confirmation Page
confirm_button = page.locator('button:has-text("Confirm")')

# Login Page (appears after clicking Confirm)
username_input = page.locator('input[type="text"]').first  # Username, not email!
password_input = page.locator('input[type="password"]').first
login_button = page.locator('button:has-text("log in")').first  # Lowercase!
```

## Key Points

### Device Confirmation Page
- Page shows user code (e.g., "QPHH-HVXQ")
- Has two buttons: "Cancel" and "Confirm"
- No login required at this stage
- Click "Confirm" to proceed

### Login Page
- Appears AFTER clicking Confirm
- **Important**: Yoto uses `username` field, not `email` type
- Use `input[type="text"]` selector for username
- Use `input[type="password"]` for password
- Login button text is "log in" (lowercase)

### Success Page
- URL: `https://login.yotoplay.com/device/success`
- May show "Congratulations, you're all set!" or similar message

### Backend Polling
- Frontend or test script polls `/api/auth/poll` with device_code
- Returns status: "pending", "success", "expired", or "error"
- Poll every 5 seconds
- Timeout after 10 attempts (50 seconds)

## Common Issues

### Read-only File System Error
```
[Errno 30] Read-only file system: '.yoto_refresh_token'
```

**Fix**: Update `config.py` to use `/tmp` directory on Lambda:
```python
elif lambda_env:
    # On Lambda, use /tmp (ephemeral but writable)
    tmp_dir = Path("/tmp")
    return tmp_dir / ".yoto_refresh_token"
```

### Wrong Button Clicked
- Make sure to click "Confirm" button, not "Cancel"
- Use `button:has-text("Confirm")` selector
- Check button text before clicking to avoid Cancel

### Login Not Detected
- Check for "log in" or "login" in page text (case-insensitive)
- Wait for page to load fully after clicking Confirm
- Use `page.wait_for_load_state("networkidle")` before checking

## Testing Locally

```bash
# Install dependencies
pip install playwright requests
playwright install chromium

# Set environment variables
export YOTO_USERNAME="your_username@example.com"
export YOTO_PASSWORD="your_password"

# Run test
python3 /tmp/test_oauth_flow.py
```

## Screenshots

The script saves screenshots at each step:
- `/tmp/oauth_step1.png` - Initial page load
- `/tmp/oauth_step2_after_check.png` - After page state check
- `/tmp/oauth_step4_after_confirm.png` - After clicking Confirm
- `/tmp/oauth_step5_login_filled.png` - Login form filled
- `/tmp/oauth_step6_final.png` - Final page after login
- `/tmp/oauth_error.png` - Error screenshot (if any)

## Integration with CI/CD

Store YOTO_USERNAME and YOTO_PASSWORD as GitHub Secrets and use in workflows:

```yaml
- name: Test OAuth Flow
  env:
    YOTO_USERNAME: ${{ secrets.YOTO_USERNAME }}
    YOTO_PASSWORD: ${{ secrets.YOTO_PASSWORD }}
  run: python3 test_oauth_flow.py
```
