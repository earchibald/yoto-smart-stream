#!/usr/bin/env python3
"""
Quick test to verify oauth tool returns Status field.
"""

import asyncio
import sys
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent / "mcp-server"))

from server import mcp


async def test_oauth_status_field():
    """Verify oauth tool returns Status field in response."""
    print("Testing oauth Status field...\n")
    
    # Test deactivate (doesn't require real auth)
    print("1. Testing deactivate (should return error status due to no auth):")
    result = await mcp.call_tool(
        "oauth",
        {
            "params": {
                "service_url": "http://localhost:8000",
                "action": "deactivate"
            }
        }
    )
    
    result_text = str(result[0]) if result else ""
    
    # Handle nested list structure from FastMCP
    if isinstance(result[0], list):
        # It's a list of TextContent objects
        content_item = result[0][0] if result[0] else None
    else:
        content_item = result[0]
    
    # If it's a TextContent object, extract the text field
    if hasattr(content_item, 'text'):
        result_text = content_item.text
    else:
        result_text = str(content_item)
    
    print(f"Result structure: {type(result)} -> {type(result[0])}")
    print(f"Response:\n{result_text}\n")
    
    # Check for Status field
    if "Status:" in result_text:
        print("✅ Status field found in response")
        
        # Extract status value
        for line in result_text.split('\n'):
            if line.startswith("Status:"):
                status_value = line.split(":", 1)[1].strip()
                print(f"✅ Status value: '{status_value}'")
                
                # Validate it's one of the expected values
                valid_statuses = ["success", "pending", "error", "expired"]
                if status_value in valid_statuses:
                    print(f"✅ Status value is valid (one of: {valid_statuses})")
                else:
                    print(f"❌ Status value '{status_value}' not in expected values: {valid_statuses}")
    else:
        print("❌ Status field NOT found in response")
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(test_oauth_status_field())
    sys.exit(0 if success else 1)
