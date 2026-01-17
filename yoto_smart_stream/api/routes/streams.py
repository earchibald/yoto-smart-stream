"""Dynamic audio streaming endpoints with queue management."""

import logging
import os
from typing import List, Optional
from datetime import datetime

import requests
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...config import get_settings
from ...utils.s3 import s3_enabled, object_exists, stream_object
from ...database import get_db
from ...models import User
from .user_auth import require_auth
from ..mqtt_event_store import get_mqtt_event_store
from ..stream_manager import get_stream_manager, StreamQueue
from ..dependencies import get_yoto_client

router = APIRouter()
logger = logging.getLogger(__name__)

# Constants
STREAM_CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming


async def _async_wrap_generator(generator):
    """Wrap a sync generator so it can be awaited in async contexts."""
    for item in generator:
        yield item


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


class CreatePlaylistRequest(BaseModel):
    """Request model for creating a Yoto playlist from a stream."""
    
    playlist_name: str = Field(..., description="Name for the playlist")
    stream_name: str = Field(..., description="Name of the stream to link to the playlist")


class DeletePlaylistRequest(BaseModel):
    """Request model for deleting a Yoto playlist."""
    
    playlist_id: str = Field(..., description="ID of the playlist to delete")


# Queue Management Endpoints


@router.get("/streams/queues", response_model=QueuesListResponse)
async def list_stream_queues(user: User = Depends(require_auth)):
    """
    List all available stream queues.

    Returns:
        List of queue names with count
    """
    stream_manager = get_stream_manager()
    queues = await stream_manager.list_queues()
    return {"queues": queues, "count": len(queues)}


@router.get("/streams/{stream_name}/queue", response_model=QueueInfoResponse)
async def get_stream_queue(stream_name: str, user: User = Depends(require_auth)):
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
async def add_files_to_queue(stream_name: str, request: AddFilesRequest, user: User = Depends(require_auth)):
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
    use_s3 = s3_enabled(settings)
    for filename in request.files:
        if use_s3:
            if not object_exists(settings.s3_audio_bucket, filename):
                missing_files.append(filename)
        else:
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
async def remove_file_from_queue(stream_name: str, file_index: int, user: User = Depends(require_auth)):
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
async def clear_stream_queue(stream_name: str, user: User = Depends(require_auth)):
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
async def reorder_queue(stream_name: str, request: ReorderRequest, user: User = Depends(require_auth)):
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
async def delete_stream_queue(stream_name: str, user: User = Depends(require_auth)):
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


# Playlist Management Endpoints


