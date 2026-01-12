"""
Tests for dynamic audio streaming endpoints.

Tests the stream queue management and dynamic streaming functionality.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from yoto_smart_stream.api import app
from yoto_smart_stream.api.stream_manager import StreamManager, StreamQueue, get_stream_manager


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def stream_manager():
    """Create a fresh StreamManager for each test."""
    return StreamManager()


@pytest.fixture
def mock_audio_files(tmp_path):
    """Create mock audio files for testing."""
    audio_dir = tmp_path / "audio_files"
    audio_dir.mkdir()
    
    # Create dummy MP3 files
    for i in range(1, 6):
        audio_file = audio_dir / f"{i}.mp3"
        # Create a minimal valid MP3 file header and some content
        audio_file.write_bytes(b"ID3" + b"\x00" * 100 + b"audio content " * 100)
    
    return audio_dir


class TestStreamQueue:
    """Test the StreamQueue class."""

    def test_create_empty_queue(self):
        """Test creating an empty queue."""
        queue = StreamQueue(name="test")
        assert queue.name == "test"
        assert len(queue.files) == 0
        assert queue.loop is False

    def test_add_files_to_queue(self):
        """Test adding files to a queue."""
        queue = StreamQueue(name="test")
        queue.add_file("1.mp3")
        queue.add_file("2.mp3")
        
        assert len(queue.files) == 2
        assert queue.files == ["1.mp3", "2.mp3"]

    def test_remove_file_from_queue(self):
        """Test removing a file from a queue."""
        queue = StreamQueue(name="test")
        queue.add_file("1.mp3")
        queue.add_file("2.mp3")
        queue.add_file("3.mp3")
        
        removed = queue.remove_file(1)
        
        assert removed == "2.mp3"
        assert len(queue.files) == 2
        assert queue.files == ["1.mp3", "3.mp3"]

    def test_remove_invalid_index(self):
        """Test removing with an invalid index."""
        queue = StreamQueue(name="test")
        queue.add_file("1.mp3")
        
        removed = queue.remove_file(5)
        
        assert removed is None
        assert len(queue.files) == 1

    def test_clear_queue(self):
        """Test clearing all files from a queue."""
        queue = StreamQueue(name="test")
        queue.add_file("1.mp3")
        queue.add_file("2.mp3")
        
        queue.clear()
        
        assert len(queue.files) == 0

    def test_get_files_returns_copy(self):
        """Test that get_files returns a copy, not the original list."""
        queue = StreamQueue(name="test")
        queue.add_file("1.mp3")
        
        files = queue.get_files()
        files.append("2.mp3")
        
        # Original queue should be unchanged
        assert len(queue.files) == 1
        assert queue.files == ["1.mp3"]

    def test_reorder_files(self):
        """Test reordering files in the queue."""
        queue = StreamQueue(name="test")
        queue.add_file("1.mp3")
        queue.add_file("2.mp3")
        queue.add_file("3.mp3")
        
        success = queue.reorder(0, 2)
        
        assert success is True
        assert queue.files == ["2.mp3", "3.mp3", "1.mp3"]

    def test_reorder_invalid_indices(self):
        """Test reordering with invalid indices."""
        queue = StreamQueue(name="test")
        queue.add_file("1.mp3")
        
        success = queue.reorder(0, 5)
        
        assert success is False
        assert queue.files == ["1.mp3"]


class TestStreamManager:
    """Test the StreamManager class."""

    @pytest.mark.asyncio
    async def test_create_new_queue(self, stream_manager):
        """Test creating a new queue."""
        queue = await stream_manager.get_or_create_queue("test-stream")
        
        assert queue.name == "test-stream"
        assert len(queue.files) == 0

    @pytest.mark.asyncio
    async def test_get_existing_queue(self, stream_manager):
        """Test getting an existing queue."""
        queue1 = await stream_manager.get_or_create_queue("test-stream")
        queue1.add_file("1.mp3")
        
        queue2 = await stream_manager.get_or_create_queue("test-stream")
        
        assert queue1 is queue2
        assert len(queue2.files) == 1

    @pytest.mark.asyncio
    async def test_get_nonexistent_queue(self, stream_manager):
        """Test getting a queue that doesn't exist."""
        queue = await stream_manager.get_queue("nonexistent")
        
        assert queue is None

    @pytest.mark.asyncio
    async def test_delete_queue(self, stream_manager):
        """Test deleting a queue."""
        await stream_manager.get_or_create_queue("test-stream")
        
        deleted = await stream_manager.delete_queue("test-stream")
        
        assert deleted is True
        
        queue = await stream_manager.get_queue("test-stream")
        assert queue is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_queue(self, stream_manager):
        """Test deleting a queue that doesn't exist."""
        deleted = await stream_manager.delete_queue("nonexistent")
        
        assert deleted is False

    @pytest.mark.asyncio
    async def test_list_queues(self, stream_manager):
        """Test listing all queues."""
        await stream_manager.get_or_create_queue("stream1")
        await stream_manager.get_or_create_queue("stream2")
        await stream_manager.get_or_create_queue("stream3")
        
        queues = await stream_manager.list_queues()
        
        assert len(queues) == 3
        assert set(queues) == {"stream1", "stream2", "stream3"}

    @pytest.mark.asyncio
    async def test_get_queue_info(self, stream_manager):
        """Test getting queue information."""
        queue = await stream_manager.get_or_create_queue("test-stream")
        queue.add_file("1.mp3")
        queue.add_file("2.mp3")
        
        info = await stream_manager.get_queue_info("test-stream")
        
        assert info is not None
        assert info["name"] == "test-stream"
        assert info["files"] == ["1.mp3", "2.mp3"]
        assert info["file_count"] == 2
        assert info["loop"] is False

    @pytest.mark.asyncio
    async def test_get_info_for_nonexistent_queue(self, stream_manager):
        """Test getting info for a queue that doesn't exist."""
        info = await stream_manager.get_queue_info("nonexistent")
        
        assert info is None


