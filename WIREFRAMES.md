# Yoto Smart Stream Web UI - Wireframe Proposal

## Overview
This document proposes wireframe ideas for the Yoto Smart Stream web interface, designed to manage audio streaming, device monitoring via MQTT, and interactive audio experiences like "Choose Your Own Adventure" stories.

---

## 1. Dashboard / Home Page

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ [Logo] Yoto Smart Stream                    [User] [Settings]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │  Connected Devices  │  │   Stream Status     │              │
│  │                     │  │                     │              │
│  │  🟢 Living Room     │  │  ▶️ Playing         │              │
│  │  🟢 Kids Bedroom    │  │  "Story Time Vol 1" │              │
│  │  🔴 Kitchen (Off)   │  │  Track 3/12         │              │
│  │                     │  │  [Pause] [Skip]     │              │
│  └─────────────────────┘  └─────────────────────┘              │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Recent Activity                                 ││
│  │  • Living Room played "Bedtime Stories" - 5 mins ago        ││
│  │  • Kids Bedroom completed "CYOA: Dragon Quest" - 1hr ago    ││
│  │  • Kitchen device disconnected - 2hrs ago                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
│  [Quick Actions]                                                 │
│  [➕ Upload Audio]  [🎙️ Record Audio]  [📝 New Card Script]    │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Features
- Real-time device status with MQTT connection indicators
- Current playback status across all devices
- Quick access to common actions
- Activity feed showing recent events

---

## 2. Audio Library

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Audio Library                                                    │
├─────────────────────────────────────────────────────────────────┤
│ [🔍 Search]  [📁 Filter: All ▼]  [+ Upload Audio]  [🎙️ Record] │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  🎵        │  │  🎵        │  │  🎵        │                │
│  │            │  │            │  │            │                │
│  │ Story Time │  │  Bedtime   │  │  Music     │                │
│  │  Vol 1     │  │  Tales     │  │  Mix       │                │
│  │            │  │            │  │            │                │
│  │ 12 tracks  │  │  8 tracks  │  │ 20 tracks  │                │
│  │ 45:32      │  │ 32:15      │  │ 1:15:00    │                │
│  │            │  │            │  │            │                │
│  │ [▶️] [✏️]  │  │ [▶️] [✏️]  │  │ [▶️] [✏️]  │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                   │
│  [View: Grid | List]                        [Page 1 of 5 →]     │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Features
- Grid and list view options
- Search and filter capabilities
- Metadata display (duration, track count)
- Quick play and edit actions
- Batch operations for multiple files

---

## 3. Card Script Editor

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Card Script Editor                                [Save] [Test]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Script Name: [Dragon Quest Adventure____________] Type: [CYOA ▼]│
│                                                                   │
│  ┌─────────────────────┐  ┌───────────────────────────────────┐│
│  │ Script Structure    │  │ Node Editor                       ││
│  │                     │  │                                   ││
│  │ 📍 Start            │  │ Node ID: start_01                ││
│  │ ├─ 🔊 intro.mp3     │  │                                   ││
│  │ └─ ❓ Choice 1      │  │ Audio: [intro.mp3 ▼] [Preview ▶️]││
│  │    ├─ 🔊 path_a.mp3 │  │                                   ││
│  │    └─ 🔊 path_b.mp3 │  │ Type: [Audio Playback ▼]         ││
│  │                     │  │                                   ││
│  │ [+ Add Node]        │  │ Next Actions:                     ││
│  │                     │  │ • MQTT Button 1 → [choice_1a]    ││
│  │                     │  │ • MQTT Button 2 → [choice_1b]    ││
│  │                     │  │ • Auto-advance  → [none]         ││
│  │                     │  │                                   ││
│  │                     │  │ [Add Action +]                    ││
│  └─────────────────────┘  └───────────────────────────────────┘│
│                                                                   │
│  Visual Flow Preview:                                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  [Start] → [Intro Audio] → {Choice?} → [Path A] / [Path B] │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Features
- Tree view of script structure
- Node-based editor for individual script elements
- MQTT event mapping (button presses, etc.)
- Visual flow diagram
- Audio preview for each node
- Support for branching logic (Choose Your Own Adventure)
- Templates for common script patterns

---

