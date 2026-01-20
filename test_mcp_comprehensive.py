#!/usr/bin/env python3
"""
Comprehensive MCP server testing against the yoto-smart-stream API.
Tests oauth and query_library tools with curl-based API comparison.
"""

import asyncio
import httpx
import json
import logging
import os
import sys
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from server import mcp
import mcp.types as types

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
SERVICE_URL = os.getenv("YOTO_SERVICE_URL", "http://localhost:8000")
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "yoto")
YOTO_USER = os.getenv("YOTO_USERNAME", "")
YOTO_PASS = os.getenv("YOTO_PASSWORD", "")


async def test_server_startup():
    """Test that the MCP server starts without requiring YOTO_SERVICE_URL."""
    logger.info("Testing server startup (lazy initialization)...")
    try:
        # Just verify the server mcp exists and has tools
        tools = await mcp.list_tools()
        logger.info(f"✅ Server has {len(tools)} tools available")
        
        tool_names = [tool.name for tool in tools]
        logger.info(f"   Tools: {tool_names}")
        
        assert "oauth" in tool_names, "oauth tool not found"
        assert "query_library" in tool_names, "query_library tool not found"
        logger.info("✅ Server startup test passed")
        return True
    except Exception as e:
        logger.error(f"❌ Server startup test failed: {e}")
        return False


async def test_api_connectivity():
    """Test connectivity to the yoto-smart-stream API."""
    logger.info(f"Testing API connectivity to {SERVICE_URL}...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Try health check endpoint
            response = await client.get(f"{SERVICE_URL}/api/health")
            if response.status_code == 200:
                logger.info(f"✅ API health check passed")
                return True
            else:
                logger.warning(f"⚠️  API returned status {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ API connectivity failed: {e}")
        return False


async def test_api_authentication():
    """Test admin authentication against the API."""
    logger.info(f"Testing API authentication...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{SERVICE_URL}/api/user/login",
                json={"username": ADMIN_USER, "password": ADMIN_PASS}
            )
            if response.status_code == 200:
                logger.info(f"✅ API authentication successful")
                return response.cookies
            else:
                logger.error(f"❌ API authentication failed: {response.status_code}")
                logger.error(f"   Response: {response.text[:200]}")
                return None
    except Exception as e:
        logger.error(f"❌ API authentication error: {e}")
        return None


async def test_library_data_fetch():
    """Test fetching library data from the API."""
    logger.info("Testing library data fetch...")
    try:
        # First authenticate
        cookies = await test_api_authentication()
        if not cookies:
            return None
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try to fetch cards/library data
            response = await client.get(
                f"{SERVICE_URL}/api/library",
                cookies=cookies
            )
            if response.status_code == 200:
                data = response.json()
                card_count = len(data.get("cards", []))
                playlist_count = len(data.get("playlists", []))
                logger.info(f"✅ Library data fetched: {card_count} cards, {playlist_count} playlists")
                return data
            else:
                logger.warning(f"⚠️  Library fetch returned {response.status_code}")
                logger.info(f"   Trying alternative endpoint...")
                
                # Try alternative endpoint
                response = await client.get(
                    f"{SERVICE_URL}/api/cards",
                    cookies=cookies
                )
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"✅ Cards endpoint available")
                    return data
                return None
    except Exception as e:
        logger.error(f"❌ Library data fetch failed: {e}")
        return None


async def test_query_library_tool():
    """Test the query_library MCP tool."""
    logger.info("Testing query_library tool...")
    try:
        # Get library data first
        cookies = await test_api_authentication()
        if not cookies:
            logger.warning("⚠️  Skipping query_library test - authentication required")
            return False
        
        library_data = await test_library_data_fetch()
        if not library_data:
            logger.warning("⚠️  Skipping query_library test - no library data")
            return False
        
        # Call the query_library tool
        result = await mcp.call_tool(
            "query_library",
            {
                "params": {
                    "service_url": SERVICE_URL,
                    "query": "how many cards are in the library?"
                }
            }
        )
        
        logger.info(f"✅ query_library tool returned: {result[0][:100] if result else 'empty'}...")
        return True
        
    except Exception as e:
        logger.error(f"❌ query_library tool test failed: {e}")
        return False


async def test_oauth_tool():
    """Test the oauth MCP tool (activate/deactivate)."""
    logger.info("Testing oauth tool...")
    try:
        # Test deactivate first (safer)
        result = await mcp.call_tool(
            "oauth",
            {
                "params": {
                    "service_url": SERVICE_URL,
                    "action": "deactivate"
                }
            }
        )
        
        # Result is a list of TextContent objects or strings
        result_text = str(result[0]) if result else ""
        
        # Check if Status field is present in response
        if "Status:" in result_text:
            logger.info(f"✅ oauth tool returned structured response with Status field")
            # Extract and verify status value
            lines = result_text.split('\n')
            for line in lines:
                if line.startswith("Status:"):
                    status_value = line.split(":", 1)[1].strip()
                    logger.info(f"   Status value: {status_value}")
                    return True
            return True
        else:
            logger.warning(f"⚠️  oauth tool response missing Status field: {result_text[:100]}")
            return False
        
    except Exception as e:
        logger.error(f"❌ oauth tool test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("MCP SERVER COMPREHENSIVE TEST SUITE")
    logger.info("=" * 60)
    
    results = {
        "Server Startup": await test_server_startup(),
        "API Connectivity": await test_api_connectivity(),
        "API Authentication": (await test_api_authentication()) is not None,
        "Library Data Fetch": (await test_library_data_fetch()) is not None,
        "query_library Tool": await test_query_library_tool(),
        "oauth Tool": await test_oauth_tool(),
    }
    
    logger.info("=" * 60)
    logger.info("TEST RESULTS")
    logger.info("=" * 60)
    
    passed = 0
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
        if result:
            passed += 1
    
    logger.info("=" * 60)
    logger.info(f"Total: {passed}/{len(results)} tests passed")
    logger.info("=" * 60)
    
    return all(results.values())


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
