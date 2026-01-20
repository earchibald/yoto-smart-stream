"""
Tests for settings management API.

Tests setting CRUD operations, environment variable overrides, and settings integration.
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from yoto_smart_stream.api.app import create_app
from yoto_smart_stream.auth import get_password_hash
from yoto_smart_stream.database import Base, get_db
from yoto_smart_stream.models import User

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """Create a test client with test database."""
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Create admin user
    db = TestingSessionLocal()
    try:
        admin_user = User(
            username="admin",
            hashed_password=get_password_hash("testpass"),
            is_active=True,
            is_admin=True,
        )
        db.add(admin_user)
        db.commit()
    finally:
        db.close()

    # Create app and override database
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for admin user."""
    response = client.post("/api/user/login", json={"username": "admin", "password": "testpass"})
    assert response.status_code == 200

    # Extract session cookie
    cookies = response.cookies
    return {"Cookie": f"session={cookies.get('session')}"}


def test_list_settings(client, auth_headers):
    """Test listing all available settings."""
    response = client.get("/api/settings", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert "settings" in data
    assert (
        len(data["settings"]) >= 2
    )  # Should have at least transcription_enabled and yoto_client_id

    # Check that both settings are present
    setting_keys = [s["key"] for s in data["settings"]]
    assert "transcription_enabled" in setting_keys
    assert "yoto_client_id" in setting_keys


def test_get_specific_setting(client, auth_headers):
    """Test getting a specific setting."""
    response = client.get("/api/settings/transcription_enabled", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "transcription_enabled"
    assert data["value"] in ["true", "false"]
    assert "description" in data
    assert "is_overridden" in data


def test_update_setting(client, auth_headers):
    """Test updating a setting value."""
    # Update transcription_enabled to true
    response = client.put(
        "/api/settings/transcription_enabled", headers=auth_headers, json={"value": "true"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "transcription_enabled"
    assert data["value"] == "true"

    # Verify it persists
    response = client.get("/api/settings/transcription_enabled", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["value"] == "true"


def test_update_yoto_client_id_setting(client, auth_headers):
    """Test updating yoto_client_id setting."""
    test_client_id = "test_client_id_12345"

    # Update yoto_client_id
    response = client.put(
        "/api/settings/yoto_client_id", headers=auth_headers, json={"value": test_client_id}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["key"] == "yoto_client_id"
    assert data["value"] == test_client_id

    # Verify it persists
    response = client.get("/api/settings/yoto_client_id", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["value"] == test_client_id


def test_env_var_override(client, auth_headers):
    """Test that environment variables override database settings."""
    # Set database value
    response = client.put(
        "/api/settings/transcription_enabled", headers=auth_headers, json={"value": "false"}
    )
    assert response.status_code == 200

    # Set environment variable
    os.environ["TRANSCRIPTION_ENABLED"] = "true"

    try:
        # Get setting - should return env var value
        response = client.get("/api/settings/transcription_enabled", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Should show env override
        assert data["is_overridden"] is True
        assert data["env_var_override"] == "true"
        assert data["value"] == "true"  # Effective value is from env var
    finally:
        # Cleanup
        del os.environ["TRANSCRIPTION_ENABLED"]


def test_yoto_client_id_env_var_override(client, auth_headers):
    """Test that YOTO_CLIENT_ID environment variable overrides database setting."""
    # Set database value
    db_client_id = "db_client_id_123"
    response = client.put(
        "/api/settings/yoto_client_id", headers=auth_headers, json={"value": db_client_id}
    )
    assert response.status_code == 200

    # Set environment variable
    env_client_id = "env_client_id_456"
    os.environ["YOTO_CLIENT_ID"] = env_client_id

    try:
        # Get setting - should return env var value
        response = client.get("/api/settings/yoto_client_id", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Should show env override
        assert data["is_overridden"] is True
        assert data["value"] == env_client_id.lower()  # Normalized to lowercase
        # env_var_override should also be lowercase
        assert data["env_var_override"] == env_client_id.lower()
    finally:
        # Cleanup
        del os.environ["YOTO_CLIENT_ID"]


def test_setting_not_found(client, auth_headers):
    """Test accessing non-existent setting."""
    response = client.get("/api/settings/nonexistent_setting", headers=auth_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_unauthorized_access(client):
    """Test that settings require admin authentication."""
    # Try to access without auth
    response = client.get("/api/settings")
    assert response.status_code in [401, 403]

    # Try to update without auth
    response = client.put("/api/settings/transcription_enabled", json={"value": "true"})
    assert response.status_code in [401, 403]