## 4. Device Monitor & Control

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Devices                                        [+ Add Device]    │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Device: Living Room Yoto                        🟢 Connected    │
│  ┌──────────────────────────────────────────────────────────────┤
│  │ Current Status:                                              │
│  │   Playing: "Dragon Quest - Part 2"                          │
│  │   Progress: [████████░░░░░░] 8:32 / 15:00                   │
│  │   Volume: [██████░░░░] 60%                                   │
│  │                                                              │
│  │ Controls:                                                    │
│  │   [⏮️ Prev]  [⏸️ Pause]  [⏭️ Next]  [🔊 Volume]            │
│  │                                                              │
│  │ MQTT Events (Live):                                         │
│  │   ┌────────────────────────────────────────────────────────┐│
│  │   │ 08:15:32 - Button 1 pressed                           ││
│  │   │ 08:15:30 - Playback started                           ││
│  │   │ 08:15:28 - Card inserted (ID: card_001)               ││
│  │   │ 08:14:55 - Volume changed to 60%                      ││
│  │   └────────────────────────────────────────────────────────┘│
│  │                                                              │
│  │ Device Info:                                                 │
│  │   IP: 192.168.1.105    Firmware: 2.4.1    Battery: 85%     │
│  │                                                              │
│  └──────────────────────────────────────────────────────────────┤
│                                                                   │
│  Device: Kids Bedroom Yoto                       🟢 Connected    │
│  ┌──────────────────────────────────────────────────────────────┤
│  │ Current Status: Idle                                         │
│  │ Last Activity: 45 minutes ago                                │
│  └──────────────────────────────────────────────────────────────┤
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Features
- Real-time device status via MQTT
- Live event stream for each device
- Remote control capabilities
- Device information and health metrics
- Multi-device management

---

## 5. Upload & Recording Interface

### Upload Modal
```
┌─────────────────────────────────────────────────┐
│ Upload Audio Files                        [✕]   │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌────────────────────────────────────────────┐│
│  │                                            ││
│  │     📁 Drag & Drop Files Here             ││
│  │           or                              ││
│  │     [Browse Files]                        ││
│  │                                            ││
│  │  Supported: MP3, WAV, OGG, FLAC           ││
│  │  Max size: 500MB per file                 ││
│  │                                            ││
│  └────────────────────────────────────────────┘│
│                                                 │
│  Uploaded Files:                                │
│  ✓ story_intro.mp3       (2.3 MB)             │
│  ⏳ bedtime_tale.wav     (15.2 MB) [▓▓░░] 45% │
│                                                 │
│  [Cancel]                        [Upload All]  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Recording Interface
```
┌─────────────────────────────────────────────────┐
│ Record Audio                              [✕]   │
├─────────────────────────────────────────────────┤
│                                                 │
│  🎙️ Ready to Record                            │
│                                                 │
│  ┌────────────────────────────────────────────┐│
│  │         [●] Record                         ││
│  │         [⏸️] Pause                          ││
│  │         [⏹️] Stop                           ││
│  │                                            ││
│  │         00:00:00                           ││
│  │                                            ││
│  │  Level: [████████░░░░░] 🔊               ││
│  └────────────────────────────────────────────┘│
│                                                 │
│  Input Device: [Built-in Microphone ▼]         │
│  Quality: [High (320kbps) ▼]                   │
│                                                 │
│  File Name: [my_recording_____________]         │
│                                                 │
│  [Cancel]                            [Save]    │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Features
- Drag-and-drop file upload
- Progress indicators for uploads
- Multiple file support
- Direct audio recording from browser
- Real-time audio level monitoring
- Format and quality selection

---

## 6. Interactive Story (CYOA) Builder

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ CYOA Story Builder: Dragon Quest              [Save] [Preview]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [Story Info] [Nodes] [Flow] [Test]                             │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Visual Flow Editor                      │  │
│  │                                                            │  │
│  │     ┌─────────┐                                           │  │
│  │     │ START   │                                           │  │
│  │     │ intro   │                                           │  │
│  │     └────┬────┘                                           │  │
│  │          │                                                │  │
│  │          ↓                                                │  │
│  │     ┌────────────┐                                        │  │
│  │     │  CHOICE 1  │                                        │  │
│  │     │ Go left/   │                                        │  │
│  │     │ right?     │                                        │  │
│  │     └──┬─────┬───┘                                        │  │
│  │        │     │                                            │  │
│  │   ┌────┘     └────┐                                       │  │
│  │   ↓               ↓                                       │  │
│  │ ┌─────┐       ┌─────┐                                    │  │
│  │ │Left │       │Right│                                    │  │
│  │ │Path │       │Path │                                    │  │
│  │ └──┬──┘       └──┬──┘                                    │  │
│  │    │             │                                        │  │
│  │    └──────┬──────┘                                        │  │
│  │           ↓                                               │  │
│  │       ┌───────┐                                           │  │
│  │       │  END  │                                           │  │
│  │       └───────┘                                           │  │
│  │                                                            │  │
│  │  [+ Add Node]  [🔗 Connect]  [🗑️ Delete]  [📋 Copy]     │  │
│  │                                                            │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                   │
│  Selected Node: Choice 1                                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Audio: [choice_1.mp3 ▼]                   [Preview ▶️]     ││
│  │ Text: "Do you want to go left or right?"                   ││
│  │                                                             ││
│  │ Button Actions:                                             ││
│  │ • Button 1 (Left) → Node: left_path                        ││
│  │ • Button 2 (Right) → Node: right_path                      ││
│  │                                                             ││
│  │ Options:                                                    ││
│  │ ☑️ Repeat if no response (30 sec timeout)                  ││
│  │ ☑️ Show display icon on Yoto Mini                          ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Features
- Drag-and-drop node editor
- Visual flow representation
- Connection mapping between nodes
- Button/MQTT event configuration
- Audio preview at each decision point
- Timeout and fallback options
- Story validation (check for dead ends, loops)
- Test mode to simulate playback

