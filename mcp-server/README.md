# Yoto Library MCP Server

An MCP (Model Context Protocol) server that provides natural language query capabilities for Yoto card library data and OAuth management.

## Features

- **Query your Yoto library** using natural language
- **Manage Yoto OAuth** - Activate/deactivate OAuth authentication automatically
- Find cards by title, author, or metadata
- List playlists and their contents
- Explore metadata keys and values across your library
- Query different deployments by specifying the service URL
- Per-host authentication caching for seamless multi-deployment access

## Installation

### Using uvx (Recommended)

The easiest way to use this MCP server is with `uvx`:

```bash
uvx --from /path/to/yoto-smart-stream/mcp-server mcp-server
```

### Using pip

Alternatively, you can install it locally:

```bash
cd mcp-server
pip install -e .
```

## Configuration

### Environment Variables

- `ADMIN_USERNAME`: Username for yoto-smart-stream service authentication (default: `admin`)
- `ADMIN_PASSWORD`: Password for yoto-smart-stream service authentication (required)
- `YOTO_USERNAME`: Yoto account email for OAuth automation (optional, required for oauth tool)
- `YOTO_PASSWORD`: Yoto account password for OAuth automation (optional, required for oauth tool)

### Command Line Arguments

You can also pass configuration via command line arguments:

```bash
python server.py --url https://your-deployment.railway.app \
                 --username admin \
                 --password your-password
```

Arguments take precedence over environment variables.

**Available arguments:**
- `--url`: URL of yoto-smart-stream service (not required - pass per-request instead)
- `--username`: Admin username for authentication
- `--password`: Admin password for authentication

**Note**: Unlike the original implementation, the service URL is now passed as a parameter to each tool call, allowing you to query multiple deployments.

## VS Code Configuration

Add this to your VS Code `mcp.json` file (typically at `.vscode/mcp.json` or in your user settings):

### Option 1: Using uvx (Recommended)

