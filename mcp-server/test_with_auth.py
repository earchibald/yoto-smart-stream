#!/usr/bin/env python3
"""Test MCP server tools with credentials."""

import asyncio
import sys
import os

# Set credentials before importing
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "yoto"
os.environ["YOTO_SERVICE_URL"] = "https://yoto-smart-stream-develop.up.railway.app"

# Add mcp-server to path
sys.path.insert(0, '/Users/earchibald/work/yoto-smart-stream/mcp-server')

from server import (
    call_tool,
    list_tools,
    configure_from_args,
)

SERVICE_URL = "https://yoto-smart-stream-develop.up.railway.app"


async def test_mcp_with_auth():
    """Test MCP server tools with authentication."""
    # Configure credentials
    configure_from_args()
    
    print("🧪 Testing MCP Server Tools (With Authentication)\n")
    
    # Test 1: query_library - count cards
    print("1️⃣  Testing query_library - count cards...")
    try:
        result = await call_tool(
            "query_library",
            {
                "service_url": SERVICE_URL,
                "query": "how many cards are there?"
            }
        )
        response_text = result[0].text
        print(f"   ✅ Query succeeded")
        print(f"   Response: {response_text}")
        assert "card" in response_text.lower(), "Should mention cards"
        print()
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: query_library - metadata keys
    print("2️⃣  Testing query_library - metadata keys...")
    try:
        result = await call_tool(
            "query_library",
            {
                "service_url": SERVICE_URL,
                "query": "what metadata keys are used across the library?"
            }
        )
        response_text = result[0].text
        print(f"   ✅ Metadata query succeeded")
        print(f"   Response: {response_text[:300]}...")
        assert "metadata" in response_text.lower() or "key" in response_text.lower(), "Should mention metadata"
        print()
    except Exception as e:
        print(f"   ❌ Metadata query failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 3: query_library - list playlists
    print("3️⃣  Testing query_library - list playlists...")
    try:
        result = await call_tool(
            "query_library",
            {
                "service_url": SERVICE_URL,
                "query": "list all playlists"
            }
        )
        response_text = result[0].text
        print(f"   ✅ Playlist query succeeded")
        print(f"   Response: {response_text[:300]}...")
        assert "playlist" in response_text.lower(), "Should mention playlists"
        print()
    except Exception as e:
        print(f"   ❌ Playlist query failed: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 4: OAuth deactivate (test connectivity)
    print("4️⃣  Testing oauth deactivate tool...")
    try:
        result = await call_tool(
            "oauth",
            {
                "service_url": SERVICE_URL,
                "action": "deactivate"
            }
        )
        response_text = result[0].text
        print(f"   ✅ OAuth deactivate call succeeded")
        print(f"   Response: {response_text[:300]}...")
        print()
    except Exception as e:
        print(f"   ❌ OAuth call failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("✅ MCP server testing complete!")


if __name__ == "__main__":
    asyncio.run(test_mcp_with_auth())
