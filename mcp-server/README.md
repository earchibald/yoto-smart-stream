# Yoto Library MCP Server

An MCP (Model Context Protocol) server that provides natural language query capabilities for Yoto card library data.

## Features

- Query your Yoto library using natural language
- Find cards by title, author, or metadata
- List playlists and their contents
- Explore metadata keys and values across your library
- Connects to your yoto-smart-stream deployment

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

- `YOTO_SERVICE_URL`: URL of your yoto-smart-stream deployment (default: `http://localhost:8000`)
- `ADMIN_USERNAME`: Username for authentication (default: `admin`)
- `ADMIN_PASSWORD`: Password for authentication (required)

### Command Line Arguments

You can also pass configuration via command line arguments:

```bash
python server.py --url https://your-deployment.railway.app \
                 --username admin \
                 --password your-password
```

Arguments take precedence over environment variables.

**Available arguments:**
- `--url`: URL of yoto-smart-stream service
- `--username`: Admin username for authentication
- `--password`: Admin password for authentication

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
        "YOTO_SERVICE_URL": "http://localhost:8000",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "your-local-password"
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
        "YOTO_SERVICE_URL": "https://your-deployment.up.railway.app",
        "ADMIN_USERNAME": "your-username",
        "ADMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

## Usage Examples

Once configured, you can query your library using natural language:

### Finding Cards

```
Find all cards with "princess" in the title
```

### Exploring Metadata

```
What metadata keys are used across the library?
```

### Checking Authors

```
What sorts of things are in card author fields?
```

### Listing Content

```
List all playlists
How many cards are there?
List all cards
```

## Available Tools

### query_library

Query the Yoto library using natural language.

**Input:**
- `query` (string): Natural language query about the library

**Examples:**
- `"find all cards with 'bedtime' in the title"`
- `"what authors are in the library?"`
- `"list all playlists"`
- `"what metadata keys are used?"`

## Available Resources

### yoto://library

Access to the complete Yoto card library data as JSON.

## Development

### Testing Locally

1. Start your yoto-smart-stream service locally or connect to a Railway deployment
2. Set environment variables:
   ```bash
   export YOTO_SERVICE_URL="http://localhost:8000"
   export ADMIN_USERNAME="admin"
   export ADMIN_PASSWORD="your-password"
   ```
3. Run the server:
   ```bash
   python server.py
   ```
4. Test with MCP Inspector:
   ```bash
   npx @modelcontextprotocol/inspector python server.py
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
