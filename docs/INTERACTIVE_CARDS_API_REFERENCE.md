# Yoto API: Interactive Card Capabilities

Complete reference for programmatically creating interactive (branching/choice-based) cards via the Yoto API.

## API Endpoint

**Create or Update Content:** `POST https://api.yotoplay.com/content`

- Omit `cardId` to create a new card (auto-generated 5-char alphanumeric ID)
- Include `cardId` to update an existing card
- Auth: `Authorization: Bearer {access_token}`
- Content-Type: `application/json`

The legacy `POST /card` endpoint exists but `/content` is the modern endpoint that supports interactive cards and streaming.

---

## Complete Card Payload Schema

```json
{
  "cardId": "optional - auto-generated if omitted",
  "title": "string (1-100 chars, required)",
  "metadata": {
    "description": "string",
    "author": "string",
    "category": "none|stories|music|radio|podcast|sfx|activities|alarms",
    "cover": { "imageL": "URL" },
    "media": { "duration": 0, "fileSize": 0 },
    "minAge": 0,
    "maxAge": 0,
    "languages": ["en-GB"],
    "genres": ["max 3"],
    "note": "string"
  },
  "content": {
    "version": "1",
    "activity": "yoto_Player",
    "playbackType": "interactive",
    "availability": "",
    "config": { ... },
    "editSettings": { ... },
    "chapters": [ ... ]
  }
}
```

### `content.config` — Interactive Card Settings

```json
{
  "autoadvance": "none",
  "disableTrackNav": true,
  "disableChapterNav": true,
  "resumeTimeout": 2592000,
  "onlineOnly": true,
  "shuffle": [{ "start": 0, "end": 5, "limit": 3 }]
}
```

| Field | Type | Required for Interactive | Purpose |
|-------|------|------------------------|---------|
| `autoadvance` | `"next"\|"repeat"\|"none"` | Yes — set `"none"` | Prevents auto-advancing to next chapter |
| `disableTrackNav` | bool | Yes — set `true` | Prevents physical dial from skipping tracks |
| `disableChapterNav` | bool | Yes — set `true` | Prevents physical dial from skipping chapters |
| `resumeTimeout` | int (seconds) | No | How long resume position is remembered (default 2592000 = 30 days) |
| `onlineOnly` | bool | Required if streaming | Player must be online to play |
| `shuffle` | array | No | Shuffle ranges for randomized playback |

### `content.editSettings`

```json
{
  "autoOverlayLabels": "chapters",
  "editKeys": false,
  "interactiveContent": true,
  "transcodeAudioUploads": true
}
```

`interactiveContent: true` marks the card as interactive in the Yoto app editor.

---

## Chapter Schema

```json
{
  "key": "string (required, unique within card)",
  "title": "string (required)",
  "tracks": [ ... ],
  "display": {
    "icon16x16": "yoto:#<sha256>"
  },
  "defaultTrackDisplay": "string",
  "defaultTrackAmbient": "string",
  "overlayLabel": "string",
  "availableFrom": "ISO date or null",
  "duration": 0,
  "fileSize": 0
}
```

### Chapter Display Icons

16x16 pixel PNG icons (32-bit RGBA). Two ways to reference:

1. **Uploaded icon:** `"icon16x16": "yoto:#<mediaId>"` — upload via `POST /media/displayIcons/user/me/upload`
2. **URL icon:** `"iconUrl16x16": "https://..."` — direct URL to a 16x16 PNG

---

## Track Schema

```json
{
  "key": "string (required, unique within chapter)",
  "uid": "string",
  "title": "string (required)",
  "trackUrl": "https://your-server.com/audio.mp3",
  "type": "stream",
  "format": "mp3",
  "channels": "mono|stereo",
  "duration": 0,
  "fileSize": 0,
  "display": { "icon16x16": "yoto:#<sha256>" },
  "overlayLabel": "string",
  "isNew": false,
  "events": { ... }
}
```

### Track Types

| `type` | `trackUrl` format | When to use |
|--------|-------------------|-------------|
| `"stream"` | `https://...` external URL | Streaming from your own server |
| `"audio"` | `"yoto:#<transcodedSha256>"` | Uploaded to Yoto's servers |

### Audio Formats

Supported values for `format`: `mp3`, `aac`, `alac`, `flac`, `pcm_s16le`, `opus`, `ogg`, `x-m4a`, `wav`, `aiff`, `mpeg`

**Recommended:** MP3, mono, 128-192 kbps. MP3 is the most universally reliable format for streaming.

---

## Events — The Interactive Navigation System

Events are the core mechanism for interactive cards. They are defined per-track and fire on specific triggers.

