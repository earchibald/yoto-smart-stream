"""Library management endpoints for viewing Yoto cards and playlists."""

import json
import logging
import re

import requests
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ...models import User
from ..dependencies import get_yoto_client
from .user_auth import require_auth

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/library")
async def get_library(
    fresh: bool = Query(False, description="Force refresh and prune stale items"),
    user: User = Depends(require_auth),
):
    """
    Get user's Yoto library including cards and MYO (Make Your Own) content/playlists.

    Returns:
        Dictionary with cards and playlists from the user's Yoto library
    """
    try:
        client = get_yoto_client()
        manager = client.get_manager()

        # Update library from Yoto API (with cache clear via YotoClient)
        client.update_library()

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
                    if not attr.startswith("_"):
                        try:
                            value = getattr(card, attr)
                            if not callable(value):
                                card_attrs[attr] = value
                        except Exception:
                            pass
                logger.info(f"  card attributes and values: {card_attrs}")

        def _safe_attr(obj, *names):
            for name in names:
                if hasattr(obj, name):
                    value = getattr(obj, name)
                    if value:
                        return value
            return None

        # Extract cards from the dictionary with stable identifiers for downstream deletion
        cards = []
        if library_dict and isinstance(library_dict, dict):
            for card_id, card in library_dict.items():
                card_identifier = _safe_attr(card, "cardId", "id") or card_id
                content_id = (
                    _safe_attr(card, "contentId", "content_id", "card_id") or card_identifier
                )

                # Get cover image URL - check multiple possible locations
                cover_url = None
                cover_value = None

                # Try card.metadata['cover_image_large'] if metadata is a dict
                if hasattr(card, "metadata"):
                    metadata = card.metadata
                    if isinstance(metadata, dict) and "cover_image_large" in metadata:
                        cover_value = metadata["cover_image_large"]
                    elif hasattr(metadata, "cover_image_large"):
                        cover_value = metadata.cover_image_large
                # Fall back to card.cover_image_large
                if not cover_value and hasattr(card, "cover_image_large"):
                    cover_value = card.cover_image_large

                # Validate it's a proper URL
                if cover_value:
                    cover_str = str(cover_value).strip()
                    if cover_str and (
                        cover_str.startswith("http://") or cover_str.startswith("https://")
                    ):
                        cover_url = cover_str

                card_info = {
                    "id": card_identifier,
                    "cardId": card_identifier,
                    "contentId": content_id,
                    "title": card.title
                    if hasattr(card, "title") and card.title
                    else "Unknown Title",
                    "description": card.description if hasattr(card, "description") else "",
                    "author": card.author if hasattr(card, "author") else "",
                    "icon": None,
                    "cover": cover_url,
                    "type": _safe_attr(card, "type", "cardType") or "card",
                    "source": "card",
                }

                cards.append(card_info)

        logger.info(f"Processed {len(cards)} cards from library")

        # Extract playlists (MYO content) - fetch from /content/mine endpoint
        playlists = []
        existing_content_ids = set()
        try:
            # Make direct API call to MYO content endpoint
            # Note: yoto_api library doesn't have a built-in method for this yet
            token = manager.token
            if token and hasattr(token, "access_token"):
                # Use the same authentication headers format as yoto_api
                headers = {
                    "User-Agent": "Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4",
                    "Content-Type": "application/json",
                    "Authorization": f"{token.token_type} {token.access_token}",
                }
                logger.info("Fetching MYO content from /content/mine endpoint...")
                response = requests.get(
                    "https://api.yotoplay.com/content/mine", headers=headers, timeout=10
                )
                logger.info(f"MYO content endpoint response status: {response.status_code}")

                if response.status_code == 200:
                    myo_data = response.json()
                    logger.info(
                        f"MYO response type: {type(myo_data)}, keys: {myo_data.keys() if isinstance(myo_data, dict) else 'not a dict'}"
                    )

                    # MYO content may be in different formats - handle both list and dict with items
                    items = []
                    if isinstance(myo_data, list):
                        items = myo_data
                    elif isinstance(myo_data, dict) and "items" in myo_data:
                        items = myo_data["items"]
                    elif isinstance(myo_data, dict) and "content" in myo_data:
                        items = myo_data["content"]

                    logger.info(f"Found {len(items)} MYO content items")
                    for item in items:
                        playlist_id = item.get("id") or item.get("cardId") or item.get("contentId")
                        if playlist_id:
                            existing_content_ids.add(item.get("contentId") or playlist_id)
                        playlist_info = {
                            "id": playlist_id,
                            "cardId": item.get("cardId"),
                            "contentId": item.get("contentId") or playlist_id,
                            "name": item.get("title") or item.get("name", "Unknown Playlist"),
                            "imageId": item.get("imageId") or item.get("coverImageId"),
                            "itemCount": len(item.get("chapters", [])) if "chapters" in item else 0,
                            "type": "playlist",
                            "source": "playlist",
                        }
                        playlists.append(playlist_info)
                    logger.info(
                        f"Successfully processed {len(playlists)} playlists from MYO content"
                    )
                else:
                    logger.warning(
                        f"Failed to fetch MYO content: HTTP {response.status_code}, body: {response.text[:200]}"
                    )
            else:
                logger.warning(
                    f"Token not available or missing access_token: token={token}, has_access_token={hasattr(token, 'access_token') if token else False}"
                )
        except Exception as e:
            logger.error(f"Could not fetch MYO content/playlists: {e}", exc_info=True)

        # When fresh is requested, prune stale MYO-backed cards no longer present
        if fresh:
            pruned_cards = []
            for c in cards:
                cid = c.get("contentId")
                # Only prune if it looks like MYO content (has a contentId) and is missing
                if cid and existing_content_ids and cid not in existing_content_ids:
                    logger.info(
                        f"Pruning stale card not in MYO content list: {c.get('title')} ({cid})"
                    )
                    continue
                pruned_cards.append(c)
            cards = pruned_cards

        return {
            "cards": cards,
            "playlists": playlists,
            "totalCards": len(cards),
            "totalPlaylists": len(playlists),
        }

    except RuntimeError as e:
        # Not authenticated
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first.",
        ) from e
    except Exception as e:
        logger.error(f"Error fetching library: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch library: {str(e)}",
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
        if not re.match(r"^[a-zA-Z0-9_-]+$", content_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID format"
            )

        client = get_yoto_client()
        manager = client.get_manager()

        # Get token for authentication
        token = manager.token
        if not token or not hasattr(token, "access_token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to Yoto first.",
            )

        # Make direct API call to content endpoint
        headers = {
            "User-Agent": "Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4",
            "Content-Type": "application/json",
            "Authorization": f"{token.token_type} {token.access_token}",
        }

        logger.info(f"Fetching content details for ID: {content_id}")
        response = requests.get(
            f"https://api.yotoplay.com/content/{content_id}", headers=headers, timeout=10
        )

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content with ID {content_id} not found",
            )

        if response.status_code != 200:
            logger.warning(f"Failed to fetch content details: HTTP {response.status_code}")
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Failed to fetch content details: {response.text[:200]}",
            )

        content_data = response.json()
        logger.info(f"Successfully fetched content details for {content_id}")

        return content_data

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first.",
        ) from e
    except Exception as e:
        logger.error(f"Error fetching content details: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch content details: {str(e)}",
        ) from e


