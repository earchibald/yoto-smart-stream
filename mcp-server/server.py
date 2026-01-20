"""
Yoto Library MCP Server

An MCP server that provides natural language query capabilities for Yoto card library data.
Connects to the yoto-smart-stream service to access library information.

Usage:
    python server.py --yoto-service-url https://your-deployment.railway.app \\
                     --username admin --password secret
    
Environment Variables:
    YOTO_SERVICE_URL: Default service URL (overridable per-query)
    ADMIN_USERNAME: Admin username for authentication
    ADMIN_PASSWORD: Admin password for authentication
    YOTO_USERNAME: Yoto account email for OAuth automation
    YOTO_PASSWORD: Yoto account password for OAuth automation
"""

import argparse
import asyncio
import logging
import os
from typing import Any, Optional

import httpx
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, ConfigDict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("yoto_library_mcp")

# Global configuration variables
ADMIN_USERNAME = ""
ADMIN_PASSWORD = ""
YOTO_USERNAME = ""
YOTO_PASSWORD = ""
YOTO_SERVICE_URL = ""

# Per-host authentication cache: {service_url: cookies}
AUTH_CACHE: dict[str, httpx.Cookies] = {}

# Constants
MAX_DESCRIPTION_LENGTH = 100
MAX_CARDS_TO_DISPLAY = 20


class OAuthInput(BaseModel):
    """Input model for OAuth operations."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    service_url: Optional[str] = Field(
        default=None,
        description="URL of the yoto-smart-stream service (uses default if not provided)"
    )
    action: str = Field(
        ...,
        description="Action to perform: 'activate' to log in to Yoto OAuth, 'deactivate' to log out"
    )


class LibraryStatsInput(BaseModel):
    """Get library statistics."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    service_url: Optional[str] = Field(
        default=None,
        description="URL of the yoto-smart-stream service (uses default if not provided)"
    )


class ListCardsInput(BaseModel):
    """List cards in the library with optional filtering."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of cards to return (1-100)"
    )
    service_url: Optional[str] = Field(
        default=None,
        description="URL of the yoto-smart-stream service (uses default if not provided)"
    )


class SearchCardsInput(BaseModel):
    """Search for cards by title."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    title_contains: str = Field(
        ...,
        description="Search for cards with this text in the title",
        min_length=1
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results to return (1-100)"
    )
    service_url: Optional[str] = Field(
        default=None,
        description="URL of the yoto-smart-stream service (uses default if not provided)"
    )


class ListPlaylistsInput(BaseModel):
    """List playlists in the library."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    service_url: Optional[str] = Field(
        default=None,
        description="URL of the yoto-smart-stream service (uses default if not provided)"
    )


class GetMetadataKeysInput(BaseModel):
    """Get all metadata keys used in the library."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    service_url: Optional[str] = Field(
        default=None,
        description="URL of the yoto-smart-stream service (uses default if not provided)"
    )


class GetFieldValuesInput(BaseModel):
    """Get all unique values for a specific card field."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    field_name: str = Field(
        ...,
        description="The card field to get values for (e.g., 'author', 'type', 'genre')",
        min_length=1
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of values to return (1-500)"
    )
    service_url: Optional[str] = Field(
        default=None,
        description="URL of the yoto-smart-stream service (uses default if not provided)"
    )


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Yoto Library MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (used if args not provided):
  YOTO_SERVICE_URL    Default URL of yoto-smart-stream deployment
  ADMIN_USERNAME      Username for authentication
  ADMIN_PASSWORD      Password for authentication
  YOTO_USERNAME       Yoto account email for OAuth
  YOTO_PASSWORD       Yoto account password for OAuth

Examples:
  %(prog)s --yoto-service-url https://app.railway.app --username admin --password secret
  YOTO_SERVICE_URL=https://app.railway.app %(prog)s
        """,
    )

    parser.add_argument(
        "--url", help="URL of yoto-smart-stream service (env: YOTO_SERVICE_URL)"
    )
    parser.add_argument(
        "--yoto-service-url", dest="yoto_service_url",
        help="Default Yoto service URL for all queries (overridable per query)"
    )
    parser.add_argument(
        "--username", help="Admin username for authentication (env: ADMIN_USERNAME)"
    )
    parser.add_argument(
        "--password", help="Admin password for authentication (env: ADMIN_PASSWORD)"
    )

    return parser.parse_args()