```json
{
  "events": {
    "onEnd": { "cmd": "stop" },
    "onLhb": { "cmd": "goto", "params": { "chapterKey": "02", "trackKey": "01" } },
    "onRhb": { "cmd": "goto", "params": { "chapterKey": "03", "trackKey": "01" } }
  }
}
```

### Event Triggers

| Trigger | Physical Action | Description |
|---------|----------------|-------------|
| `onEnd` | Track finishes playing | Fires when audio playback reaches the end |
| `onLhb` | Left hardware button pressed | Orange button on Yoto Player |
| `onRhb` | Right hardware button pressed | Green button / twist on Yoto Player |

### Event Commands

| Command | Params | Effect |
|---------|--------|--------|
| `"stop"` | none | Stops playback entirely |
| `"repeat"` | none | Replays the current track |
| `"goto"` | `{ "chapterKey": "...", "trackKey": "..." }` | Jumps to the specified chapter and track |

### Interactive Design Pattern

The standard pattern for a choice point:

1. **Audio narrates the choice:** "Press the left button for the cave, or the right button for the forest"
2. **`onEnd: stop`** — Player waits silently for a button press
3. **`onLhb: goto cave_chapter`** — Left button → cave path
4. **`onRhb: goto forest_chapter`** — Right button → forest path

Each chapter typically has exactly **one track** in interactive cards. The chapter serves as a "node" in the story graph, and events on its single track define the edges.

---

## Streaming URL Requirements

### What Works

- **HTTPS URLs** — fully supported, recommended
- **HTTP URLs** — works (community reports success with radio streams)
- **Railway / cloud-hosted URLs** — confirmed working in this project
- **S3 signed URLs** — used by Yoto internally for uploaded content

### What to Consider

- **`.local` domains (mDNS):** Not officially supported. The Yoto Player resolves URLs over its WiFi connection, so `.local` would only work if the player supports mDNS and is on the same LAN. This is undocumented and likely unreliable. Use a proper hostname or IP instead.
- **Content-Type headers:** Your server should return the correct MIME type (`audio/mpeg` for MP3, `audio/aac` for AAC, etc.)
- **`onlineOnly: true`** must be set in config when using streaming URLs, since the player needs network access to fetch audio

### Audio Upload Flow (Alternative to Streaming)

If you prefer Yoto-hosted audio instead of streaming:

1. Compute SHA256 of your audio file
2. `GET /media/transcode/audio/uploadUrl?sha256={hash}&filename={name}` → returns `uploadUrl`, `uploadId`
3. `PUT {uploadUrl}` with raw audio bytes
4. Poll `GET /media/upload/{uploadId}/transcoded?loudnorm=false` every 500ms until `transcodedSha256` appears
5. Reference as `trackUrl: "yoto:#${transcodedSha256}"` with `type: "audio"`

---

## Complete Interactive Card Example

Minimal branching story with 4 nodes:

```json
{
  "title": "Choose Your Adventure",
  "metadata": {
    "description": "A branching story with choices",
    "author": "My App"
  },
  "content": {
    "version": "1",
    "activity": "yoto_Player",
    "playbackType": "interactive",
    "config": {
      "resumeTimeout": 2592000,
      "disableTrackNav": true,
      "disableChapterNav": true,
      "autoadvance": "none",
      "onlineOnly": true
    },
    "editSettings": {
      "autoOverlayLabels": "chapters",
      "editKeys": false,
      "interactiveContent": true
    },
    "chapters": [
      {
        "key": "intro",
        "title": "Introduction",
        "tracks": [{
          "key": "intro",
          "title": "Introduction",
          "type": "stream",
          "format": "mp3",
          "trackUrl": "https://your-server.com/audio/intro.mp3",
          "events": {
            "onEnd": { "cmd": "stop" },
            "onLhb": { "cmd": "goto", "params": { "chapterKey": "cave", "trackKey": "cave" } },
            "onRhb": { "cmd": "goto", "params": { "chapterKey": "forest", "trackKey": "forest" } }
          }
        }]
      },
      {
        "key": "cave",
        "title": "The Cave",
        "tracks": [{
          "key": "cave",
          "title": "The Cave",
          "type": "stream",
          "format": "mp3",
          "trackUrl": "https://your-server.com/audio/cave.mp3",
          "events": {
            "onEnd": { "cmd": "goto", "params": { "chapterKey": "ending", "trackKey": "ending" } }
          }
        }]
      },
      {
        "key": "forest",
        "title": "The Forest",
        "tracks": [{
          "key": "forest",
          "title": "The Forest",
          "type": "stream",
          "format": "mp3",
          "trackUrl": "https://your-server.com/audio/forest.mp3",
          "events": {
            "onEnd": { "cmd": "goto", "params": { "chapterKey": "ending", "trackKey": "ending" } }
          }
        }]
      },
      {
        "key": "ending",
        "title": "The End",
        "tracks": [{
          "key": "ending",
          "title": "The End",
          "type": "stream",
          "format": "mp3",
          "trackUrl": "https://your-server.com/audio/ending.mp3",
          "events": {
            "onEnd": { "cmd": "stop" },
            "onLhb": { "cmd": "goto", "params": { "chapterKey": "intro", "trackKey": "intro" } }
          }
        }]
      }
    ]
  }
}
```

