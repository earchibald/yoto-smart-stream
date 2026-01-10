# UI Components Library

This document outlines the reusable UI components that would be needed for the Yoto Smart Stream web interface.

---

## Component Catalog

### 1. DeviceCard
**Purpose**: Display individual device status and basic controls

**Props**:
- deviceName: string
- status: 'connected' | 'disconnected' | 'idle'
- currentTrack: string | null
- progress: number (0-100)
- volume: number (0-100)

**Layout**:
```
┌──────────────────────────────────┐
│ 🟢 Living Room Yoto             │
│                                  │
│ Playing: "Story Track 3"         │
│ [████████░░░░] 8:32 / 15:00     │
│                                  │
│ [⏸️] [⏭️] [🔊 60%]              │
└──────────────────────────────────┘
```

---

### 2. AudioFileCard
**Purpose**: Display audio file in library with metadata and actions

**Props**:
- title: string
- duration: string
- trackCount: number
- thumbnail: string | null
- onPlay: function
- onEdit: function
- onDelete: function

**Layout**:
```
┌─────────────────┐
│   🎵            │
│                 │
│  Story Time     │
│  Volume 1       │
│                 │
│  12 tracks      │
│  45:32          │
│                 │
│ [▶️] [✏️] [🗑️]  │
└─────────────────┘
```

---

### 3. NodeEditor
**Purpose**: Edit individual script nodes in CYOA builder

**Props**:
- nodeId: string
- nodeType: 'audio' | 'choice' | 'action'
- audioFile: string | null
- nextNodes: array
- buttonMappings: object

**Layout**:
```
┌──────────────────────────────────┐
│ Node: start_01                   │
├──────────────────────────────────┤
│ Type: [Audio Playback ▼]         │
│                                  │
│ Audio: [intro.mp3 ▼] [▶️]       │
│                                  │
│ Next Actions:                    │
│ • Button 1 → [choice_1a]         │
│ • Button 2 → [choice_1b]         │
│ • Timeout  → [repeat]            │
│                                  │
│ [+ Add Action]                   │
└──────────────────────────────────┘
```

---

### 4. MQTTEventLog
**Purpose**: Display real-time MQTT events from devices

**Props**:
- deviceId: string
- maxEvents: number
- events: array of {timestamp, type, message}

**Layout**:
```
┌──────────────────────────────────────┐
│ MQTT Events                          │
├──────────────────────────────────────┤
│ 08:15:32 - Button 1 pressed         │
│ 08:15:30 - Playback started         │
│ 08:15:28 - Card inserted            │
│ 08:14:55 - Volume changed to 60%    │
│ 08:14:50 - Connection established   │
├──────────────────────────────────────┤
│ [Clear Log] [Export] [⏸️ Pause]     │
└──────────────────────────────────────┘
```

---

### 5. FileUploader
**Purpose**: Handle drag-and-drop and browse file uploads

**Props**:
- acceptedFormats: array
- maxFileSize: number
- onUpload: function
- multiple: boolean

**Layout**:
```
┌──────────────────────────────────┐
│                                  │
│   📁 Drag & Drop Files Here     │
│         or                       │
│   [Browse Files]                 │
│                                  │
│ Supported: MP3, WAV, OGG, FLAC  │
│ Max size: 500MB per file        │
│                                  │
└──────────────────────────────────┘
```

**With Files**:
```
┌──────────────────────────────────┐
│ Uploaded Files:                  │
│ ✓ story_intro.mp3    (2.3 MB)  │
│ ⏳ bedtime.wav [▓▓░░] 45%      │
│ ❌ toolarge.wav (Error)         │
└──────────────────────────────────┘
```

---

### 6. AudioRecorder
**Purpose**: Record audio directly in the browser

**Props**:
- onRecordingComplete: function
- maxDuration: number
- format: string

**Layout**:
```
┌──────────────────────────────────┐
│ 🎙️ Recording                     │
│                                  │
│     00:02:35                     │
│                                  │
│ Level: [████████░░░░] 🔊        │
│                                  │
│ [⏸️ Pause] [⏹️ Stop]            │
│                                  │
│ Input: [Built-in Mic ▼]         │
│ Quality: [High (320kbps) ▼]     │
└──────────────────────────────────┘
```

---

### 7. FlowCanvas
**Purpose**: Visual node-based editor for CYOA stories

