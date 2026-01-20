#!/usr/bin/env python3
"""Test that MCP server exposes correct tools."""

import sys
import os

def test_tools():
    """Test that the MCP server code has the correct tools."""
    # Read the server.py file and verify it has the right tools
    server_file = os.path.join(os.path.dirname(__file__), 'mcp-server', 'server.py')
    
    with open(server_file, 'r') as f:
        content = f.read()
    
    print("Testing MCP server source code...")
    
    # Check for correct tools in list_tools()
    has_oauth = 'name="oauth"' in content
    has_query = 'name="query_library"' in content
    has_activate = 'activate_yoto_oauth' in content
    has_deactivate = 'deactivate_yoto_oauth' in content
    
    print(f"  - oauth tool defined: {'✅' if has_oauth else '❌'}")
    print(f"  - query_library tool defined: {'✅' if has_query else '❌'}")
    print(f"  - activate_yoto_oauth function: {'✅' if has_activate else '❌'}")
    print(f"  - deactivate_yoto_oauth function: {'✅' if has_deactivate else '❌'}")
    
    # Check for wrong tools
    has_add = 'name="add"' in content and '@app.tool' in content[:content.find('name="add"')] if 'name="add"' in content else False
    has_subtract = 'name="subtract"' in content and '@app.tool' in content[:content.find('name="subtract"')] if 'name="subtract"' in content else False
    has_multiply = 'name="multiply"' in content and '@app.tool' in content[:content.find('name="multiply"')] if 'name="multiply"' in content else False
    has_divide = 'name="divide"' in content and '@app.tool' in content[:content.find('name="divide"')] if 'name="divide"' in content else False
    
    print(f"  - add tool defined: {'❌ ERROR' if has_add else '✅'}")
    print(f"  - subtract tool defined: {'❌ ERROR' if has_subtract else '✅'}")
    print(f"  - multiply tool defined: {'❌ ERROR' if has_multiply else '✅'}")
    print(f"  - divide tool defined: {'❌ ERROR' if has_divide else '✅'}")
    
    # Count @app.tool decorators (should be exactly 2: list_tools and call_tool, plus resources)
    import re
    tools_pattern = r'@app\.tool\(\)'
    tool_count = len(re.findall(tools_pattern, content))
    list_tools_count = len(re.findall(r'@app\.list_tools\(\)', content))
    call_tool_count = len(re.findall(r'@app\.call_tool\(\)', content))
    
    print(f"\n  MCP handler structure:")
    print(f"    - @app.list_tools() decorators: {list_tools_count} (should be 1)")
    print(f"    - @app.call_tool() decorators: {call_tool_count} (should be 1)")
    
    all_passed = (has_oauth and has_query and has_activate and has_deactivate and 
                  not has_add and not has_subtract and not has_multiply and not has_divide and
                  list_tools_count == 1 and call_tool_count == 1)
    
    if all_passed:
        print("\n✅ All checks passed! MCP server code has correct tools.")
        return True
    else:
        print("\n❌ Some checks failed!")
        return False


if __name__ == "__main__":
    result = test_tools()
    sys.exit(0 if result else 1)
