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


class QueryLibraryInput(BaseModel):
    """Input model for querying the Yoto library."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )

    query: str = Field(
        ...,
        description="Natural language query about the library, e.g., 'find all cards with princess in the title' or 'what metadata keys are used?'",
        min_length=1
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


def search_library(library_data: dict, query: str) -> str:
    """Search library using natural language query."""
    cards = library_data.get("cards", [])
    playlists = library_data.get("playlists", [])

    if library_data.get("error"):
        return f"❌ Error accessing library: {library_data.get('error')}"

    query_lower = query.lower()

    # Query: find cards with text in title
    if "find" in query_lower and "title" in query_lower and "with" in query_lower:
        # Extract search term from query like "find all cards with 'term' in the title"
        if '"' in query or "'" in query:
            try:
                start = query.find('"') if '"' in query else query.find("'")
                end = query.rfind('"') if '"' in query else query.rfind("'")
                search_term = query[start + 1 : end]
                
                matching = [c for c in cards if search_term.lower() in c.get("title", "").lower()]
                if matching:
                    result = f"Found {len(matching)} card(s) with '{search_term}' in title:\n\n"
                    for card in matching[:MAX_CARDS_TO_DISPLAY]:
                        result += f"- {card.get('title', 'Unknown')} by {card.get('author', 'Unknown')}\n"
                        result += f"  Type: {card.get('type', 'unknown')}\n"
                        result += f"  ID: {card.get('id', 'Unknown')}\n"
                        if card.get("description"):
                            desc = card["description"]
                            if len(desc) > MAX_DESCRIPTION_LENGTH:
                                result += (
                                    f"  Description: {desc[:MAX_DESCRIPTION_LENGTH]}...\n"
                                )
                            else:
                                result += f"  Description: {desc}\n"
                        result += "\n"
                    return result
                else:
                    return f"No cards found with '{search_term}' in title."
            except Exception as e:
                logger.error(f"Error parsing search term: {e}")
                return "Could not extract search term from query. Please use format: 'find all cards with \"search term\" in the title'"
        else:
            return "Could not extract search term from query. Please use format: 'find all cards with \"search term\" in the title'"

    # Query: list playlists
    if "playlist" in query_lower and (
        "list" in query_lower or "show" in query_lower or "all" in query_lower
    ):
        if playlists:
            result = f"Found {len(playlists)} playlist(s):\n\n"
            for playlist in playlists:
                result += f"- {playlist.get('name', 'Unknown')}\n"
                result += f"  ID: {playlist.get('id', 'Unknown')}\n"
                result += f"  Items: {playlist.get('itemCount', 0)}\n\n"
            return result
        else:
            return "No playlists found in library."

    # Query: count cards
    if "how many" in query_lower and "card" in query_lower:
        return (
            f"Total cards in library: {len(cards)}\nTotal playlists: {len(playlists)}"
        )

    # Query: list all cards
    if "list" in query_lower and "card" in query_lower:
        if cards:
            result = f"Found {len(cards)} card(s) in library:\n\n"
            for card in cards[:MAX_CARDS_TO_DISPLAY]:
                result += f"- {card.get('title', 'Unknown')} by {card.get('author', 'Unknown')}\n"
                result += f"  Type: {card.get('type', 'unknown')}\n"
            if len(cards) > MAX_CARDS_TO_DISPLAY:
                result += f"\n... and {len(cards) - MAX_CARDS_TO_DISPLAY} more cards"
            return result
        else:
            return "No cards found in library."

    # Default: provide summary
    return (
        f"Library Summary:\n"
        f"- Total cards: {len(cards)}\n"
        f"- Total playlists: {len(playlists)}\n\n"
        f"Supported queries:\n"
        f"- 'what metadata keys are used across the library?'\n"
        f"- 'what sorts of things are in card author fields?'\n"
        f"- 'find all cards with \"princess\" in the title'\n"
        f"- 'list all playlists'\n"
        f"- 'how many cards are there?'\n"
        f"- 'list all cards'\n"
    )


async def activate_yoto_oauth(service_url: str) -> str:
    """Activate Yoto OAuth by automating the device code flow."""
    if not YOTO_USERNAME or not YOTO_PASSWORD:
        return (
            "❌ Error: YOTO_USERNAME and YOTO_PASSWORD environment variables are required for OAuth automation.\n\n"
            "Please set these variables with your Yoto account credentials:\n"
            "  export YOTO_USERNAME='your-email@example.com'\n"
            "  export YOTO_PASSWORD='your-yoto-password'\n"
        )

    try:
        # Get cached cookies for admin auth
        cookies = AUTH_CACHE.get(service_url)

        async with httpx.AsyncClient(timeout=60.0) as client:
            # Authenticate with admin if needed
            if not cookies:
                cookies = await authenticate_host(service_url)
                if not cookies:
                    return f"❌ Error: Failed to authenticate with {service_url}"

            # Start OAuth device code flow
            logger.info(f"Starting Yoto OAuth device code flow for {service_url}...")
            start_response = await client.post(
                f"{service_url}/api/auth/start",
                cookies=cookies,
            )

            if start_response.status_code != 200:
                return f"❌ Error: Failed to start OAuth: {start_response.status_code}\n{start_response.text[:200]}"

            flow_data = start_response.json()
            device_code = flow_data.get("device_code")
            user_code = flow_data.get("user_code")
            verification_uri = flow_data.get("verification_uri")

            if not device_code:
                return f"❌ Error: No device code returned from server"

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
                    "❌ Error: Playwright is not installed.\n\n"
                    "To use automated OAuth, install playwright:\n"
                    "  pip install playwright\n"
                    "  playwright install chromium\n"
                )
            except Exception as browser_error:
                logger.error(f"Browser automation error: {browser_error}")
                return f"⚠️ Browser automation failed: {browser_error}\n\nYou may need to manually complete the OAuth flow at:\n{verification_uri}\nUser code: {user_code}"

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
                    if poll_data.get("authenticated"):
                        return (
                            f"✅ Yoto OAuth activated successfully for {service_url}!\n\n"
                            f"Status: {poll_data.get('message', 'Authenticated')}\n"
                        )
                    elif poll_data.get("status") == "pending":
                        continue
                    elif poll_data.get("status") == "error":
                        return f"❌ OAuth error: {poll_data.get('message')}"

            return (
                f"⏱️ OAuth polling timed out. The authentication may still complete.\n\n"
                f"If not completed, you can manually authorize at:\n"
                f"{verification_uri}\n"
                f"User code: {user_code}"
            )

    except Exception as e:
        logger.error(f"Error activating OAuth for {service_url}: {e}")
        return f"❌ Error activating OAuth: {str(e)}"


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
                    return f"❌ Error: Failed to authenticate with {service_url}"

            # Call logout endpoint
            logger.info(f"Deactivating Yoto OAuth for {service_url}...")
            logout_response = await client.post(
                f"{service_url}/api/auth/logout",
                cookies=cookies,
            )

            if logout_response.status_code == 200:
                logout_data = logout_response.json()
                return (
                    f"✅ Yoto OAuth deactivated successfully for {service_url}\n\n"
                    f"Message: {logout_data.get('message', 'Logged out')}\n"
                )
            else:
                return f"❌ Error: Failed to deactivate OAuth: HTTP {logout_response.status_code}\n{logout_response.text}"

    except Exception as e:
        logger.error(f"Error deactivating OAuth for {service_url}: {e}")
        return f"❌ Error deactivating OAuth: {str(e)}"


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
    """
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return "❌ Error: No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable."

    if params.action.lower() == "activate":
        return await activate_yoto_oauth(service_url)
    elif params.action.lower() == "deactivate":
        return await deactivate_yoto_oauth(service_url)
    else:
        return f"❌ Error: Unknown action '{params.action}'. Use 'activate' or 'deactivate'."


@mcp.tool(
    name="query_library",
    annotations={
        "title": "Query Yoto Library",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def query_library_tool(params: QueryLibraryInput) -> str:
    """Query the Yoto library using natural language.
    
    Search and explore the Yoto card library with natural language queries.
    Examples: 'find all cards with princess in the title', 'how many cards?',
    'list all playlists', 'what metadata keys are used?'
    """
    service_url = params.service_url or YOTO_SERVICE_URL
    
    if not service_url:
        return "❌ Error: No service URL provided. Either pass service_url parameter or set YOTO_SERVICE_URL environment variable."

    logger.info(f"Processing query for {service_url}: {params.query}")
    library_data = await get_library_data(service_url)
    result = search_library(library_data, params.query)
    
    return result


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
