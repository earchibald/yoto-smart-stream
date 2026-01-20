---
name: yoto-smart-stream-testing
description: Comprehensive testing guide for Yoto Smart Stream - covering authentication testing, functional testing, Playwright UI automation, and test-and-fix development loops. Use when writing tests, debugging test failures, or implementing test coverage.
---

# Yoto Smart Stream Testing

Comprehensive testing guide covering authentication testing, functional testing patterns, Playwright UI automation, and iterative test-and-fix development loops.

## Overview

Testing strategy for Yoto Smart Stream focuses on:

1. **Authentication Testing** - Verifying login flows, session management, and OAuth integration
2. **Functional Testing** - API endpoints, business logic, and integration testing
3. **Playwright Testing** - UI automation for login workflows and end-to-end scenarios
4. **Test-and-Fix Loops** - Iterative development with automated validation

### Test Philosophy

- **Test First**: Write tests before implementing features (TDD)
- **Fast Feedback**: Tests should run quickly and provide clear error messages
- **Real Scenarios**: Tests should mirror actual user workflows
- **Automated**: All tests should run in CI/CD without manual intervention
- **Maintainable**: Tests should be easy to understand and update

## Quick Start

### Prerequisites

```bash
# Install development dependencies
pip install -e ".[dev]"

# Verify pytest is installed
pytest --version

# Verify Playwright is installed (for UI tests)
playwright --version
```

### Run All Tests

```bash
# Run all tests with coverage
pytest --cov=yoto_smart_stream --cov-report=html

# Run specific test categories
pytest tests/test_auth.py          # Authentication tests
pytest tests/test_api.py           # API endpoint tests
pytest tests/test_login_flows.py   # Playwright UI tests

# Run with verbose output
pytest -v

# Run with output capture disabled (see print statements)
pytest -s
```

### Basic Test Structure

```python
import pytest
from fastapi.testclient import TestClient
from yoto_smart_stream.api.app import app

@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)

def test_health_endpoint(client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_login_success(client):
    """Test successful login."""
    response = client.post("/api/user/login", json={
        "username": "admin",
        "password": "yoto"
    })
    assert response.status_code == 200
    assert "access_token" in response.json()
```

## Reference Documentation

For detailed testing information, refer to:

- [📋 Testing Guide](../../docs/TESTING_GUIDE.md) - Complete testing guide with unit tests, integration tests, and manual testing procedures
- [🔐 Login Workflows](../../docs/LOGIN_WORKFLOWS.md) - Detailed documentation of authentication flows and Playwright UI testing patterns

## Common Testing Patterns

### 1. Resolving Service URL

**Pattern**: Determine the correct service URL for testing

```python
import os
import subprocess

def get_service_url():
    """Get service URL from environment or Railway CLI."""
    # Try environment variable first
    url = os.getenv("SERVICE_URL")
    if url:
        return url
    
    # Try Railway CLI
    try:
        result = subprocess.run(
            ["railway", "domain"],
            capture_output=True,
            text=True,
            check=True
        )
        domain = result.stdout.strip()
        return f"https://{domain}"
    except Exception:
        pass
    
    # Fall back to pattern
    env = os.getenv("RAILWAY_ENVIRONMENT", "develop")
    return f"https://yoto-smart-stream-{env}.up.railway.app"

# Use in tests
@pytest.fixture
def service_url():
    return get_service_url()

def test_service_health(service_url):
    response = requests.get(f"{service_url}/api/health")
    assert response.status_code == 200
```

### 2. UI Login (Playwright)

**Pattern**: Automate browser login for UI testing

```python
import pytest
from playwright.sync_api import Page, expect

@pytest.fixture(scope="session")
def service_url():
    """Get service URL for testing."""
    return os.getenv("SERVICE_URL", "https://yoto-smart-stream-develop.up.railway.app")

def test_ui_login(page: Page, service_url: str):
    """Test login via UI."""
    # Navigate to login page
    page.goto(service_url)
    
    # Should redirect to login
    expect(page).to_have_url(f"{service_url}/login")
    
    # Fill login form
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "yoto")
    page.click('button[type="submit"]')
    
    # Should redirect to dashboard
    expect(page).to_have_url(f"{service_url}/")
    expect(page.locator("h1")).to_contain_text("Dashboard")

def test_oauth_button_visible(page: Page, service_url: str):
    """Test OAuth connect button appears after login."""
    # Login first
    page.goto(f"{service_url}/login")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "yoto")
    page.click('button[type="submit"]')
    
    # Check OAuth button
    oauth_button = page.locator('button:has-text("Connect Yoto Account")')
    expect(oauth_button).to_be_visible()
```

### 3. API Login (Programmatic)

