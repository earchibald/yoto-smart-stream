"""
Stream queue management for dynamic audio streaming.

This module manages queues of audio files that can be streamed sequentially
to clients, appearing as a single continuous MP3 stream.
"""

import asyncio
import logging
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
    """
    
    name: str
    files: List[str] = field(default_factory=list)
    loop: bool = False
    
    def add_file(self, filename: str) -> None:
        """Add a file to the end of the queue."""
        self.files.append(filename)
        logger.info(f"Added '{filename}' to stream '{self.name}'. Queue length: {len(self.files)}")
    
    def remove_file(self, index: int) -> Optional[str]:
        """Remove a file at the specified index. Returns the removed filename or None."""
        if 0 <= index < len(self.files):
            removed = self.files.pop(index)
            logger.info(f"Removed '{removed}' from stream '{self.name}' at index {index}")
            return removed
        return None
    
    def clear(self) -> None:
        """Clear all files from the queue."""
        self.files.clear()
        logger.info(f"Cleared all files from stream '{self.name}'")
    
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
            return True
        return False


class StreamManager:
    """
    Manages multiple stream queues.
    
    This class provides a centralized manager for multiple named stream queues,
    allowing the server to maintain different playlists for different purposes.
    """
    
    def __init__(self):
        """Initialize the stream manager with an empty collection of queues."""
        self._queues: dict[str, StreamQueue] = {}
        self._lock = asyncio.Lock()
        logger.info("StreamManager initialized")
    
    async def get_or_create_queue(self, name: str) -> StreamQueue:
        """Get an existing queue or create a new one."""
        async with self._lock:
            if name not in self._queues:
                self._queues[name] = StreamQueue(name=name)
                logger.info(f"Created new stream queue: '{name}'")
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
            return {
                "name": queue.name,
                "files": queue.files.copy(),
                "loop": queue.loop,
                "file_count": len(queue.files),
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
