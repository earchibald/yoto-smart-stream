"""S3-compatible storage implementation for Railway Buckets."""

import asyncio
import logging
from functools import partial

import boto3
from botocore.exceptions import ClientError

from .base import BaseStorage

logger = logging.getLogger(__name__)


class S3Storage(BaseStorage):
    """S3-compatible storage backend for Railway Buckets."""

    def __init__(
        self,
        bucket_name: str,
        access_key_id: str,
        secret_access_key: str,
        endpoint_url: str = "https://storage.railway.app",
        region: str = "auto",
    ):
        """
        Initialize S3 storage.

        Args:
            bucket_name: S3 bucket name
            access_key_id: S3 access key ID
            secret_access_key: S3 secret access key
            endpoint_url: S3 endpoint URL (default: Railway Buckets)
            region: S3 region (default: auto)
        """
        self.bucket_name = bucket_name
        self.endpoint_url = endpoint_url
        self.region = region

        # Initialize S3 client
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            endpoint_url=endpoint_url,
            region_name=region,
        )

        logger.info(
            f"Initialized S3Storage: bucket={bucket_name}, endpoint={endpoint_url}, region={region}"
        )

    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous boto3 function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(func, *args, **kwargs))

    async def save(self, filename: str, file_data: bytes) -> str:
        """Save file to S3 bucket."""
        try:
            await self._run_sync(
                self.s3_client.put_object,
                Bucket=self.bucket_name,
                Key=filename,
                Body=file_data,
                ContentType="audio/mpeg",
            )
            logger.debug(f"Saved file to S3: {filename} ({len(file_data)} bytes)")
            return f"s3://{self.bucket_name}/{filename}"
        except ClientError as e:
            logger.error(f"Failed to save file to S3: {filename} - {e}")
            raise

    async def get_url(self, filename: str, expiry: int = 604800) -> str:
        """
        Get presigned URL for S3 object.

        Args:
            filename: Name of the file
            expiry: URL expiry in seconds (default: 7 days)

        Returns:
            Presigned URL for direct access
        """
        try:
            url = await self._run_sync(
                self.s3_client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": filename},
                ExpiresIn=expiry,
            )
            logger.debug(f"Generated presigned URL for {filename} (expires in {expiry}s)")
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {filename} - {e}")
            raise

    async def delete(self, filename: str) -> bool:
        """Delete file from S3 bucket."""
        try:
            await self._run_sync(
                self.s3_client.delete_object,
                Bucket=self.bucket_name,
                Key=filename,
            )
            logger.debug(f"Deleted file from S3: {filename}")
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                logger.warning(f"File not found in S3: {filename}")
                return False
            logger.error(f"Failed to delete file from S3: {filename} - {e}")
            raise

    async def exists(self, filename: str) -> bool:
        """Check if file exists in S3 bucket."""
        try:
            await self._run_sync(
                self.s3_client.head_object,
                Bucket=self.bucket_name,
                Key=filename,
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                return False
            logger.error(f"Failed to check file existence in S3: {filename} - {e}")
            raise

    async def list_files(self) -> list[str]:
        """List all MP3 files in S3 bucket."""
        try:
            response = await self._run_sync(
                self.s3_client.list_objects_v2,
                Bucket=self.bucket_name,
            )

            if "Contents" not in response:
                return []

            # Filter for MP3 files and extract filenames
            files = [obj["Key"] for obj in response["Contents"] if obj["Key"].endswith(".mp3")]
            return sorted(files)
        except ClientError as e:
            logger.error(f"Failed to list files in S3: {e}")
            raise

    async def get_file_size(self, filename: str) -> int:
        """Get file size from S3 bucket."""
        try:
            response = await self._run_sync(
                self.s3_client.head_object,
                Bucket=self.bucket_name,
                Key=filename,
            )
            return response["ContentLength"]
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logger.warning(f"File not found in S3: {filename}")
                return 0
            logger.error(f"Failed to get file size from S3: {filename} - {e}")
            raise

    async def read(self, filename: str) -> bytes:
        """Read file data from S3 bucket."""
        try:
            response = await self._run_sync(
                self.s3_client.get_object,
                Bucket=self.bucket_name,
                Key=filename,
            )
            return response["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                raise FileNotFoundError(f"File not found in S3: {filename}") from None
            logger.error(f"Failed to read file from S3: {filename} - {e}")
            raise