**Pattern**: Get JWT token for API testing

```python
import requests

@pytest.fixture
def auth_token(service_url):
    """Get authentication token for API tests."""
    response = requests.post(
        f"{service_url}/api/user/login",
        json={"username": "admin", "password": "yoto"}
    )
    assert response.status_code == 200
    return response.json()["access_token"]

def test_authenticated_endpoint(service_url, auth_token):
    """Test endpoint requiring authentication."""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = requests.get(
        f"{service_url}/api/players",
        headers=headers
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### 4. Hybrid Testing (UI + API)

**Pattern**: Combine UI and API testing for complex scenarios

```python
def test_complete_user_journey(page: Page, service_url: str):
    """Test complete user journey from login to playing audio."""
    # 1. Login via UI
    page.goto(f"{service_url}/login")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "yoto")
    page.click('button[type="submit"]')
    
    # 2. Extract auth cookie/token from browser
    cookies = page.context.cookies()
    auth_cookie = next(c for c in cookies if c["name"] == "session")
    
    # 3. Use API to create content
    headers = {"Cookie": f"session={auth_cookie['value']}"}
    response = requests.post(
        f"{service_url}/api/cards",
        headers=headers,
        json={"title": "Test Card", "content": {...}}
    )
    assert response.status_code == 201
    card_id = response.json()["id"]
    
    # 4. Verify card appears in UI
    page.goto(f"{service_url}/library")
    expect(page.locator(f'[data-card-id="{card_id}"]')).to_be_visible()
```

### 5. Fixture-Based Testing

**Pattern**: Reusable test fixtures for common setups

```python
import pytest
from playwright.sync_api import Page

@pytest.fixture
def logged_in_page(page: Page, service_url: str):
    """Fixture providing a logged-in browser page."""
    page.goto(f"{service_url}/login")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "yoto")
    page.click('button[type="submit"]')
    expect(page).to_have_url(f"{service_url}/")
    return page

@pytest.fixture
def api_client(service_url: str):
    """Fixture providing authenticated API client."""
    response = requests.post(
        f"{service_url}/api/user/login",
        json={"username": "admin", "password": "yoto"}
    )
    token = response.json()["access_token"]
    
    class AuthClient:
        def __init__(self, base_url, token):
            self.base_url = base_url
            self.headers = {"Authorization": f"Bearer {token}"}
        
        def get(self, path):
            return requests.get(f"{self.base_url}{path}", headers=self.headers)
        
        def post(self, path, json):
            return requests.post(f"{self.base_url}{path}", headers=self.headers, json=json)
    
    return AuthClient(service_url, token)

# Use fixtures in tests
def test_dashboard_loads(logged_in_page: Page):
    """Test dashboard loads after login."""
    expect(logged_in_page.locator("h1")).to_contain_text("Dashboard")

def test_api_players_list(api_client):
    """Test listing players via API."""
    response = api_client.get("/api/players")
    assert response.status_code == 200
```

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── test_auth.py             # Authentication tests
├── test_api_endpoints.py    # API endpoint tests
├── test_login_flows.py      # Playwright UI tests
├── test_audio.py            # Audio management tests
├── test_cards.py            # MYO card tests
├── test_users.py            # User management tests
├── test_oauth.py            # OAuth flow tests
├── integration/             # Integration tests
│   ├── test_complete_flows.py
│   └── test_player_control.py
└── fixtures/                # Test data
    ├── sample_audio.mp3
    └── sample_icon.png
```

### Test Categories

**Unit Tests** (`test_*.py` in root):
- Fast execution
- Isolated components
- Mocked dependencies
- High coverage target (>80%)

**Integration Tests** (`integration/`):
- Test component interactions
- Use real dependencies where possible
- Slower but more realistic
- Coverage target (>60%)

**UI Tests** (`test_login_flows.py`, `test_ui_*.py`):
- Playwright browser automation
- Real user workflows
- Slower execution
- Focus on critical paths

### Test Pyramid

```
     /\
    /UI\         ← Few (critical workflows)
   /────\
  /INTEG\        ← Some (component interactions)
 /──────\
/  UNIT  \       ← Many (isolated components)
──────────
```

## Best Practices

### 1. Test Naming

```python
# Good: Descriptive test names
def test_login_with_valid_credentials_returns_token():
    ...

def test_login_with_invalid_password_returns_401():
    ...

# Bad: Vague test names
def test_login():
    ...

def test_case_1():
    ...
```

### 2. Arrange-Act-Assert

```python
def test_create_user():
    # Arrange: Setup test data
    user_data = {
        "username": "testuser",
        "password": "testpass",
        "role": "user"
    }
    
    # Act: Execute the action
    response = client.post("/api/admin/users", json=user_data)
    
    # Assert: Verify the results
    assert response.status_code == 201
    assert response.json()["username"] == "testuser"
    assert response.json()["role"] == "user"
```