@router.delete("/library/{content_id}")
async def delete_library_item(content_id: str, user: User = Depends(require_auth)):
    """Delete a card or playlist from the user's library."""
    try:
        if not re.match(r"^[a-zA-Z0-9_-]+$", content_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid content ID format"
            )

        client = get_yoto_client()
        manager = client.get_manager()

        token = manager.token
        if not token or not hasattr(token, "access_token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated. Please log in to Yoto first.",
            )

        auth_header = f"{getattr(token, 'token_type', 'Bearer')} {token.access_token}"
        headers = {
            "User-Agent": "Yoto/2.73 (com.yotoplay.Yoto; build:10405; iOS 17.4.0) Alamofire/5.6.4",
            "Content-Type": "application/json",
            "Authorization": auth_header,
        }

        response = requests.delete(
            f"https://api.yotoplay.com/content/{content_id}", headers=headers, timeout=10
        )

        if response.status_code in (200, 204):
            try:
                manager.update_library()
            except Exception:
                logger.warning("Library refresh failed after delete", exc_info=True)

            return {
                "success": True,
                "contentId": content_id,
                "status": response.status_code,
                "message": "Deleted from library",
            }

        if response.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Content with ID {content_id} not found",
            )

        raise HTTPException(
            status_code=response.status_code,
            detail=f"Failed to delete content: {response.text[:200]}",
        )

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first.",
        ) from e
    except Exception as e:
        logger.error(f"Error deleting content: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete content: {str(e)}",
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
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Card {card_id} not found in library"
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
                    "key": chapter_key,
                    "title": chapter.title
                    if hasattr(chapter, "title")
                    else f"Chapter {chapter_key}",
                    "duration": chapter.duration if hasattr(chapter, "duration") else None,
                    "icon": chapter.icon if hasattr(chapter, "icon") else None,
                }
                chapters.append(chapter_info)

        # Get cover image URL - check multiple possible locations
        cover_url = None
        cover_value = None

        # Try card.metadata['cover_image_large'] if metadata is a dict
        if hasattr(card, "metadata"):
            metadata = card.metadata
            if isinstance(metadata, dict) and "cover_image_large" in metadata:
                cover_value = metadata["cover_image_large"]
            elif hasattr(metadata, "cover_image_large"):
                cover_value = metadata.cover_image_large
        # Fall back to card.cover_image_large
        if not cover_value and hasattr(card, "cover_image_large"):
            cover_value = card.cover_image_large

        # Validate it's a proper URL
        if cover_value:
            cover_str = str(cover_value).strip()
            if cover_str and (cover_str.startswith("http://") or cover_str.startswith("https://")):
                cover_url = cover_str

        return {
            "card_id": card_id,
            "card_title": card.title if hasattr(card, "title") else "Unknown",
            "card_author": card.author if hasattr(card, "author") else "",
            "card_cover": cover_url,
            "chapters": chapters,
            "total_chapters": len(chapters),
        }

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first.",
        ) from e
    except Exception as e:
        logger.error(f"Error fetching card chapters: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch card chapters: {str(e)}",
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
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Card {card_id} not found in library"
            )

        card = manager.library[card_id]

        # Update card details to get all information
        logger.info(f"Fetching comprehensive raw data for card {card_id}")
        manager.update_card_detail(card_id)

        # Extract all attributes from the card object
        raw_data = {
            "card_id": card_id,
            "metadata": {},
            "chapters": {},
            "attributes": {},
            "raw_object": {},
        }

        # Get all card attributes
        for attr_name in dir(card):
            # Skip private/magic methods and callables
            if attr_name.startswith("_") or callable(getattr(card, attr_name)):
                continue

            try:
                attr_value = getattr(card, attr_name)

                # Convert to serializable format
                if isinstance(attr_value, (str, int, float, bool, type(None))):
                    raw_data["attributes"][attr_name] = attr_value
                elif isinstance(attr_value, dict):
                    raw_data["attributes"][attr_name] = dict(attr_value)
                elif isinstance(attr_value, list):
                    raw_data["attributes"][attr_name] = list(attr_value)
                else:
                    # Try to convert to string for complex objects
                    raw_data["attributes"][attr_name] = str(attr_value)
            except Exception as e:
                logger.warning(f"Could not serialize attribute {attr_name}: {e}")
                raw_data["attributes"][attr_name] = f"<Error: {str(e)}>"

        # Extract standard metadata fields
        standard_fields = [
            "title",
            "author",
            "description",
            "language",
            "duration",
            "cover_image",
            "cover_image_large",
            "card_type",
            "content_type",
            "interactive",
            "is_interactive",
            "is_myo",
            "is_podcast",
        ]
        for field in standard_fields:
            if hasattr(card, field):
                raw_data["metadata"][field] = getattr(card, field)

        # Extract chapters with full details
        if hasattr(card, "chapters") and card.chapters:
            for chapter_key, chapter in card.chapters.items():
                chapter_data = {}
                for attr in dir(chapter):
                    if attr.startswith("_") or callable(getattr(chapter, attr)):
                        continue
                    try:
                        chapter_data[attr] = getattr(chapter, attr)
                    except Exception:
                        pass
                raw_data["chapters"][chapter_key] = chapter_data

        # Try to get the raw JSON representation if available
        if hasattr(card, "__dict__"):
            try:
                raw_data["raw_object"] = {
                    k: v for k, v in card.__dict__.items() if not k.startswith("_")
                }
            except Exception:
                pass

        return raw_data

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first.",
        ) from e
    except Exception as e:
        logger.error(f"Error fetching raw card data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch raw card data: {str(e)}",
        ) from e


