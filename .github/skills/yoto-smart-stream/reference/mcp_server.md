# Yoto Smart Stream MCP Server Guide

## Overview

The Yoto Smart Stream project includes an MCP (Model Context Protocol) server that enables AI agents and LLMs to interact with the Yoto Smart Stream service through standardized tools.

**Package**: `yoto-library-mcp`  
**Location**: `mcp-server/` directory  
**Current Version**: 0.1.4 (stable)  
**Status**: Production-ready  
**Framework**: FastMCP (mcp.server.fastmcp)

## Available Tools

The MCP server exposes seven specialized structured query tools:

> **Migration Note (v0.1.4+)**: Previous versions used a single natural language `query_library` tool. This has been replaced with 7 specialized structured query tools for better LLM integration and reliability. See [Migration Guide](#migration-from-natural-language-queries) below.

### 1. `oauth()` - Yoto Authentication Management

Activate or deactivate Yoto OAuth authentication for automated login.

**Parameters:**
- `service_url` (string): URL of the yoto-smart-stream deployment (e.g., `https://your-app.railway.app`)
- `action` (string): Either `"activate"` to log in or `"deactivate"` to log out

### 2. `library_stats()` - Get Library Statistics

Get total count of cards and playlists in the library.

**Parameters:**
- `service_url` (string, optional): URL of the yoto-smart-stream service (uses default if not provided)

**Returns:** `{"total_cards": number, "total_playlists": number}`

### 3. `list_cards()` - List Cards

List all cards in the library with pagination support.

**Parameters:**
- `limit` (integer, 1-100): Maximum number of cards to return (default: 20)
- `service_url` (string, optional): URL of the yoto-smart-stream service

**Returns:** Array of cards with id, title, author, type, and description

### 4. `search_cards()` - Search Cards by Title

Search for cards where the title contains specified text.

**Parameters:**
- `title_contains` (string): Text to search for in card titles
- `limit` (integer, 1-100): Maximum results to return (default: 20)
- `service_url` (string, optional): URL of the yoto-smart-stream service

**Returns:** Matching cards with search metadata

### 5. `list_playlists()` - List Playlists

List all playlists in the library.

**Parameters:**
- `service_url` (string, optional): URL of the yoto-smart-stream service

**Returns:** Array of playlists with id, name, and item count

### 6. `get_metadata_keys()` - Get Metadata Keys

Get all unique metadata keys used across library cards.

**Parameters:**
- `service_url` (string, optional): URL of the yoto-smart-stream service

**Returns:** Sorted list of field names used in card objects

### 7. `get_field_values()` - Get Field Values

Get all unique values for a specific card field.

**Parameters:**
- `field_name` (string): The card field to get values for (e.g., 'author', 'type', 'genre')
- `limit` (integer, 1-500): Maximum values to return (default: 50)
- `service_url` (string, optional): URL of the yoto-smart-stream service

**Returns:** Sorted list of unique values for the field

## Installation & Setup

### Local Development

```bash
cd mcp-server
pip install -e .
```

### VS Code Integration

Add to `.mcp-servers.json` or `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "yoto-library": {
      "command": "uvx",
      "args": ["--from", "/path/to/yoto-smart-stream/mcp-server", "mcp-server"],
      "env": {
        "YOTO_SERVICE_URL": "https://your-deployment.railway.app",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "your-password",
        "YOTO_USERNAME": "your-yoto-email@example.com",
        "YOTO_PASSWORD": "your-yoto-password"
      }
    }
  }
}
```

### Environment Variables

**Required for Service Access:**
- `ADMIN_USERNAME` - Admin username for yoto-smart-stream
- `ADMIN_PASSWORD` - Admin password for yoto-smart-stream
- `YOTO_SERVICE_URL` - Base URL of yoto-smart-stream deployment

**Optional for OAuth Automation:**
- `YOTO_USERNAME` - Email for Yoto account
- `YOTO_PASSWORD` - Password for Yoto account

### Railway Deployment

For a deployed instance at `https://yoto-smart-stream-production.up.railway.app`:

```bash
mcp-server \
  --url https://yoto-smart-stream-production.up.railway.app \
  --username admin \
  --password $ADMIN_PASSWORD
```

## Authentication & Caching

### Per-Host Authentication

The MCP server implements per-host authentication caching:

- Authenticates once with admin credentials per service URL
- Caches session cookies to avoid repeated authentication
- Automatically re-authenticates on 401 Unauthorized response
- Thread-safe cache managed in `AUTH_CACHE` dictionary

### Error Handling

- **Authentication Failures**: Clear error messages with next steps
- **Service Unavailability**: Graceful degradation with helpful messages
- **Invalid Queries**: Natural language fallback with pattern suggestions

## Implementation Details

### Architecture

```
MCP Server (stdio protocol)
    ↓
FastMCP Framework (tool registration)
    ↓
Tool Handlers (oauth, query_library)
    ↓
HTTP Client (async httpx)
    ↓
Yoto Smart Stream Service
```

### Request Flow: OAuth Tool

1. Receive service_url + action
2. Call `/api/auth/start` to initiate device code flow
3. Display verification URL and user code to user
4. Poll `/api/auth/status` endpoint
5. Return authorization result with Status field to LLM

### Response Format: Structured JSON

All tools return structured JSON responses with:

**Library Query Tools:**
```json
{
  "total_cards": 150,        // or "cards": [...], "matches": [...], etc
  "field_name": "author",    // context-specific fields
  "values": [...],           // returned data
  // ... other response-specific fields
}
```

**OAuth Tool:**
```
Action result message...
Status: <status_value>
```
- Status values: `success`, `pending`, `error`, `expired`

## Testing

### Unit Tests

```bash
cd mcp-server
python test_tools.py        # Test tool structure and schemas
python test_with_auth.py    # Test actual functionality with authentication
```

### Test Coverage

- Tool registration and discovery
- Input schema validation
- Authentication flows
- Library queries (all patterns)
- OAuth Status field format validation
- Error handling
- Response formatting

## Development & Maintenance

### Project Structure

```
mcp-server/
├── server.py              # Main MCP server implementation
├── pyproject.toml         # Package configuration
├── test_tools.py          # Tool structure tests
├── test_with_auth.py      # Integration tests
├── README.md              # User documentation
└── TEST_RESULTS.md        # Test result summary
```

### Version History

- **0.1.4** (Current): Stable, production-ready
  - Added Status field to oauth tool responses (success, pending, error, expired)
  - Comprehensive test coverage with status field verification
  - FastMCP framework migration complete
  - All tools fully tested and documented

- **0.1.1**: Stable version
  - Both `oauth()` and `query_library()` fully functional
  - Comprehensive test suite
  - Production-ready

- **0.1.0**: Initial release
  - Basic tool structure
  - Core functionality

### Semver Guidelines

When making changes:
- **Patch (0.1.x)**: Bug fixes, test additions, documentation updates
- **Minor (0.x.0)**: New tools, new query patterns, non-breaking enhancements
- **Major (x.0.0)**: Breaking changes to tool signatures or protocols

### Known Limitations

- OAuth automation requires Yoto credentials (browser-based auth not automatable for security)
- Library queries are in-memory searches (no database queries)
- Query patterns limited to documented natural language forms
- Max 20 cards displayed per response (pagination available via modified queries)

## API Integration Points

The MCP server depends on these yoto-smart-stream API endpoints:

- `POST /api/user/login` - Admin authentication
- `GET /api/library` - Library data retrieval
- `POST /api/auth/start` - Device flow initiation
- `GET /api/auth/status` - Device flow polling
- `POST /api/auth/logout` - OAuth logout

## Best Practices

1. **Configure for each deployment**: Use environment variables to target specific deployments
2. **Enable OAuth credentials only when needed**: OAuth automation requires storing credentials
3. **Cache friendly**: The server handles authentication caching internally
4. **Query patterns**: Use documented natural language patterns for best results
5. **Error recovery**: Errors include suggestions for resolution

## Troubleshooting

### Authentication Failures

**Issue**: `401 Unauthorized` on service requests

**Solution**:
1. Verify `ADMIN_USERNAME` and `ADMIN_PASSWORD` are correct
2. Check service is running: `curl https://service-url/api/status`
3. Ensure credentials have admin privileges

### OAuth Activation Fails

**Issue**: `YOTO_USERNAME and YOTO_PASSWORD environment variables are required`

**Solution**:
1. Set environment variables with valid Yoto account credentials
2. Ensure Yoto account is registered and has device(s) authorized
3. For automation, use device code flow (browser-based recommended for security)

### Query Returns Limited Results

**Issue**: Only 20 cards shown in library list

**Solution**:
- This is the configured limit for response size
- Modify query to be more specific: `"find all cards with 'specific title' in the title"`
- Use pagination patterns (documented in query_library function)

## Future Enhancements

Potential improvements for future versions:

- Tool for advanced filtering across multiple fields
- Tool for creating/uploading cards via MCP
- Streaming audio playback control
- MQTT device monitoring integration
- Card metadata editing capabilities
- Batch operations for multiple cards

## Migration from Natural Language Queries

### Background: Why We Changed

**Previous Approach (< v0.1.4):**
- Single `query_library()` tool accepting free-form natural language queries
- Tool tried to parse queries and route to appropriate functionality
- Examples: "find all cards with 'math' in the title", "how many playlists do I have?"
- **Problem**: Fragile regex parsing, inconsistent results, unclear tool interface

**New Approach (v0.1.4+):**
- Seven specialized structured query tools with explicit parameters
- Each tool has clear purpose and typed input/output
- LLMs can reliably understand capabilities without guessing
- **Benefit**: Better integration, consistent results, clearer error messages

### Migration Path

If you were using the `query_library` tool before v0.1.4, here's how to migrate:

**Old Query:**
```
"Find all cards with 'math' in the title"
→ query_library(query="find all cards with 'math' in the title")
```

**New Query:**
```
→ search_cards(title_contains="math")
```

**Old Query:**
```
"How many cards and playlists do I have?"
→ query_library(query="how many cards and playlists do I have?")
```

**New Query:**
```
→ library_stats()
```

**Old Query:**
```
"Show me all the cards"
→ query_library(query="list all cards")
```

**New Query:**
```
→ list_cards(limit=50)  # or whatever limit you need
```

**Old Query:**
```
"What categories of cards do I have?"
→ query_library(query="get metadata keys")
```

**New Query:**
```
→ get_metadata_keys()
```

### Why This is Better

1. **Clear Contracts**: Each tool has documented parameters and return types
2. **Better Error Messages**: If you pass invalid parameters, you get clear feedback
3. **Type Safety**: Pydantic validation ensures parameters are valid before execution
4. **LLM Integration**: LLMs understand tools better than parsing natural language
5. **Performance**: No regex parsing overhead, direct execution
6. **Testing**: Easier to write tests for each tool independently

### Unsupported Query Patterns

The following natural language patterns are no longer supported in v0.1.4+:

| Old Pattern | Migration Strategy |
|---|---|
| "Find cards created by X" | Use `get_field_values(field_name="author")` then filter results |
| "Show me X cards" | Use `list_cards(limit=X)` |
| "Filter by X property" | Use `get_field_values(field_name="X")` to explore values |
| "How many items in playlist Y" | Use `list_playlists()` to find playlist, check item_count |

If you need a query pattern that's no longer available, consider opening an issue to request a new specialized tool.
