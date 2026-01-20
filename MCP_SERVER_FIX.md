# MCP Server Tool Exposure Fix

## Problem Identified

The MCP server was showing 4 incorrect tools (add, subtract, multiply, divide) instead of the 2 correct tools (oauth, query_library) when discovered by VS Code.

## Root Cause

The issue was in `.vscode/mcp.json` configuration:

```json
"args": ["mcp-server"]  // ← AMBIGUOUS: uvx treats this as PyPI package name
```

When `uvx` encounters a bare package name without `--from`, it defaults to searching PyPI for a package with that name. There is likely a public "mcp-server" package on PyPI that implements math tools, which was being loaded instead of the local yoto-smart-stream MCP server implementation.

## Solution Implemented

Fixed the `.vscode/mcp.json` to explicitly reference the local package:

```json
"args": [
    "--from",
    "/Users/earchibald/work/yoto-smart-stream/mcp-server",
    "mcp-server"
]
```

This tells `uvx` to look for the `mcp-server` entry point in the local directory, not PyPI.

## Changes Made

1. **Fixed `.vscode/mcp.json`** - Updated to use `--from` flag with absolute path to local mcp-server package
2. **Fixed `mcp-server/server.py`** - Corrected syntax error (missing closing parenthesis in `app.run()` call)
3. **Added `test_mcp_tools.py`** - Verification test to ensure server has correct tools

## Verification

The MCP server now has:
- ✅ `oauth` tool - for activating/deactivating Yoto OAuth
- ✅ `query_library` tool - for natural language queries of the library
- ✅ No math tools (add, subtract, multiply, divide)

## Entry Point Configuration

The `mcp-server` entry point is correctly defined in `pyproject.toml`:

```toml
[project.scripts]
mcp-server = "server:main"
```

This maps the command to the `async def main()` function in `server.py`, which properly initializes the MCP server with stdio transport.

## How to Test

```bash
# Verify the MCP server code has correct tools
python test_mcp_tools.py

# Should output:
# ✅ All checks passed! MCP server code has correct tools.
```

## Next Steps

1. Restart VS Code to reload the MCP configuration
2. The "Yoto Library" MCP server should now discover the correct 2 tools
3. Test the oauth and query_library tools in VS Code's Claude Chat

## Commits

- `0c0e775` - Fix MCP server: correct syntax error and update mcp.json to use local package
- `7e08f9f` - Add MCP server tools verification test
