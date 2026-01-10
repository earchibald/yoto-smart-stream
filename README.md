# Yoto Smart Stream

A service to stream audio to Yoto devices, monitor events via MQTT, and manage interactive audio experiences with a web UI. Includes support for "Choose Your Own Adventure" style interactive stories.

## 🎯 Features

- **Audio Streaming**: Stream custom audio content to Yoto players
- **Real-time Monitoring**: Track player events via MQTT (play/pause, button presses, battery status)
- **Interactive Cards**: Create Choose Your Own Adventure style experiences using physical button controls
- **Web UI**: Manage your audio library, configure cards, and write interactive scripts
- **Card Management**: Upload, organize, and configure custom Yoto cards
- **Multi-format Support**: Automatic audio conversion to Yoto-compatible formats

## 📋 Prerequisites

- Python 3.9 or higher
- A Yoto player and Yoto account
- Yoto API client ID (get from [yoto.dev](https://yoto.dev/get-started/start-here/))

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/earchibald/yoto-smart-stream.git
cd yoto-smart-stream
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your Yoto client ID
# YOTO_CLIENT_ID=your_client_id_here
```

### 3. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Authenticate with Yoto API

```bash
# Run the simple client example to authenticate
python examples/simple_client.py
```

Follow the prompts to authenticate. Your refresh token will be saved for future use.

### 5. Start the API Server

```bash
# Run the basic server example
python examples/basic_server.py

# Or use uvicorn directly
uvicorn examples.basic_server:app --reload
```

Visit http://localhost:8000/docs for interactive API documentation.

## 📚 Documentation

- **[Creating MYO Cards](docs/CREATING_MYO_CARDS.md)**: Complete guide to creating custom Yoto MYO (Make Your Own) cards
- **[Yoto API Reference](docs/YOTO_API_REFERENCE.md)**: Complete API specification with endpoints, MQTT topics, and code examples
- **[Yoto MQTT Reference](docs/yoto-mqtt-reference.md)**: Deep dive into MQTT event service implementation and real-time communication
- **[Architecture Guide](docs/ARCHITECTURE.md)**: System design and implementation recommendations
- **[Planning Questions](docs/PLANNING_QUESTIONS.md)**: Open questions and decision points
- **[Getting Started Guide](docs/GETTING_STARTED.md)**: Step-by-step setup instructions
- **[AgentSkill](/.github/agentskills/yoto-api-development.md)**: Comprehensive development guide for Yoto API

## 🛠️ Development

### Using GitHub Codespaces

This project is configured for GitHub Codespaces with a complete development environment:

1. Click "Code" → "Create codespace on main"
2. Wait for the environment to set up automatically
3. Start developing!

### Local Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linter
ruff check .

# Format code
black .
```

## 📖 Examples

### Basic Player Control

```python
from yoto_api import YotoManager

# Initialize and authenticate
ym = YotoManager(client_id="your_client_id")
ym.set_refresh_token("your_refresh_token")
ym.check_and_refresh_token()

# Get players
ym.update_player_status()
for player_id, player in ym.players.items():
    print(f"{player.name}: {'Online' if player.online else 'Offline'}")

# Control a player
ym.pause_player(player_id)
ym.play_player(player_id)
ym.set_volume(player_id, 10)
```

### Listen to MQTT Events

```bash
python examples/mqtt_listener.py
```

### Start API Server

```bash
python examples/basic_server.py
```

Then use the API:
```bash
# List players
curl http://localhost:8000/api/players

# Control a player
curl -X POST http://localhost:8000/api/players/{player_id}/control \
  -H "Content-Type: application/json" \
  -d '{"action": "pause"}'
```

## 🎨 Creating Custom MYO Cards

Create your own custom audio cards for Yoto players:

```python
from yoto_api import YotoManager

# Authenticate
ym = YotoManager(client_id="your_client_id")
ym.set_refresh_token("your_refresh_token")

# Create a custom card with your audio
# 1. Calculate file hash
# 2. Get upload URL
# 3. Upload audio file
# 4. Create card with metadata
# 5. Play on device
```

**Complete Step-by-Step Guide**: See [Creating MYO Cards](docs/CREATING_MYO_CARDS.md) for detailed instructions including:
- Audio file preparation and upload
- Cover image creation
- Multi-chapter card creation
- Complete Python code examples
- Troubleshooting tips

## 🎮 Interactive Cards (Choose Your Own Adventure)

Create interactive stories that respond to button presses:

```json
{
  "card_id": "adventure-001",
  "chapters": {
    "1": {
      "audio_file_id": "intro.mp3",
      "choices": {
        "left": {"next_chapter": 2},
        "right": {"next_chapter": 3}
      }
    },
    "2": {
      "audio_file_id": "left-path.mp3",
      "choices": {
        "left": {"next_chapter": 4},
        "right": {"next_chapter": 5}
      }
    }
  }
}
```

See [Architecture Guide](docs/ARCHITECTURE.md) for detailed implementation.

## 🏗️ Project Structure

```
yoto-smart-stream/
├── .devcontainer/          # GitHub Codespaces configuration
├── .github/
│   └── agentskills/       # Development guides
├── docs/                  # Documentation
├── examples/              # Example scripts
│   ├── simple_client.py   # Basic API usage
│   ├── mqtt_listener.py   # Event monitoring
│   └── basic_server.py    # FastAPI server
├── yoto_smart_stream/     # Main package (to be implemented)
├── tests/                 # Test suite
├── pyproject.toml         # Project configuration
├── requirements.txt       # Dependencies
└── README.md             # This file
```

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines before submitting PRs.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- [yoto_api](https://github.com/cdnninja/yoto_api) by cdnninja - Python wrapper for Yoto API
- Yoto Play for creating an amazing audio player for kids
- Community contributors and testers

## ⚠️ Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Yoto Play. It's an independent community project built using publicly available APIs.

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/earchibald/yoto-smart-stream/issues)
- **Discussions**: [GitHub Discussions](https://github.com/earchibald/yoto-smart-stream/discussions)
- **Yoto API**: [yoto.dev](https://yoto.dev/)

## 🗺️ Roadmap

- [x] Project setup and documentation
- [x] Basic API client examples
- [ ] Core API implementation
- [ ] Audio management system
- [ ] Interactive script engine
- [ ] Web UI
- [ ] Text-to-speech integration
- [ ] Cloud deployment guides
- [ ] Mobile app (future consideration)

---

Made with ❤️ for the Yoto community