def configure_from_args():
    """Configure global variables from command line args or environment."""
    global YOTO_SERVICE_URL, ADMIN_USERNAME, ADMIN_PASSWORD, YOTO_USERNAME, YOTO_PASSWORD

    args = parse_args()

    # Priority: CLI args > environment variables > defaults
    # Support both --url and --yoto-service-url for backwards compatibility
    YOTO_SERVICE_URL = (
        args.url 
        or args.yoto_service_url 
        or os.getenv("YOTO_SERVICE_URL") 
        or ""
    )
    ADMIN_USERNAME = args.username or os.getenv("ADMIN_USERNAME") or "admin"
    ADMIN_PASSWORD = args.password or os.getenv("ADMIN_PASSWORD") or ""
    YOTO_USERNAME = os.getenv("YOTO_USERNAME") or ""
    YOTO_PASSWORD = os.getenv("YOTO_PASSWORD") or ""

    # Only log if YOTO_SERVICE_URL was provided
    if YOTO_SERVICE_URL:
        logger.info(f"Default service URL: {YOTO_SERVICE_URL}")
    else:
        logger.info("No default service URL provided - service_url optional in tool calls")
    
    logger.info(f"Using admin username: {ADMIN_USERNAME}")

    if not ADMIN_PASSWORD:
        logger.warning("No admin password provided! Tool calls may fail.")
        logger.warning(
            "Set ADMIN_PASSWORD environment variable or use --password argument."
        )

    if YOTO_USERNAME and YOTO_PASSWORD:
        logger.info("Yoto OAuth credentials available for automated login")