@router.post("/streams/{stream_name}/create-playlist", status_code=status.HTTP_201_CREATED)
async def create_playlist_from_stream(
    stream_name: str,
    request: CreatePlaylistRequest,
    user: User = Depends(require_auth),
):
    """
    Create a Yoto playlist from a managed stream.
    
    This creates a new playlist in your Yoto library that points to the specified stream.
    The playlist will stream audio from the server-managed queue.
    
    Args:
        stream_name: Name of the stream to link to the playlist
        request: CreatePlaylistRequest with playlist_name
        
    Returns:
        Created playlist information including playlist ID
    """
    settings = get_settings()
    client = get_yoto_client()
    stream_manager = get_stream_manager()
    
    # Verify the stream exists
    queue = await stream_manager.get_queue(stream_name)
    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream queue '{stream_name}' not found. Create the stream first.",
        )
    
    if not queue.files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stream queue '{stream_name}' is empty. Add files to the stream first.",
        )
    
    # Verify PUBLIC_URL is configured
    if not settings.public_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="PUBLIC_URL environment variable not set. "
            "Set it to your public server URL (e.g., https://example.ngrok.io)",
        )
    
    # Ensure we're authenticated
    try:
        manager = client.get_manager()
        manager.check_and_refresh_token()
    except Exception as e:
        logger.error(f"Failed to authenticate with Yoto API: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Failed to authenticate with Yoto API. Please ensure you're logged in.",
        ) from e
    
    # Build the streaming URL for this queue
    streaming_url = f"{settings.public_url}/api/streams/{stream_name}/stream.mp3"
    
    # Create playlist data structure following Yoto API specification
    # https://yoto.dev/myo/streaming-tracks/
    playlist_data = {
        "title": request.playlist_name,
        "content": {
            "chapters": [
                {
                    "key": "01",
                    "title": request.playlist_name,
                    "tracks": [
                        {
                            "key": "01",
                            "type": "stream",
                            "format": "mp3",
                            "title": request.playlist_name,
                            "trackUrl": streaming_url,
                        }
                    ],
                }
            ]
        },
        "metadata": {
            "description": f"Playlist streaming from '{stream_name}' queue"
        },
    }
    
    try:
        # Create the playlist via Yoto API using /content endpoint
        response = requests.post(
            "https://api.yotoplay.com/content",
            headers={
                "Authorization": f"Bearer {manager.token.access_token}",
                "Content-Type": "application/json",
            },
            json=playlist_data,
            timeout=30,
        )
        
        response.raise_for_status()
        playlist = response.json()
        
        # The /content endpoint returns an id field
        playlist_id = playlist.get("id") or playlist.get("cardId") or playlist.get("contentId")
        logger.info(f"Created playlist '{request.playlist_name}' (ID: {playlist_id}) for stream '{stream_name}'")
        
        return {
            "success": True,
            "playlist_id": playlist_id,
            "playlist_name": request.playlist_name,
            "stream_name": stream_name,
            "streaming_url": streaming_url,
            "message": f"Playlist '{request.playlist_name}' created successfully!",
        }
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to create playlist: {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create playlist: {e.response.text}",
        ) from e
    except Exception as e:
        logger.error(f"Failed to create playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create playlist: {str(e)}",
        ) from e


