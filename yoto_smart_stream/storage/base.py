"""Base storage interface for audio files."""

from abc import ABC, abstractmethod


class BaseStorage(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    async def save(self, filename: str, file_data: bytes) -> str:
        """
        Save file to storage.

        Args:
            filename: Name of the file
            file_data: Binary file data

        Returns:
            Storage path/key of the saved file
        """
        pass

    @abstractmethod
    async def get_url(self, filename: str, expiry: int = 604800) -> str:
        """
        Get URL for file access.

        For S3: returns presigned URL
        For local: returns local path

        Args:
            filename: Name of the file
            expiry: URL expiry in seconds (default: 7 days)

        Returns:
            URL or path to access the file
        """
        pass

    @abstractmethod
    async def delete(self, filename: str) -> bool:
        """
        Delete file from storage.

        Args:
            filename: Name of the file

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, filename: str) -> bool:
        """
        Check if file exists in storage.

        Args:
            filename: Name of the file

        Returns:
            True if file exists, False otherwise
        """
        pass

    @abstractmethod
    async def list_files(self) -> list[str]:
        """
        List all files in storage.

        Returns:
            List of filenames
        """
        pass

    @abstractmethod
    async def get_file_size(self, filename: str) -> int:
        """
        Get file size in bytes.

        Args:
            filename: Name of the file

        Returns:
            File size in bytes, or 0 if not found
        """
        pass

    @abstractmethod
    async def read(self, filename: str) -> bytes:
        """
        Read file data from storage.

        Args:
            filename: Name of the file

        Returns:
            Binary file data

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        pass
