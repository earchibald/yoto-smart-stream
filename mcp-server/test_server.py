"""
Test script for the Yoto Library MCP Server

This script tests the core functionality of the MCP server without requiring
a live yoto-smart-stream deployment.
"""

import sys

sys.path.insert(0, "/home/runner/work/yoto-smart-stream/yoto-smart-stream/mcp-server")

from server import search_library  # noqa: E402


def test_search_library():
    """Test the search_library function with various queries."""

    # Mock library data
    mock_library = {
        "cards": [
            {
                "id": "card1",
                "title": "The Princess and the Pea",
                "author": "Hans Christian Andersen",
                "description": "A classic fairy tale",
                "type": "card",
            },
            {
                "id": "card2",
                "title": "Princess Stories Collection",
                "author": "Various Authors",
                "description": "A collection of princess stories",
                "type": "card",
            },
            {
                "id": "card3",
                "title": "Bedtime Stories",
                "author": "Jane Smith",
                "description": "Calming stories for bedtime",
                "type": "card",
            },
        ],
        "playlists": [
            {"id": "playlist1", "name": "My Favorite Songs", "itemCount": 10}
        ],
    }

    print("Testing MCP Server Search Functionality\n")
    print("=" * 60)

    # Test 1: Metadata keys
    print("\n1. Testing metadata keys query...")
    result = search_library(
        mock_library, "what metadata keys are used across the library?"
    )
    assert "author" in result
    assert "title" in result
    print("✓ Metadata keys query works")
    print(f"   Result preview: {result[:100]}...")

    # Test 2: Author fields
    print("\n2. Testing author fields query...")
    result = search_library(
        mock_library, "what sorts of things are in card author fields?"
    )
    assert "Hans Christian Andersen" in result
    assert "Jane Smith" in result
    print("✓ Author fields query works")
    print(f"   Result preview: {result[:100]}...")

    # Test 3: Find by title
    print("\n3. Testing find by title query...")
    result = search_library(mock_library, 'find all cards with "princess" in the title')
    assert "Princess and the Pea" in result
    assert "Princess Stories Collection" in result
    assert "Bedtime Stories" not in result
    print("✓ Find by title query works")
    print(f"   Result preview: {result[:150]}...")

    # Test 4: List playlists
    print("\n4. Testing list playlists query...")
    result = search_library(mock_library, "list all playlists")
    assert "My Favorite Songs" in result
    assert "10" in result
    print("✓ List playlists query works")
    print(f"   Result preview: {result[:100]}...")

    # Test 5: Count cards
    print("\n5. Testing count cards query...")
    result = search_library(mock_library, "how many cards are there?")
    assert "3" in result
    assert "1" in result  # 1 playlist
    print("✓ Count cards query works")
    print(f"   Result: {result}")

    # Test 6: List cards
    print("\n6. Testing list all cards query...")
    result = search_library(mock_library, "list all cards")
    assert "Princess and the Pea" in result
    assert "Bedtime Stories" in result
    print("✓ List cards query works")
    print(f"   Result preview: {result[:150]}...")

    # Test 7: Default/unknown query
    print("\n7. Testing default response for unknown query...")
    result = search_library(mock_library, "some unknown query")
    assert "Library Summary" in result
    assert "Supported queries" in result
    print("✓ Default response works")
    print(f"   Result preview: {result[:100]}...")

    print("\n" + "=" * 60)
    print("✅ All tests passed successfully!")
    print("\nMCP Server is ready to use.")
    print("\nNext steps:")
    print("1. Deploy yoto-smart-stream to Railway")
    print("2. Configure MCP server with deployment URL and credentials")
    print("3. Add to VS Code or Claude Desktop configuration")
    print("4. Start querying your Yoto library!")


if __name__ == "__main__":
    try:
        test_search_library()
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
