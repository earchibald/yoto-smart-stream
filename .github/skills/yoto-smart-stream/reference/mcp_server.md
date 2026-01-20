# Yoto Smart Stream MCP Server Guide

## Overview

The Yoto Smart Stream project includes an MCP (Model Context Protocol) server that enables AI agents and LLMs to interact with the Yoto Smart Stream service through standardized tools.

**Package**: `yoto-library-mcp`  
**Location**: `mcp-server/` directory  
**Current Version**: 0.1.1 (stable)  
**Status**: Production-ready

## Available Tools

The MCP server exposes two primary tools:

### 1. `oauth()` - Yoto Authentication Management

Activate or deactivate Yoto OAuth authentication for automated login.

**Parameters:**
- `service_url` (string): URL of the yoto-smart-stream deployment (e.g., `https://your-app.railway.app`)
- `action` (string): Either `"activate"` to log in or `"deactivate"` to log out

**Activate (Login)**:
```json
{
  "service_url": "https://yoto-smart-stream-production.up.railway.app",
  "action": "activate"
}
```

**Requirements:**
- `YOTO_USERNAME` environment variable with Yoto account email
- `YOTO_PASSWORD` environment variable with Yoto password
- Enables automatic OAuth device flow completion with browser automation

**Response**: Status message with OAuth token persistence confirmation

**Deactivate (Logout)**:
```json
{
  "service_url": "https://yoto-smart-stream-production.up.railway.app",
  "action": "deactivate"
}
```

**Response**: Confirmation message with logout status

### 2. `query_library()` - Natural Language Library Queries

Query the Yoto library using natural language. Supports various query patterns for exploring card metadata and structure.

**Parameters:**
- `service_url` (string): URL of the yoto-smart-stream deployment
- `query` (string): Natural language question about the library

**Supported Query Patterns:**

1. **Count cards**:
   ```
   "how many cards are there?"
   ```
   Returns: Total card count and playlist count

2. **Metadata keys**:
   ```
   "what metadata keys are used across the library?"
   ```
   Returns: List of all field names used in card objects

3. **Authors/Sources**:
   ```
   "what sorts of things are in card author fields?"
   ```
   Returns: Unique values from author field

4. **Search by title**:
   ```
   "find all cards with 'princess' in the title"
   ```
   Returns: Matching cards with details

5. **List playlists**:
   ```
   "list all playlists"
   ```
   Returns: All playlists with metadata

6. **List all cards**:
   ```
   "list all cards"
   ```
   Returns: All cards in library (truncated at 20 per response)

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

### Request Flow: query_library

1. Receive natural language query + service_url
2. Authenticate with admin credentials (or use cached cookies)
3. Fetch library JSON from `/api/library` endpoint
4. Parse and search library in-memory
5. Format response based on query pattern
6. Return results to LLM

### Request Flow: oauth

1. Receive service_url + action
2. Call `/api/auth/start` to initiate device code flow
3. Display verification URL and user code to user
4. Poll `/api/auth/status` endpoint
5. Return authorization result to LLM

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

- **0.1.1** (Current): Stable, fully tested
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

- Additional query patterns for complex library searches
- Tool for creating/uploading cards via MCP
- Streaming audio playback control
- MQTT device monitoring integration
- Card metadata editing capabilities