**Props**:
- nodes: array
- connections: array
- onNodeAdd: function
- onNodeDelete: function
- onNodeConnect: function
- selectedNode: string | null

**Features**:
- Drag-and-drop nodes
- Click-and-drag connections
- Zoom and pan
- Auto-layout option
- Minimap for large flows

**Interaction**:
- Click node to select/edit
- Drag from output to input to connect
- Right-click for context menu
- Scroll to zoom
- Double-click to add node

---

### 8. ScriptTreeView
**Purpose**: Hierarchical tree view of script structure

**Props**:
- rootNode: object
- onNodeSelect: function
- expandedNodes: array

**Layout**:
```
┌──────────────────────┐
│ Script Structure     │
├──────────────────────┤
│ 📍 Start             │
│ ├─ 🔊 intro.mp3      │
│ └─ ❓ Choice 1       │
│    ├─ 🔊 path_a.mp3  │
│    │  └─ ⏹️ End A    │
│    └─ 🔊 path_b.mp3  │
│       └─ ⏹️ End B    │
│                      │
│ [+ Add Node]         │
│ [🗑️ Delete]          │
│ [📋 Duplicate]       │
└──────────────────────┘
```

---

### 9. StatusIndicator
**Purpose**: Show connection/status with color coding

**Props**:
- status: 'connected' | 'disconnected' | 'warning' | 'error'
- label: string
- showLabel: boolean

**Variants**:
- 🟢 Connected
- 🔴 Disconnected  
- 🟡 Warning
- ⚪ Unknown

---

### 10. ProgressBar
**Purpose**: Show progress for uploads, playback, etc.

**Props**:
- value: number (0-100)
- variant: 'default' | 'success' | 'warning' | 'error'
- showLabel: boolean
- label: string

**Layout**:
```
[████████░░░░░░] 45%
```

---

### 11. PlaybackControls
**Purpose**: Standard media player controls

**Props**:
- isPlaying: boolean
- currentTime: number
- duration: number
- volume: number
- onPlay: function
- onPause: function
- onNext: function
- onPrevious: function
- onVolumeChange: function

**Layout**:
```
┌──────────────────────────────────────┐
│ [⏮️] [⏸️] [⏭️]                      │
│                                      │
│ [████████░░░░░░] 8:32 / 15:00       │
│                                      │
│ 🔊 [██████░░░░] 60%                 │
└──────────────────────────────────────┘
```

---

### 12. Modal
**Purpose**: Overlay dialog for focused tasks

**Props**:
- isOpen: boolean
- title: string
- onClose: function
- size: 'small' | 'medium' | 'large'

**Layout**:
```
┌─────────────────────────────────┐
│ Modal Title                [✕] │
├─────────────────────────────────┤
│                                 │
│   Content goes here             │
│                                 │
├─────────────────────────────────┤
│        [Cancel]   [Confirm]     │
└─────────────────────────────────┘
```

---

### 13. Sidebar Navigation
**Purpose**: Main app navigation

**Props**:
- currentRoute: string
- user: object

**Layout**:
```
┌────────────────────┐
│ [Logo] Yoto Stream │
├────────────────────┤
│ 🏠 Dashboard       │ ← Active
│ 🎵 Library         │
│ 📝 Scripts         │
│ 🎮 CYOA Builder    │
│ 📱 Devices         │
│ 📊 Analytics       │
│ ⚙️  Settings       │
├────────────────────┤
│ 👤 User Profile    │
│ 🚪 Logout          │
└────────────────────┘
```

**Mobile (Collapsed)**:
```
[☰] Yoto Stream
```

---

### 14. SearchBar
**Purpose**: Search and filter content

**Props**:
- placeholder: string
- value: string
- onSearch: function
- suggestions: array

**Layout**:
```
┌──────────────────────────────────┐
│ 🔍 [Search audio files...____]  │
└──────────────────────────────────┘
```

---

### 15. FilterPanel
**Purpose**: Filter and sort options

**Props**:
- filters: object
- onFilterChange: function

**Layout**:
```
┌──────────────────────────────────┐
│ Filters                          │
├──────────────────────────────────┤
│ Type: [All ▼]                    │
│ Duration: [Any ▼]                │
│ Date Added: [All Time ▼]         │
│                                  │
│ [Reset] [Apply]                  │
└──────────────────────────────────┘
```

