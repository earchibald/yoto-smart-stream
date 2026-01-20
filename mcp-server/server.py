"""
Yoto Library MCP Server

An MCP server that provides natural language query capabilities for Yoto card library data.
Connects to the yoto-smart-stream service to access library information.

Usage:
    uvx --from . mcp-server
    python server.py --url https://your-deployment.railway.app --username admin --password secret

Or add to VS Code mcp.json:
    {
      "mcpServers": {
        "yoto-library": {
          "command": "uvx",
          "args": ["--from", "/path/to/yoto-smart-stream/mcp-server", "mcp-server"],
          "env": {
            "YOTO_SERVICE_URL": "https://your-deployment.railway.app",
            "ADMIN_USERNAME": "your-username",
            "ADMIN_PASSWORD": "your-password"
          }
        }
      }
    }
"""

import argparse
import asyncio
import json
import logging
import os
from typing import Any, Union

import httpx
import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl, BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration variables for default credentials
ADMIN_USERNAME = ""
ADMIN_PASSWORD = ""
YOTO_USERNAME = ""  # For Yoto OAuth automation
YOTO_PASSWORD = ""  # For Yoto OAuth automation

# Constants for search results
MAX_DESCRIPTION_LENGTH = 100
MAX_CARDS_TO_DISPLAY = 20

# Per-host authentication cache: {service_url: cookies}
AUTH_CACHE: dict[str, httpx.Cookies] = {}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Yoto Library MCP Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables (used if args not provided):
  YOTO_SERVICE_URL    URL of yoto-smart-stream deployment
  ADMIN_USERNAME      Username for authentication
  ADMIN_PASSWORD      Password for authentication