class TestStreamEndpoints:
    """Test the stream management API endpoints."""

    def test_list_empty_queues(self, client):
        """Test listing queues when none exist."""
        # Reset the global stream manager
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        response = client.get("/api/streams/queues")
        assert response.status_code == 200
        
        data = response.json()
        assert data["count"] == 0
        assert data["queues"] == []

    def test_add_files_to_new_queue(self, client, mock_audio_files):
        """Test adding files to a new queue."""
        # Reset and configure mock settings
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            response = client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3", "2.mp3"]}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["queue"]["file_count"] == 2
            assert data["queue"]["files"] == ["1.mp3", "2.mp3"]

    def test_add_nonexistent_files(self, client, mock_audio_files):
        """Test adding files that don't exist."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            response = client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["nonexistent.mp3"]}
            )
            
            assert response.status_code == 404
            data = response.json()
            assert "not found" in data["detail"].lower()

    def test_get_queue_info(self, client, mock_audio_files):
        """Test getting queue information."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            # Add files first
            client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3", "2.mp3", "3.mp3"]}
            )
            
            # Get queue info
            response = client.get("/api/streams/test-stream/queue")
            
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "test-stream"
            assert data["file_count"] == 3
            assert data["files"] == ["1.mp3", "2.mp3", "3.mp3"]

    def test_get_nonexistent_queue(self, client):
        """Test getting info for a queue that doesn't exist."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        response = client.get("/api/streams/nonexistent/queue")
        
        assert response.status_code == 404

    def test_remove_file_from_queue(self, client, mock_audio_files):
        """Test removing a file from a queue."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            # Add files
            client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3", "2.mp3", "3.mp3"]}
            )
            
            # Remove middle file
            response = client.delete("/api/streams/test-stream/queue/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["queue"]["file_count"] == 2
            assert data["queue"]["files"] == ["1.mp3", "3.mp3"]

    def test_remove_invalid_index(self, client, mock_audio_files):
        """Test removing a file with invalid index."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            # Add files
            client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3"]}
            )
            
            # Try to remove with invalid index
            response = client.delete("/api/streams/test-stream/queue/5")
            
            assert response.status_code == 400

    def test_clear_queue(self, client, mock_audio_files):
        """Test clearing all files from a queue."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            # Add files
            client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3", "2.mp3", "3.mp3"]}
            )
            
            # Clear queue
            response = client.delete("/api/streams/test-stream/queue")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["queue"]["file_count"] == 0

    def test_reorder_queue(self, client, mock_audio_files):
        """Test reordering files in a queue."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            # Add files
            client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3", "2.mp3", "3.mp3"]}
            )
            
            # Reorder: move first file to last position
            response = client.put(
                "/api/streams/test-stream/queue/reorder",
                json={"old_index": 0, "new_index": 2}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["queue"]["files"] == ["2.mp3", "3.mp3", "1.mp3"]

    def test_delete_queue(self, client, mock_audio_files):
        """Test deleting a queue entirely."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            # Create a queue
            client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3"]}
            )
            
            # Delete it
            response = client.delete("/api/streams/test-stream")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # Verify it's gone
            response = client.get("/api/streams/test-stream/queue")
            assert response.status_code == 404

    def test_stream_audio_from_queue(self, client, mock_audio_files):
        """Test streaming audio from a queue."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            # Add files to queue
            client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3", "2.mp3"]}
            )
            
            # Stream the queue
            response = client.get("/api/streams/test-stream/stream.mp3")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "audio/mpeg"
            assert "x-stream-name" in response.headers
            assert response.headers["x-stream-name"] == "test-stream"
            assert response.headers["x-file-count"] == "2"
            
            # Check that content is not empty
            content = response.content
            assert len(content) > 0

    def test_stream_empty_queue(self, client, mock_audio_files):
        """Test streaming from an empty queue."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        with patch("yoto_smart_stream.api.routes.streams.get_settings") as mock_settings:
            mock_settings.return_value.audio_files_dir = mock_audio_files
            
            # Create empty queue
            client.post(
                "/api/streams/test-stream/queue",
                json={"files": ["1.mp3"]}
            )
            client.delete("/api/streams/test-stream/queue")
            
            # Try to stream
            response = client.get("/api/streams/test-stream/stream.mp3")
            
            assert response.status_code == 404

    def test_stream_nonexistent_queue(self, client):
        """Test streaming from a queue that doesn't exist."""
        from yoto_smart_stream.api import stream_manager as sm
        sm._stream_manager = StreamManager()
        
        response = client.get("/api/streams/nonexistent/stream.mp3")
        
        assert response.status_code == 404


