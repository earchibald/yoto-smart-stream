"""Local filesystem storage implementation."""

import logging
from pathlib import Path

import aiofiles

from .base import BaseStorage

logger = logging.getLogger(__name__)


class LocalStorage(BaseStorage):
    """Local filesystem storage backend."""

    def __init__(self, base_path: Path):
        """
        Initialize local storage.

        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Initialized LocalStorage at {self.base_path}")

    async def save(self, filename: str, file_data: bytes) -> str:
        """Save file to local filesystem."""
        file_path = self.base_path / filename
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(file_data)
        logger.debug(f"Saved file: {filename} ({len(file_data)} bytes)")
        return str(file_path)

    async def get_url(self, filename: str, expiry: int = 604800) -> str:
        """Get local file path (expiry is ignored for local storage)."""
        return str(self.base_path / filename)

    async def delete(self, filename: str) -> bool:
        """Delete file from local filesystem."""
        file_path = self.base_path / filename
        try:
            file_path.unlink()
            logger.debug(f"Deleted file: {filename}")
            return True
        except FileNotFoundError:
            logger.warning(f"File not found for deletion: {filename}")
            return False

    async def exists(self, filename: str) -> bool:
        """Check if file exists on local filesystem."""
        file_path = self.base_path / filename
        return file_path.exists()

    async def list_files(self) -> list[str]:
        """List all MP3 files in local directory."""
        files = [f.name for f in self.base_path.glob("*.mp3")]
        return sorted(files)

    async def get_file_size(self, filename: str) -> int:
        """Get file size from local filesystem."""
        file_path = self.base_path / filename
        try:
            return file_path.stat().st_size
        except FileNotFoundError:
            logger.warning(f"File not found: {filename}")
            return 0

    async def read(self, filename: str) -> bytes:
        """Read file data from local filesystem."""
        file_path = self.base_path / filename
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {filename}")
        async with aiofiles.open(file_path, "rb") as f:
            return await f.read()
