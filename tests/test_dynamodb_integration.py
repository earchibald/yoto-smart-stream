"""
Integration tests for DynamoDB store operations.

Tests cover user management, audio metadata, and transcript tracking operations
against DynamoDB. These tests verify that DynamoStore correctly handles CRUD
operations and maintains data integrity.
"""

import os
import pytest
from datetime import datetime, timezone
from typing import Generator

from yoto_smart_stream.storage.dynamodb_store import (
    DynamoStore,
    UserRecord,
    AudioFileRecord,
    _now_utc,
    _iso,
    _parse_dt,
    _as_int,
)


# Fixtures
@pytest.fixture
def dynamodb_table_name() -> str:
    """Get DynamoDB table name for tests"""
    table = os.getenv("TEST_DYNAMODB_TABLE", "yoto-smart-stream-dev")
    return table


@pytest.fixture
def aws_region() -> str:
    """Get AWS region for tests"""
    return os.getenv("AWS_REGION", "us-east-1")


@pytest.fixture
def store(dynamodb_table_name: str, aws_region: str) -> DynamoStore:
    """Create DynamoStore instance for testing"""
    return DynamoStore(table_name=dynamodb_table_name, region_name=aws_region)


@pytest.fixture(autouse=True)
def cleanup_test_users(store: DynamoStore):
    """Clean up test users before and after each test"""
    # Cleanup before test
    for user in store.list_users():
        if user.username.startswith("test_"):
            # Note: DynamoStore doesn't have delete_user method
            # In real tests, we'd need to add this or use a test isolation strategy
            pass
    
    yield
    
    # Cleanup after test
    for user in store.list_users():
        if user.username.startswith("test_"):
            pass


# ============================================================
# User Management Tests
# ============================================================

class TestUserManagement:
    """Test suite for user CRUD operations"""

    def test_create_user_success(self, store: DynamoStore):
        """Test successful user creation"""
        user = store.create_user(
            username="test_user_create",
            hashed_password="hashed_password_123",
            email="test@example.com",
            is_admin=False
        )
        
        assert user.username == "test_user_create"
        assert user.email == "test@example.com"
        assert user.hashed_password == "hashed_password_123"
        assert user.is_admin is False
        assert user.is_active is True
        assert user.user_id > 0
        assert user.created_at is not None
        assert user.updated_at is not None

    def test_create_admin_user(self, store: DynamoStore):
        """Test creating an admin user"""
        user = store.create_user(
            username="test_admin_user",
            hashed_password="admin_hash",
            email="admin@example.com",
            is_admin=True
        )
        
        assert user.is_admin is True
        assert user.username == "test_admin_user"

    def test_get_user_by_username(self, store: DynamoStore):
        """Test retrieving user by username"""
        created = store.create_user(
            username="test_get_user",
            hashed_password="pwd_hash",
            email="get@example.com",
            is_admin=False
        )
        
        retrieved = store.get_user("test_get_user")
        
        assert retrieved is not None
        assert retrieved.username == created.username
        assert retrieved.email == created.email
        assert retrieved.user_id == created.user_id

    def test_get_nonexistent_user(self, store: DynamoStore):
        """Test retrieving a user that doesn't exist"""
        user = store.get_user("nonexistent_user_xyz")
        assert user is None

    def test_get_user_by_id(self, store: DynamoStore):
        """Test retrieving user by ID"""
        created = store.create_user(
            username="test_get_by_id",
            hashed_password="pwd",
            email="byid@example.com",
            is_admin=False
        )
        
        retrieved = store.get_user_by_id(created.user_id)
        
        assert retrieved is not None
        assert retrieved.user_id == created.user_id
        assert retrieved.username == "test_get_by_id"

    def test_get_user_by_nonexistent_id(self, store: DynamoStore):
        """Test retrieving user with non-existent ID"""
        user = store.get_user_by_id(999999999)
        assert user is None

    def test_list_users(self, store: DynamoStore):
        """Test listing all users"""
        # Create multiple users
        store.create_user("test_list_user1", "pwd1", "user1@example.com", False)
        store.create_user("test_list_user2", "pwd2", "user2@example.com", False)
        
        users = store.list_users()
        
        assert len(users) >= 2
        usernames = [u.username for u in users]
        assert "test_list_user1" in usernames
        assert "test_list_user2" in usernames

    def test_user_count(self, store: DynamoStore):
        """Test user count operation"""
        initial_count = store.user_count()
        
        store.create_user("test_count_user", "pwd", "count@example.com", False)
        new_count = store.user_count()
        
        assert new_count > initial_count

    def test_update_user_email(self, store: DynamoStore):
        """Test updating user email"""
        created = store.create_user(
            username="test_update_email",
            hashed_password="pwd",
            email="old@example.com",
            is_admin=False
        )
        
        updated = store.update_user(
            user_id=created.user_id,
            email="new@example.com",
            hashed_password=None
        )
        
        assert updated is not None
        assert updated.email == "new@example.com"
        assert updated.hashed_password == "pwd"  # Unchanged

    def test_update_user_password(self, store: DynamoStore):
        """Test updating user password"""
        created = store.create_user(
            username="test_update_pwd",
            hashed_password="old_pwd",
            email="pwd@example.com",
            is_admin=False
        )
        
        updated = store.update_user(
            user_id=created.user_id,
            email=None,
            hashed_password="new_pwd"
        )
        
        assert updated is not None
        assert updated.hashed_password == "new_pwd"
        assert updated.email == "pwd@example.com"  # Unchanged

    def test_update_user_both_fields(self, store: DynamoStore):
        """Test updating both email and password"""
        created = store.create_user(
            username="test_update_both",
            hashed_password="old_pwd",
            email="old@example.com",
            is_admin=False
        )
        
        updated = store.update_user(
            user_id=created.user_id,
            email="new@example.com",
            hashed_password="new_pwd"
        )
        
        assert updated is not None
        assert updated.email == "new@example.com"
        assert updated.hashed_password == "new_pwd"

    def test_ensure_admin_user_creates_if_not_exists(self, store: DynamoStore):
        """Test ensure_admin_user creates admin if not exists"""
        admin = store.ensure_admin_user(
            hashed_password="admin_pwd",
            email="admin@test.com"
        )
        
        assert admin.username == "admin"
        assert admin.is_admin is True

    def test_ensure_admin_user_returns_existing(self, store: DynamoStore):
        """Test ensure_admin_user returns existing admin"""
        # Create admin first
        first = store.ensure_admin_user("pwd1", "email1@test.com")
        
        # Call again - should return existing
        second = store.ensure_admin_user("pwd2", "email2@test.com")
        
        assert first.user_id == second.user_id
        assert first.username == second.username
        assert first.hashed_password == second.hashed_password  # Unchanged from first call

    def test_user_record_id_property(self, store: DynamoStore):
        """Test UserRecord.id property for SQLAlchemy compatibility"""
        user = store.create_user(
            username="test_id_property",
            hashed_password="pwd",
            email="id@example.com",
            is_admin=False
        )
        
        # Test that .id is same as .user_id
        assert user.id == user.user_id


