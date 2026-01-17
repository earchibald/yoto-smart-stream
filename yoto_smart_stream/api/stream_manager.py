"""
Stream queue management for dynamic audio streaming.

This module manages queues of audio files that can be streamed sequentially
to clients, appearing as a single continuous MP3 stream.

Storage Backend:
- Lambda/AWS: Uses in-memory storage with optional DynamoDB persistence
- Local Development: Uses local filesystem at ./streams
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StreamQueue:
    """
    A queue of audio files to be streamed sequentially.
    
    Attributes:
        name: Unique name for this stream queue
        files: List of filenames in the queue
        loop: Whether to loop the queue when it reaches the end
        _manager: Reference to parent StreamManager for persistence callbacks
    """
    
    name: str
    files: List[str] = field(default_factory=list)
    loop: bool = False
    _manager: Optional['StreamManager'] = field(default=None, repr=False, compare=False)
    
    def _trigger_save(self) -> None:
        """Trigger persistence save if manager is set."""
        if self._manager:
            self._manager._save_queue_to_disk(self)
    
    def add_file(self, filename: str) -> None:
        """Add a file to the end of the queue."""
        self.files.append(filename)
        logger.info(f"Added '{filename}' to stream '{self.name}'. Queue length: {len(self.files)}")
        self._trigger_save()
    
    def remove_file(self, index: int) -> Optional[str]:
        """Remove a file at the specified index. Returns the removed filename or None."""
        if 0 <= index < len(self.files):
            removed = self.files.pop(index)
            logger.info(f"Removed '{removed}' from stream '{self.name}' at index {index}")
            self._trigger_save()
            return removed
        return None
    
    def clear(self) -> None:
        """Clear all files from the queue."""
        self.files.clear()
        logger.info(f"Cleared all files from stream '{self.name}'")
        self._trigger_save()
    
    def get_files(self) -> List[str]:
        """Get a copy of the current file list."""
        return self.files.copy()
    
    def reorder(self, old_index: int, new_index: int) -> bool:
        """
        Move a file from old_index to new_index.
        Returns True if successful, False otherwise.
        """
        if 0 <= old_index < len(self.files) and 0 <= new_index < len(self.files):
            file = self.files.pop(old_index)
            self.files.insert(new_index, file)
            logger.info(f"Moved '{file}' in stream '{self.name}' from index {old_index} to {new_index}")
            self._trigger_save()
            return True
        return False


class StreamManager:
    """
    Manages multiple stream queues with environment-aware storage.
    
    Storage backends:
    - Lambda/AWS: In-memory storage (ephemeral, but safe)
    - Local Development: Local filesystem at ./streams
    
    Note: Stream queue configuration is typically ephemeral in Lambda deployments
    since streams are created dynamically. For persistent stream configurations,
    consider using DynamoDB tables managed separately.
    """
    
    def __init__(self, storage_dir: Optional[Path] = None):
        """Initialize the stream manager with environment-aware storage.
        
        Args:
            storage_dir: Optional override for storage directory. If not provided,
                        auto-detects: /tmp on Lambda, ./streams in development
        """
        self._queues: dict[str, StreamQueue] = {}
        self._lock = asyncio.Lock()
        self._is_lambda = os.environ.get("AWS_LAMBDA_FUNCTION_NAME") is not None
        
        # Determine storage directory
        if storage_dir:
            self._storage_dir = storage_dir
        elif self._is_lambda:
            # On Lambda, use in-memory storage (ephemeral)
            # Could optionally use /tmp for temporary files, but streams are usually ephemeral
            self._storage_dir = Path("/tmp/streams")
            logger.info("StreamManager running on Lambda - using ephemeral storage at /tmp/streams")
        else:
            # Local development: use current directory
            self._storage_dir = Path("./streams")
            logger.info("StreamManager in local development - using ./streams directory")
        
        # Try to initialize persistent storage if directory is writable
        self._storage_enabled = self._init_storage()
    
    def _init_storage(self) -> bool:
        """Initialize storage directory if possible. Returns True if successful."""
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"StreamManager storage initialized at {self._storage_dir}")
            # Load existing queues from disk
            self._load_queues_from_disk()
            return True
        except (OSError, PermissionError) as e:
            logger.warning(
                f"Failed to create/access storage directory {self._storage_dir}: {e}. "
                f"Continuing with in-memory storage only."
            )
            return False
    
    def _get_queue_file_path(self, queue_name: str) -> Path:
        """Get the file path for a queue's persistent storage."""
        return self._storage_dir / f"{queue_name}.json"
    
    def _save_queue_to_disk(self, queue: StreamQueue) -> None:
        """Save a queue to disk if storage is enabled."""
        if not self._storage_enabled:
            return
        
        try:
            queue_file = self._get_queue_file_path(queue.name)
            data = {
                "name": queue.name,
                "files": queue.files,
                "loop": queue.loop,
            }
            queue_file.write_text(json.dumps(data, indent=2))
            logger.debug(f"Saved queue '{queue.name}' to {queue_file}")
        except Exception as e:
            logger.error(f"Failed to save queue '{queue.name}' to disk: {e}")
    
    def _load_queues_from_disk(self) -> None:
        """Load all queues from disk on startup."""
        try:
            json_files = list(self._storage_dir.glob("*.json"))
            for queue_file in json_files:
                try:
                    data = json.loads(queue_file.read_text())
                    queue = StreamQueue(
                        name=data.get("name", queue_file.stem),
                        files=data.get("files", []),
                        loop=data.get("loop", False),
                        _manager=self,  # Set manager reference for persistence
                    )
                    self._queues[queue.name] = queue
                    logger.info(f"Loaded queue '{queue.name}' with {len(queue.files)} files from disk")
                except Exception as e:
                    logger.error(f"Failed to load queue from {queue_file}: {e}")
            
            if json_files:
                logger.info(f"Loaded {len(self._queues)} queue(s) from {self._storage_dir}")
        except Exception as e:
            logger.error(f"Failed to load queues from disk: {e}")
    
    def _delete_queue_from_disk(self, queue_name: str) -> None:
        """Delete a queue's file from disk if storage is enabled."""
        if not self._storage_enabled:
            return
        
        try:
            queue_file = self._get_queue_file_path(queue_name)
            if queue_file.exists():
                queue_file.unlink()
                logger.debug(f"Deleted queue file {queue_file}")
        except Exception as e:
            logger.error(f"Failed to delete queue '{queue_name}' from disk: {e}")
    
    async def get_or_create_queue(self, name: str) -> StreamQueue:
        """Get an existing queue or create a new one."""
        async with self._lock:
            if name not in self._queues:
                self._queues[name] = StreamQueue(name=name, _manager=self)
                logger.info(f"Created new stream queue: '{name}'")
                self._save_queue_to_disk(self._queues[name])
            return self._queues[name]
    
    async def get_queue(self, name: str) -> Optional[StreamQueue]:
        """Get a queue by name, or None if it doesn't exist."""
        async with self._lock:
            return self._queues.get(name)
    
    async def delete_queue(self, name: str) -> bool:
        """Delete a queue. Returns True if deleted, False if it didn't exist."""
        async with self._lock:
            if name in self._queues:
                del self._queues[name]
                self._delete_queue_from_disk(name)
                logger.info(f"Deleted stream queue: '{name}'")
                return True
            return False
    
    async def list_queues(self) -> List[str]:
        """List all queue names."""
        async with self._lock:
            return list(self._queues.keys())
    
    async def get_queue_info(self, name: str) -> Optional[dict]:
        """Get information about a specific queue."""
        queue = await self.get_queue(name)
        if queue:
            files = queue.get_files()
            return {
                "name": queue.name,
                "files": files,
                "loop": queue.loop,
                "file_count": len(files),
            }
        return None


# Global stream manager instance
_stream_manager: Optional[StreamManager] = None


def get_stream_manager() -> StreamManager:
    """Get the global stream manager instance."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = StreamManager()
    return _stream_manager