### 3. Test Isolation

```python
# Good: Each test is independent
@pytest.fixture
def clean_database():
    db.clear()
    yield
    db.clear()

def test_create_user(clean_database):
    # Test creates user in clean database
    ...

def test_list_users(clean_database):
    # Test lists users in clean database
    ...

# Bad: Tests depend on each other
def test_create_user():
    global user_id
    user_id = create_user()

def test_delete_user():
    delete_user(user_id)  # Depends on previous test
```

### 4. Clear Error Messages

```python
# Good: Descriptive assertions
def test_player_status():
    response = client.get("/api/players/123")
    assert response.status_code == 200, \
        f"Expected 200 but got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    assert "online" in data, \
        f"'online' field missing from response. Got: {list(data.keys())}"

# Bad: Bare assertions
def test_player_status():
    response = client.get("/api/players/123")
    assert response.status_code == 200
    assert "online" in response.json()
```

### 5. Fixtures Over Setup/Teardown

```python
# Good: Use fixtures
@pytest.fixture
def test_user(client):
    response = client.post("/api/admin/users", json={
        "username": "testuser",
        "password": "testpass"
    })
    user_id = response.json()["id"]
    yield user_id
    client.delete(f"/api/admin/users/{user_id}")

def test_with_user(client, test_user):
    # User automatically created and cleaned up
    ...

# Bad: Manual setup/teardown
def test_with_user(client):
    # Setup
    response = client.post("/api/admin/users", ...)
    user_id = response.json()["id"]
    
    try:
        # Test
        ...
    finally:
        # Teardown
        client.delete(f"/api/admin/users/{user_id}")
```

## Running Tests

### Local Development

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_auth.py

# Run specific test
pytest tests/test_auth.py::test_login_success

# Run tests matching pattern
pytest -k "login"

# Run with coverage
pytest --cov=yoto_smart_stream --cov-report=html

# Run and stop on first failure
pytest -x

# Run with verbose output
pytest -v

# Run with print statements visible
pytest -s

# Run in parallel (requires pytest-xdist)
pytest -n auto
```

### Playwright Tests

```bash
# Run Playwright tests
pytest tests/test_login_flows.py

# Run in headed mode (see browser)
pytest tests/test_login_flows.py --headed

# Run specific browser
pytest tests/test_login_flows.py --browser chromium
pytest tests/test_login_flows.py --browser firefox
pytest tests/test_login_flows.py --browser webkit

# Debug mode (opens Playwright Inspector)
PWDEBUG=1 pytest tests/test_login_flows.py

# Generate trace for debugging
pytest tests/test_login_flows.py --tracing on
```

### CI/CD Testing

```bash
# Run in CI mode (non-interactive)
pytest --tb=short --maxfail=3

# Generate JUnit XML for CI reporting
pytest --junitxml=test-results.xml

# Generate coverage reports for CI
pytest --cov=yoto_smart_stream --cov-report=xml --cov-report=term