# ============================================================
# Audio File Metadata Tests
# ============================================================

class TestAudioFileMetadata:
    """Test suite for audio file CRUD operations"""

    def test_upsert_audio_file_creates_new(self, store: DynamoStore):
        """Test creating new audio file metadata"""
        audio = store.upsert_audio_file(
            filename="test_audio_1.mp3",
            size=5242880,
            duration=240
        )
        
        assert audio.filename == "test_audio_1.mp3"
        assert audio.size == 5242880
        assert audio.duration == 240
        assert audio.transcript_status == "pending"
        assert audio.transcript is None
        assert audio.transcript_error is None
        assert audio.created_at is not None
        assert audio.updated_at is not None

    def test_upsert_audio_file_updates_existing(self, store: DynamoStore):
        """Test updating existing audio file metadata"""
        # Create first
        audio1 = store.upsert_audio_file(
            filename="test_audio_update.mp3",
            size=1000000,
            duration=100
        )
        created_at_1 = audio1.created_at
        
        # Update with new size/duration
        audio2 = store.upsert_audio_file(
            filename="test_audio_update.mp3",
            size=2000000,
            duration=200
        )
        
        assert audio2.filename == audio1.filename
        assert audio2.size == 2000000
        assert audio2.duration == 200
        assert audio2.created_at == created_at_1  # Created time should not change

    def test_get_audio_file(self, store: DynamoStore):
        """Test retrieving audio file metadata"""
        created = store.upsert_audio_file(
            filename="test_get_audio.mp3",
            size=3000000,
            duration=180
        )
        
        retrieved = store.get_audio_file("test_get_audio.mp3")
        
        assert retrieved is not None
        assert retrieved.filename == created.filename
        assert retrieved.size == created.size
        assert retrieved.duration == created.duration

    def test_get_nonexistent_audio_file(self, store: DynamoStore):
        """Test retrieving non-existent audio file"""
        audio = store.get_audio_file("nonexistent_file.mp3")
        assert audio is None

    def test_list_audio_files(self, store: DynamoStore):
        """Test listing all audio files"""
        # Create multiple audio files
        store.upsert_audio_file("test_list_1.mp3", 1000000, 100)
        store.upsert_audio_file("test_list_2.mp3", 2000000, 200)
        
        files = store.list_audio_files()
        
        assert len(files) >= 2
        filenames = [f.filename for f in files]
        assert "test_list_1.mp3" in filenames
        assert "test_list_2.mp3" in filenames

    def test_search_audio_files_exact_match(self, store: DynamoStore):
        """Test searching audio files with exact filename"""
        store.upsert_audio_file("test_search_exact.mp3", 1000000, 100)
        
        results = store.search_audio_files("test_search_exact.mp3")
        
        assert len(results) >= 1
        assert any(f.filename == "test_search_exact.mp3" for f in results)

    def test_search_audio_files_partial_match(self, store: DynamoStore):
        """Test searching audio files with partial filename"""
        store.upsert_audio_file("test_search_partial_song.mp3", 1000000, 100)
        store.upsert_audio_file("test_search_partial_podcast.mp3", 2000000, 200)
        
        results = store.search_audio_files("partial")
        
        assert len(results) >= 2

    def test_search_audio_files_empty_query(self, store: DynamoStore):
        """Test searching with empty query returns all files"""
        store.upsert_audio_file("test_empty_query_1.mp3", 1000000, 100)
        store.upsert_audio_file("test_empty_query_2.mp3", 2000000, 200)
        
        results = store.search_audio_files("")
        
        assert len(results) >= 2


