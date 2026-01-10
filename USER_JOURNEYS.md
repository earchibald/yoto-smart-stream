# User Journeys and Interaction Patterns

This document details the user journeys and interaction patterns for the Yoto Smart Stream web interface.

---

## User Personas

### Persona 1: Sarah - The Parent
**Background**: Mother of two young children, tech-comfortable but not technical
**Goals**: Create custom audio stories for bedtime, manage device in kids' room
**Needs**: Simple interface, quick uploads, reliable playback

### Persona 2: Mike - The Content Creator
**Background**: Audiobook narrator, wants to create interactive stories
**Goals**: Build complex Choose Your Own Adventure stories with branching paths
**Needs**: Advanced editing tools, visual flow design, audio management

### Persona 3: Tom - The System Administrator  
**Background**: Manages Yoto devices for a school or library
**Goals**: Monitor multiple devices, troubleshoot issues, manage content library
**Needs**: Device monitoring, MQTT logs, bulk operations, analytics

---

## Journey 1: First Time User Setup

### Scenario
Sarah just installed the Yoto Smart Stream service and wants to play her first audio story.

### Steps

1. **Landing / Dashboard** (First Visit)
   ```
   User sees:
   - Welcome message
   - Quick start guide
   - "No devices connected" state
   - "Empty library" state
   - [Get Started] button
   ```
   **Action**: Click "Get Started"

2. **Setup Wizard - Step 1: Connect Device**
   ```
   Instructions shown:
   - "Power on your Yoto device"
   - "Ensure device is on same network"
   - "Device should appear automatically"
   
   Device discovery:
   - Scanning animation
   - Device appears: "Yoto-ABC123 found"
   - [Connect This Device] button
   ```
   **Action**: Click "Connect This Device"

3. **Setup Wizard - Step 2: Name Device**
   ```
   Form:
   - Device Name: [______________]
   - Location: [Optional: e.g., "Kids Bedroom"]
   - [Back] [Continue]
   ```
   **Action**: Enter "Kids Room", click Continue

4. **Setup Wizard - Step 3: Upload First Audio**
   ```
   Upload interface:
   - "Let's add your first audio file"
   - Drag & drop area
   - [Browse Files] button
   - [Skip for Now] link
   ```
   **Action**: Upload "bedtime_story.mp3"

5. **Setup Wizard - Step 4: Create Card Script**
   ```
   Simple form:
   - Script Name: [Bedtime Story]
   - Audio: [bedtime_story.mp3 ✓]
   - Playback: [○ Once  ● Loop  ○ Playlist]
   - [Create Script]
   ```
   **Action**: Select "Once", click Create

6. **Complete Setup**
   ```
   Success screen:
   - ✅ "You're all set!"
   - "Your script is ready to play"
   - Instructions: "Insert a card to start playback"
   - [Go to Dashboard]
   ```
   **Action**: Click "Go to Dashboard"

7. **Dashboard (Now Populated)**
   ```
   Shows:
   - ✓ 1 device connected (Kids Room)
   - ✓ 1 audio file in library
   - ✓ 1 card script created
   - Recent activity log
   ```

**Success Criteria**: User successfully connected device, uploaded audio, and created playable script

**Time Estimate**: 5-10 minutes

---

## Journey 2: Creating a Simple Playlist

### Scenario
Sarah wants to create a bedtime playlist with multiple stories that play in sequence.

### Steps

1. **Navigate to Library**
   ```
   Dashboard → Library
   Current state: 1 audio file
   ```

2. **Upload Multiple Files**
   ```
   Click [+ Upload Audio]
   
   Modal appears:
   - Drag & drop area
   - Select multiple files:
     - story1.mp3 (5.2 MB)
     - story2.mp3 (4.8 MB)
     - story3.mp3 (6.1 MB)
   - Upload progress shows for each
   - ✓ All complete
   ```

3. **Create Playlist Script**
   ```
   Click [New Card Script]
   
   Script editor:
   - Name: [Bedtime Playlist]
   - Type: [Playlist ▼]
   - Add tracks:
     [+ Add Track]
     Select "story1.mp3"
     [+ Add Track]
     Select "story2.mp3"
     [+ Add Track]  
     Select "story3.mp3"
   
   Playlist options:
   - ☑️ Play in order
   - ☐ Shuffle
   - ☐ Loop playlist
   
   [Save Script]
   ```

