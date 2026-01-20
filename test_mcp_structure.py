#!/usr/bin/env python3
"""
MCP server structure and tools validation test.
"""

import sys
import os
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from server import app
import mcp.types as types
import inspect

def test_mcp_structure():
    """Test MCP server structure."""
    print("=" * 60)
    print("MCP SERVER STRUCTURE TEST")
    print("=" * 60)
    
    tests_passed = 0
    tests_total = 0
    
    # Test 1: Server object exists
    tests_total += 1
    print(f"\n[Test {tests_total}] MCP Server object exists")
    if app:
        print(f"✅ Server created: {type(app).__name__}")
        tests_passed += 1
    else:
        print("❌ No server object")
    
    # Test 2: Check for list_tools handler
    tests_total += 1
    print(f"\n[Test {tests_total}] list_tools handler exists")
    if hasattr(app, 'list_tools'):
        print("✅ list_tools handler found")
        tests_passed += 1
    else:
        print("❌ list_tools handler not found")
    
    # Test 3: Check for call_tool handler
    tests_total += 1
    print(f"\n[Test {tests_total}] call_tool handler exists")
    if hasattr(app, 'call_tool'):
        print("✅ call_tool handler found")
        tests_passed += 1
    else:
        print("❌ call_tool handler not found")
    
    # Test 4: Verify tool definitions in source
    tests_total += 1
    print(f"\n[Test {tests_total}] Tool definitions in source code")
    with open(Path(__file__).parent / "mcp-server" / "server.py", 'r') as f:
        source = f.read()
    
    has_oauth = 'name="oauth"' in source
    has_query = 'name="query_library"' in source
    
    if has_oauth and has_query:
        print(f"✅ Both oauth and query_library tools defined")
        tests_passed += 1
    else:
        print(f"❌ Missing tools - oauth: {has_oauth}, query_library: {has_query}")
    
    # Test 5: Check for auth caching
    tests_total += 1
    print(f"\n[Test {tests_total}] Authentication caching")
    if "AUTH_CACHE" in source:
        print("✅ AUTH_CACHE for per-host caching found")
        tests_passed += 1
    else:
        print("❌ AUTH_CACHE not found")
    
    # Test 6: Check tool schemas
    tests_total += 1
    print(f"\n[Test {tests_total}] Tool argument schemas")
    if "QueryLibraryArgs" in source and "OAuthArgs" in source:
        print("✅ Tool argument classes defined")
        if "service_url" in source:
            print("✅ service_url parameter found (multi-deployment support)")
            tests_passed += 1
        else:
            print("❌ service_url parameter not found")
    else:
        print("❌ Tool argument classes not found")
    
    # Test 7: Check lazy initialization
    tests_total += 1
    print(f"\n[Test {tests_total}] Lazy YOTO_SERVICE_URL initialization")
    if 'or ""' in source and 'YOTO_SERVICE_URL' in source and 'optional' in source.lower():
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
    
    return tests_passed == tests_total


if __name__ == "__main__":
    success = test_mcp_structure()
    sys.exit(0 if success else 1)