async def authenticate_host(service_url: str) -> Optional[httpx.Cookies]:
    """Authenticate with a specific host and cache the session cookies."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth_response = await client.post(
                f"{service_url}/api/user/login",
                json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            )

            if auth_response.status_code != 200:
                logger.error(
                    f"Authentication failed for {service_url}: {auth_response.status_code}"
                )
                return None

            # Cache the session cookies for this host
            AUTH_CACHE[service_url] = auth_response.cookies
            logger.info(f"Successfully authenticated with {service_url}")
            return auth_response.cookies

    except Exception as e:
        logger.error(f"Error authenticating with {service_url}: {e}")
        return None


async def get_library_data(service_url: str) -> dict[str, Any]:
    """Fetch library data from the yoto-smart-stream service."""
    try:
        # Check if we have cached authentication for this host
        cookies = AUTH_CACHE.get(service_url)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # If no cached auth, authenticate first
            if not cookies:
                cookies = await authenticate_host(service_url)
                if not cookies:
                    return {
                        "error": "Authentication failed",
                        "cards": [],
                        "playlists": [],
                    }

            # Fetch library data
            response = await client.get(
                f"{service_url}/api/library",
                cookies=cookies,
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch library: {response.status_code}")
                return {"error": f"HTTP {response.status_code}", "cards": [], "playlists": []}

    except Exception as e:
        logger.error(f"Error fetching library data: {e}")
        return {"error": str(e), "cards": [], "playlists": []}


def search_library(library_data: dict, title_contains: str, limit: int = 20) -> list[dict]:
    """Search library for cards by title."""
    cards = library_data.get("cards", [])
    
    if library_data.get("error"):
        return []
    
    matching = [c for c in cards if title_contains.lower() in c.get("title", "").lower()]
    return matching[:limit]


def get_library_stats(library_data: dict) -> dict[str, Any]:
    """Get library statistics."""
    if library_data.get("error"):
        return {"error": library_data.get("error"), "total_cards": 0, "total_playlists": 0}
    
    cards = library_data.get("cards", [])
    playlists = library_data.get("playlists", [])
    
    return {
        "total_cards": len(cards),
        "total_playlists": len(playlists)
    }


def get_all_cards(library_data: dict, limit: int = 20) -> list[dict]:
    """Get all cards from library."""
    cards = library_data.get("cards", [])
    
    if library_data.get("error"):
        return []
    
    return cards[:limit]


def get_all_playlists(library_data: dict) -> list[dict]:
    """Get all playlists from library."""
    playlists = library_data.get("playlists", [])
    
    if library_data.get("error"):
        return []
    
    return playlists


def get_metadata_keys(library_data: dict) -> list[str]:
    """Get all unique metadata keys used in cards."""
    cards = library_data.get("cards", [])
    
    if library_data.get("error"):
        return []
    
    # Collect all keys from all cards
    keys_set = set()
    for card in cards:
        keys_set.update(card.keys())
    
    return sorted(list(keys_set))


def get_field_values(library_data: dict, field_name: str, limit: int = 50) -> list[str]:
    """Get all unique values for a specific field."""
    cards = library_data.get("cards", [])
    
    if library_data.get("error"):
        return []
    
    # Collect unique values for the field
    values_set = set()
    for card in cards:
        value = card.get(field_name)
        if value is not None:
            # Handle both strings and lists
            if isinstance(value, list):
                values_set.update(str(v) for v in value)
            else:
                values_set.add(str(value))
    
    return sorted(list(values_set))[:limit]


async def activate_yoto_oauth(service_url: str) -> str:
    """Activate Yoto OAuth by automating the device code flow."""
    if not YOTO_USERNAME or not YOTO_PASSWORD:
        return (
            "ERROR: YOTO_USERNAME and YOTO_PASSWORD environment variables are required for OAuth automation.\n\n"
            "Please set these variables with your Yoto account credentials:\n"
            "  export YOTO_USERNAME='your-email@example.com'\n"
            "  export YOTO_PASSWORD='your-yoto-password'\n\n"
            "Status: error"
        )

    try:
        # Get cached cookies for admin auth
        cookies = AUTH_CACHE.get(service_url)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Authenticate with admin if needed
            if not cookies:
                cookies = await authenticate_host(service_url)
                if not cookies:
                    return f"Error: Failed to authenticate with {service_url}\nStatus: error"

            # Start OAuth device code flow
            logger.info(f"Starting Yoto OAuth device code flow for {service_url}...")
            start_response = await client.post(
                f"{service_url}/api/auth/start",
                cookies=cookies,
            )

            if start_response.status_code != 200:
                return f"Error: Failed to start OAuth: {start_response.status_code}\n{start_response.text[:200]}\nStatus: error"

            flow_data = start_response.json()
            device_code = flow_data.get("device_code")
            user_code = flow_data.get("user_code")
            verification_uri = flow_data.get("verification_uri")

            if not device_code:
                return f"Error: No device code returned from server\nStatus: error"

            logger.info(f"Device code: {device_code}, User code: {user_code}")

            # Try browser automation with Playwright if available
            try:
                from playwright.async_api import async_playwright

                logger.info("Attempting browser automation with Playwright...")
                async with async_playwright() as p:
                    browser = await p.chromium.launch()
                    page = await browser.new_page()

                    # Navigate to verification URI
                    await page.goto(verification_uri, wait_until="networkidle")

                    # Enter user code
                    code_input = page.locator('input[type="text"]').first
                    if await code_input.is_visible(timeout=5000):
                        await code_input.fill(user_code)

                    # Click submit
                    submit_button = page.locator(
                        'button:has-text("Submit"), button:has-text("Continue"), button[type="submit"]'
                    ).first
                    await submit_button.click()
                    await page.wait_for_load_state("networkidle")

                    # Enter credentials if needed
                    email_input = page.locator(
                        'input[type="email"], input[name*="email"]'
                    ).first
                    if await email_input.is_visible(timeout=5000):
                        await email_input.fill(YOTO_USERNAME)

                    password_input = page.locator(
                        'input[type="password"], input[name*="password"]'
                    ).first
                    if await password_input.is_visible(timeout=5000):
                        await password_input.fill(YOTO_PASSWORD)

                    # Click sign in
                    signin_button = page.locator(
                        'button:has-text("Sign in"), button:has-text("Log in"), button[type="submit"]'
                    ).first
                    await signin_button.click()
                    await page.wait_for_load_state("networkidle")

                    # Look for authorize/allow button
                    authorize_button = page.locator(
                        'button:has-text("Authorize"), button:has-text("Allow"), button:has-text("Accept")'
                    ).first
                    if await authorize_button.is_visible(timeout=5000):
                        await authorize_button.click()
                        await page.wait_for_load_state("networkidle")

                    await browser.close()
                    logger.info("Browser automation completed")

            except ImportError:
                return (
                    "Error: Playwright is not installed.\n\n"
                    "To use automated OAuth, install playwright:\n"
                    "  pip install playwright\n"
                    "  playwright install chromium\n\n"
                    "Status: error"
                )
            except Exception as browser_error:
                logger.error(f"Browser automation error: {browser_error}")
                return f"Warning: Browser automation failed: {browser_error}\n\nYou may need to manually complete the OAuth flow at:\n{verification_uri}\nUser code: {user_code}\nStatus: pending"

            # Poll for OAuth completion
            logger.info("Polling for OAuth completion...")
            for _ in range(12):  # Poll for up to 60 seconds
                await asyncio.sleep(5)

                poll_response = await client.post(
                    f"{service_url}/api/auth/poll",
                    json={"device_code": device_code},
                    cookies=cookies,
                )

                if poll_response.status_code == 200:
                    poll_data = poll_response.json()
                    status = poll_data.get("status", "unknown")
                    
                    if poll_data.get("authenticated"):
                        return (
                            f"Success: Yoto OAuth activated successfully for {service_url}!\n"
                            f"Message: {poll_data.get('message', 'Authenticated')}\n"
                            f"Status: {status}"
                        )
                    elif status == "pending":
                        continue
                    elif status == "error":
                        return f"Error: OAuth error: {poll_data.get('message')}\nStatus: {status}"
                    elif status == "expired":
                        return f"Error: Authentication expired. Please start again.\nStatus: {status}"

            return (
                f"Timeout: OAuth polling timed out. The authentication may still complete.\n\n"
                f"If not completed, you can manually authorize at:\n"
                f"{verification_uri}\n"
                f"User code: {user_code}\n"
                f"Status: pending"
            )

    except Exception as e:
        logger.error(f"Error activating OAuth for {service_url}: {e}")
        return f"Error: {str(e)}\nStatus: error"


async def deactivate_yoto_oauth(service_url: str) -> str:
    """Deactivate Yoto OAuth by logging out."""
    try:
        # Get cached cookies for admin auth
        cookies = AUTH_CACHE.get(service_url)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Authenticate with admin if needed
            if not cookies:
                cookies = await authenticate_host(service_url)
                if not cookies:
                    return f"Error: Failed to authenticate with {service_url}\nStatus: error"

            # Call logout endpoint
            logger.info(f"Deactivating Yoto OAuth for {service_url}...")
            logout_response = await client.post(
                f"{service_url}/api/auth/logout",
                cookies=cookies,
            )

            if logout_response.status_code == 200:
                logout_data = logout_response.json()
                return (
                    f"Success: Yoto OAuth deactivated successfully for {service_url}\n"
                    f"Message: {logout_data.get('message', 'Logged out')}\n"
                    f"Status: success"
                )
            else:
                return f"Error: Failed to deactivate OAuth: HTTP {logout_response.status_code}\n{logout_response.text}\nStatus: error"

    except Exception as e:
        logger.error(f"Error deactivating OAuth for {service_url}: {e}")
        return f"Error: {str(e)}\nStatus: error"


# FastMCP Tools
@mcp.tool(
    name="oauth",
    annotations={
        "title": "Manage Yoto OAuth",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def manage_oauth(params: OAuthInput) -> str:
    """Manage Yoto OAuth authentication.
    
    Activate or deactivate Yoto OAuth authentication for a yoto-smart-stream service.
    Use 'activate' to log in (requires YOTO_USERNAME and YOTO_PASSWORD env vars),
    or 'deactivate' to log out.
    
    Returns a response with Status field indicating the result:
    - 'success': Operation completed successfully
    - 'pending': Waiting for user action or still polling
    - 'error': An error occurred
    - 'expired': Token/code has expired
    """
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return "Error: No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable.\nStatus: error"

    if params.action.lower() == "activate":
        return await activate_yoto_oauth(service_url)
    elif params.action.lower() == "deactivate":
        return await deactivate_yoto_oauth(service_url)
    else:
        return f"Error: Unknown action '{params.action}'. Use 'activate' or 'deactivate'.\nStatus: error"


# FastMCP Library Query Tools

@mcp.tool(
    name="library_stats",
    annotations={
        "title": "Get Library Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def library_stats_tool(params: LibraryStatsInput) -> dict[str, Any]:
    """Get library statistics (total cards and playlists)."""
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return {"error": "No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable."}
    
    logger.info(f"Getting library stats for {service_url}")
    library_data = await get_library_data(service_url)
    return get_library_stats(library_data)


@mcp.tool(
    name="list_cards",
    annotations={
        "title": "List All Cards",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_cards_tool(params: ListCardsInput) -> dict[str, Any]:
    """List cards in the library."""
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return {"error": "No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable."}
    
    logger.info(f"Listing cards for {service_url} (limit: {params.limit})")
    library_data = await get_library_data(service_url)
    
    if library_data.get("error"):
        return {"error": library_data.get("error"), "cards": []}
    
    cards = get_all_cards(library_data, params.limit)
    return {
        "total_cards": len(library_data.get("cards", [])),
        "returned_count": len(cards),
        "cards": [
            {
                "id": card.get("id"),
                "title": card.get("title"),
                "author": card.get("author"),
                "type": card.get("type"),
                "description": card.get("description", "")[:MAX_DESCRIPTION_LENGTH],
            }
            for card in cards
        ]
    }


@mcp.tool(
    name="search_cards",
    annotations={
        "title": "Search Cards by Title",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def search_cards_tool(params: SearchCardsInput) -> dict[str, Any]:
    """Search for cards where title contains the specified text."""
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return {"error": "No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable."}
    
    logger.info(f"Searching cards for '{params.title_contains}' on {service_url} (limit: {params.limit})")
    library_data = await get_library_data(service_url)
    
    if library_data.get("error"):
        return {"error": library_data.get("error"), "matches": []}
    
    cards = search_library(library_data, params.title_contains, params.limit)
    return {
        "search_term": params.title_contains,
        "matched_count": len(cards),
        "matches": [
            {
                "id": card.get("id"),
                "title": card.get("title"),
                "author": card.get("author"),
                "type": card.get("type"),
                "description": card.get("description", "")[:MAX_DESCRIPTION_LENGTH],
            }
            for card in cards
        ]
    }


@mcp.tool(
    name="list_playlists",
    annotations={
        "title": "List All Playlists",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_playlists_tool(params: ListPlaylistsInput) -> dict[str, Any]:
    """List all playlists in the library."""
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return {"error": "No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable."}
    
    logger.info(f"Listing playlists for {service_url}")
    library_data = await get_library_data(service_url)
    
    if library_data.get("error"):
        return {"error": library_data.get("error"), "playlists": []}
    
    playlists = get_all_playlists(library_data)
    return {
        "total_playlists": len(playlists),
        "playlists": [
            {
                "id": pl.get("id"),
                "name": pl.get("name"),
                "item_count": pl.get("itemCount", 0),
            }
            for pl in playlists
        ]
    }


@mcp.tool(
    name="get_metadata_keys",
    annotations={
        "title": "Get Metadata Keys",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_metadata_keys_tool(params: GetMetadataKeysInput) -> dict[str, Any]:
    """Get all unique metadata keys used across library cards."""
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return {"error": "No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable."}
    
    logger.info(f"Getting metadata keys for {service_url}")
    library_data = await get_library_data(service_url)
    
    if library_data.get("error"):
        return {"error": library_data.get("error"), "keys": []}
    
    keys = get_metadata_keys(library_data)
    return {
        "total_keys": len(keys),
        "keys": keys
    }


@mcp.tool(
    name="get_field_values",
    annotations={
        "title": "Get Field Values",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def get_field_values_tool(params: GetFieldValuesInput) -> dict[str, Any]:
    """Get all unique values for a specific card field."""
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return {"error": "No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable."}
    
    logger.info(f"Getting values for field '{params.field_name}' on {service_url} (limit: {params.limit})")
    library_data = await get_library_data(service_url)
    
    if library_data.get("error"):
        return {"error": library_data.get("error"), "values": []}
    
    values = get_field_values(library_data, params.field_name, params.limit)
    return {
        "field_name": params.field_name,
        "total_unique_values": len(values),
        "values": values
    }


async def main():
    """Run the MCP server (async version)."""
    # Configure from args/env first
    configure_from_args()

    logger.info("Yoto Library MCP Server starting...")
    if YOTO_SERVICE_URL:
        logger.info(f"Default service URL: {YOTO_SERVICE_URL}")
    logger.info("Waiting for tool calls on stdio transport...")

    # Run the FastMCP server on stdio transport
    await mcp.run_stdio_async()


def main_sync():
    """Synchronous entry point that runs the FastMCP server."""
    # FastMCP.run_stdio_async() needs to be wrapped in anyio.run()
    import anyio
    anyio.run(main)


if __name__ == "__main__":
    main_sync()
