#!/usr/bin/env python3
"""Test MCP server startup with proper initialization."""

import subprocess
import sys
import time
import os

def test_server_startup():
    """Test that server starts without errors."""
    print("Testing MCP server startup...")
    
    # Run server with stdio redirect
    proc = subprocess.Popen(
        [
            sys.executable,
            "/Users/earchibald/work/yoto-smart-stream/mcp-server/server.py",
            "--yoto-service-url",
            "https://yoto-smart-stream-production.up.railway.app"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env={
            **os.environ,
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "yoto",
        }
    )
    
    # Wait a bit for startup
    time.sleep(1)
    
    # Check if process is still alive
    poll_result = proc.poll()
    
    if poll_result is not None:
        # Process exited
        stdout, stderr = proc.communicate(timeout=1)
        print(f"❌ Server exited with code {poll_result}")
        print("STDERR:", stderr[:500] if stderr else "None")
        return False
    
    # Process is running
    print("✅ Server started successfully and is waiting for stdio input")
    
    # Terminate gracefully
    proc.terminate()
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
    
    return True


if __name__ == "__main__":
    success = test_server_startup()
    sys.exit(0 if success else 1)
