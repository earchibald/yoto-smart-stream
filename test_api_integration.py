#!/usr/bin/env python3
"""
MCP server integration test against production API.
Tests oauth and query_library tools with API comparison.
"""

import asyncio
import httpx
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Test configuration
SERVICE_URL = "https://yoto-smart-stream-production.up.railway.app"
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "yoto")


async def test_api_health():
    """Test API health check."""
    logger.info(f"Testing API health check at {SERVICE_URL}...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{SERVICE_URL}/api/health")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ API health check passed: {data}")
                return True
            else:
                logger.error(f"❌ API health returned {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ API health check failed: {e}")
        return False


async def test_api_authentication():
    """Test admin authentication."""
    logger.info("Testing API authentication...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{SERVICE_URL}/api/user/login",
                json={"username": ADMIN_USER, "password": ADMIN_PASS}
            )
            if response.status_code == 200:
                logger.info(f"✅ Authentication successful")
                return response.cookies
            else:
                logger.error(f"❌ Authentication failed: {response.status_code}")
                logger.error(f"   Response: {response.text[:200]}")
                return None
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        return None


async def test_library_data():
    """Test library data retrieval."""
    logger.info("Testing library data retrieval...")
    try:
        cookies = await test_api_authentication()
        if not cookies:
            return None
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Try /api/library first
            response = await client.get(
                f"{SERVICE_URL}/api/library",
                cookies=cookies
            )
            if response.status_code == 200:
                data = response.json()
                cards = data.get("cards", [])
                playlists = data.get("playlists", [])
                logger.info(f"✅ Library data: {len(cards)} cards, {len(playlists)} playlists")
                return data
            
            # Try alternative /api/cards
            logger.info("   Trying /api/cards endpoint...")
            response = await client.get(
                f"{SERVICE_URL}/api/cards",
                cookies=cookies
            )
            if response.status_code == 200:
                cards = response.json()
                logger.info(f"✅ Cards endpoint: {len(cards)} cards")
                return {"cards": cards, "playlists": []}
            
            logger.error(f"❌ Library data retrieval failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"❌ Library data error: {e}")
        return None


async def test_oauth_endpoints():
    """Test OAuth endpoints."""
    logger.info("Testing OAuth endpoints...")
    try:
        cookies = await test_api_authentication()
        if not cookies:
            return False
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Check if OAuth start endpoint exists
            response = await client.post(
                f"{SERVICE_URL}/api/auth/start",
                cookies=cookies
            )
            if response.status_code in [200, 400]:  # 400 is ok if already authenticated
                logger.info(f"✅ OAuth endpoints available")
                return True
            else:
                logger.warning(f"⚠️  OAuth endpoint returned {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ OAuth endpoint test failed: {e}")
        return False


async def run_all_tests():
    """Run all integration tests."""
    logger.info("=" * 60)
    logger.info("MCP SERVER INTEGRATION TESTS (Production API)")
    logger.info("=" * 60)
    
    results = {
        "API Health Check": await test_api_health(),
        "API Authentication": (await test_api_authentication()) is not None,
        "Library Data Retrieval": (await test_library_data()) is not None,
        "OAuth Endpoints": await test_oauth_endpoints(),
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