---

## Advanced Patterns

### Multi-Track Chapters (Linear Segments Between Choices)

A chapter can have multiple tracks for sequential audio before a choice:

```json
{
  "key": "scene1",
  "title": "Scene 1",
  "tracks": [
    { "key": "narration", "title": "Narration", "trackUrl": "...", "type": "stream", "format": "mp3" },
    { "key": "choice", "title": "Make your choice", "trackUrl": "...", "type": "stream", "format": "mp3",
      "events": {
        "onEnd": { "cmd": "stop" },
        "onLhb": { "cmd": "goto", "params": { "chapterKey": "path_a", "trackKey": "path_a" } },
        "onRhb": { "cmd": "goto", "params": { "chapterKey": "path_b", "trackKey": "path_b" } }
      }
    }
  ]
}
```

Only the last track needs events — earlier tracks auto-play sequentially within the chapter (since `autoadvance` applies at chapter level, track-to-track within a chapter still advances normally).

### Path Convergence

Multiple branches can `goto` the same chapter to reconverge the story:

```
intro → [cave | forest] → shared_ending
```

Both `cave` and `forest` use `onEnd: goto shared_ending`.

### Loops and Replay

Use `"cmd": "repeat"` or `goto` back to the current chapter for retry/replay loops (e.g., quiz wrong answer → replay question).

### Class/Role Selection (D&D Pattern)

The official D&D card uses a pattern where early choice sets a "class" and all subsequent chapters have variants:
- Chapter keys: `13F` (Fighter path), `13W` (Wizard path)
- The initial class choice `goto`s the appropriate variant for all downstream content
- Paths can reconverge at chapters without class suffixes

This supports 197+ tracks in a single card with deep branching.

---

## Other Useful Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/content/{cardId}?signingType=s3&playable=true` | Get full card with signed streaming URLs |
| `GET` | `/content/mine` | List user's MYO content (no chapters — must fetch each card individually) |
| `DELETE` | `/content/{cardId}` | Delete a card |
| `POST` | `/media/displayIcons/user/me/upload?autoConvert=true&filename=icon.png` | Upload 16x16 chapter icon |

---

## Authentication Quick Reference

**Device Code Flow (headless/server):**

1. `POST https://login.yotoplay.com/oauth/device/code` — body: `client_id`, `scope=profile offline_access openid`, `audience=https://api.yotoplay.com`
2. User visits URL, enters code
3. Poll `POST https://login.yotoplay.com/oauth/token` — body: `grant_type=urn:ietf:params:oauth:grant-type:device_code`, `device_code`, `client_id`
4. Returns `access_token`, `refresh_token`

**Token Refresh:** `POST https://login.yotoplay.com/oauth/token` — body: `grant_type=refresh_token`, `refresh_token`, `client_id`

---

## Key Constraints and Gotchas

1. **`playbackType` must be `"interactive"`** for events to work. Without it, button presses are ignored.
2. **`disableTrackNav` and `disableChapterNav` should be `true`** — otherwise the physical dial overrides your event-based navigation.
3. **`autoadvance` should be `"none"`** — prevents the player from auto-advancing past choice points.
4. **Chapter and track keys must match in `goto` params** — a typo silently fails (no error, just no navigation).
5. **`/content/mine` does NOT return chapters** — you must call `/content/{cardId}` individually to get the full structure.
6. **Streaming requires `onlineOnly: true`** — without it, the player may attempt to cache/download and fail.
7. **16x16 icons only** — the Yoto Player's display is tiny. Icons must be exactly 16x16 px, 32-bit RGBA PNG.
8. **Keys can contain spaces** — the existing scripts use keys like `"01 Chapter 1"` and it works, but simple keys like `"01"` are cleaner.

---

## Sources

- [Yoto Developer Portal](https://yoto.dev/)
- [Card Content Schema](https://yoto.dev/reference/card-content-schema/)
- [Create or Update Content API](https://yoto.dev/api/createorupdatecontent/)
- [Streaming Tracks](https://yoto.dev/myo/streaming-tracks/)
- [Interactive Story Tutorial (Yoto Space)](https://yoto.space/tutorials/post/how-to-make-an-interactive-story-yGWSd8O2nkbYDmN)
- [MQTT Documentation](https://yoto.dev/players-mqtt/mqtt-docs/)
- Existing codebase: `scripts/submit_interactive_card.py`, `INTERACTIVE_CARD_ANALYSIS.md`
