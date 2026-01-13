"""Library management endpoints for viewing Yoto cards and playlists."""

import logging
import re

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..dependencies import get_yoto_client
from ...database import get_db
from ...models import User
from .user_auth import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/library")
async def get_library(user: User = Depends(require_auth)):
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
        
        # Extract playlists (MYO content) - fetch from /content/mine endpoint
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
                logger.info("Fetching MYO content from /content/mine endpoint...")
                response = requests.get('https://api.yotoplay.com/content/mine', headers=headers, timeout=10)
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


@router.get("/library/content/{content_id}")
async def get_content_details(content_id: str, user: User = Depends(require_auth)):
    """
    Get detailed information about a specific card or MYO content.
    
    Args:
        content_id: The ID of the card or MYO content
        
    Returns:
        Dictionary with detailed content information including chapters/tracks
    """
    try:
        # Validate content_id format (alphanumeric, hyphens, underscores only)
        if not re.match(r'^[a-zA-Z0-9_-]+$', content_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid content ID format"
            )
        
        client = get_yoto_client()
        manager = client.get_manager()
        
        # Get token for authentication
        token = manager.token
        if not token or not hasattr(token, 'access_token'):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to Yoto first."
            )
        
        # Make direct API call to content endpoint
        headers = {
            'User-Agent': 'Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4',
            'Content-Type': 'application/json',
            'Authorization': f'{token.token_type} {token.access_token}',
        }
        
        logger.info(f"Fetching content details for ID: {content_id}")
        response = requests.get(
            f'https://api.yotoplay.com/content/{content_id}',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content with ID {content_id} not found"
            )
        
        if response.status_code != 200:
            logger.warning(f"Failed to fetch content details: HTTP {response.status_code}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch content details: {response.text[:200]}"
            )
        
        content_data = response.json()
        logger.info(f"Successfully fetched content details for {content_id}")
        
        return content_data
        
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first."
        ) from e
    except Exception as e:
        logger.error(f"Error fetching content details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch content details: {str(e)}"
        ) from e


@router.get("/library/{card_id}/chapters")
async def get_card_chapters(card_id: str, user: User = Depends(require_auth)):
    """
    Get chapters for a specific card from the library.
    
    Args:
        card_id: The card ID
        
    Returns:
        List of chapters with their metadata
    """
    try:
        client = get_yoto_client()
        manager = client.get_manager()
        
        # Ensure library is loaded
        if not manager.library:
            manager.update_library()
        
        # Check if card exists in library
        if card_id not in manager.library:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Card {card_id} not found in library"
            )
        
        card = manager.library[card_id]
        
        # Update card details to get chapters if not already loaded
        if not card.chapters or len(card.chapters) == 0:
            logger.info(f"Fetching chapter details for card {card_id}")
            manager.update_card_detail(card_id)
        
        # Extract chapter information
        chapters = []
        if card.chapters:
            for chapter_key, chapter in card.chapters.items():
                chapter_info = {
                    'key': chapter_key,
                    'title': chapter.title if hasattr(chapter, 'title') else f'Chapter {chapter_key}',
                    'duration': chapter.duration if hasattr(chapter, 'duration') else None,
                    'icon': chapter.icon if hasattr(chapter, 'icon') else None,
                }
                chapters.append(chapter_info)
        
        return {
            'card_id': card_id,
            'card_title': card.title if hasattr(card, 'title') else 'Unknown',
            'card_author': card.author if hasattr(card, 'author') else '',
            'card_cover': card.cover_image_large if hasattr(card, 'cover_image_large') else None,
            'chapters': chapters,
            'total_chapters': len(chapters)
        }
        
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first."
        ) from e
    except Exception as e:
        logger.error(f"Error fetching card chapters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch card chapters: {str(e)}"
        ) from e


@router.get("/library/{card_id}/raw")
async def get_card_raw_data(card_id: str, user: User = Depends(require_auth)):
    """
    Get comprehensive raw data for a card including all metadata, chapters, and attributes.
    Useful for debugging and inspecting interactive cards.
    
    Args:
        card_id: The card ID
        
    Returns:
        Dictionary with all available card data
    """
    try:
        client = get_yoto_client()
        manager = client.get_manager()
        
        # Ensure library is loaded
        if not manager.library:
            manager.update_library()
        
        # Check if card exists in library
        if card_id not in manager.library:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Card {card_id} not found in library"
            )
        
        card = manager.library[card_id]
        
        # Update card details to get all information
        logger.info(f"Fetching comprehensive raw data for card {card_id}")
        manager.update_card_detail(card_id)
        
        # Extract all attributes from the card object
        raw_data = {
            'card_id': card_id,
            'metadata': {},
            'chapters': {},
            'attributes': {},
            'raw_object': {}
        }
        
        # Get all card attributes
        for attr_name in dir(card):
            # Skip private/magic methods and callables
            if attr_name.startswith('_') or callable(getattr(card, attr_name)):
                continue
            
            try:
                attr_value = getattr(card, attr_name)
                
                # Convert to serializable format
                if isinstance(attr_value, (str, int, float, bool, type(None))):
                    raw_data['attributes'][attr_name] = attr_value
                elif isinstance(attr_value, dict):
                    raw_data['attributes'][attr_name] = dict(attr_value)
                elif isinstance(attr_value, list):
                    raw_data['attributes'][attr_name] = list(attr_value)
                else:
                    # Try to convert to string for complex objects
                    raw_data['attributes'][attr_name] = str(attr_value)
            except Exception as e:
                logger.warning(f"Could not serialize attribute {attr_name}: {e}")
                raw_data['attributes'][attr_name] = f"<Error: {str(e)}>"
        
        # Extract standard metadata fields
        standard_fields = ['title', 'author', 'description', 'language', 'duration', 
                          'cover_image', 'cover_image_large', 'card_type', 'content_type',
                          'interactive', 'is_interactive', 'is_myo', 'is_podcast']
        for field in standard_fields:
            if hasattr(card, field):
                raw_data['metadata'][field] = getattr(card, field)
        
        # Extract chapters with full details
        if hasattr(card, 'chapters') and card.chapters:
            for chapter_key, chapter in card.chapters.items():
                chapter_data = {}
                for attr in dir(chapter):
                    if attr.startswith('_') or callable(getattr(chapter, attr)):
                        continue
                    try:
                        chapter_data[attr] = getattr(chapter, attr)
                    except:
                        pass
                raw_data['chapters'][chapter_key] = chapter_data
        
        # Try to get the raw JSON representation if available
        if hasattr(card, '__dict__'):
            try:
                raw_data['raw_object'] = {
                    k: v for k, v in card.__dict__.items() 
                    if not k.startswith('_')
                }
            except:
                pass
        
        return raw_data
        
    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first."
        ) from e
    except Exception as e:
        logger.error(f"Error fetching raw card data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch raw card data: {str(e)}"
        ) from e