4. **Test Playback**
   ```
   Script saved screen:
   - Preview player appears
   - [▶️ Test Playback] button
   - Click to test
   - Plays through tracks
   - Shows "Track 1 of 3" progress
   ```

**Success Criteria**: Playlist created with multiple tracks in specified order

**Time Estimate**: 8-12 minutes

---

## Journey 3: Building a CYOA Story

### Scenario
Mike wants to create an interactive "Choose Your Own Adventure" story with multiple decision points.

### Steps

1. **Navigate to CYOA Builder**
   ```
   Dashboard → CYOA Builder
   [+ New Story] button
   ```

2. **Create Story Project**
   ```
   New Story modal:
   - Story Name: [Dragon Quest]
   - Description: [An adventure in the dragon's lair]
   - [Create]
   ```

3. **Add Start Node**
   ```
   Canvas appears with initial "START" node
   
   Click START node to edit:
   - Node Type: [Audio Playback ▼]
   - Audio: [Upload or Select]
   - Upload "intro.mp3"
   - Text Description: "You stand at the entrance..."
   - Auto-advance to: [Next node]
   ```

4. **Add First Choice**
   ```
   Click [+ Add Node] → Select "Choice"
   
   New choice node appears
   Connect START → CHOICE_1
   
   Edit CHOICE_1:
   - Audio: Upload "choice1.mp3"
   - Text: "Do you enter the cave or go around?"
   - Button 1 label: "Enter cave"
   - Button 2 label: "Go around"
   - Timeout: [30] seconds, then [Repeat ▼]
   ```

5. **Add Path Branches**
   ```
   Add two new audio nodes:
   - PATH_CAVE (upload "cave.mp3")
   - PATH_AROUND (upload "around.mp3")
   
   Connect:
   - CHOICE_1 (Button 1) → PATH_CAVE
   - CHOICE_1 (Button 2) → PATH_AROUND
   
   Visual flow updates automatically
   ```

6. **Add More Choices**
   ```
   From PATH_CAVE, add CHOICE_2:
   - "You hear a noise. Fight or hide?"
   - Button 1 → FIGHT_DRAGON
   - Button 2 → HIDE_ROCKS
   
   From PATH_AROUND, add direct path to END_SAFE
   ```

7. **Add Endings**
   ```
   Add ending nodes:
   - END_VICTORY (from FIGHT_DRAGON)
   - END_ESCAPE (from HIDE_ROCKS)
   - END_SAFE (from PATH_AROUND)
   
   Mark as ending nodes (no next actions)
   ```

8. **Visual Flow Check**
   ```
   Switch to [Flow] tab
   
   Visual shows:
   START → CHOICE_1 → {PATH_CAVE, PATH_AROUND}
   PATH_CAVE → CHOICE_2 → {FIGHT_DRAGON, HIDE_ROCKS}
   PATH_AROUND → END_SAFE
   FIGHT_DRAGON → END_VICTORY
   HIDE_ROCKS → END_ESCAPE
   
   Validation: ✓ No dead ends
   ```

9. **Test Story**
   ```
   Click [Preview] button
   
   Simulator opens:
   - Shows virtual Yoto device
   - Plays through story
   - Click buttons to make choices
   - Tests all paths
   - Confirms audio plays correctly
   ```

10. **Deploy to Device**
    ```
    Click [Deploy]
    
    Select target device(s):
    ☑️ Kids Room
    ☐ Living Room
    
    [Deploy Story]
    
    Success: "Dragon Quest deployed to Kids Room"
    ```

**Success Criteria**: Multi-path interactive story created, tested, and deployed

**Time Estimate**: 30-45 minutes (depending on audio preparation)

---

## Journey 4: Monitoring Device Activity

### Scenario
Tom needs to monitor multiple school devices and troubleshoot a reported issue.

### Steps

1. **Navigate to Devices**
   ```
   Dashboard → Devices
   
   Device list shows:
   - 🟢 Classroom A (Active)
   - 🟢 Classroom B (Active)
   - 🟡 Classroom C (Warning: Low battery)
   - 🔴 Library (Disconnected)
   ```

