# yoto-smart-stream

A service package to stream audio to a yoto device, monitor events from that device with MQTT and change what it is doing in response, with a web UI to configure, upload, record and manage audio and card scripts. Should support "Choose Your Own Adventure" style as one option.

## 📚 Documentation

This repository contains comprehensive documentation for the Yoto Smart Stream project, including API references, MQTT service documentation, and web UI wireframe proposals.

### API & Integration Documentation

- **[YOTO_API_REFERENCE.md](YOTO_API_REFERENCE.md)** - Comprehensive Yoto API documentation
  - Authentication and OAuth2 Device Flow
  - REST API endpoints for devices, content, and configuration
  - MQTT real-time communication
  - Code examples in Python and Node.js
  - Useful libraries and official resources

- **[Yoto MQTT Event Service Reference](docs/yoto-mqtt-reference.md)** - Deep dive into MQTT implementation
  - Architecture and core components
  - Authentication and token management
  - MQTT connection setup and lifecycle
  - Topic structure and message formats
  - Command reference for player control
  - Event handling and state management
  - Integration patterns and examples
  - Security, performance, and debugging best practices

### Web UI Wireframe Documents

- **[WIREFRAME_SUMMARY.md](./WIREFRAME_SUMMARY.md)** - Start here! Overview of all wireframe documentation
- **[WIREFRAMES.md](./WIREFRAMES.md)** - Detailed wireframes for 7 core pages (31KB, 516 lines)
  - Dashboard, Library, Script Editor, CYOA Builder, Device Monitor, Upload/Recording, Settings
- **[UI_COMPONENTS.md](./UI_COMPONENTS.md)** - Reusable component library (16KB, 602 lines)
  - 20 detailed UI components with props and layouts
- **[USER_JOURNEYS.md](./USER_JOURNEYS.md)** - User flows and interaction patterns (20KB, 850 lines)
  - 3 user personas, 5 complete user journeys, interaction patterns, accessibility
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - System architecture and data flows (30KB, 857 lines)
  - System diagrams, database schema, API endpoints, MQTT structure, deployment

## 🎯 Key Features

### 1. Audio Management
- Upload audio files via drag-and-drop
- Record audio directly in the browser
- Organize and search audio library
- Create playlists and card scripts

### 2. Device Monitoring (MQTT)
- Real-time device status tracking
- Live event streams from devices
- Remote device control
- Multi-device management

### 3. Interactive Story Builder (CYOA)
- Visual node-based editor
- Branching narrative paths
- MQTT button mapping
- Audio integration at decision points

### 4. Web Interface
- Responsive design (mobile, tablet, desktop)
- Real-time updates via WebSocket
- Intuitive user flows
- Comprehensive analytics

## 🚀 Quick Start

### Explore the Wireframes

1. Start with [WIREFRAME_SUMMARY.md](./WIREFRAME_SUMMARY.md) for an overview
2. Review [WIREFRAMES.md](./WIREFRAMES.md) to see all page layouts
3. Check [USER_JOURNEYS.md](./USER_JOURNEYS.md) for user flows
4. Read [ARCHITECTURE.md](./ARCHITECTURE.md) for technical details

### Implementation

The wireframes are implementation-agnostic but include technology recommendations:
- **Frontend**: React/Vue/Svelte with TypeScript
- **Backend**: Node.js or Python with REST API
- **Real-time**: WebSocket for MQTT events
- **Database**: PostgreSQL + Redis
- **MQTT Broker**: Mosquitto or RabbitMQ

See [ARCHITECTURE.md](./ARCHITECTURE.md) for complete technology stack recommendations.

## 📖 What's Included

### Page Wireframes
- Dashboard with device status and quick actions
- Audio library with grid/list views
- Card script editor with playlist support
- CYOA story builder with visual flow editor
- Device monitoring with live MQTT events
- Upload modal and recording interface
- Settings and configuration pages

### UI Components (20 total)
DeviceCard, AudioFileCard, NodeEditor, MQTTEventLog, FileUploader, AudioRecorder, FlowCanvas, ScriptTreeView, StatusIndicator, ProgressBar, PlaybackControls, Modal, Sidebar, SearchBar, FilterPanel, NotificationToast, StatCard, TabPanel, ContextMenu, EmptyState

### User Journeys (5 scenarios)
1. First-time user setup
2. Creating a simple playlist
3. Building a CYOA story
4. Monitoring device activity
5. Recording audio directly

### Architecture Coverage
- System architecture diagrams
- Data flow illustrations
- Database schema (7 tables)
- API endpoints (30+ endpoints)
- MQTT topic structure
- Security considerations
- Scalability patterns
- Deployment architecture

## 🎨 Design Principles

1. **Clarity**: Clear labels and intuitive workflows
2. **Real-time Feedback**: Live updates via MQTT
3. **Flexibility**: Support simple and complex use cases
4. **Accessibility**: WCAG 2.1 Level AA compliance
5. **Performance**: Optimized for large libraries and real-time data

## 🔧 Next Steps

1. **Prototype**: Create clickable prototypes in Figma/Sketch
2. **User Testing**: Validate wireframes with target users
3. **Technical Planning**: Assess implementation complexity
4. **Design**: Create high-fidelity mockups
5. **Development**: Begin implementation

## 📊 Documentation Stats

- **Total Documentation**: ~103KB across 5 markdown files
- **Total Lines**: 2,882 lines of detailed specifications
- **Wireframe Pages**: 7 core pages + navigation
- **UI Components**: 20 reusable components
- **User Journeys**: 5 complete end-to-end flows
- **API Endpoints**: 30+ REST endpoints documented

## 📝 License

[Specify your license here]

## 👥 Contributing

This is a wireframe proposal repository. For implementation, please:
1. Review all wireframe documents
2. Provide feedback on user flows
3. Suggest improvements or missing features
4. Help prioritize development phases

## 📧 Contact

[Add contact information for questions/feedback]