```json
{
  "mcpServers": {
    "yoto-library": {
      "command": "uvx",
      "args": [
        "--from",
        "/absolute/path/to/yoto-smart-stream/mcp-server",
        "mcp-server"
      ],
      "env": {
        "YOTO_SERVICE_URL": "https://your-deployment.up.railway.app",
        "ADMIN_USERNAME": "your-username",
        "ADMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

### Option 2: Using Python directly

```json
{
  "mcpServers": {
    "yoto-library": {
      "command": "python",
      "args": [
        "/absolute/path/to/yoto-smart-stream/mcp-server/server.py"
      ],
      "env": {
        "YOTO_SERVICE_URL": "https://your-deployment.up.railway.app",
        "ADMIN_USERNAME": "your-username",
        "ADMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

### Option 4: Using CLI arguments

```json
{
  "mcpServers": {
    "yoto-library": {
      "command": "python",
      "args": [
        "/absolute/path/to/yoto-smart-stream/mcp-server/server.py",
        "--url",
        "https://your-deployment.up.railway.app",
        "--username",
        "admin",
        "--password",
        "your-password"
      ]
    }
  }
}
```

**Note**: Using environment variables is more secure than passing passwords as command-line arguments.

### Option 5: Local development

### Option 4: Local development

For local development against a locally-running yoto-smart-stream service:

```json
{
  "mcpServers": {
    "yoto-library": {
      "command": "python",
      "args": [
        "/absolute/path/to/yoto-smart-stream/mcp-server/server.py"
      ],
      "env": {
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "your-local-password",
        "YOTO_USERNAME": "your-yoto-email@example.com",
        "YOTO_PASSWORD": "your-yoto-password"
      }
    }
  }
}
```

## Claude Desktop Configuration

Add this to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "yoto-library": {
      "command": "uvx",
      "args": [
        "--from",
        "/absolute/path/to/yoto-smart-stream/mcp-server",
        "mcp-server"
      ],
      "env": {
        "ADMIN_USERNAME": "your-username",
        "ADMIN_PASSWORD": "your-password",
        "YOTO_USERNAME": "your-yoto-email@example.com",
        "YOTO_PASSWORD": "your-yoto-password"
      }
    }
  }
}
```

## Usage Examples

### Managing Yoto OAuth

Before querying the library, you need to activate Yoto OAuth:

```
Activate Yoto OAuth for https://yoto-smart-stream-production.up.railway.app
```

To deactivate:

```
Deactivate Yoto OAuth for https://yoto-smart-stream-production.up.railway.app
```

**Note**: OAuth activation requires `YOTO_USERNAME` and `YOTO_PASSWORD` environment variables with your Yoto account credentials.

### Finding Cards

```
Find all cards with "princess" in the title at https://yoto-smart-stream-production.up.railway.app
```

### Exploring Metadata

```
What metadata keys are used across the library at https://yoto-smart-stream-develop.up.railway.app?
```

### Checking Authors

```
What sorts of things are in card author fields at https://myapp.railway.app?
```

### Listing Content

```
List all playlists from https://yoto-smart-stream-pr-105.up.railway.app
How many cards are there at https://yoto-smart-stream-production.up.railway.app?
```

**Note**: You can query different deployments by specifying different service URLs in your requests.

## Available Tools

### oauth

Activate or deactivate Yoto OAuth authentication.

**Input:**
- `service_url` (string): URL of the yoto-smart-stream service
- `action` (string): "activate" to log in, "deactivate" to log out

**Examples:**
- `service_url: "https://yoto-smart-stream-pr-105.up.railway.app", action: "activate"`
- `service_url: "https://yoto-smart-stream-production.up.railway.app", action: "deactivate"`

**Requirements:**
- For activation: `YOTO_USERNAME` and `YOTO_PASSWORD` environment variables must be set
- Playwright must be installed: `pip install playwright && playwright install chromium`

### query_library

Query the Yoto library using natural language.

**Input:**
- `service_url` (string): URL of the yoto-smart-stream service
- `query` (string): Natural language query about the library

**Examples:**
- `service_url: "https://yoto-smart-stream-production.up.railway.app", query: "find all cards with 'bedtime' in the title"`
- `service_url: "https://yoto-smart-stream-pr-105.up.railway.app", query: "what authors are in the library?"`
- `service_url: "https://yoto-smart-stream-develop.up.railway.app", query: "list all playlists"`

## Available Resources

### yoto://library

Access to the complete Yoto card library data as JSON (not yet implemented as parameterized resource).

## Development

### Installing Dependencies

```bash
cd mcp-server
pip install -e .
pip install playwright
playwright install chromium
```

### Testing Locally

1. Start your yoto-smart-stream service locally or connect to a Railway deployment
2. Set environment variables:
   ```bash
   export ADMIN_USERNAME="admin"
   export ADMIN_PASSWORD="your-password"
   export YOTO_USERNAME="your-yoto-email@example.com"
   export YOTO_PASSWORD="your-yoto-password"
   ```
3. Run the server:
   ```bash
   python server.py
   ```
4. Test with MCP Inspector:
   ```bash
   npx @modelcontextprotocol/inspector python server.py
   ```

### Testing OAuth Tool

```bash
# Install playwright
pip install playwright
playwright install chromium

# Test OAuth activation
# The tool will use YOTO_USERNAME and YOTO_PASSWORD to automate browser login
python server.py
# Then use the oauth tool with action="activate" and your service URL
```

### Project Structure

```
mcp-server/
├── server.py           # Main MCP server implementation
├── pyproject.toml      # Package configuration
└── README.md           # This file
```

## Troubleshooting

### Authentication Errors

If you see "Authentication failed" errors:
- Verify your `ADMIN_USERNAME` and `ADMIN_PASSWORD` are correct
- Ensure the user exists in your yoto-smart-stream deployment
- Check that the deployment URL is accessible

### Connection Errors

If you see connection errors:
- Verify `YOTO_SERVICE_URL` is correct and accessible
- Check that your yoto-smart-stream service is running
- Ensure you're using `https://` for Railway deployments, `http://` for local

### No Results

If queries return no results:
- Ensure you're logged into Yoto in your yoto-smart-stream service
- Check that the library has been synced
- Visit the `/api/library` endpoint in your browser to verify data exists

## License

MIT
