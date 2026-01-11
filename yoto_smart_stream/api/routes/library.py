"""Library management endpoints for viewing Yoto cards and playlists."""

import logging

import requests
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
        logger.info(f"Library contains {len(library_dict)} total items")
        
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
        
        logger.info(f"Processed {len(cards)} cards from library")
        
        # Extract playlists (groups) - fetch from /groups endpoint
        playlists = []
        try:
            # Make direct API call to /groups endpoint
            # Note: yoto_api library doesn't have a built-in method for this yet
            token = manager.token
            if token and hasattr(token, 'access_token'):
                # Use the same authentication headers format as yoto_api
                headers = {
                    'User-Agent': 'Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4',
                    'Content-Type': 'application/json',
                    'Authorization': f'{token.token_type} {token.access_token}',
                }
                logger.info("Fetching groups from /groups endpoint...")
                response = requests.get('https://api.yotoplay.com/groups', headers=headers, timeout=10)
                logger.info(f"Groups endpoint response status: {response.status_code}")
                
                if response.status_code == 200:
                    groups_data = response.json()
                    logger.info(f"Groups response type: {type(groups_data)}, data: {groups_data if isinstance(groups_data, list) and len(groups_data) < 10 else 'large dataset'}")
                    
                    if isinstance(groups_data, list):
                        for group in groups_data:
                            playlist_info = {
                                'id': group.get('id'),
                                'name': group.get('name', 'Unknown Playlist'),
                                'imageId': group.get('imageId'),
                                'itemCount': len(group.get('items', [])),
                            }
                            playlists.append(playlist_info)
                        logger.info(f"Successfully fetched {len(playlists)} playlists from /groups endpoint")
                    else:
                        logger.warning(f"Groups data is not a list: {type(groups_data)}")
                else:
                    logger.warning(f"Failed to fetch groups: HTTP {response.status_code}, body: {response.text[:200]}")
            else:
                logger.warning(f"Token not available or missing access_token: token={token}, has_access_token={hasattr(token, 'access_token') if token else False}")
        except Exception as e:
            logger.error(f"Could not fetch groups/playlists: {e}", exc_info=True)
        
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
