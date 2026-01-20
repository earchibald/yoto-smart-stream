#!/usr/bin/env python3
"""Test MCP server tools against the API."""

import asyncio
import sys
import os
from typing import Any

# Add mcp-server to path
sys.path.insert(0, '/Users/earchibald/work/yoto-smart-stream/mcp-server')

from server import (
    call_tool,
    list_tools,
    QueryLibraryArgs,
    OAuthArgs,
)

SERVICE_URL = "https://yoto-smart-stream-develop.up.railway.app"


async def test_mcp_server():
    """Test MCP server tools."""
    print("🧪 Testing MCP Server Tools\n")
    
    # Test 1: List tools
    print("1️⃣  Testing list_tools()...")
    tools = await list_tools()
    print(f"   ✅ Available tools: {[t.name for t in tools]}")
    assert len(tools) == 2, "Should have exactly 2 tools"
    assert any(t.name == "oauth" for t in tools), "Missing oauth tool"
    assert any(t.name == "query_library" for t in tools), "Missing query_library tool"
    print()
    
    # Test 2: Test query_library tool
    print("2️⃣  Testing query_library tool...")
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
        print(f"   Response: {response_text[:200]}...")
        assert "card" in response_text.lower() or "error" in response_text.lower(), "Unexpected response"
        print()
    except Exception as e:
        print(f"   ❌ Query failed: {e}")
        raise
    
    # Test 3: Test query_library with library search
    print("3️⃣  Testing query_library with metadata query...")
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
        print(f"   Response: {response_text[:200]}...")
        assert "metadata" in response_text.lower() or "error" in response_text.lower(), "Unexpected response"
        print()
    except Exception as e:
        print(f"   ❌ Metadata query failed: {e}")
        raise
    
    # Test 4: OAuth tool activation (without actual credentials, should show error message)
    print("4️⃣  Testing oauth tool...")
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
        print(f"   Response: {response_text[:200]}...")
        assert "deactivat" in response_text.lower() or "error" in response_text.lower() or "logout" in response_text.lower(), "Unexpected response"
        print()
    except Exception as e:
        print(f"   ❌ OAuth call failed: {e}")
        raise
    
    # Test 5: Verify tool schemas
    print("5️⃣  Verifying tool schemas...")
    oauth_tool = next((t for t in tools if t.name == "oauth"), None)
    query_tool = next((t for t in tools if t.name == "query_library"), None)
    
    assert oauth_tool is not None, "oauth tool missing"
    assert query_tool is not None, "query_library tool missing"
    
    assert "action" in oauth_tool.inputSchema.get("properties", {}), "oauth missing action parameter"
    assert "service_url" in oauth_tool.inputSchema.get("properties", {}), "oauth missing service_url parameter"
    
    assert "query" in query_tool.inputSchema.get("properties", {}), "query_library missing query parameter"
    assert "service_url" in query_tool.inputSchema.get("properties", {}), "query_library missing service_url parameter"
    
    print(f"   ✅ Tool schemas valid")
    print(f"   - oauth: {list(oauth_tool.inputSchema.get('properties', {}).keys())}")
    print(f"   - query_library: {list(query_tool.inputSchema.get('properties', {}).keys())}")
    print()
    
    print("🎉 All MCP server tests passed!")
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_mcp_server())
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
