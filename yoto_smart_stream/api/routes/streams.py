"""Dynamic audio streaming endpoints with queue management."""

import logging
from typing import List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ...config import get_settings
from ...database import get_db
from ...models import User
from .user_auth import require_auth
from ..stream_manager import get_stream_manager, StreamQueue
from ..dependencies import get_yoto_client

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
        
        token = manager.token
        if not token or not hasattr(token, 'access_token'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to Yoto first."
            )
        
        # Use correct authentication headers format
        headers = {
            'User-Agent': 'Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4',
            'Content-Type': 'application/json',
            'Authorization': f'{token.token_type} {token.access_token}',
        }
        
        # Delete the playlist via Yoto API using /content endpoint
        response = requests.delete(
            f"https://api.yotoplay.com/content/{playlist_id}",
            headers=headers,
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
    Search for Yoto playlists (MYO cards) by name.
    
    This searches the user's already-loaded Yoto library for playlists matching the given name.
    Useful for finding and managing playlists, including orphaned ones.
    
    Args:
        playlist_name: Name (or partial name) to search for
        
    Returns:
        List of matching playlists with IDs and metadata
    """
    client = get_yoto_client()
    
    try:
        # Ensure we're authenticated
        manager = client.get_manager()
        manager.check_and_refresh_token()
        
        # Get MYO content from /content/mine endpoint (this is what library.py uses)
        token = manager.token
        if not token or not hasattr(token, 'access_token'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to Yoto first."
            )
        
        # Use the same authentication headers format as library.py
        headers = {
            'User-Agent': 'Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4',
            'Content-Type': 'application/json',
            'Authorization': f'{token.token_type} {token.access_token}',
        }
        
        logger.info("Fetching MYO content from /content/mine endpoint...")
        response = requests.get(
            'https://api.yotoplay.com/content/mine',
            headers=headers,
            timeout=30
        )
        
        response.raise_for_status()
        data = response.json()
        
        # Extract playlists/cards from response (handle both list and dict formats)
        all_playlists = []
        if isinstance(data, list):
            all_playlists = data
        elif isinstance(data, dict) and 'items' in data:
            all_playlists = data['items']
        elif isinstance(data, dict) and 'content' in data:
            all_playlists = data['content']
        
        # Filter by name (case-insensitive, partial match)
        search_term = playlist_name.lower()
        matching_playlists = [
            {
                "id": p.get("id"),
                "title": p.get("title") or p.get("name", "Untitled"),
                "description": p.get("description", ""),
                "type": p.get("type", "myo"),
                "created_at": p.get("createdAt", ""),
            }
            for p in all_playlists
            if search_term in (p.get("title") or p.get("name", "")).lower()
        ]
        
        logger.info(f"Found {len(matching_playlists)} playlists matching '{playlist_name}'")
        
        return {
            "playlists": matching_playlists,
            "count": len(matching_playlists),
            "query": playlist_name,
        }
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"Failed to search playlists: {e.response.text}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search playlists: {e.response.text}",
        ) from e
    except Exception as e:
        logger.error(f"Failed to search playlists: {e}")
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
        
        token = manager.token
        if not token or not hasattr(token, 'access_token'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to Yoto first."
            )
        
        # Use correct authentication headers format
        headers = {
            'User-Agent': 'Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4',
            'Content-Type': 'application/json',
            'Authorization': f'{token.token_type} {token.access_token}',
        }
        
        for playlist_id in request.playlist_ids:
            try:
                # Delete the playlist via Yoto API
                response = requests.delete(
                    f"https://api.yotoplay.com/content/{playlist_id}",
                    headers=headers,
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
    
    for filename in files_to_stream:
        audio_path = audio_files_dir / filename
        if not audio_path.exists():
            logger.warning(f"File not found during streaming: {filename}, skipping")
            continue

        logger.info(f"Streaming file: {filename} (mode: {play_mode})")
        
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
async def stream_dynamic_audio(stream_name: str, play_mode: str = "sequential"):
    """
    Stream audio from a named queue as a continuous MP3 file.

    This endpoint streams all files in the queue sequentially, making them
    appear as a single continuous audio file to the client. Each client
    that connects gets the current queue state at connection time.

    Args:
        stream_name: Name of the stream queue to play
        play_mode: How to play the files - "sequential", "loop", "shuffle", or "endless-shuffle"

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
