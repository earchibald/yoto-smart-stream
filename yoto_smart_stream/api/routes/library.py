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
    Get user's Yoto library including cards and MYO (Make Your Own) content/playlists.
    
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
        
        # Log detailed information about the first few items to understand their structure
        if library_dict:
            sample_size = min(5, len(library_dict))
            logger.info(f"=== Examining first {sample_size} items in library ===")
            for idx, (card_id, card) in enumerate(list(library_dict.items())[:sample_size]):
                logger.info(f"Item {idx + 1}:")
                logger.info(f"  card_id (key): {card_id}")
                logger.info(f"  type: {type(card)}")
                logger.info(f"  card object attributes: {dir(card)}")
                
                # Log all non-private attributes and their values
                card_attrs = {}
                for attr in dir(card):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(card, attr)
                            if not callable(value):
                                card_attrs[attr] = value
                        except:
                            pass
                logger.info(f"  card attributes and values: {card_attrs}")
        
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
        
        # Extract playlists (MYO content) - fetch from /users/me/myo/content endpoint
        playlists = []
        try:
            # Make direct API call to MYO content endpoint
            # Note: yoto_api library doesn't have a built-in method for this yet
            token = manager.token
            if token and hasattr(token, 'access_token'):
                # Use the same authentication headers format as yoto_api
                headers = {
                    'User-Agent': 'Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4',
                    'Content-Type': 'application/json',
                    'Authorization': f'{token.token_type} {token.access_token}',
                }
                logger.info("Fetching MYO content from /users/me/myo/content endpoint...")
                response = requests.get('https://api.yotoplay.com/users/me/myo/content', headers=headers, timeout=10)
                logger.info(f"MYO content endpoint response status: {response.status_code}")
                
                if response.status_code == 200:
                    myo_data = response.json()
                    logger.info(f"MYO response type: {type(myo_data)}, keys: {myo_data.keys() if isinstance(myo_data, dict) else 'not a dict'}")
                    
                    # MYO content may be in different formats - handle both list and dict with items
                    items = []
                    if isinstance(myo_data, list):
                        items = myo_data
                    elif isinstance(myo_data, dict) and 'items' in myo_data:
                        items = myo_data['items']
                    elif isinstance(myo_data, dict) and 'content' in myo_data:
                        items = myo_data['content']
                    
                    logger.info(f"Found {len(items)} MYO content items")
                    for item in items:
                        playlist_info = {
                            'id': item.get('id'),
                            'name': item.get('title') or item.get('name', 'Unknown Playlist'),
                            'imageId': item.get('imageId') or item.get('coverImageId'),
                            'itemCount': len(item.get('chapters', [])) if 'chapters' in item else 0,
                        }
                        playlists.append(playlist_info)
                    logger.info(f"Successfully processed {len(playlists)} playlists from MYO content")
                else:
                    logger.warning(f"Failed to fetch MYO content: HTTP {response.status_code}, body: {response.text[:200]}")
            else:
                logger.warning(f"Token not available or missing access_token: token={token}, has_access_token={hasattr(token, 'access_token') if token else False}")
        except Exception as e:
            logger.error(f"Could not fetch MYO content/playlists: {e}", exc_info=True)
        
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
