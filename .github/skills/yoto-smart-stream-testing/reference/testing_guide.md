# Comprehensive Automated Functional Testing Guide

## Overview

This guide provides a systematic approach to automated functional testing for Yoto API applications, including best practices, patterns, and guardrails for maintaining a repeatable test-and-fix loop.

## Testing Philosophy

### Core Principles

1. **Test What Matters**: Focus on API interactions, MQTT events, and business logic
2. **Fast Feedback**: Unit tests run in seconds, integration tests in minutes
3. **Reliable**: Tests should be deterministic and reproducible
4. **Maintainable**: Clear naming, minimal mocking, well-structured
5. **Automated**: Run tests on every commit via CI/CD

### Test Pyramid

```
        ┌─────────────┐
        │   E2E Tests │  ← 5-10% (Real devices, full flow)
        └─────────────┘
      ┌─────────────────┐
      │ Integration Tests│  ← 20-30% (API calls, MQTT)
      └─────────────────┘
    ┌───────────────────────┐
    │     Unit Tests        │  ← 60-75% (Business logic)
    └───────────────────────┘
```

## Test Structure

### Directory Layout

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests (no external dependencies)
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_audio_manager.py
│   └── test_script_engine.py
├── integration/             # Integration tests (API/MQTT)
│   ├── __init__.py
│   ├── test_yoto_api.py
│   ├── test_mqtt_events.py
│   └── test_icon_management.py
├── functional/              # End-to-end functional tests
│   ├── __init__.py
│   ├── test_card_playback.py
│   └── test_interactive_cards.py
└── fixtures/                # Test data
    ├── sample_audio.mp3
    ├── sample_icon.png
    └── mock_responses.json
```

## Unit Tests

### Purpose
Test individual functions and classes in isolation without external dependencies.

### Example: Testing Audio Manager

```python
# tests/unit/test_audio_manager.py
import pytest
from pathlib import Path
from yoto_smart_stream.core.audio_manager import AudioManager, AudioValidationError

@pytest.fixture
def audio_manager(tmp_path):
    """Fixture providing AudioManager with temp directory"""
    return AudioManager(storage_path=tmp_path)

@pytest.fixture
def sample_audio_file(tmp_path):
    """Fixture providing a sample audio file"""
    audio_path = tmp_path / "test_audio.mp3"
    # Create a minimal valid MP3 file
    audio_path.write_bytes(b'ID3\\x04\\x00\\x00\\x00\\x00\\x00\\x00')
    return audio_path

class TestAudioManager:
    """Test suite for AudioManager"""
    
    def test_validate_audio_format_valid(self, audio_manager, sample_audio_file):
        """Test audio validation accepts valid MP3 files"""
        result = audio_manager.validate_audio(sample_audio_file)
        assert result.is_valid is True
        assert result.format == "mp3"
    
    def test_validate_audio_format_invalid(self, audio_manager, tmp_path):
        """Test audio validation rejects invalid formats"""
        invalid_file = tmp_path / "test.txt"
        invalid_file.write_text("not an audio file")
        
        with pytest.raises(AudioValidationError) as exc:
            audio_manager.validate_audio(invalid_file)
        assert "Invalid audio format" in str(exc.value)
    
    @pytest.mark.asyncio
    async def test_convert_audio_to_mp3(self, audio_manager, sample_audio_file):
        """Test audio conversion to MP3 format"""
        output_path = await audio_manager.convert_to_mp3(
            sample_audio_file,
            bitrate="192k"
        )
        
        assert output_path.exists()
        assert output_path.suffix == ".mp3"
```

### Best Practices for Unit Tests

1. **One Assertion Per Test** (when practical) - Makes failures clear
2. **Use Descriptive Names** - `test_validate_audio_rejects_files_over_500mb`
3. **Arrange-Act-Assert Pattern** - Clear test structure
4. **Parameterize Similar Tests** - Use `@pytest.mark.parametrize`

## Integration Tests

### Purpose
Test interactions with external systems (Yoto API, MQTT) using mocks or test environments.

### Example: Testing Yoto API Client

```python
# tests/integration/test_yoto_api.py
import pytest
from unittest.mock import AsyncMock, patch
from yoto_smart_stream.core.yoto_client import YotoClient

@pytest.mark.asyncio
async def test_get_players_success(mock_httpx_client):
    """Test getting player list from API"""
    # Arrange
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "devices": [{"deviceId": "player-123", "name": "Test Player"}]
    }
    mock_httpx_client.get.return_value = mock_response
    
    client = YotoClient(client_id="test", access_token="token")
    
    # Act
    players = await client.get_players()
    
    # Assert
    assert len(players) == 1
    assert players[0].id == "player-123"
```

### MQTT Integration Testing

```python
# tests/integration/test_mqtt_events.py
import pytest
from unittest.mock import MagicMock
from yoto_smart_stream.core.mqtt_handler import MQTTEventHandler

def test_handle_playback_event(mqtt_handler):
    """Test handling of playback status event"""
    # Arrange
    event_received = False
    captured_event = {}
    
    def callback(event):
        nonlocal event_received
        captured_event.update(event)
        event_received = True
    
    mqtt_handler.on_playback_event(callback)
    
    # Act
    mock_message = MagicMock()
    mock_message.topic = "device/player-123/events"
    mock_message.payload = b'{"playbackStatus": "playing"}'
    mqtt_handler._on_message(None, None, mock_message)
    
    # Assert
    assert event_received
    assert captured_event["playbackStatus"] == "playing"
