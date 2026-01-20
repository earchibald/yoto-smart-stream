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
import json
import logging
import os
from typing import Any

import httpx
import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from pydantic import AnyUrl, BaseModel, Field

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global configuration variables
YOTO_SERVICE_URL = ""
ADMIN_USERNAME = ""
ADMIN_PASSWORD = ""


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
    global YOTO_SERVICE_URL, ADMIN_USERNAME, ADMIN_PASSWORD

    args = parse_args()

    # Priority: CLI args > environment variables > defaults
    YOTO_SERVICE_URL = (
        args.url or os.getenv("YOTO_SERVICE_URL") or "http://localhost:8000"
    )
    ADMIN_USERNAME = args.username or os.getenv("ADMIN_USERNAME") or "admin"
    ADMIN_PASSWORD = args.password or os.getenv("ADMIN_PASSWORD") or ""

    logger.info(f"Configured to connect to: {YOTO_SERVICE_URL}")
    logger.info(f"Using username: {ADMIN_USERNAME}")

    if not ADMIN_PASSWORD:
        logger.warning("No password provided! Authentication may fail.")
        logger.warning(
            "Set ADMIN_PASSWORD environment variable or use --password argument."
        )


# Create MCP server
app = Server("yoto-library")


class QueryLibraryArgs(BaseModel):
    """Arguments for querying the Yoto library."""

    query: str = Field(
        description="Natural language query about the library, e.g., 'find all cards with princess in the title' or 'what metadata keys are used?'"
    )


async def get_library_data() -> dict[str, Any]:
    """Fetch library data from the yoto-smart-stream service."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First, authenticate
            auth_response = await client.post(
                f"{YOTO_SERVICE_URL}/api/auth/login",
                data={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            )

            if auth_response.status_code != 200:
                logger.error(f"Authentication failed: {auth_response.status_code}")
                return {"error": "Authentication failed", "cards": [], "playlists": []}

            # Get session cookie
            cookies = auth_response.cookies

            # Fetch library data
            library_response = await client.get(
                f"{YOTO_SERVICE_URL}/api/library",
                cookies=cookies,
            )

            if library_response.status_code != 200:
                logger.error(f"Failed to fetch library: {library_response.status_code}")
                return {
                    "error": f"Failed to fetch library: {library_response.status_code}",
                    "cards": [],
                    "playlists": [],
                }

            library_data: dict[str, Any] = library_response.json()
            return library_data

    except Exception as e:
        logger.error(f"Error fetching library data: {e}")
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
                        result += (
                            f"  Description: {card['description'][:100]}...\n"
                            if len(card["description"]) > 100
                            else f"  Description: {card['description']}\n"
                        )
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
            for card in cards[:20]:  # Limit to first 20
                result += f"- {card.get('title', 'Unknown')} by {card.get('author', 'Unknown')}\n"
                result += f"  Type: {card.get('type', 'unknown')}\n"
            if len(cards) > 20:
                result += f"\n... and {len(cards) - 20} more cards"
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


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """List available MCP tools."""
    return [
        types.Tool(
            name="query_library",
            description=(
                "Query the Yoto library using natural language. "
                "Examples: 'find all cards with princess in the title', "
                "'what metadata keys are used?', 'list all playlists', "
                "'what authors are in the library?'"
            ),
            inputSchema=QueryLibraryArgs.model_json_schema(),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls."""
    if name != "query_library":
        raise ValueError(f"Unknown tool: {name}")

    # Validate arguments
    args = QueryLibraryArgs(**arguments)

    # Fetch library data
    logger.info(f"Processing query: {args.query}")
    library_data = await get_library_data()

    # Search library
    result = search_library(library_data, args.query)

    return [types.TextContent(type="text", text=result)]


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
        library_data = await get_library_data()
        return json.dumps(library_data, indent=2)

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
                server_version="0.1.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
