#!/usr/bin/env python3
"""
MCP server structure and tools validation test.
"""

import sys
import os
from pathlib import Path
import asyncio
import pytest

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from server import mcp
import inspect

@pytest.mark.asyncio
async def test_mcp_structure():
    """Test MCP server structure."""
    print("=" * 60)
    print("MCP SERVER STRUCTURE TEST")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: FastMCP server object exists
    tests_total += 1
    print(f"\n[Test {tests_total}] FastMCP Server object exists")
    if mcp:
        print(f"✅ FastMCP server created: {type(mcp).__name__}")
        tests_passed += 1
    else:
        print("❌ No FastMCP server object")
    
    # Test 2: Check for list_tools method
    tests_total += 1
    print(f"\n[Test {tests_total}] list_tools method exists")
    if hasattr(mcp, 'list_tools') and callable(mcp.list_tools):
        print("✅ list_tools method found")
        tests_passed += 1
    else:
        print("❌ list_tools method not found")
    
    # Test 3: Discover registered tools
    tests_total += 1
    print(f"\n[Test {tests_total}] Tools are discoverable")
    try:
        tools = await mcp.list_tools()
        tool_names = {t.name for t in tools}
        if tool_names:
            print(f"✅ {len(tools)} tools discovered: {tool_names}")
            tests_passed += 1
        else:
            print("❌ No tools discovered")
    except Exception as e:
        print(f"❌ Error discovering tools: {e}")
    
    # Test 4: Verify correct tool names
    tests_total += 1
    print(f"\n[Test {tests_total}] Correct tool names registered")
    expected_tools = {'oauth', 'query_library'}
    try:
        tools = await mcp.list_tools()
        actual_tools = {t.name for t in tools}
        if expected_tools.issubset(actual_tools):
            print(f"✅ Required tools found: {expected_tools}")
            tests_passed += 1
        else:
            print(f"❌ Missing tools. Expected: {expected_tools}, Got: {actual_tools}")
    except Exception as e:
        print(f"❌ Error checking tool names: {e}")
    
    # Test 5: Check for auth caching
    tests_total += 1
    print(f"\n[Test {tests_total}] Authentication caching")
    with open(Path(__file__).parent / "mcp-server" / "server.py", 'r') as f:
        source = f.read()
    if "AUTH_CACHE" in source:
        print("✅ AUTH_CACHE for per-host caching found")
        tests_passed += 1
    else:
        print("❌ AUTH_CACHE not found")
    
    # Test 6: Check tool input models (Pydantic)
    tests_total += 1
    print(f"\n[Test {tests_total}] Tool input models (Pydantic)")
    if "OAuthInput" in source and "QueryLibraryInput" in source:
        print("✅ Tool input models defined")
        if "service_url" in source:
            print("✅ service_url parameter found (multi-deployment support)")
            tests_passed += 1
        else:
            print("❌ service_url parameter not found")
    else:
        print("❌ Tool input models not found")
    
    # Test 7: Check lazy initialization
    tests_total += 1
    print(f"\n[Test {tests_total}] Lazy YOTO_SERVICE_URL initialization")
    if 'or ""' in source and 'YOTO_SERVICE_URL' in source and 'Optional' in source:
        print("✅ YOTO_SERVICE_URL is optional (lazy init)")
        tests_passed += 1
    else:
        print("⚠️  Could not verify lazy YOTO_SERVICE_URL init")
    
    # Test 8: Verify entry point
    tests_total += 1
    print(f"\n[Test {tests_total}] Entry point configuration")
    with open(Path(__file__).parent / "mcp-server" / "pyproject.toml", 'r') as f:
        toml = f.read()
    
    if 'mcp-server = "server:sync_main"' in toml:
        print("✅ Entry point correctly configured to sync_main")
        tests_passed += 1
    else:
        print("❌ Entry point not correctly configured")
    
    print("\n" + "=" * 60)
    print(f"RESULTS: {tests_passed}/{tests_total} tests passed")
    print("=" * 60)
    
    assert tests_passed == tests_total, f"Only {tests_passed}/{tests_total} tests passed"


async def test_mcp_structure_async():
    """Test MCP server structure (async, for non-pytest use)."""
    await test_mcp_structure()


if __name__ == "__main__":
    success = asyncio.run(test_mcp_structure_async())
    sys.exit(0)