```

## Functional/E2E Tests

### Purpose
Test complete user workflows from end to end.

### Example: Card Playback Flow

```python
# tests/functional/test_card_playback.py
import pytest
from yoto_smart_stream import YotoApp

@pytest.mark.functional
@pytest.mark.asyncio
async def test_complete_card_playback_flow():
    """Test complete flow: upload audio, create card, play on device"""
    app = YotoApp(client_id=pytest.test_client_id)
    
    try:
        # Upload audio
        audio_id = await app.upload_audio("tests/fixtures/sample_audio.mp3")
        assert audio_id is not None
        
        # Create card
        card = await app.create_card(
            title="Test Card",
            tracks=[{"audio_id": audio_id, "title": "Track 1"}]
        )
        
        # Play on device
        await app.play_card(pytest.test_player_id, card.id)
        
        # Verify playback started
        player_status = await app.get_player_status(pytest.test_player_id)
        assert player_status.active_card == card.id
        
    finally:
        if card:
            await app.delete_card(card.id)
```

## Test Fixtures and Utilities

### Shared Fixtures (conftest.py)

```python
# tests/conftest.py
import pytest
import os

def pytest_configure(config):
    """Configure pytest with test credentials"""
    pytest.test_client_id = os.getenv("YOTO_TEST_CLIENT_ID")
    pytest.test_refresh_token = os.getenv("YOTO_TEST_REFRESH_TOKEN")
    pytest.test_player_id = os.getenv("YOTO_TEST_PLAYER_ID")

@pytest.fixture
def sample_audio_file():
    """Provide path to sample audio file"""
    return Path(__file__).parent / "fixtures" / "sample_audio.mp3"

@pytest.fixture
async def authenticated_client():
    """Provide authenticated Yoto client for integration tests"""
    if not pytest.test_client_id:
        pytest.skip("Test credentials not available")
    
    client = YotoClient(
        client_id=pytest.test_client_id,
        refresh_token=pytest.test_refresh_token
    )
    await client.authenticate()
    
    yield client
    
    await client.close()
```

## Test Execution

### Running Tests

```bash
# Run all tests
pytest

# Run specific test types
pytest tests/unit                    # Unit tests only
pytest tests/integration            # Integration tests only
pytest tests/functional             # Functional tests only

# Run with coverage
pytest --cov=yoto_smart_stream --cov-report=html

# Run with markers
pytest -m "not slow"                # Skip slow tests
pytest -m "functional"              # Only functional tests

# Verbose output
pytest -v

# Stop on first failure
pytest -x

# Run failed tests from last run
pytest --lf
```

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt
      
      - name: Run linters
        run: |
          black --check .
          ruff check .
      
      - name: Run unit tests
        run: |
          pytest tests/unit -v --cov=yoto_smart_stream
      
      - name: Run integration tests
        run: |
          pytest tests/integration -v
```

## Test-and-Fix Loop

### Development Workflow

1. **Write Failing Test First** (TDD approach)
2. **Run Test** - Should fail
3. **Implement Minimum Code** to pass
4. **Run Test Again** - Should pass
5. **Refactor if Needed** - Keep tests passing
6. **Run Full Test Suite** - Ensure no regressions

### Debugging Failed Tests

```bash
# Run with debugging on failure
pytest --pdb

# Run with print statements visible
pytest -s

# Run with detailed output
pytest -vv
```

## Testing Guardrails

### Code Coverage Requirements

- **Minimum**: 70% overall coverage
- **Target**: 80%+ for core business logic
- **Unit Tests**: Should cover >90% of non-I/O code

### Test Quality Checks

1. **Tests Must Be Fast**
   - Unit tests: <100ms each
   - Integration tests: <5s each
   - Functional tests: <30s each

2. **Tests Must Be Isolated**
   - No dependencies between tests
   - Can run in any order
   - Clean up resources

3. **Tests Must Be Reliable**
   - No flaky tests
   - Deterministic results
   - Proper timeouts

4. **Tests Must Be Maintainable**
   - Clear names
   - Single responsibility
   - Minimal complexity

## Common Testing Patterns

### Testing Async Code

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

### Testing Exceptions

```python
def test_raises_exception():
    with pytest.raises(ValueError) as exc_info:
        function_that_raises()
    assert "error message" in str(exc_info.value)
```

### Parameterized Tests

```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_doubles_number(input, expected):
    assert double(input) == expected
```

### Testing with Temporary Files

```python
def test_file_operations(tmp_path):
    # tmp_path is a pytest fixture providing temporary directory
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    
    result = process_file(test_file)
    assert result is not None
```

## Summary

### Quick Reference

**Run Tests**:
```bash
pytest                          # All tests
pytest tests/unit              # Unit tests only
pytest -v --cov               # With coverage
pytest -m "not slow"          # Skip slow tests
```

**Test Structure**:
- Unit tests: `tests/unit/test_*.py`
- Integration tests: `tests/integration/test_*.py`
- Functional tests: `tests/functional/test_*.py`

**Key Practices**:
- Write tests first (TDD)
- Keep tests fast and isolated
- Mock external dependencies
- Aim for >70% coverage
- Use descriptive test names
- Clean up resources

**Guardrails**:
- Pre-commit hooks run quick tests
- CI runs full test suite
- Coverage reports track quality
- Failed tests block merges
