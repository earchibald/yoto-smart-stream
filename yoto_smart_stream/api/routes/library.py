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
        
        # Get library data - library is a dict with card IDs as keys
        library_dict = manager.library
        
        # Extract cards from the dictionary
        cards = []
        if library_dict and isinstance(library_dict, dict):
            for card_id, card in library_dict.items():
                card_info = {
                    'id': card.id if hasattr(card, 'id') else card_id,
                    'title': card.title if hasattr(card, 'title') and card.title else 'Unknown Title',
                    'description': card.description if hasattr(card, 'description') else '',
                    'author': card.author if hasattr(card, 'author') else '',
                    'icon': None,
                    'cover': card.cover_image_large if hasattr(card, 'cover_image_large') else None,
                }
                
                cards.append(card_info)
        
        # Extract playlists (groups) - Note: groups are not directly supported by yoto_api library
        # They would need to be fetched via direct API calls to /groups endpoint
        # For now, return empty list until groups support is added
        playlists = []
        # Future enhancement: Add direct API call to GET /groups endpoint
        
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