# Run with environment-specific config
SERVICE_URL=https://yoto-smart-stream-pr-61.up.railway.app pytest
```

## Troubleshooting

### Tests Failing Locally

**Symptom:** Tests pass in CI but fail locally (or vice versa)

**Common Causes:**

1. **Environment Variables:**
   ```bash
   # Check required environment variables
   echo $SERVICE_URL
   echo $YOTO_CLIENT_ID
   
   # Set for testing
   export SERVICE_URL=https://yoto-smart-stream-develop.up.railway.app
   ```

2. **Database State:**
   ```bash
   # Clear test database
   rm -f test_database.db
   
   # Or use fixture to ensure clean state
   @pytest.fixture(autouse=True)
   def clean_db():
       db.clear()
       yield
       db.clear()
   ```

3. **Network Issues:**
   ```bash
   # Test connectivity
   curl https://yoto-smart-stream-develop.up.railway.app/api/health
   
   # Check if service is running
   railway status
   ```

### Playwright Tests Timing Out

**Symptom:** Playwright tests hang or timeout

**Solutions:**

1. **Increase Timeout:**
   ```python
   @pytest.fixture(scope="session")
   def browser_context_args(browser_context_args):
       return {
           **browser_context_args,
           "timeout": 30000  # 30 seconds
       }
   ```

2. **Wait for Elements:**
   ```python
   # Bad: No wait
   page.click("button")
   
   # Good: Wait for element
   page.wait_for_selector("button", state="visible")
   page.click("button")
   ```

3. **Debug with Traces:**
   ```bash
   # Generate trace
   pytest tests/test_login_flows.py --tracing on
   
   # View trace
   playwright show-trace test-results/trace.zip
   ```

### OAuth Tests Failing

**Symptom:** Tests requiring OAuth fail with "Not authenticated"

**Solutions:**

1. **Mock OAuth in Tests:**
   ```python
   @pytest.fixture
   def mock_oauth(monkeypatch):
       """Mock OAuth for testing."""
       def mock_get_players():
           return [{"id": "player-123", "name": "Test Player"}]
       
       monkeypatch.setattr("yoto_smart_stream.api.routes.get_players", mock_get_players)
   
   def test_with_oauth(client, mock_oauth):
       # OAuth is mocked
       response = client.get("/api/players")
       assert response.status_code == 200
   ```

2. **Skip OAuth Tests:**
   ```python
   @pytest.mark.skipif(
       not os.getenv("OAUTH_CONFIGURED"),
       reason="OAuth not configured"
   )
   def test_real_oauth():
       # Only runs when OAuth is configured
       ...
   ```

### Slow Test Suite

**Symptom:** Tests take too long to run

**Solutions:**

1. **Run Tests in Parallel:**
   ```bash
   pip install pytest-xdist
   pytest -n auto
   ```

2. **Use Markers to Run Subsets:**
   ```python
   @pytest.mark.fast
   def test_fast():
       ...
   
   @pytest.mark.slow
   def test_slow():
       ...
   
   # Run only fast tests
   pytest -m fast
   ```

3. **Mock External Services:**
   ```python
   # Instead of real Yoto API calls
   @pytest.fixture
   def mock_yoto_client(monkeypatch):
       monkeypatch.setattr("yoto_api.YotoClient", MockYotoClient)
   ```

### Coverage Not Accurate

**Symptom:** Coverage report shows missing lines that are actually tested

**Solutions:**

1. **Include Source in Coverage:**
   ```ini
   # setup.cfg or pyproject.toml
   [tool.pytest.ini_options]
   testpaths = ["tests"]
   
   [tool.coverage.run]
   source = ["yoto_smart_stream"]
   omit = ["*/tests/*", "*/venv/*"]
   ```

2. **Run Tests with Coverage:**
   ```bash
   pytest --cov=yoto_smart_stream --cov-report=html
   open htmlcov/index.html
   ```

## Test-and-Fix Development Loop

### Iterative Development Pattern

1. **Write Failing Test:**
   ```python
   def test_new_feature():
       response = client.post("/api/new-endpoint", json={...})
       assert response.status_code == 200
   ```

2. **Run Test (Verify Failure):**
   ```bash
   pytest tests/test_new_feature.py -v
   # Should fail with clear error
   ```

3. **Implement Minimum Code:**
   ```python
   @app.post("/api/new-endpoint")
   def new_endpoint(data: dict):
       return {"status": "ok"}
   ```

4. **Run Test Again:**
   ```bash
   pytest tests/test_new_feature.py -v
   # Should pass
   ```

5. **Refactor:**
   - Improve implementation
   - Add error handling
   - Optimize performance

6. **Run Full Test Suite:**
   ```bash
   pytest --cov=yoto_smart_stream
   # Verify no regressions
   ```

### Example: Adding New Endpoint

```python
# Step 1: Write test
def test_get_player_volume(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/players/123/volume", headers=headers)
    assert response.status_code == 200
    assert "volume" in response.json()
    assert 0 <= response.json()["volume"] <= 100

# Step 2: Run test (fails)
# $ pytest tests/test_players.py::test_get_player_volume
# E   404 Not Found

# Step 3: Implement endpoint
@app.get("/api/players/{player_id}/volume")
async def get_player_volume(
    player_id: str,
    current_user: User = Depends(get_current_user)
):
    player = await get_player(player_id)
    return {"volume": player.config.volume}

# Step 4: Run test (passes)
# $ pytest tests/test_players.py::test_get_player_volume
# ✓ PASSED

# Step 5: Add more test cases
def test_get_player_volume_invalid_id(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = client.get("/api/players/invalid/volume", headers=headers)
    assert response.status_code == 404

# Step 6: Run full suite
# $ pytest --cov=yoto_smart_stream
# ✓ All tests passed
# Coverage: 87%
```

---

## Additional Resources

- **Project Docs**: See `/docs` folder for additional guides
- **Service Operations**: See [yoto-smart-stream-service skill](../yoto-smart-stream-service/SKILL.md)
- **API Development**: See [yoto-smart-stream skill](../yoto-smart-stream/SKILL.md)
- **Example Tests**: See `/tests` folder for test examples
- **Playwright Docs**: https://playwright.dev/python/docs/intro
- **pytest Docs**: https://docs.pytest.org/