Examples:
  %(prog)s --url https://myapp.railway.app --username admin --password secret
  YOTO_SERVICE_URL=http://localhost:8000 %(prog)s
        """,
    )

    parser.add_argument(
        "--url", help="URL of yoto-smart-stream service (env: YOTO_SERVICE_URL)"
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
    YOTO_SERVICE_URL = (
        args.url or os.getenv("YOTO_SERVICE_URL") or "http://localhost:8000"
    )
    ADMIN_USERNAME = args.username or os.getenv("ADMIN_USERNAME") or "admin"
    ADMIN_PASSWORD = args.password or os.getenv("ADMIN_PASSWORD") or ""
    YOTO_USERNAME = os.getenv("YOTO_USERNAME") or ""
    YOTO_PASSWORD = os.getenv("YOTO_PASSWORD") or ""

    logger.info(f"Configured to connect to: {YOTO_SERVICE_URL}")
    logger.info(f"Using username: {ADMIN_USERNAME}")

    if not ADMIN_PASSWORD:
        logger.warning("No password provided! Authentication may fail.")
        logger.warning(
            "Set ADMIN_PASSWORD environment variable or use --password argument."
        )

    if YOTO_USERNAME and YOTO_PASSWORD:
        logger.info("Yoto OAuth credentials configured for automated login")


# Create MCP server
app = Server("yoto-library")


class OAuthArgs(BaseModel):
    """Arguments for OAuth operations."""

    service_url: str = Field(
        description="URL of the yoto-smart-stream service, e.g., 'https://yoto-smart-stream-production.up.railway.app'"
    )
    action: str = Field(
        description="Action to perform: 'activate' to log in to Yoto OAuth, 'deactivate' to log out"
    )


class QueryLibraryArgs(BaseModel):
    """Arguments for querying the Yoto library."""

    service_url: str = Field(
        description="URL of the yoto-smart-stream service, e.g., 'https://yoto-smart-stream-production.up.railway.app'"
    )
    query: str = Field(
        description="Natural language query about the library, e.g., 'find all cards with princess in the title' or 'what metadata keys are used?'"
    )


async def authenticate_host(service_url: str) -> Union[httpx.Cookies, None]:
    """
    Authenticate with a specific host and cache the session cookies.

    Args:
        service_url: URL of the yoto-smart-stream service

    Returns:
        Session cookies if authentication succeeds, None otherwise
    """
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
    """
    Fetch library data from the yoto-smart-stream service.

    Args:
        service_url: URL of the yoto-smart-stream service

    Returns:
        Library data dictionary with cards and playlists
    """
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

            # Try to fetch library data with cached credentials
            library_response = await client.get(
                f"{service_url}/api/library",
                cookies=cookies,
            )

            # If authentication expired (401), re-authenticate and retry
            if library_response.status_code == 401:
                logger.info(
                    f"Authentication expired for {service_url}, re-authenticating..."
                )
                cookies = await authenticate_host(service_url)
                if not cookies:
                    return {
                        "error": "Re-authentication failed",
                        "cards": [],
                        "playlists": [],
                    }

                library_response = await client.get(
                    f"{service_url}/api/library",
                    cookies=cookies,
                )

            if library_response.status_code != 200:
                logger.error(
                    f"Failed to fetch library from {service_url}: {library_response.status_code}"
                )
                return {
                    "error": f"Failed to fetch library: {library_response.status_code}",
                    "cards": [],
                    "playlists": [],
                }

            library_data: dict[str, Any] = library_response.json()
            return library_data

    except Exception as e:
        logger.error(f"Error fetching library data from {service_url}: {e}")
        return {"error": str(e), "cards": [], "playlists": []}


def search_library(library_data: dict[str, Any], query: str) -> str:
    """
    Search the library based on natural language query.

    Supports queries like:
    - "what metadata keys are used across the library?"
    - "what sorts of things are in card author fields?"
    - "find all cards with princess in the title"
    - "list all playlists"
    - "how many cards are there?"
    """
    query_lower = query.lower()
    cards = library_data.get("cards", [])
    playlists = library_data.get("playlists", [])

    # Check for error in data
    if "error" in library_data:
        return f"Error accessing library: {library_data['error']}"

    # Query: metadata keys
    if "metadata" in query_lower and "key" in query_lower:
        all_keys = set()
        for card in cards:
            all_keys.update(card.keys())
        return "Metadata keys used across the library:\n" + "\n".join(sorted(all_keys))

    # Query: author fields
    if "author" in query_lower and ("field" in query_lower or "what" in query_lower):
        authors = set()
        for card in cards:
            if card.get("author"):
                authors.add(card["author"])
        return f"Authors found in library ({len(authors)} unique):\n" + "\n".join(
            sorted(authors)
        )

    # Query: find cards by title
    if "find" in query_lower and "title" in query_lower:
        # Extract search term (look for quoted text or words after "with")
        search_term = None
        if '"' in query:
            parts = query.split('"')
            if len(parts) >= 2:
                search_term = parts[1].lower()
        elif "with " in query_lower:
            parts = query_lower.split("with ")
            if len(parts) >= 2:
                search_term = parts[1].split(" in ")[0].strip()

        if search_term:
            matching_cards = [
                card for card in cards if search_term in card.get("title", "").lower()
            ]
            if matching_cards:
                result = f"Found {len(matching_cards)} card(s) with '{search_term}' in title:\n\n"
                for card in matching_cards:
                    result += f"- {card.get('title', 'Unknown')} by {card.get('author', 'Unknown')}\n"
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
    """
    Activate Yoto OAuth by automating the device code flow with browser automation.

    Args:
        service_url: URL of the yoto-smart-stream service

    Returns:
        Status message
    """
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
                return f"❌ Error: Failed to start OAuth flow: HTTP {start_response.status_code}\n{start_response.text}"

            device_data = start_response.json()
            verification_uri = device_data.get(
                "verification_uri_complete"
            ) or device_data.get("verification_uri")
            user_code = device_data.get("user_code")
            device_code = device_data.get("device_code")

            logger.info(
                f"Device code flow started. Verification URI: {verification_uri}"
            )
            logger.info(f"User code: {user_code}")

            # Use playwright to automate browser login
            try:
                from playwright.async_api import async_playwright

                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    context = await browser.new_context()
                    page = await context.new_page()

                    # Navigate to verification URI
                    await page.goto(verification_uri)
                    await page.wait_for_load_state("networkidle")

                    # Fill in email
                    email_input = page.locator(
                        'input[type="email"], input[name="email"], input[id="email"]'
                    ).first
                    if await email_input.is_visible(timeout=5000):
                        await email_input.fill(YOTO_USERNAME)

                        # Look for continue/submit button
                        continue_button = page.locator(
                            'button:has-text("Continue"), button[type="submit"]'
                        ).first
                        await continue_button.click()
                        await page.wait_for_load_state("networkidle")

                    # Fill in password
                    password_input = page.locator(
                        'input[type="password"], input[name="password"], input[id="password"]'
                    ).first
                    if await password_input.is_visible(timeout=5000):
                        await password_input.fill(YOTO_PASSWORD)

                        # Look for sign in button
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
    """
    Deactivate Yoto OAuth by logging out.

    Args:
        service_url: URL of the yoto-smart-stream service

    Returns:
        Status message
    """
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


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available MCP tools."""
    return [
        types.Tool(
            name="oauth",
            description=(
                "Activate or deactivate Yoto OAuth authentication for a yoto-smart-stream service. "
                "Use 'activate' to log in (requires YOTO_USERNAME and YOTO_PASSWORD env vars), "
                "or 'deactivate' to log out. "
                "Example: action='activate' to enable Yoto API access."
            ),
            inputSchema=OAuthArgs.model_json_schema(),
        ),
        types.Tool(
            name="query_library",
            description=(
                "Query the Yoto library using natural language. "
                "Requires service_url parameter to specify which yoto-smart-stream deployment to query. "
                "Examples: 'find all cards with princess in the title', "
                "'what metadata keys are used?', 'list all playlists', "
                "'what authors are in the library?'"
            ),
            inputSchema=QueryLibraryArgs.model_json_schema(),
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls."""
    if name == "oauth":
        # Handle OAuth activation/deactivation
        oauth_args = OAuthArgs(**arguments)

        if oauth_args.action.lower() == "activate":
            result = await activate_yoto_oauth(oauth_args.service_url)
        elif oauth_args.action.lower() == "deactivate":
            result = await deactivate_yoto_oauth(oauth_args.service_url)
        else:
            result = f"❌ Error: Unknown action '{oauth_args.action}'. Use 'activate' or 'deactivate'."

        return [types.TextContent(type="text", text=result)]

    elif name == "query_library":
        # Validate arguments
        query_args = QueryLibraryArgs(**arguments)

        # Fetch library data from the specified service
        logger.info(
            f"Processing query for {query_args.service_url}: {query_args.query}"
        )
        library_data = await get_library_data(query_args.service_url)

        # Search library
        result = search_library(library_data, query_args.query)

        return [types.TextContent(type="text", text=result)]

    else:
        raise ValueError(f"Unknown tool: {name}")


@app.list_resources()
async def list_resources() -> list[types.Resource]:
    """List available resources."""
    return [
        types.Resource(
            uri=AnyUrl("yoto://library"),
            name="Yoto Library",
            description="Access to the complete Yoto card library",
            mimeType="application/json",
        )
    ]


@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource."""
    if uri == "yoto://library":
        # Note: This would need a service_url parameter to be useful
        # For now, return an error message
        return json.dumps(
            {
                "error": "Resource access requires service_url parameter. Use the query_library tool instead."
            },
            indent=2,
        )

    raise ValueError(f"Unknown resource: {uri}")


async def main():
    """Run the MCP server using stdio transport."""
    # Configure from args/env first
    configure_from_args()

    logger.info("Yoto Library MCP Server starting...")
    logger.info(f"Connecting to: {YOTO_SERVICE_URL}")

    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="yoto-library",
                    server_version="0.1.1",
        )


if __name__ == "__main__":
    asyncio.run(main())