---

## 7. Settings & Configuration

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Settings                                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│ [General] [MQTT] [Audio] [Devices] [Users] [System]             │
│                                                                   │
│ MQTT Configuration                                               │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │                                                               ││
│ │ Broker URL:     [mqtt://broker.local_________________]       ││
│ │ Port:           [1883____]                                   ││
│ │ Username:       [admin____________________]                  ││
│ │ Password:       [**********]                                 ││
│ │                                                               ││
│ │ Topics:                                                       ││
│ │   Device Status:  [yoto/+/status_______]                     ││
│ │   Events:         [yoto/+/events_______]                     ││
│ │   Commands:       [yoto/+/commands_____]                     ││
│ │                                                               ││
│ │ Connection Status: 🟢 Connected                              ││
│ │                                                               ││
│ │ [Test Connection]                                            ││
│ │                                                               ││
│ └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│ Audio Settings                                                   │
│ ┌──────────────────────────────────────────────────────────────┐│
│ │                                                               ││
│ │ Default Format:  [MP3 ▼]                                     ││
│ │ Bitrate:         [192 kbps ▼]                                ││
│ │ Sample Rate:     [44.1 kHz ▼]                                ││
│ │                                                               ││
│ │ Storage Path:    [/var/lib/yoto/audio__________]             ││
│ │                                                               ││
│ │ ☑️ Auto-convert uploaded files to default format             ││
│ │ ☑️ Generate thumbnails for audio files                       ││
│ │ ☐ Enable audio normalization                                ││
│ │                                                               ││
│ └──────────────────────────────────────────────────────────────┘│
│                                                                   │
│ [Save Changes]                                                   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Features
- MQTT broker configuration
- Audio format and quality settings
- Device management and pairing
- User access control
- System preferences
- Backup and restore options

---

## 8. Display Icon Manager

### Layout
```
┌─────────────────────────────────────────────────────────────────┐
│ Display Icon Manager                         [+ Upload Icon]    │
├─────────────────────────────────────────────────────────────────┤
│ [Public Icons] [My Icons] [Recently Used]                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [🔍 Search icons...]  [📁 Category: All ▼]  [Grid | List]     │
│                                                                   │
│  Public Icon Repository:                                         │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  🎵        │  │  📖        │  │  ⭐        │                │
│  │            │  │            │  │            │                │
│  │  Music     │  │  Story     │  │  Featured  │                │
│  │            │  │            │  │            │                │
│  │ [Select]   │  │ [Select]   │  │ [Select]   │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │  🌙        │  │  🎨        │  │  🎮        │                │
│  │            │  │            │  │            │                │
│  │  Bedtime   │  │  Creative  │  │  Games     │                │
│  │            │  │            │  │            │                │
│  │ [Select]   │  │ [Select]   │  │ [Select]   │                │
│  └────────────┘  └────────────┘  └────────────┘                │
│                                                                   │
│  My Custom Icons:                                                │
│  ┌────────────┐  ┌────────────┐                                │
│  │  Custom 1  │  │  Custom 2  │                                │
│  │            │  │            │                                │
│  │ [Edit] [✕] │  │ [Edit] [✕] │                                │
│  └────────────┘  └────────────┘                                │
│                                                                   │
│  [Page 1 of 8 →]                                                │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Icon Upload Modal
```
┌─────────────────────────────────────────────────┐
│ Upload Display Icon                       [✕]   │
├─────────────────────────────────────────────────┤
│                                                 │
│  Icon for Yoto Mini Display (16x16 pixels)     │
│                                                 │
│  ┌────────────────────────────────────────────┐│
│  │                                            ││
│  │     📁 Drag & Drop Icon Here              ││
│  │           or                              ││
│  │     [Browse Files]                        ││
│  │                                            ││
│  │  Format: PNG, 16x16 pixels                ││
│  │  Max size: 10KB                           ││
│  │                                            ││
│  └────────────────────────────────────────────┘│
│                                                 │
│  Preview:                                       │
│  ┌────────┐                                    │
│  │  Icon  │  ← Actual size on Yoto Mini       │
│  └────────┘                                    │
│                                                 │
│  Icon Name: [my_custom_icon________]           │
│                                                 │
│  Tags: [bedtime] [story] [___________]         │
│                                                 │
│  [Cancel]                            [Upload]  │
│                                                 │
└─────────────────────────────────────────────────┘
```

### Features
- Browse public icon repository from Yoto API
- Upload custom user icons (16x16 pixels for Yoto Mini)
- Search and filter icons by category/tags
- Preview icons at actual device size
- Assign icons to chapters/tracks in card scripts
- Icon library management (view, edit, delete custom icons)
- Support for both Yoto Player and Yoto Mini display formats

**Device Compatibility Note**: 
- Yoto Mini has a 16x16 pixel display that shows custom icons
- Original Yoto Player does not have a display screen
- Icons are optional but enhance the Yoto Mini experience

---

## 9. Navigation Structure

### Main Navigation (Sidebar)
```
┌────────────────┐
│ 🏠 Dashboard   │
│ 🎵 Library     │
│ 📝 Scripts     │
│ 🎮 CYOA        │
│ 🎨 Icons       │
│ 📱 Devices     │
│ 📊 Analytics   │
│ ⚙️  Settings   │
│                │
│ ─────────────  │
│ 👤 Profile     │
│ 🚪 Logout      │
└────────────────┘
```

---

## 9. User Flows

### Flow 1: Creating a Simple Audio Card
1. Navigate to Library
2. Click "Upload Audio"
3. Select/drag audio files
4. Add metadata (title, description)
5. Save to library
6. Navigate to Scripts
7. Create new card script
8. Select audio from library
9. Configure playback order
10. Save and test

### Flow 2: Creating a CYOA Story
1. Navigate to CYOA Builder
2. Create new story project
3. Add start node with intro audio
4. Add choice node with decision audio
5. Connect choice to multiple path nodes
6. Add audio for each path
7. Connect paths back together or to different endings
8. Configure button mappings for each choice
9. Test story in simulator
10. Deploy to devices

### Flow 3: Monitoring Device Playback
1. Navigate to Devices
2. View connected devices
3. Select device to monitor
4. View real-time MQTT events
5. See current playback status
6. Use remote controls if needed
7. Check playback history
8. View analytics

---

## 10. Responsive Considerations

### Mobile View Adaptations
- Stack dashboard widgets vertically
- Collapsible sidebar navigation → hamburger menu
- Card-based layout for library items
- Simplified script editor with tabbed interface
- Touch-optimized controls for device monitoring
- Full-screen mode for CYOA visual editor

### Tablet View
- Two-column layout for dashboard
- Side-by-side script editor and preview
- Grid view for library (2-3 columns)
- Maintain full functionality with adapted spacing

---

## 11. Design System Suggestions

### Color Palette
- Primary: Blue (#3B82F6) - Actions, links
- Success: Green (#10B981) - Connected devices, successful operations
- Warning: Yellow (#F59E0B) - Alerts, timeouts
- Error: Red (#EF4444) - Disconnected devices, errors
- Neutral: Gray scale - Backgrounds, text

### Typography
- Headings: Bold, clear hierarchy (H1-H4)
- Body: Readable font (16px base)
- Monospace: MQTT topics, device IDs, technical info

### Components
- Buttons: Clear CTAs with icons
- Cards: Shadow/border for grouping content
- Forms: Clear labels, validation feedback
- Modals: For focused tasks (upload, record, settings)
- Toast notifications: For feedback on actions
- Loading states: Spinners, skeleton screens

---

## 12. Accessibility Features

- Keyboard navigation support
- ARIA labels for screen readers
- High contrast mode option
- Focus indicators
- Alt text for icons and images
- Scalable text sizes
- Error messages in multiple formats (visual + text)

---

## 13. Future Enhancements

- Mobile companion app
- Multi-user collaboration on scripts
- Analytics dashboard with usage statistics
- Template marketplace for CYOA stories
- AI-assisted script generation
- Bulk operations for library management
- Advanced MQTT event triggers
- Schedule-based playback automation
- Integration with external audio sources (Spotify, podcasts)
- Custom display icon creation and management
- Icon animation sequences for Yoto Mini

**Note**: Voice command integration is not possible as Yoto devices do not have microphones.

---

## Technical Notes

This wireframe is designed to be implemented with modern web technologies:
- **Frontend**: React/Vue/Svelte with responsive CSS framework
- **Real-time**: WebSocket for MQTT event streaming
- **Audio**: Web Audio API for recording and playback
- **State Management**: For complex CYOA flow logic
- **File Upload**: Chunked upload for large audio files
- **Testing**: Preview mode should simulate actual device behavior

The interface prioritizes:
1. **Clarity**: Clear labels and intuitive workflows
2. **Real-time feedback**: Live updates via MQTT
3. **Flexibility**: Support for simple and complex audio experiences
4. **Accessibility**: Usable by all skill levels
5. **Performance**: Efficient handling of large audio libraries
