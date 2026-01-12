"""Dynamic audio streaming endpoints with queue management."""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ...config import get_settings
from ..stream_manager import get_stream_manager, StreamQueue

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
STREAM_CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming


# Helper functions


def _build_queue_response(queue: StreamQueue) -> dict:
    """Build a consistent queue response object."""
    files = queue.get_files()
    return {
        "name": queue.name,
        "files": files,
        "file_count": len(files),
    }


# Request/Response models
class AddFilesRequest(BaseModel):
    """Request model for adding files to a stream queue."""

    files: List[str] = Field(..., description="List of audio filenames to add to the queue", min_length=1)


class ReorderRequest(BaseModel):
    """Request model for reordering files in the queue."""

    old_index: int = Field(..., description="Current index of the file to move", ge=0)
    new_index: int = Field(..., description="New index where the file should be moved", ge=0)


class QueueInfoResponse(BaseModel):
    """Response model for queue information."""

    name: str
    files: List[str]
    loop: bool
    file_count: int


class QueuesListResponse(BaseModel):
    """Response model for listing all queues."""

    queues: List[str]
    count: int


# Queue Management Endpoints


@router.get("/streams/queues", response_model=QueuesListResponse)
async def list_stream_queues():
    """
    List all available stream queues.

    Returns:
        List of queue names with count
    """
    stream_manager = get_stream_manager()
    queues = await stream_manager.list_queues()
    return {"queues": queues, "count": len(queues)}


@router.get("/streams/{stream_name}/queue", response_model=QueueInfoResponse)
async def get_stream_queue(stream_name: str):
    """
    Get information about a specific stream queue.

    Args:
        stream_name: Name of the stream queue

    Returns:
        Queue information including list of files
    """
    stream_manager = get_stream_manager()
    queue_info = await stream_manager.get_queue_info(stream_name)

    if queue_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream queue '{stream_name}' not found",
        )

    return queue_info


@router.post("/streams/{stream_name}/queue", status_code=status.HTTP_200_OK)
async def add_files_to_queue(stream_name: str, request: AddFilesRequest):
    """
    Add audio files to a stream queue.

    The files will be added to the end of the queue in the order specified.
    Files must exist in the audio_files directory.

    Args:
        stream_name: Name of the stream queue
        request: List of audio filenames to add

    Returns:
        Success message with updated queue information
    """
    settings = get_settings()
    stream_manager = get_stream_manager()

    # Verify all files exist before adding any
    missing_files = []
    for filename in request.files:
        audio_path = settings.audio_files_dir / filename
        if not audio_path.exists():
            missing_files.append(filename)

    if missing_files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audio files not found: {', '.join(missing_files)}. "
            f"Add them to {settings.audio_files_dir}/",
        )

    # Get or create the queue
    queue = await stream_manager.get_or_create_queue(stream_name)

    # Add all files
    for filename in request.files:
        queue.add_file(filename)

    return {
        "success": True,
        "message": f"Added {len(request.files)} file(s) to stream '{stream_name}'",
        "queue": _build_queue_response(queue),
    }


@router.delete("/streams/{stream_name}/queue/{file_index}", status_code=status.HTTP_200_OK)
async def remove_file_from_queue(stream_name: str, file_index: int):
    """
    Remove a file from the stream queue at the specified index.

    Args:
        stream_name: Name of the stream queue
        file_index: Index of the file to remove (0-based)

    Returns:
        Success message with the removed filename
    """
    stream_manager = get_stream_manager()
    queue = await stream_manager.get_queue(stream_name)

    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream queue '{stream_name}' not found",
        )

    removed_file = queue.remove_file(file_index)

    if removed_file is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file index: {file_index}. Queue has {len(queue.files)} files.",
        )

    return {
        "success": True,
        "message": f"Removed '{removed_file}' from stream '{stream_name}'",
        "queue": _build_queue_response(queue),
    }


