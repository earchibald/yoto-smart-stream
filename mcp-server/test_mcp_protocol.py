#!/usr/bin/env python3
"""
Test MCP protocol interactions directly using stdio.
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from server import app, configure_from_args
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions
import io


async def test_mcp_protocol():
    """Test the MCP server protocol directly."""
    print("\n" + "="*70)
    print("MCP PROTOCOL TEST")
    print("="*70)
    
    # Configure server
    configure_from_args()
    
    # Test 1: List tools
    print("\n1. Testing list_tools()...")
    tools = await app._list_tools_handler()
    print(f"✓ Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:60]}...")
        print(f"    Required params: {tool.inputSchema.get('required', [])}")
    
    # Test 2: Test query_library tool
    print("\n2. Testing query_library tool...")
    try:
        result = await app._call_tool_handler(
            "query_library",
            {
                "service_url": "https://yoto-smart-stream-yoto-smart-stream-pr-105.up.railway.app",
                "query": "how many cards are there?"
            }
        )
        print(f"✓ query_library executed successfully")
        print(f"  Result preview: {result[0].text[:100]}...")
    except Exception as e:
        print(f"✗ query_library failed: {e}")
    
    # Test 3: List resources
    print("\n3. Testing list_resources()...")
    resources = await app._list_resources_handler()
    print(f"✓ Found {len(resources)} resources:")
    for resource in resources:
        print(f"  - {resource.uri}: {resource.description}")
    
    # Test 4: Test oauth tool structure (without actually calling it)
    print("\n4. Testing oauth tool parameters...")
    oauth_tool = next((t for t in tools if t.name == "oauth"), None)
    if oauth_tool:
        print(f"✓ OAuth tool found")
        schema = oauth_tool.inputSchema
        print(f"  Properties: {list(schema.get('properties', {}).keys())}")
        print(f"  Required: {schema.get('required', [])}")
        if 'action' in schema.get('properties', {}):
            action_enum = schema['properties']['action'].get('enum', [])
            print(f"  Actions: {action_enum}")
    
    print("\n" + "="*70)
    print("✓ MCP PROTOCOL TEST COMPLETE")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_mcp_protocol())
