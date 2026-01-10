# Getting Started with Yoto Smart Stream

This guide will walk you through setting up Yoto Smart Stream from scratch.

## Prerequisites

Before you begin, ensure you have:

1. **A Yoto Player and Account**
   - Physical Yoto Player or Yoto Mini device
   - Active Yoto account

2. **Yoto API Credentials**
   - Visit [yoto.dev](https://yoto.dev/get-started/start-here/)
   - Sign in with your Yoto account
   - Create a new application to get your Client ID

3. **Development Environment**
   - Python 3.9 or higher
   - Git
   - Code editor (VS Code recommended)

## Setup Methods

Choose one of these methods to get started:

### Method 1: GitHub Codespaces (Recommended - Easiest)

1. **Open in Codespaces**
   - Navigate to the repository on GitHub
   - Click "Code" → "Codespaces" → "Create codespace on main"
   - Wait 2-3 minutes for automatic setup

2. **Configure Environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your YOTO_CLIENT_ID
   ```

3. **Authenticate**
   ```bash
   python examples/simple_client.py
   ```

4. **Start Developing!**
   Everything is pre-configured and ready to go.

### Method 2: Local Development

1. **Clone Repository**
   ```bash
   git clone https://github.com/earchibald/yoto-smart-stream.git
   cd yoto-smart-stream
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # On Linux/Mac:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your Yoto client ID:
   ```
   YOTO_CLIENT_ID=your_client_id_here
   ```

5. **Authenticate with Yoto**
   ```bash
   python examples/simple_client.py
   ```
   
   Follow the prompts to authenticate. You'll need to:
   - Visit the URL shown
   - Enter the code displayed
   - Authorize the application
   
   Your refresh token will be saved automatically.

### Method 3: Docker (Coming Soon)

Docker support is planned for future releases.

## Next Steps

Once you're set up, try these examples:

### 1. Test API Connection

```bash
python examples/simple_client.py
```

This will:
- Authenticate with Yoto API
- List your players
- Demonstrate basic player control

### 2. Monitor MQTT Events

```bash
python examples/mqtt_listener.py
```

This will:
- Connect to the MQTT broker
- Display real-time events from your players
- Help you understand event structure

Try interacting with your Yoto player to see events!

### 3. Start API Server

```bash
python examples/basic_server.py
```

Or with auto-reload:
```bash
uvicorn examples.basic_server:app --reload
```

Then visit:
- http://localhost:8000/docs - Interactive API docs
- http://localhost:8000/redoc - Alternative API docs

Try the API:
```bash
# List players
curl http://localhost:8000/api/players

# Get specific player
curl http://localhost:8000/api/players/{player_id}

# Control player
curl -X POST http://localhost:8000/api/players/{player_id}/control \
  -H "Content-Type: application/json" \
  -d '{"action": "pause"}'
```

## Development Workflow

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Set Up Pre-commit Hooks

```bash
pre-commit install
```

This will automatically:
- Format code with Black
- Lint with Ruff
- Check for common issues

### Run Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=yoto_smart_stream --cov-report=html
```

### Code Formatting

```bash
# Format code
black .

# Check formatting
black . --check

# Lint
ruff check .

# Fix linting issues
ruff check . --fix
```

## Project Structure Overview

```
yoto-smart-stream/
├── .devcontainer/          # Codespaces configuration
├── .github/
│   └── agentskills/       # Yoto API development guide
├── docs/
│   ├── ARCHITECTURE.md    # System design
│   └── PLANNING_QUESTIONS.md
├── examples/
│   ├── simple_client.py   # Basic API usage
│   ├── mqtt_listener.py   # Event monitoring
│   └── basic_server.py    # FastAPI server
├── yoto_smart_stream/     # Main package (to be implemented)
├── tests/                 # Test suite
├── pyproject.toml         # Project config
└── requirements.txt       # Dependencies
```

## Common Tasks

### Update Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Clear Cached Data

```bash
rm .yoto_refresh_token  # Remove stored token
rm -rf __pycache__      # Clear Python cache
```

### Re-authenticate

If your token expires or you want to switch accounts:

```bash
rm .yoto_refresh_token
python examples/simple_client.py
```

## Troubleshooting

### "YOTO_CLIENT_ID not configured"

**Solution**: Make sure you've:
1. Created a `.env` file from `.env.example`
2. Added your client ID to `.env`

### "Not authenticated"

**Solution**: Run the authentication script:
```bash
python examples/simple_client.py
```

### "Failed to connect to MQTT"

**Possible causes**:
- Network firewall blocking MQTT (port 8883)
- Invalid credentials
- Yoto service temporarily unavailable

**Solution**: 
- Check your network allows outbound TLS connections
- Try re-authenticating
- Check Yoto service status

### Import errors

**Solution**: Make sure you're in the virtual environment:
```bash
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

And dependencies are installed:
```bash
pip install -r requirements.txt
```

## Learning Resources

### Essential Reading

1. **[Yoto API Reference](YOTO_API_REFERENCE.md)**
   - **START HERE**: Complete API specification
   - All REST API endpoints and request/response formats
   - MQTT topics, commands, and message formats
   - Authentication details and token management
   - Data structures and models
   - Python and Node.js code examples

2. **[Yoto MQTT Reference](yoto-mqtt-reference.md)** - **NEW FROM PR#4**
   - **ESSENTIAL FOR REAL-TIME**: Deep dive into MQTT implementation
   - AWS IoT Core WebSocket connection details
   - JWT authentication specifics for MQTT
   - Complete topic structure: device/{id}/events, device/{id}/status, device/{id}/command
   - Event message formats and parsing
   - Player state synchronization patterns
   - Interactive skill integration examples

3. **[Yoto API AgentSkill](../.github/agentskills/yoto-api-development.md)**
   - Comprehensive guide to Yoto API development
   - Best practices and patterns
   - Common pitfalls and solutions

4. **[Architecture Document](ARCHITECTURE.md)**
   - System design and recommendations
   - Technology stack rationale
   - Implementation phases

5. **[Planning Questions](PLANNING_QUESTIONS.md)**
   - Strategic decisions to make
   - Feature prioritization
   - Technical considerations

### External Resources

- [Yoto Developer Portal](https://yoto.dev/)
- [yoto_api Library](https://github.com/cdnninja/yoto_api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MQTT Documentation](https://mqtt.org/)

## Next Steps for Development

1. **Read the Documentation**
   - Review the architecture document
   - Understand the Yoto API patterns
   - Review planning questions

2. **Experiment with Examples**
   - Modify the examples to try different features
   - Monitor MQTT events while using your player
   - Test API endpoints with the FastAPI server

3. **Start Building**
   - Choose a feature to implement
   - Follow the architecture recommendations
   - Use the agentskill as a reference

4. **Test and Iterate**
   - Test with your real Yoto player
   - Monitor events and logs
   - Iterate based on feedback

## Getting Help

- **GitHub Issues**: Report bugs or request features
- **GitHub Discussions**: Ask questions, share ideas
- **Documentation**: Check the docs folder for detailed guides

## Contributing

We welcome contributions! Before starting:

1. Read the architecture document
2. Check existing issues and PRs
3. Follow the code style (Black + Ruff)
4. Write tests for new features
5. Update documentation

Happy coding! 🎵🎮