@router.delete("/streams/{stream_name}/queue", status_code=status.HTTP_200_OK)
async def clear_stream_queue(stream_name: str):
    """
    Clear all files from a stream queue.

    Args:
        stream_name: Name of the stream queue

    Returns:
        Success message
    """
    stream_manager = get_stream_manager()
    queue = await stream_manager.get_queue(stream_name)

    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream queue '{stream_name}' not found",
        )

    queue.clear()

    return {
        "success": True,
        "message": f"Cleared all files from stream '{stream_name}'",
        "queue": _build_queue_response(queue),
    }


@router.put("/streams/{stream_name}/queue/reorder", status_code=status.HTTP_200_OK)
async def reorder_queue(stream_name: str, request: ReorderRequest):
    """
    Reorder files in the stream queue by moving a file from one index to another.

    Args:
        stream_name: Name of the stream queue
        request: Old and new indices for the file

    Returns:
        Success message with updated queue
    """
    stream_manager = get_stream_manager()
    queue = await stream_manager.get_queue(stream_name)

    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream queue '{stream_name}' not found",
        )

    success = queue.reorder(request.old_index, request.new_index)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid indices: old_index={request.old_index}, new_index={request.new_index}. "
            f"Queue has {len(queue.files)} files.",
        )

    return {
        "success": True,
        "message": f"Reordered queue '{stream_name}'",
        "queue": _build_queue_response(queue),
    }


@router.delete("/streams/{stream_name}", status_code=status.HTTP_200_OK)
async def delete_stream_queue(stream_name: str):
    """
    Delete a stream queue entirely.

    Args:
        stream_name: Name of the stream queue to delete

    Returns:
        Success message
    """
    stream_manager = get_stream_manager()
    deleted = await stream_manager.delete_queue(stream_name)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream queue '{stream_name}' not found",
        )

    return {
        "success": True,
        "message": f"Deleted stream queue '{stream_name}'",
    }


# Streaming Endpoint


async def generate_sequential_stream(queue_files: List[str], audio_files_dir):
    """
    Generator that streams multiple audio files sequentially.

    This reads files one by one and yields their content, creating a
    continuous stream that appears as a single file to the client.

    Args:
        queue_files: List of audio filenames to stream
        audio_files_dir: Path to the audio files directory

    Yields:
        Audio data chunks
    """
    for filename in queue_files:
        audio_path = audio_files_dir / filename
        if not audio_path.exists():
            logger.warning(f"File not found during streaming: {filename}, skipping")
            continue

        logger.info(f"Streaming file: {filename}")
        
        try:
            with open(audio_path, "rb") as f:
                # Read and yield in chunks
                while True:
                    chunk = f.read(STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.error(f"Error streaming file {filename}: {e}")
            # Continue to next file instead of breaking the stream


@router.get("/streams/{stream_name}/stream.mp3")
async def stream_dynamic_audio(stream_name: str):
    """
    Stream audio from a named queue as a continuous MP3 file.

    This endpoint streams all files in the queue sequentially, making them
    appear as a single continuous audio file to the client. Each client
    that connects gets the current queue state at connection time.

    Args:
        stream_name: Name of the stream queue to play

    Returns:
        Streaming audio response with MP3 content
    """
    stream_manager = get_stream_manager()
    queue = await stream_manager.get_queue(stream_name)

    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream queue '{stream_name}' not found. Create it by adding files first.",
        )

    if not queue.files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream queue '{stream_name}' is empty. Add files to the queue first.",
        )

    settings = get_settings()
    
    # Get a snapshot of the current queue state for this client
    queue_snapshot = queue.get_files()
    
    logger.info(f"Client connected to stream '{stream_name}' with {len(queue_snapshot)} files")

    return StreamingResponse(
        generate_sequential_stream(queue_snapshot, settings.audio_files_dir),
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "none",  # Disable seeking since we're streaming multiple files
            "Cache-Control": "no-cache, no-store, must-revalidate",  # Don't cache dynamic content
            "X-Stream-Name": stream_name,
            "X-File-Count": str(len(queue_snapshot)),
        },
    )