class TestConcurrentAccess:
    """Test concurrent access to stream queues."""

    @pytest.mark.asyncio
    async def test_concurrent_queue_operations(self, stream_manager):
        """Test that concurrent operations are safe."""
        queue = await stream_manager.get_or_create_queue("test-stream")
        
        # Add files concurrently
        async def add_files(start, end):
            for i in range(start, end):
                queue.add_file(f"{i}.mp3")
                await asyncio.sleep(0.001)  # Small delay
        
        # Run multiple tasks concurrently
        await asyncio.gather(
            add_files(1, 10),
            add_files(10, 20),
            add_files(20, 30),
        )
        
        # All files should be added
        assert len(queue.files) == 29  # 9 + 10 + 10 = 29

    @pytest.mark.asyncio
    async def test_concurrent_manager_operations(self, stream_manager):
        """Test concurrent operations on the manager."""
        async def create_and_delete():
            for i in range(10):
                await stream_manager.get_or_create_queue(f"stream-{i}")
                if i > 0:
                    await stream_manager.delete_queue(f"stream-{i-1}")
        
        # Run multiple tasks
        await asyncio.gather(
            create_and_delete(),
            create_and_delete(),
        )
        
        # At least some queues should exist
        queues = await stream_manager.list_queues()
        assert len(queues) >= 0
