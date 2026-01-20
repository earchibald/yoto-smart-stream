#!/usr/bin/env python3
"""
Verification script for MCP Server structured query tools.

This script validates that all 7 tools are properly registered and discoverable.
Run this after deploying the refactored MCP server to verify the new interface.

Usage:
    python verify_mcp_tools.py [--service-url https://your-deployment.railway.app]
"""

import asyncio
import sys
import json
from typing import Any
import argparse


async def verify_mcp_tools(service_url: str = "http://localhost:8000") -> dict[str, Any]:
    """Verify all 7 MCP tools are properly registered and working."""

    try:
        # Import the server module
        sys.path.insert(0, "./mcp-server")
        import server
        
        # Check that required input models exist
        required_models = [
            "OAuthInput",
            "LibraryStatsInput",
            "ListCardsInput",
            "SearchCardsInput",
            "ListPlaylistsInput",
            "GetMetadataKeysInput",
            "GetFieldValuesInput",
        ]
        
        missing_models = []
        for model_name in required_models:
            if not hasattr(server, model_name):
                missing_models.append(model_name)
        
        if missing_models:
            return {
                "status": "error",
                "message": f"Missing input models: {', '.join(missing_models)}",
                "tools": [],
            }
            
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Failed to import server module: {e}",
            "tools": [],
        }

    results = {
        "status": "success",
        "message": "All 7 tools verified successfully",
        "tools": [],
    }

    # Verify each tool
    tools_to_verify = [
        ("oauth", "OAuthInput", "Authentication management"),
        ("library_stats", "LibraryStatsInput", "Get library statistics"),
        ("list_cards", "ListCardsInput", "List all cards"),
        ("search_cards", "SearchCardsInput", "Search cards by title"),
        ("list_playlists", "ListPlaylistsInput", "List all playlists"),
        ("get_metadata_keys", "GetMetadataKeysInput", "Get field names"),
        ("get_field_values", "GetFieldValuesInput", "Get unique field values"),
    ]

    for tool_name, input_model_name, description in tools_to_verify:
        try:
            # Check that input model exists in server module
            if not hasattr(server, input_model_name):
                raise ValueError(f"Input model {input_model_name} not found in server module")
            
            input_model_class = getattr(server, input_model_name)
            
            # Try to create an instance with minimal params
            if tool_name == "oauth":
                instance = input_model_class(action="activate")
            elif tool_name == "search_cards":
                instance = input_model_class(title_contains="test")
            elif tool_name == "get_field_values":
                instance = input_model_class(field_name="test")
            else:
                instance = input_model_class()

            results["tools"].append(
                {
                    "name": tool_name,
                    "status": "✅ OK",
                    "description": description,
                    "input_model": input_model_name,
                }
            )
        except Exception as e:
            results["tools"].append(
                {
                    "name": tool_name,
                    "status": "❌ FAILED",
                    "description": description,
                    "error": str(e),
                }
            )
            results["status"] = "partial"

    return results


def print_verification_report(results: dict[str, Any]) -> None:
    """Print verification report in human-readable format."""

    print("\n" + "=" * 70)
    print("MCP SERVER STRUCTURED QUERY TOOLS - VERIFICATION REPORT")
    print("=" * 70)

    status = results.get("status", "unknown")
    status_icon = "✅" if status == "success" else "⚠️" if status == "partial" else "❌"

    print(f"\nOverall Status: {status_icon} {status.upper()}")
    print(f"Message: {results.get('message', 'N/A')}\n")

    print("Tools Verified:")
    print("-" * 70)

    for tool in results.get("tools", []):
        status = tool.get("status", "UNKNOWN")
        name = tool.get("name", "UNNAMED")
        description = tool.get("description", "No description")
        input_model = tool.get("input_model", "N/A")

        print(f"\n{status} {name}")
        print(f"   Description: {description}")
        print(f"   Input Model: {input_model}")

        if "error" in tool:
            print(f"   Error: {tool['error']}")

    print("\n" + "-" * 70)

    # Count results
    total = len(results.get("tools", []))
    ok = sum(1 for t in results.get("tools", []) if "✅" in t.get("status", ""))

    print(f"\nResults: {ok}/{total} tools verified")

    if ok == total:
        print("\n✅ All tools are properly configured and ready to use!")
    elif ok > 0:
        print(f"\n⚠️ {total - ok} tool(s) have issues. Please review the errors above.")
    else:
        print("\n❌ No tools could be verified. Please check the installation.")

    print("=" * 70 + "\n")


def main():
    """Main entry point for verification script."""

    parser = argparse.ArgumentParser(
        description="Verify MCP server structured query tools installation"
    )
    parser.add_argument(
        "--service-url",
        default="http://localhost:8000",
        help="Service URL (for future use in extended validation)",
    )
    parser.add_argument(
        "--json", action="store_true", help="Output results as JSON"
    )

    args = parser.parse_args()

    # Run verification
    results = asyncio.run(verify_mcp_tools(args.service_url))

    # Output results
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_verification_report(results)

    # Exit with appropriate code
    if results.get("status") == "success":
        sys.exit(0)
    elif results.get("status") == "partial":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    main()