@router.delete("/streams/playlists/{playlist_id}", status_code=status.HTTP_200_OK)
async def delete_playlist(
    playlist_id: str,
    user: User = Depends(require_auth),
):
    """
    Delete a Yoto playlist.
    
    Args:
        playlist_id: ID of the playlist to delete
        
    Returns:
        Success message
    """
    client = get_yoto_client()
    
    try:
        # Ensure we're authenticated
        manager = client.get_manager()
        manager.check_and_refresh_token()
        
        # Delete the playlist via Yoto API using /content endpoint
        response = requests.delete(
            f"https://api.yotoplay.com/content/{playlist_id}",
            headers={
                "Authorization": f"Bearer {manager.token.access_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        
        # 204 No Content or 200 OK both indicate success
        if response.status_code not in (200, 204):
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to delete playlist: {response.text}",
            )
        
        logger.info(f"Deleted playlist (ID: {playlist_id})")
        
        return {
            "success": True,
            "playlist_id": playlist_id,
            "message": "Playlist deleted successfully!",
        }
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to delete playlist: {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete playlist: {e.response.text}",
        ) from e
    except Exception as e:
        logger.error(f"Failed to delete playlist: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete playlist: {str(e)}",
        ) from e


# Playlist Search and Management


class PlaylistSearchResponse(BaseModel):
    """Response model for playlist search results."""
    
    playlists: List[dict] = Field(..., description="List of matching playlists")
    count: int = Field(..., description="Number of matching playlists")
    query: str = Field(..., description="The search query used")


@router.get("/streams/playlists/search/{playlist_name}", response_model=PlaylistSearchResponse)
async def search_playlists_by_name(
    playlist_name: str,
    user: User = Depends(require_auth),
):
    """
    Search for Yoto playlists by name.
    
    This searches the user's Yoto library for playlists matching the given name.
    Useful for finding and managing playlists, including orphaned ones.
    
    Args:
        playlist_name: Name (or partial name) to search for
        
    Returns:
        List of matching playlists with IDs and metadata
    """
    client = get_yoto_client()
    
    try:
        # Ensure we're authenticated and get library
        manager = client.get_manager()
        manager.check_and_refresh_token()
        
        # Update library from Yoto API
        client.update_library()
        
        # Get library data - library is a dict with card IDs as keys
        library_dict = manager.library
        
        if not library_dict:
            return {
                "playlists": [],
                "count": 0,
                "query": playlist_name,
            }
        
        def _safe_attr(obj, *names):
            for name in names:
                if hasattr(obj, name):
                    value = getattr(obj, name)
                    if value:
                        return value
            return None
        
        # Extract playlists/cards from the library
        all_items = []
        for card_id, card in library_dict.items():
            card_identifier = _safe_attr(card, 'cardId', 'id') or card_id
            title = _safe_attr(card, 'title', 'name') or "Untitled"
            
            item = {
                "id": card_identifier,
                "title": title,
                "description": _safe_attr(card, 'description') or "",
                "type": _safe_attr(card, 'type') or "unknown",
                "created_at": _safe_attr(card, 'created', 'createdAt') or "",
            }
            all_items.append(item)
        
        # Filter by name (case-insensitive, partial match)
        search_term = playlist_name.lower()
        matching_playlists = [
            item for item in all_items
            if search_term in item["title"].lower()
        ]
        
        logger.info(f"Found {len(matching_playlists)} items matching '{playlist_name}' out of {len(all_items)} total items")
        
        return {
            "playlists": matching_playlists,
            "count": len(matching_playlists),
            "query": playlist_name,
        }
        
    except Exception as e:
        logger.error(f"Failed to search playlists: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search playlists: {str(e)}",
        ) from e


class DeletePlaylistsRequest(BaseModel):
    """Request model for deleting multiple playlists."""
    
    playlist_ids: List[str] = Field(..., description="List of playlist IDs to delete", min_length=1)


@router.post("/streams/playlists/delete-multiple", status_code=status.HTTP_200_OK)
async def delete_multiple_playlists(
    request: DeletePlaylistsRequest,
    user: User = Depends(require_auth),
):
    """
    Delete multiple Yoto playlists by ID.
    
    This allows batch deletion of playlists, useful for cleaning up orphaned playlists.
    
    Args:
        request: DeletePlaylistsRequest with list of playlist IDs
        
    Returns:
        Results for each deletion attempt
    """
    client = get_yoto_client()
    results = {
        "success": [],
        "failed": [],
        "total": len(request.playlist_ids),
    }
    
    try:
        # Ensure we're authenticated
        manager = client.get_manager()
        manager.check_and_refresh_token()
        
        for playlist_id in request.playlist_ids:
            try:
                # Delete the playlist via Yoto API
                response = requests.delete(
                    f"https://api.yotoplay.com/content/{playlist_id}",
                    headers={
                        "Authorization": f"Bearer {manager.token.access_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )
                
                # 204 No Content or 200 OK both indicate success
                if response.status_code in (200, 204):
                    results["success"].append(playlist_id)
                    logger.info(f"Deleted playlist (ID: {playlist_id})")
                else:
                    results["failed"].append({
                        "playlist_id": playlist_id,
                        "error": f"Status {response.status_code}: {response.text}",
                    })
                    logger.warning(f"Failed to delete playlist {playlist_id}: {response.text}")
                    
            except Exception as e:
                results["failed"].append({
                    "playlist_id": playlist_id,
                    "error": str(e),
                })
                logger.error(f"Error deleting playlist {playlist_id}: {e}")
        
        return results
        
    except Exception as e:
        logger.error(f"Error in bulk delete operation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during bulk delete: {str(e)}",
        ) from e


# Streaming Endpoint


async def generate_sequential_stream(queue_files: List[str], audio_files_dir, play_mode: str = "sequential"):
    """
    Generator that streams multiple audio files sequentially or in other modes.

    This reads files one by one and yields their content, creating a
    continuous stream that appears as a single file to the client.

    Args:
        queue_files: List of audio filenames to stream
        audio_files_dir: Path to the audio files directory
        play_mode: How to play the files - "sequential" (once), "loop" (repeat), 
                   "shuffle" (random once), "endless-shuffle" (random forever)

    Yields:
        Audio data chunks
    """
    import random
    
    # Determine files to stream based on play mode
    if play_mode == "sequential":
        files_to_stream = queue_files
    elif play_mode == "loop":
        # Loop indefinitely - we'll yield a very large number of repetitions
        # In practice, the client will stop when it closes the connection
        files_to_stream = queue_files * 1000  # 1000 loops should be "endless" for most purposes
    elif play_mode == "shuffle":
        files_to_stream = list(queue_files)
        random.shuffle(files_to_stream)
    elif play_mode == "endless-shuffle":
        # Shuffle forever - generate random list repeatedly
        files_to_stream = []
        for _ in range(1000):  # 1000 shuffled repetitions
            shuffled = list(queue_files)
            random.shuffle(shuffled)
            files_to_stream.extend(shuffled)
    else:
        # Default to sequential for unknown modes
        files_to_stream = queue_files
    
    use_s3 = s3_enabled()
    s3_bucket = os.environ.get("S3_AUDIO_BUCKET") if use_s3 else None

    for filename in files_to_stream:
        if use_s3:
            if not s3_bucket:
                logger.error("S3 bucket not configured; skipping stream")
                continue
            if not object_exists(s3_bucket, filename):
                logger.warning(f"S3 object not found during streaming: {filename}, skipping")
                continue

            logger.info(f"Streaming file from S3: {filename} (mode: {play_mode})")
            try:
                async for chunk in _async_wrap_generator(stream_object(s3_bucket, filename, STREAM_CHUNK_SIZE)):
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                logger.error(f"Error streaming S3 file {filename}: {e}")
            continue

        audio_path = audio_files_dir / filename
        if not audio_path.exists():
            logger.warning(f"File not found during streaming: {filename}, skipping")
            continue

        logger.info(f"Streaming file: {filename} (mode: {play_mode})")
        try:
            with open(audio_path, "rb") as f:
                while True:
                    chunk = f.read(STREAM_CHUNK_SIZE)
                    if not chunk:
                        break
                    yield chunk
        except Exception as e:
            logger.error(f"Error streaming file {filename}: {e}")


@router.get("/streams/{stream_name}/stream.mp3")
async def stream_dynamic_audio(stream_name: str, play_mode: str = "sequential", request: Request = None):
    """
    Stream audio from a named queue as a continuous MP3 file.

    This endpoint streams all files in the queue sequentially, making them
    appear as a single continuous audio file to the client. Each client
    that connects gets the current queue state at connection time.

    Args:
        stream_name: Name of the stream queue to play
        play_mode: How to play the files - "sequential", "loop", "shuffle", or "endless-shuffle"
        request: HTTP request object for logging

    Returns:
        Streaming audio response with MP3 content
    """
    settings = get_settings()
    mqtt_store = get_mqtt_event_store()
    
    # Log incoming audio stream request with device state correlation
    if request:
        # Record stream request and correlate with MQTT events
        stream_request = mqtt_store.add_stream_request(
            stream_name=stream_name,
            device_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        # Get current device state
        device_state = mqtt_store.get_device_state()
        
        # Enhanced logging
        if settings.log_full_streams_requests:
            logger.info(
                f"🎵 STREAM REQUEST: {stream_name} "
                f"from {request.client.host if request.client else 'unknown'}"
            )
            
            # Log headers (redact Authorization)
            log_headers = dict(request.headers)
            if "authorization" in log_headers:
                log_headers["authorization"] = "[REDACTED]"
            logger.info(f"  Headers: {log_headers}")
            
            # Log query parameters
            if request.query_params:
                logger.info(f"  Query params: {dict(request.query_params)}")
        
        # Always log device state correlation if available
        if device_state:
            logger.info(
                f"  📱 Device State: status={device_state.playback_status}, "
                f"volume={device_state.volume}/{device_state.volume_max}, "
                f"streaming={device_state.streaming}, card={device_state.card_id}"
            )
        
        if settings.debug:
            logger.debug(f"  Stream request details: {stream_request.to_dict()}")
    
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
    
    # Get a snapshot of the current queue state for this client
    queue_snapshot = queue.get_files()
    
    # Validate play_mode
    valid_modes = ["sequential", "loop", "shuffle", "endless-shuffle"]
    if play_mode not in valid_modes:
        play_mode = "sequential"
    
    logger.info(f"Client connected to stream '{stream_name}' with {len(queue_snapshot)} files in {play_mode} mode")

    return StreamingResponse(
        generate_sequential_stream(queue_snapshot, settings.audio_files_dir, play_mode),
        media_type="audio/mpeg",
        headers={
            "Accept-Ranges": "none",  # Disable seeking since we're streaming multiple files
            "Cache-Control": "no-cache, no-store, must-revalidate",  # Don't cache dynamic content
            "X-Stream-Name": stream_name,
            "X-File-Count": str(len(queue_snapshot)),
            "X-Play-Mode": play_mode,
        },
    )


# MQTT Analysis and Device Control Endpoints


@router.get("/mqtt/analyzer")
async def get_mqtt_analyzer_data(user: User = Depends(require_auth)):
    """
    Get MQTT event data for the analyzer dashboard.

    Returns recent device state, MQTT events, and stream requests for visualization.
    """
    mqtt_store = get_mqtt_event_store()
    
    return {
        "success": True,
        "data": mqtt_store.to_dict(),
        "recent_events": [e.to_dict() for e in mqtt_store.get_recent_events(30)],
        "recent_stream_requests": [r.to_dict() for r in mqtt_store.get_stream_requests_since(300)],
    }


@router.post("/mqtt/track-nav")
async def track_navigation(
    direction: str,  # "next" or "previous"
    stream_name: str = None,
    user: User = Depends(require_auth)
):
    """
    Handle track navigation (next/previous) from device button clicks.
    
    This endpoint receives MQTT button click events (via left/right clicks)
    and can signal the streaming client to skip to next/previous track.
    
    Args:
        direction: "next" or "previous"
        stream_name: Optional stream context
    """
    mqtt_store = get_mqtt_event_store()
    
    if direction not in ["next", "previous"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="direction must be 'next' or 'previous'"
        )
    
    logger.info(f"Track navigation: {direction} for stream {stream_name}")
    
    return {
        "success": True,
        "direction": direction,
        "stream_name": stream_name,
        "current_state": mqtt_store.get_device_state().to_dict() if mqtt_store.get_device_state() else None,
    }


@router.get("/mqtt/device-state")
async def get_device_state(user: User = Depends(require_auth)):
    """Get current device state from last MQTT event."""
    mqtt_store = get_mqtt_event_store()
    device_state = mqtt_store.get_device_state()
    
    if not device_state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No device state available yet. Waiting for MQTT events from device."
        )
    
    return {
        "success": True,
        "device_state": device_state.to_dict(),
    }


@router.get("/streams/detect-smart-stream/{device_id}")
async def detect_smart_stream(device_id: str, user: User = Depends(require_auth)):
    """
    Detect if a device is playing a smart stream and identify the current track.
    
    Returns:
        {
            "is_playing_smart_stream": bool,
            "stream_name": str or None,
            "current_track_index": int or None,
            "current_track_name": str or None,
            "total_tracks": int or None,
            "streaming_url": str or None,
            "device_id": str,
            "playback_status": str or None,
            "playback_position": float or None (seconds)
        }
    """
    try:
        mqtt_store = get_mqtt_event_store()
        stream_manager = get_stream_manager()
        
        # Get the latest device state
        device_state = mqtt_store.get_device_state()
        
        # If no device state yet, return not playing
        if not device_state or device_state.device_id != device_id:
            return {
                "is_playing_smart_stream": False,
                "stream_name": None,
                "current_track_index": None,
                "current_track_name": None,
                "total_tracks": None,
                "streaming_url": None,
                "device_id": device_id,
                "playback_status": None,
                "playback_position": None,
            }
        
        # Check if device is streaming from our smart stream endpoint
        # The stream URL pattern is: /api/streams/{stream_name}/stream.mp3
        settings = get_settings()
        
        # List all available streams to check if any match the streaming URL
        is_playing_smart_stream = False
        matching_stream = None
        
        for stream_name in stream_manager.get_queue_names():
            queue = stream_manager.get_queue(stream_name)
            if queue:
                streaming_url = f"{settings.public_url}/api/streams/{stream_name}/stream.mp3"
                # In a real scenario, we'd need to track the actual card URL the device is playing
                # For now, we check if the stream name appears in recent requests
                matching_stream = stream_name
                break
        
        # Get recent stream requests to find matching stream
        recent_requests = mqtt_store.get_stream_requests_since(seconds=300)  # Last 5 minutes
        current_stream = None
        stream_start_time = None
        
        for req in recent_requests:
            if req.stream_name and req.timestamp:
                current_stream = req.stream_name
                stream_start_time = req.timestamp
                break
        
        if not current_stream:
            return {
                "is_playing_smart_stream": False,
                "stream_name": None,
                "current_track_index": None,
                "current_track_name": None,
                "total_tracks": None,
                "streaming_url": None,
                "device_id": device_id,
                "playback_status": device_state.playback_status,
                "playback_position": None,
            }
        
        # We found a recently requested stream
        queue = stream_manager.get_queue(current_stream)
        if not queue or not queue.get_files():
            return {
                "is_playing_smart_stream": False,
                "stream_name": current_stream,
                "current_track_index": None,
                "current_track_name": None,
                "total_tracks": 0,
                "streaming_url": f"{settings.public_url}/api/streams/{current_stream}/stream.mp3",
                "device_id": device_id,
                "playback_status": device_state.playback_status,
                "playback_position": None,
            }
        
        # Calculate which track is currently playing based on playback position
        files = queue.get_files()
        current_track_index = 0
        current_track_name = files[0] if files else None
        
        # In a real implementation, you'd calculate this based on:
        # 1. When the stream started playing on the device
        # 2. How long it's been playing
        # 3. The duration of each audio file
        # For now, we assume it's the first track if it's playing
        
        is_playing_smart_stream = device_state.streaming and device_state.playback_status == "playing"
        
        return {
            "is_playing_smart_stream": is_playing_smart_stream,
            "stream_name": current_stream if is_playing_smart_stream else None,
            "current_track_index": current_track_index if is_playing_smart_stream else None,
            "current_track_name": current_track_name if is_playing_smart_stream else None,
            "total_tracks": len(files),
            "streaming_url": f"{settings.public_url}/api/streams/{current_stream}/stream.mp3",
            "device_id": device_id,
            "playback_status": device_state.playback_status,
            "playback_position": None,  # Would need audio duration metadata to calculate
        }
        
    except Exception as e:
        logger.error(f"Error detecting smart stream for device {device_id}: {e}", exc_info=True)
        # Return graceful fallback instead of 500 error to prevent UI breakage
        logger.warning(f"Returning fallback response for device {device_id}")
        return {
            "is_playing_smart_stream": False,
            "stream_name": None,
            "current_track_index": None,
            "current_track_name": None,
            "total_tracks": None,
            "streaming_url": None,
            "device_id": device_id,
            "playback_status": None,
            "playback_position": None,
            "error": "Failed to detect stream"
        }
