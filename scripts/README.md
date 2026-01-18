# Yoto Smart Stream Scripts

This directory contains utility scripts for testing and managing the Yoto Smart Stream service.

## Test Card Creation (`test_card_creation.py`)

A Python testing utility to test card creation and deletion functionality.

### Features

- Authenticates to the yoto-smart-stream server
- Creates a simple 1-chapter, 1-track streaming card with external audio URL
- Validates the card was created successfully and appears in the library
- Provides a detailed summary of results
- Optionally cleans up (deletes) the created card

### Prerequisites

```bash
# Create and activate virtual environment
python3 -m venv cdk_venv
source cdk_venv/bin/activate

# Install dependencies
pip install requests
```

### Usage

```bash
# Basic usage (uses defaults)
python scripts/test_card_creation.py

# With custom server URL
python scripts/test_card_creation.py --base-url https://your-server.com

# Skip cleanup (keep the card after testing)
python scripts/test_card_creation.py --no-delete

# Custom title
python scripts/test_card_creation.py --title "My Test Card"

# Full example
python scripts/test_card_creation.py \
  --base-url https://your-server.com \
  --username admin \
  --password yoto \
  --title "Integration Test Card" \
  --no-delete
```

### Options

- `--base-url`: Server base URL (default: `http://localhost:8000`)
- `--username`: Server username (default: `admin`)
- `--password`: Server password (default: `yoto`)
- `--no-delete`: Skip cleanup - don't delete the created card
- `--title`: Card title (default: `Test Card Creation`)

### Environment Variables

The script respects the following environment variables:

- `SERVER_API_BASE_URL`: Default server URL
- `YOTO_API_USERNAME`: Default username
- `YOTO_API_PASSWORD`: Default password

### Sample Output

```
============================================================
YOTO SMART STREAM - CARD CREATION TEST
============================================================
Server: https://your-server.com
User:   admin
✅ Authenticated as admin

📝 Creating card: 'Test Card Creation'
   Audio URL: https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3
✅ Card created successfully!
   Card ID: abc123
   Content ID: xyz789

🔍 Validating card in library...
✅ Card found in library!
   Title: Test Card Creation
   ID: abc123
   Content ID: xyz789

🗑️  Cleaning up...
✅ Card deleted successfully

============================================================
TEST SUMMARY
============================================================
Card Title:      Test Card Creation
Card ID:         abc123
Content ID:      xyz789
Streaming URL:   https://file-examples.com/wp-content/storage/2017/11/file_example_MP3_700KB.mp3
Creation:        ✅ Success
Validation:      ✅ Found in library
Cleanup:         ✅ Deleted
============================================================
```

## Other Scripts

### `delete_llm_test_cards.py`

Delete library entries containing a match string using the server API.

### `submit_interactive_card.py`

Submit interactive card payloads to the Yoto API for testing.

### `test_deployment_setup.py`

Verify deployment configuration and requirements.