# ============================================================
# Transcript Operations Tests
# ============================================================

class TestTranscriptOperations:
    """Test suite for audio transcript operations"""

    def test_update_transcript_full(self, store: DynamoStore):
        """Test full transcript update with text and status"""
        store.upsert_audio_file("test_transcript_full.mp3", 1000000, 100)
        
        audio = store.update_transcript(
            filename="test_transcript_full.mp3",
            transcript="This is the transcribed text",
            status="completed"
        )
        
        assert audio is not None
        assert audio.transcript == "This is the transcribed text"
        assert audio.transcript_status == "completed"
        assert audio.transcribed_at is not None
        assert audio.transcript_error is None

    def test_update_transcript_with_error(self, store: DynamoStore):
        """Test transcript update with error status"""
        store.upsert_audio_file("test_transcript_error.mp3", 1000000, 100)
        
        audio = store.update_transcript(
            filename="test_transcript_error.mp3",
            transcript=None,
            status="failed",
            error="Transcription timeout after 300 seconds"
        )
        
        assert audio is not None
        assert audio.transcript_status == "failed"
        assert audio.transcript_error == "Transcription timeout after 300 seconds"
        assert audio.transcript is None

    def test_set_transcript_status_without_transcript(self, store: DynamoStore):
        """Test setting transcript status without providing transcript text"""
        store.upsert_audio_file("test_status_only.mp3", 1000000, 100)
        
        audio = store.set_transcript_status(
            filename="test_status_only.mp3",
            status="processing"
        )
        
        assert audio is not None
        assert audio.transcript_status == "processing"
        assert audio.transcript is None

    def test_transcript_status_progression(self, store: DynamoStore):
        """Test full transcript status progression"""
        store.upsert_audio_file("test_progression.mp3", 1000000, 100)
        
        # Initial state
        audio1 = store.get_audio_file("test_progression.mp3")
        assert audio1.transcript_status == "pending"
        
        # Processing
        audio2 = store.set_transcript_status("test_progression.mp3", "processing")
        assert audio2.transcript_status == "processing"
        
        # Completed
        audio3 = store.update_transcript(
            filename="test_progression.mp3",
            transcript="Final transcript",
            status="completed"
        )
        assert audio3.transcript_status == "completed"
        assert audio3.transcript == "Final transcript"
        assert audio3.transcribed_at is not None

    def test_clear_transcript_error(self, store: DynamoStore):
        """Test clearing transcript error"""
        store.upsert_audio_file("test_clear_error.mp3", 1000000, 100)
        
        # Set error first
        audio1 = store.update_transcript(
            filename="test_clear_error.mp3",
            transcript=None,
            status="failed",
            error="Initial error"
        )
        assert audio1.transcript_error == "Initial error"
        
        # Clear error
        audio2 = store.update_transcript(
            filename="test_clear_error.mp3",
            transcript=None,
            status="processing",
            error=None
        )
        assert audio2.transcript_error is None


# ============================================================
# Helper Function Tests
# ============================================================