def _clean_card_payload_for_update(payload: dict) -> dict:
    """
    Clean a card payload for update by removing null values that the Yoto API doesn't accept.

    The Yoto API expects certain fields to be objects or omitted entirely, not null.
    This function recursively removes null values from the payload.

    Args:
        payload: The card payload dictionary

    Returns:
        Cleaned payload dictionary with null values removed
    """
    if not isinstance(payload, dict):
        return payload

    cleaned = {}
    for key, value in payload.items():
        if value is None:
            # Skip null values
            continue
        elif isinstance(value, dict):
            # Recursively clean nested dictionaries
            cleaned_value = _clean_card_payload_for_update(value)
            if cleaned_value:  # Only include if not empty
                cleaned[key] = cleaned_value
        elif isinstance(value, list):
            # Clean list items
            cleaned_list = []
            for item in value:
                if isinstance(item, dict):
                    cleaned_item = _clean_card_payload_for_update(item)
                    if cleaned_item:  # Only include if not empty
                        cleaned_list.append(cleaned_item)
                elif item is not None:
                    cleaned_list.append(item)
            if cleaned_list:  # Only include if not empty
                cleaned[key] = cleaned_list
        else:
            cleaned[key] = value

    return cleaned


@router.post("/library/{card_id}/edit-check")
async def check_card_editable(card_id: str, user: User = Depends(require_auth)):
    """
    Check if a card is editable (MYO card) by attempting to update it with no changes.

    This endpoint:
    1. Fetches the card's raw JSON from the Yoto API
    2. Attempts to update the card with the exact same JSON
    3. Returns success if it's a MYO card, error if it's a commercial card

    Args:
        card_id: The card ID to check

    Returns:
        Dictionary with editability status and card data
    """
    try:
        client = get_yoto_client()
        manager = client.get_manager()

        logger.info(f"[EDIT CHECK] Checking if card {card_id} is editable")

        # Ensure library is loaded
        if not manager.library:
            manager.update_library()

        # Check if card exists in library
        if card_id not in manager.library:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Card {card_id} not found in library"
            )

        # Get the card's current JSON data directly from the API
        logger.info(f"[EDIT CHECK] Fetching card JSON from API for {card_id}")

        get_response = requests.get(
            f"https://api.yotoplay.com/content/{card_id}",
            headers={
                "Authorization": f"Bearer {manager.token.access_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        get_response.raise_for_status()
        card_json = get_response.json()

        logger.info(
            f"[EDIT CHECK] Fetched card JSON keys: {card_json.keys() if isinstance(card_json, dict) else 'not a dict'}"
        )
        logger.info(f"[EDIT CHECK] Full card JSON: {json.dumps(card_json, indent=2)[:500]}...")

        # Extract the card data
        # The GET /content/{id} response might be:
        # 1. { "card": { ... } } - wrapped in 'card' key
        # 2. { ... } - direct card data
        # We need to handle both cases

        if isinstance(card_json, dict):
            # Check if response has 'card' wrapper
            if "card" in card_json:
                card_data = card_json["card"]
                logger.info("[EDIT CHECK] Extracted card data from 'card' key")
            else:
                # Response is the card data directly
                card_data = card_json
                logger.info("[EDIT CHECK] Using response as card data directly (no 'card' wrapper)")
        else:
            card_data = {}
            logger.error(f"[EDIT CHECK] Unexpected response type: {type(card_json)}")

        # Build the update payload
        # The POST /content endpoint requires the full card structure with cardId
        update_payload = {**card_data, "cardId": card_id}

        # Clean the payload to remove null values that the Yoto API doesn't accept
        # The API expects certain fields to be objects or omitted, not null
        update_payload = _clean_card_payload_for_update(update_payload)

        logger.info(f"[EDIT CHECK] Update payload keys: {update_payload.keys()}")
        logger.info(
            f"[EDIT CHECK] Update payload (first 500 chars): {json.dumps(update_payload, indent=2)[:500]}..."
        )

        # Attempt to update the card with the same data
        response = requests.post(
            "https://api.yotoplay.com/content",
            headers={
                "Authorization": f"Bearer {manager.token.access_token}",
                "Content-Type": "application/json",
            },
            json=update_payload,
            timeout=30,
        )

        logger.info(f"[EDIT CHECK] Yoto API response status: {response.status_code}")
        logger.info(f"[EDIT CHECK] Yoto API response: {response.text}")

        response.raise_for_status()

        # If we got here, it's a MYO card and we can edit it!
        logger.info(f"✓ Card {card_id} is editable (MYO card)")
        return {
            "success": True,
            "editable": True,
            "card_id": card_id,
            "message": "Card is editable (MYO card)",
            "card_data": card_data,
        }

    except requests.exceptions.HTTPError as e:
        error_detail = e.response.text if hasattr(e, "response") else str(e)
        status_code = e.response.status_code if hasattr(e, "response") else 500

        logger.error(
            f"[EDIT CHECK] Card {card_id} update failed with HTTP {status_code}: {error_detail}"
        )

        # Determine if this is truly a commercial card or another issue
        if status_code == 404:
            # 404 typically means the card doesn't exist or is a commercial card that can't be updated
            message = "This is a commercial card and cannot be edited. Only MYO (Make Your Own) cards can be edited."
        elif status_code == 400:
            # 400 might mean malformed request - the card MIGHT be editable but our payload is wrong
            message = f"Card update failed - possibly incorrect payload format. Error: {error_detail[:200]}"
        elif status_code == 403:
            # 403 means forbidden - could be permissions or commercial card
            message = f"Access forbidden - this might be a commercial card or a permissions issue. Error: {error_detail[:200]}"
        else:
            # Other errors
            message = f"Card update failed with HTTP {status_code}. Error: {error_detail[:200]}"

        return {
            "success": False,
            "editable": False,
            "card_id": card_id,
            "status_code": status_code,
            "message": message,
            "error": error_detail,
        }

    except HTTPException:
        raise
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in to Yoto first.",
        ) from e
    except Exception as e:
        logger.error(f"[EDIT CHECK] Error checking card editability: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check card editability: {str(e)}",
        ) from e