2. **Investigate Disconnected Device**
   ```
   Click "Library" device
   
   Device detail page:
   - Status: 🔴 Disconnected
   - Last seen: 2 hours ago
   - Last activity: Playing "Math Facts Vol 2"
   
   MQTT Event log shows:
   - 10:32 - Connection lost
   - 10:31 - Battery critical (5%)
   - 10:30 - Volume changed to 80%
   - 10:25 - Playback started
   ```

3. **Check Battery History**
   ```
   Click [View Analytics] tab
   
   Battery chart shows:
   - Steady decline from 100% to 5%
   - No charging events in past 24 hours
   - Alert threshold crossed at 10%
   ```

4. **Send Notification**
   ```
   Click [Send Alert]
   
   Notification modal:
   - Type: [Email ▼]
   - To: [librarian@school.edu]
   - Message: "Library Yoto device needs charging"
   - [Send]
   
   ✓ Alert sent
   ```

5. **Monitor Active Devices**
   ```
   Return to device list
   
   Click "Classroom A" (Active)
   
   Live monitoring:
   - Currently playing: "Reading Adventure Ch 4"
   - Progress: [████░░░░] 12:30 / 25:00
   - Volume: 70%
   
   MQTT events (live):
   - 11:05:32 - Still playing
   - 11:05:15 - Volume changed to 70%
   - 11:05:00 - Button 2 pressed (skip)
   - 11:04:55 - Button 1 pressed (pause)
   ```

6. **View Analytics Dashboard**
   ```
   Click [Analytics] in sidebar
   
   Dashboard shows:
   - Total devices: 12
   - Active now: 8
   - Total plays today: 156
   - Most played content: "Math Facts Vol 2"
   - Peak usage time: 10:00 AM - 11:30 AM
   
   Charts:
   - Usage by device (bar chart)
   - Plays over time (line chart)
   - Content popularity (pie chart)
   ```

**Success Criteria**: Issue identified, stakeholder notified, devices monitored

**Time Estimate**: 10-15 minutes

---

## Journey 5: Recording Audio Directly

### Scenario
Sarah wants to record a custom message/story without using external recording software.

### Steps

1. **Open Recording Interface**
   ```
   Library → [🎙️ Record Audio] button
   
   Recording modal opens
   ```

2. **Configure Settings**
   ```
   Recording setup:
   - Input Device: [Built-in Microphone ▼]
     (also shows: External USB Mic, Webcam Mic)
   - Quality: [High (320kbps) ▼]
   - Format: [MP3 ▼]
   - File name: [goodnight_message]
   
   Microphone test:
   - Level indicator shows input level
   - [Test Mic] button to hear playback
   ```

3. **Record Audio**
   ```
   Click [● Record]
   
   Recording UI:
   - 🎙️ Recording... (red indicator)
   - Timer: 00:00:05... 00:00:10...
   - Level meter animating
   - Waveform visualizer (optional)
   - [⏸️ Pause] [⏹️ Stop] buttons available
   ```

4. **Review Recording**
   ```
   After stopping:
   - Preview player appears
   - [▶️ Play] to review
   - Waveform shown
   - Duration: 00:01:23
   
   Options:
   - [🎙️ Re-record] if not satisfied
   - [✂️ Trim] to edit endpoints
   - [💾 Save] to keep
   ```

5. **Save to Library**
   ```
   Click [💾 Save]
   
   Processing:
   - "Encoding audio..."
   - Progress bar
   - ✓ "Audio saved to library"
   
   Confirmation modal:
   - "goodnight_message.mp3 added to library"
   - [Go to Library] [Record Another] [Close]
   ```

**Success Criteria**: Audio recorded, reviewed, and saved to library

**Time Estimate**: 5-8 minutes

---

## Interaction Patterns

### Pattern 1: Drag and Drop File Upload

**Trigger**: User drags files over upload area

**Sequence**:
1. Hover state: Border highlights, background changes
2. Drop: Files accepted, border flashes green
3. Upload starts: Individual progress bars for each file
4. Validation: File type/size checked, errors shown if invalid
5. Processing: Metadata extracted (duration, bitrate)
6. Complete: Success checkmark, files appear in library

