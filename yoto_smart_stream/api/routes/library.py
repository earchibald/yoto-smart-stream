"""Library management endpoints for viewing Yoto cards and playlists."""

import logging

from fastapi import APIRouter, HTTPException, status

from ..dependencies import get_yoto_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/library")
async def get_library():
    """
    Get user's Yoto library including cards and playlists (groups).
    
    Returns:
        Dictionary with cards and playlists from the user's Yoto library
    """
    try:
        client = get_yoto_client()
        manager = client.get_manager()
        
        # Update library from Yoto API
        manager.update_library()
        
        # Get library data
        library_data = manager.library
        
        # Extract cards
        cards = []
        if library_data and hasattr(library_data, 'cards'):
            for card in library_data.cards:
                card_info = {
                    'id': getattr(card, 'cardId', None),
                    'title': getattr(card, 'title', 'Unknown Title'),
                    'description': getattr(card, 'description', ''),
                    'author': getattr(card, 'author', ''),
                    'icon': None,
                    'cover': None,
                }
                
                # Try to get cover image
                if hasattr(card, 'metadata') and card.metadata:
                    metadata = card.metadata
                    if hasattr(metadata, 'cover') and metadata.cover:
                        cover = metadata.cover
                        # Get the largest available image
                        if hasattr(cover, 'imageL'):
                            card_info['cover'] = cover.imageL
                        elif hasattr(cover, 'imageM'):
                            card_info['cover'] = cover.imageM
                        elif hasattr(cover, 'imageS'):
                            card_info['cover'] = cover.imageS
                
                cards.append(card_info)
        
        # Extract playlists (groups)
        playlists = []
        if hasattr(manager, 'family') and manager.family:
            family = manager.family
            if hasattr(family, 'groups') and family.groups:
                for group in family.groups:
                    playlist_info = {
                        'id': getattr(group, 'id', None),
                        'name': getattr(group, 'name', 'Unknown Playlist'),
                        'imageId': getattr(group, 'imageId', None),
                        'itemCount': len(getattr(group, 'items', [])),
                    }
                    playlists.append(playlist_info)
        
        return {
            'cards': cards,
            'playlists': playlists,
            'totalCards': len(cards),
            'totalPlaylists': len(playlists),
        }
        
    except RuntimeError as e:
        # Not authenticated
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first."
        ) from e
    except Exception as e:
        logger.error(f"Error fetching library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch library: {str(e)}"
        ) from e