class TestHelperFunctions:
    """Test suite for utility functions"""

    def test_parse_iso_datetime(self):
        """Test parsing ISO datetime strings"""
        now = _now_utc()
        iso_str = _iso(now)
        
        parsed = _parse_dt(iso_str)
        
        assert parsed is not None
        # Allow small time differences due to precision loss
        assert abs((parsed - now).total_seconds()) < 1

    def test_parse_invalid_datetime(self):
        """Test parsing invalid datetime returns None"""
        parsed = _parse_dt("invalid datetime")
        assert parsed is None

    def test_parse_none_datetime(self):
        """Test parsing None returns None"""
        parsed = _parse_dt(None)
        assert parsed is None

    def test_as_int_from_int(self):
        """Test converting int to int"""
        result = _as_int(42)
        assert result == 42

    def test_as_int_from_float(self):
        """Test converting float to int"""
        result = _as_int(42.9)
        assert result == 42

    def test_as_int_from_string(self):
        """Test converting string to int"""
        result = _as_int("42")
        assert result == 42

    def test_as_int_from_none(self):
        """Test converting None returns None"""
        result = _as_int(None)
        assert result is None

    def test_as_int_invalid_string(self):
        """Test converting invalid string returns None"""
        result = _as_int("not_a_number")
        assert result is None

    def test_now_utc_returns_datetime(self):
        """Test that _now_utc returns current UTC datetime"""
        now = _now_utc()
        
        assert isinstance(now, datetime)
        assert now.tzinfo == timezone.utc

    def test_iso_format_is_iso8601(self):
        """Test that _iso returns ISO 8601 format"""
        now = _now_utc()
        iso_str = _iso(now)
        
        # ISO format includes T and Z
        assert "T" in iso_str
        assert "+" in iso_str or iso_str.endswith("Z") or iso_str.endswith("+00:00")


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """End-to-end integration tests"""

    def test_user_audio_workflow(self, store: DynamoStore):
        """Test complete user and audio workflow"""
        # Create user
        user = store.create_user(
            username="test_workflow_user",
            hashed_password="pwd",
            email="workflow@example.com",
            is_admin=False
        )
        assert user is not None
        
        # Create audio file
        audio = store.upsert_audio_file(
            filename="workflow_song.mp3",
            size=5000000,
            duration=300
        )
        assert audio.transcript_status == "pending"
        
        # Update transcript
        completed = store.update_transcript(
            filename="workflow_song.mp3",
            transcript="Song lyrics here",
            status="completed"
        )
        assert completed.transcript_status == "completed"
        
        # Verify data persists
        retrieved_audio = store.get_audio_file("workflow_song.mp3")
        assert retrieved_audio.transcript == "Song lyrics here"

    def test_admin_user_workflow(self, store: DynamoStore):
        """Test admin user creation and management"""
        # Ensure admin exists
        admin = store.ensure_admin_user("admin_pwd", "admin@test.com")
        assert admin.is_admin is True
        
        # Admin can be retrieved
        retrieved = store.get_user("admin")
        assert retrieved is not None
        assert retrieved.is_admin is True


# ============================================================
# Performance Tests (Optional)
# ============================================================

@pytest.mark.performance
class TestPerformance:
    """Performance and scalability tests"""

    def test_bulk_user_creation(self, store: DynamoStore):
        """Test creating multiple users for performance"""
        import time
        
        start = time.time()
        for i in range(10):
            store.create_user(
                username=f"test_perf_user_{i}",
                hashed_password="pwd",
                email=f"perf{i}@example.com",
                is_admin=False
            )
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 10 seconds for 10 users)
        assert elapsed < 10
        print(f"Created 10 users in {elapsed:.2f} seconds")

    def test_bulk_audio_file_creation(self, store: DynamoStore):
        """Test creating multiple audio files for performance"""
        import time
        
        start = time.time()
        for i in range(10):
            store.upsert_audio_file(
                filename=f"test_perf_audio_{i}.mp3",
                size=1000000 * (i + 1),
                duration=100 * (i + 1)
            )
        elapsed = time.time() - start
        
        # Should complete in reasonable time (< 10 seconds for 10 files)
        assert elapsed < 10
        print(f"Created 10 audio files in {elapsed:.2f} seconds")

    def test_large_list_query(self, store: DynamoStore):
        """Test listing large number of items"""
        import time
        
        # Create 20 audio files
        for i in range(20):
            store.upsert_audio_file(
                filename=f"test_large_list_{i}.mp3",
                size=1000000,
                duration=100
            )
        
        # List all
        start = time.time()
        files = store.list_audio_files()
        elapsed = time.time() - start
        
        assert len(files) >= 20
        print(f"Listed {len(files)} files in {elapsed:.3f} seconds")


if __name__ == "__main__":
    # Run tests with: pytest tests/test_dynamodb_integration.py -v
    pytest.main([__file__, "-v"])