**Error Handling**:
- Invalid format: "File type not supported. Please use MP3, WAV, OGG, or FLAC"
- Too large: "File exceeds 500MB limit"
- Upload failed: "Upload failed. [Retry] [Cancel]"

---

### Pattern 2: Real-time MQTT Updates

**Trigger**: MQTT event received from device

**Sequence**:
1. WebSocket receives MQTT message
2. Event parsed and validated
3. UI updates:
   - Device status badge changes color
   - Event added to log (with animation)
   - Playback progress updates
   - Notification toast if important
4. Event persisted to history

**Debouncing**:
- Volume changes: Update max once per second
- Progress updates: Update every 2 seconds
- Event log: Batch multiple events if > 5 per second

---

### Pattern 3: Node Connection in CYOA Editor

**Trigger**: User wants to connect two nodes in flow editor

**Sequence**:
1. User clicks output port on source node
2. Cursor changes to crosshair
3. User drags to target node's input port
4. Path draws dynamically during drag
5. Hover over valid target: Target highlights green
6. Release mouse: Connection established
7. Line animates into place
8. Connection settings modal appears:
   - "When [Button 1] pressed, go to [Target Node]"
   - [Confirm]

**Validation**:
- Prevent circular connections
- Highlight invalid targets in red
- Show error toast if connection invalid

---

### Pattern 4: Live Device Control

**Trigger**: User interacts with device controls

**Sequence**:
1. User clicks [Pause] button
2. Button shows loading state (spinner)
3. MQTT command sent to device
4. Wait for acknowledgment (timeout: 5 seconds)
5. On success:
   - Button updates to [Play]
   - Status updates to "Paused"
   - Toast: "Playback paused"
6. On failure:
   - Button returns to original state
   - Toast: "Command failed. Device may be offline."

**Optimistic Updates**:
- UI updates immediately for responsiveness
- Revert if command fails

---

### Pattern 5: Inline Editing

**Trigger**: User wants to edit item name/metadata

**Sequence**:
1. User double-clicks or clicks [✏️] icon
2. Text becomes editable input field
3. Original text pre-selected
4. User types new value
5. Press Enter or click outside to save
6. Press Escape to cancel
7. Validation runs (e.g., name not empty)
8. If valid: Update saved, success indicator
9. If invalid: Show error, keep editing

**Auto-save**:
- Debounce 1 second after typing stops
- Show "Saving..." indicator
- Show "Saved" checkmark on success

---

### Pattern 6: Search with Live Results

**Trigger**: User types in search box

**Sequence**:
1. User types character
2. Debounce 300ms
3. Search executes (local or API)
4. Loading indicator shows
5. Results filter/display
6. Highlight matching text
7. Show result count: "12 results for 'bedtime'"
8. If no results: Show empty state with suggestions

**Features**:
- Clear button (X) to reset
- Recent searches dropdown
- Search suggestions as you type

---

### Pattern 7: Bulk Operations

**Trigger**: User wants to perform action on multiple items

**Sequence**:
1. User clicks checkbox on first item
2. Batch toolbar appears at top
3. "1 item selected" counter
4. User selects more items
5. Counter updates: "5 items selected"
6. Bulk actions available: [Delete] [Move] [Download]
7. User clicks [Delete]
8. Confirmation modal: "Delete 5 items?"
9. Confirm: Items deleted with animation
10. Toast: "5 items deleted" with [Undo] option

**Select All**:
- Checkbox in table header
- "Select all 50 items" link if paginated
- "Clear selection" when all selected

---

## Error States and Recovery

### Connection Lost
```
┌──────────────────────────────────┐
│ ⚠️  Connection Lost              │
│                                  │
│ Lost connection to server.       │
│ Attempting to reconnect...       │
│                                  │
│ [Retry Now]                      │
└──────────────────────────────────┘
```

**Auto-recovery**: Retry every 5 seconds, exponential backoff

### Device Not Responding
```
┌──────────────────────────────────┐
│ 🔴 Device Not Responding         │
│                                  │
│ "Kids Room" is not responding    │
│ to commands.                     │
│                                  │
│ • Check device power             │
│ • Check network connection       │
│ • Restart device                 │
│                                  │
│ [View Troubleshooting Guide]     │
└──────────────────────────────────┘
```

