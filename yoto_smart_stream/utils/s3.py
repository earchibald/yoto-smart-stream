"""S3 helper utilities for Lambda audio storage."""
import os
import logging
from typing import Generator, Optional

from botocore.exceptions import ClientError

_logger = logging.getLogger(__name__)

_s3_client = None

def get_s3_client():
    """Lazy-load boto3 S3 client."""
    global _s3_client
    if _s3_client is None:
        import boto3
        _s3_client = boto3.client("s3")
    return _s3_client


def s3_enabled(settings=None) -> bool:
    """Return True when running on Lambda with an S3 bucket configured."""
    bucket = None
    if settings is not None:
        bucket = getattr(settings, "s3_audio_bucket", None)
    if not bucket:
        bucket = os.environ.get("S3_AUDIO_BUCKET")
    return bool(bucket and os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


def object_exists(bucket: str, key: str) -> bool:
    """Check whether an object exists in S3."""
    try:
        get_s3_client().head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response.get("Error", {}).get("Code") in ("404", "NoSuchKey"):
            return False
        _logger.warning(f"Error checking S3 object {bucket}/{key}: {e}")
        return False


def stream_object(bucket: str, key: str, chunk_size: int) -> Generator[bytes, None, None]:
    """Yield chunks from an S3 object."""
    obj = get_s3_client().get_object(Bucket=bucket, Key=key)
    body = obj["Body"]
    while True:
        chunk = body.read(chunk_size)
        if not chunk:
            break
        yield chunk


def upload_file(bucket: str, key: str, source_path: str) -> Optional[str]:
    """Upload a file to S3 and return the object URL."""
    try:
        get_s3_client().upload_file(source_path, bucket, key)
        return f"https://{bucket}.s3.amazonaws.com/{key}"
    except Exception as e:
        _logger.error(f"Failed to upload {source_path} to s3://{bucket}/{key}: {e}")
        return None