---

### 16. NotificationToast
**Purpose**: Temporary feedback messages

**Props**:
- message: string
- type: 'success' | 'error' | 'warning' | 'info'
- duration: number
- onClose: function

**Variants**:
```
✅ File uploaded successfully
❌ Connection failed
⚠️  Low battery on device
ℹ️  New device detected
```

---

### 17. StatCard
**Purpose**: Display key metrics on dashboard

**Props**:
- title: string
- value: string | number
- icon: string
- trend: 'up' | 'down' | 'neutral'
- trendValue: string

**Layout**:
```
┌──────────────────┐
│ 📊 Total Plays   │
│                  │
│      1,234       │
│                  │
│   ↗️ +12% today  │
└──────────────────┘
```

---

### 18. TabPanel
**Purpose**: Organize content in tabs

**Props**:
- tabs: array
- activeTab: string
- onTabChange: function

**Layout**:
```
┌────────────────────────────────────┐
│ [Info] [Audio] [Settings] [Test]  │ ← Active: Info
├────────────────────────────────────┤
│                                    │
│   Tab content here                 │
│                                    │
└────────────────────────────────────┘
```

---

### 19. ContextMenu
**Purpose**: Right-click or long-press actions

**Props**:
- items: array
- position: {x, y}
- onSelect: function

**Layout**:
```
┌──────────────────┐
│ ▶️  Play          │
│ ✏️  Edit          │
│ 📋 Duplicate     │
│ ──────────────   │
│ 🗑️  Delete       │
└──────────────────┘
```

---

### 20. EmptyState
**Purpose**: Show when no content is available

**Props**:
- icon: string
- title: string
- message: string
- actionLabel: string
- onAction: function

**Layout**:
```
┌──────────────────────────────────┐
│                                  │
│         📁                       │
│                                  │
│    No audio files yet            │
│                                  │
│  Upload your first audio file    │
│  to get started                  │
│                                  │
│    [Upload Audio]                │
│                                  │
└──────────────────────────────────┘
```

---

## Component Interaction Examples

### Example 1: Device Monitoring Flow
```
DeviceCard (shows current status)
    ↓ (user clicks device)
MQTTEventLog (shows live events)
    ↓ (events stream in)
NotificationToast (shows alerts)
```

### Example 2: Audio Upload Flow
```
FileUploader (drag and drop)
    ↓ (files selected)
ProgressBar (upload progress)
    ↓ (upload complete)
NotificationToast (success message)
    ↓ (navigate to)
AudioFileCard (new file in library)
```

### Example 3: CYOA Creation Flow
```
FlowCanvas (visual editor)
    ↓ (user adds node)
NodeEditor (configure node)
    ↓ (select audio)
Modal (audio picker)
    ↓ (connect nodes)
ScriptTreeView (updates structure)
```

---

## State Management Considerations

### Global State
- User authentication
- Device connection status
- MQTT connection
- Audio library index
- Current playback state

### Local State
- Form inputs
- UI toggles (modals, sidebars)
- Temporary selections
- Filter/search criteria

### Real-time State (via WebSocket/MQTT)
- Device status updates
- Playback progress
- Event streams
- Connection health

---

## Responsive Breakpoints

```
Mobile:   < 640px  (1 column, stacked)
Tablet:   640-1024px (2 columns, simplified)
Desktop:  > 1024px (full layout)
```

---

## Animation Guidelines

- **Transitions**: 200-300ms for UI state changes
- **Loading**: Skeleton screens for content loading
- **Feedback**: Micro-interactions on button clicks
- **Modals**: Fade in/slide up (300ms)
- **Toasts**: Slide in from top/bottom
- **Node connections**: Animated path drawing

---

## Accessibility Requirements

- All interactive elements keyboard accessible
- Focus visible and logical order
- ARIA labels on icon buttons
- Color not sole indicator of state
- Alt text on meaningful images
- Screen reader announcements for state changes
- Form validation accessible
- Skip navigation links

---

## Performance Considerations

- Lazy load audio waveforms
- Virtualize long lists (library, events)
- Debounce search inputs
- Throttle MQTT event rendering
- Code-split routes
- Optimize audio file previews
- Cache device status
- Efficient canvas rendering for flow editor