### File Upload Failed
```
┌──────────────────────────────────┐
│ ❌ Upload Failed                 │
│                                  │
│ "story.mp3" failed to upload     │
│                                  │
│ Reason: Network timeout          │
│                                  │
│ [Retry] [Cancel]                 │
└──────────────────────────────────┘
```

**Recovery Options**:
- Automatic retry (3 attempts)
- Resume partial uploads
- Queue failed uploads for later

---

## Progressive Disclosure

### Simple → Advanced

**Script Editor**:
```
Basic mode (default):
- Audio file selection
- Play order
- Loop option

↓ [Show Advanced Options]

Advanced mode:
- MQTT event triggers
- Conditional logic
- Variable playback speed
- Volume curves
- Fade in/out
```

**Device Settings**:
```
Basic:
- Name
- Location
- Volume

↓ [Advanced Settings]

Advanced:
- MQTT topics
- Network settings
- Firmware updates
- Debug logs
```

---

## Keyboard Shortcuts

### Global
- `Ctrl/Cmd + K`: Quick search
- `Ctrl/Cmd + S`: Save current work
- `Ctrl/Cmd + Z`: Undo
- `Ctrl/Cmd + Shift + Z`: Redo
- `Escape`: Close modal/cancel action

### CYOA Editor
- `Space`: Play/pause preview
- `Delete`: Delete selected node
- `Ctrl/Cmd + D`: Duplicate node
- `Ctrl/Cmd + G`: Group selection
- `Arrow keys`: Navigate nodes
- `Ctrl/Cmd + Scroll`: Zoom canvas

### Library
- `Ctrl/Cmd + A`: Select all
- `Ctrl/Cmd + Click`: Multi-select
- `Space`: Preview selected audio

---

## Mobile Interactions

### Touch Gestures
- **Swipe left** on item: Reveal actions (delete, edit)
- **Long press**: Select for bulk operations
- **Pinch to zoom**: Flow editor canvas
- **Pull to refresh**: Update device status
- **Swipe down** on modal: Dismiss

### Simplified Navigation
- Bottom tab bar (5 main sections)
- Hamburger menu for secondary options
- Floating action button for primary action
- Swipeable tabs within sections

---

## Onboarding Tooltips

**First Visit**:
```
1. Dashboard
   "👋 Welcome! This is your dashboard where you 
    can see all connected devices and recent activity."
   [Next]

2. Upload Button
   "📁 Click here to upload your first audio file."
   [Got it]

3. Device Section
   "📱 Your Yoto devices will appear here once connected."
   [Finish]
```

**Feature Discovery** (contextual):
- First time in CYOA editor: Tutorial overlay
- First upload: Tips on audio formats
- First device connected: Usage guide

---

## Accessibility Considerations

### Screen Reader Announcements
- "Device 'Kids Room' connected"
- "Playing 'Bedtime Story', track 3 of 12"
- "Upload complete. 5 files added to library"
- "Connection lost. Attempting to reconnect."

### Keyboard Navigation Flow
1. Skip to main content link
2. Main navigation (sidebar)
3. Primary content area
4. Actions/buttons
5. Footer

### ARIA Live Regions
- Device status changes
- MQTT event stream
- Upload progress
- Playback status

---

## Performance Optimization

### Lazy Loading
- Library: Virtual scrolling for 1000+ items
- MQTT logs: Only render visible events
- Audio waveforms: Generate on demand
- Flow editor: Render visible canvas area

### Caching Strategy
- Device status: 30 second cache
- Library metadata: Local storage
- Audio previews: IndexedDB
- User preferences: Session storage

### Debouncing/Throttling
- Search input: 300ms debounce
- Scroll events: 150ms throttle
- MQTT updates: 100ms throttle
- Auto-save: 1000ms debounce

---

## Success Metrics

**User Engagement**:
- Time to first audio upload
- Number of scripts created per user
- CYOA completion rate
- Device monitoring frequency

**System Performance**:
- Page load time < 2 seconds
- MQTT event latency < 500ms
- Upload success rate > 95%
- Device command response time < 1 second

**User Satisfaction**:
- Task completion rate
- Error recovery success
- Feature adoption rate
- User feedback scores
