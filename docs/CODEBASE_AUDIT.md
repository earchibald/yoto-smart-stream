# Codebase Audit: yoto-smart-stream

**Date:** 2026-03-21
**Auditor:** specExpert (crew)
**Bead:** yo-i4b
**Purpose:** Full codebase audit for TypeScript rewrite planning — what to keep, kill, rewrite.

---

## Executive Summary

The yoto-smart-stream codebase is a **Python/FastAPI application** that manages Yoto smart speaker content: audio upload/streaming, card creation, player control via MQTT, and an MCP server for AI assistant integration. It deploys on Railway with MySQL/SQLite and S3-compatible storage.

**Overall assessment:** Well-structured with good abstractions. Main issues are global state patterns, a monolithic `app.py`, and some oversized route files (cards.py at 1981 lines, streams.py at 1084 lines). The business logic, data model, and API patterns are solid and worth preserving in a TypeScript rewrite.

**By the numbers:**
- ~12,500 lines of application code (Python)
- ~4,300 lines of tests (17 test files in tests/, 8 in mcp-server/, 6 at root)
- ~30 documentation files
- 12 API route files exposing ~50+ endpoints
- 7 MCP server tools
- 3 database models (User, AudioFile, Setting)

---

## Verdict Matrix

| Module | Quality | Verdict | Notes |
|--------|---------|---------|-------|
| **config.py** | Good | KEEP | Excellent Pydantic config with Railway awareness, field validators |
| **models.py** | Good | KEEP | Clean ORM models, good field naming, transcript pipeline tracking |
| **core/yoto_client.py** | Good | KEEP | Core Yoto API wrapper, token lifecycle, MQTT integration |
| **core/audio_db.py** | Good | KEEP | Simple idempotent CRUD helpers |
| **core/transcription.py** | Good | KEEP/REFACTOR | Feature toggle pattern is excellent; refactor global state |
| **storage/base.py** | Good | KEEP | Clean async abstract interface |
| **storage/local.py** | Good | KEEP | Simple aiofiles implementation |
| **storage/s3.py** | Good | KEEP | Solid boto3 wrapper with async bridging |
| **api/mqtt_event_store.py** | Good | KEEP | Excellent event correlation system |
| **api/stream_manager.py** | Good | KEEP | Well-designed queue abstraction with persistence |
| **utils/env_logging.py** | Good | KEEP | Useful sensitive-value masking utility |
| **api/routes/admin.py** | Good | KEEP | Solid RBAC pattern |
| **api/routes/cover_images.py** | Good | KEEP | Good image validation against Yoto specs |
| **api/routes/health.py** | Good | KEEP | Standard health checks |
| **api/routes/media.py** | Good | KEEP | Clean Yoto media upload |
| **api/routes/players.py** | Good | KEEP | Complex but well-structured player control |
| **api/routes/settings.py** | Good | KEEP | Clean env-override config management |
| **api/routes/user_auth.py** | Good | KEEP | Solid cookie-based auth (remove debug endpoint) |
| **auth.py** | OK | REWRITE | Hardcoded SECRET_KEY, mismatched docstring, weak JWT validation |
| **database.py** | OK | REWRITE | Manual SQL migrations — use proper migration framework |
| **api/app.py** | OK | REWRITE | 477-line monolith mixing 6+ concerns |
| **api/dependencies.py** | OK | REWRITE | Global state instead of proper DI |
| **api/routes/auth.py** | OK | REWRITE | Extract OAuth flow from state management |
| **api/routes/library.py** | OK | REWRITE | Needs service abstraction, fragile attribute extraction |
| **api/routes/cards.py** | Poor | REWRITE | 1981 lines, mixed concerns, global task dict, needs split |
| **api/routes/streams.py** | OK | REWRITE | 1084 lines, mixed queue/streaming/MQTT concerns |
| **api/utils.py** | N/A | DELETE | Empty file |
| **mcp-server/server.py** | Good | KEEP | Battle-tested, 7 tools, per-host auth caching |
| **tests/** | Good | KEEP | 4300+ lines, good coverage |
| **docs/** | Good | KEEP | 30+ comprehensive docs |
| **requirements.txt** | Fair | REWRITE | Out of sync with pyproject.toml |

---

## Data Model (Preserve in TypeScript)

### User
| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | Auto-increment |
| username | String(50) | Unique, indexed |
| email | String(255) | Nullable |
| hashed_password | String(255) | Argon2 |
| is_active | Boolean | Default true |
| is_admin | Boolean | Default false |
| created_at | DateTime | UTC |
| updated_at | DateTime | Auto-updated |
| yoto_access_token | Text | OAuth token |
| yoto_refresh_token | Text | OAuth refresh |
| yoto_token_expires_at | DateTime | Expiration |

### AudioFile
| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | Auto-increment |
| filename | String(255) | Unique, indexed |
| size | Integer | Bytes |
| duration | Integer | Seconds, nullable |
| transcript | Text | STT result, nullable |
| transcript_status | String(20) | pending→processing→completed/error/cancelled/disabled |
| transcript_error | Text | Error message |
| created_at | DateTime | |
| updated_at | DateTime | |
| transcribed_at | DateTime | Completion time |
| tts_provider | String(50) | elevenlabs, gtts |
| tts_voice_id | String(255) | |
| tts_model | String(100) | |

### Setting
| Field | Type | Notes |
|-------|------|-------|
| id | Integer PK | |
| key | String(100) | Unique, indexed |
| value | Text | |
| description | Text | Nullable |
| created_at | DateTime | |
| updated_at | DateTime | |

---

## API Surface (All Endpoints)

### Authentication & Users
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| POST | `/auth/start` | auth.py | REWRITE — OAuth device code flow |
| POST | `/auth/poll` | auth.py | REWRITE — poll for auth completion |
| GET | `/auth/status` | auth.py | REWRITE — check auth status |
| POST | `/auth/logout` | auth.py | REWRITE — clear authentication |
| POST | `/user/login` | user_auth.py | KEEP — username/password login |
| POST | `/user/logout` | user_auth.py | KEEP — session logout |
| GET | `/user/session` | user_auth.py | KEEP — session check |
| GET | `/user/debug` | user_auth.py | KILL — exposes user list |
| GET | `/admin/users` | admin.py | KEEP — list users |
| POST | `/admin/users` | admin.py | KEEP — create user |
| PATCH | `/admin/users/{id}` | admin.py | KEEP — update user |

### Audio Management
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| GET | `/audio/list` | cards.py | KEEP — list audio files |
| POST | `/audio/upload` | cards.py | KEEP — upload audio |
| GET | `/audio/search` | cards.py | KEEP — search audio |
| GET | `/audio/{filename}` | cards.py | KEEP — stream audio |
| DELETE | `/audio/{filename}` | cards.py | KEEP — delete audio |
| GET | `/audio/tts/voices` | cards.py | KEEP — ElevenLabs voices |
| POST | `/audio/generate-tts` | cards.py | KEEP — TTS generation |
| POST | `/audio/stitch` | cards.py | KEEP — stitch audio files |
| GET | `/audio/stitch/status` | cards.py | KEEP — stitch task status |
| POST | `/audio/stitch/{id}/cancel` | cards.py | KEEP — cancel stitching |
| POST | `/audio/preview-stitch` | cards.py | KEEP — preview stitched audio |
| DELETE | `/audio/preview-stitch/{id}` | cards.py | KEEP — delete preview |

### Transcription
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| GET | `/audio/{filename}/transcript` | cards.py | KEEP |
| POST | `/audio/{filename}/transcribe` | cards.py | KEEP |
| DELETE | `/audio/{filename}/transcript` | cards.py | KEEP |
| POST | `/audio/{filename}/transcript/cancel` | cards.py | KEEP |

### Cards & Playlists
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| POST | `/cards/create-streaming` | cards.py | KEEP — create Yoto card |
| PUT | `/cards/{card_id}` | cards.py | KEEP — update card |
| DELETE | `/cards/{card_id}` | cards.py | KEEP — delete card |
| POST | `/cards/create-playlist-from-audio` | cards.py | KEEP — playlist from files |

### Library
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| GET | `/library` | library.py | REWRITE — Yoto library sync |
| GET | `/library/content/{id}` | library.py | REWRITE — content details |
| DELETE | `/library/{id}` | library.py | REWRITE — delete item |
| GET | `/library/{card_id}/chapters` | library.py | REWRITE — card chapters |
| GET | `/library/{card_id}/raw` | library.py | REWRITE — raw debug data |
| POST | `/library/{card_id}/edit-check` | library.py | REWRITE — MYO editability |

### Players
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| GET | `/players` | players.py | KEEP — list players with status |
| GET | `/players/{id}` | players.py | KEEP — player details |
| GET | `/players/{id}/status` | players.py | KEEP — raw device status |
| GET | `/players/{id}/config` | players.py | KEEP — device config |
| POST | `/players/{id}/control` | players.py | KEEP — play/pause/volume/skip |
| POST | `/players/{id}/play-card` | players.py | KEEP — play specific card |

### Streams & Queues
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| GET | `/streams/queues` | streams.py | KEEP — list queues |
| GET | `/streams/{name}/queue` | streams.py | KEEP — queue info |
| POST | `/streams/{name}` | streams.py | KEEP — create/update stream |
| POST | `/streams/{name}/queue` | streams.py | KEEP — add to queue |
| DELETE | `/streams/{name}/queue/{idx}` | streams.py | KEEP — remove from queue |
| DELETE | `/streams/{name}/queue` | streams.py | KEEP — clear queue |
| PUT | `/streams/{name}/queue/reorder` | streams.py | KEEP — reorder queue |
| DELETE | `/streams/{name}` | streams.py | KEEP — delete stream |
| POST | `/streams/{name}/create-playlist` | streams.py | KEEP — playlist from stream |
| DELETE | `/streams/playlists/{id}` | streams.py | KEEP — delete playlist |
| GET | `/streams/playlists/search/{name}` | streams.py | KEEP — search playlists |
| POST | `/streams/playlists/delete-multiple` | streams.py | KEEP — bulk delete |
| GET | `/streams/{name}/stream.mp3` | streams.py | KEEP — dynamic audio stream |
| GET | `/streams/detect-smart-stream/{device}` | streams.py | KEEP — auto-detect |

### MQTT & Events
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| GET | `/mqtt/analyzer` | streams.py | KEEP — event analysis |
| POST | `/mqtt/track-nav` | streams.py | KEEP — track navigation |
| GET | `/mqtt/device-state` | streams.py | KEEP — device state |

### Cover Images
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| GET | `/cover-images` | cover_images.py | KEEP |
| GET | `/cover-images/{filename}` | cover_images.py | KEEP |
| POST | `/cover-images/upload` | cover_images.py | KEEP |
| POST | `/cover-images/fetch` | cover_images.py | KEEP |
| DELETE | `/cover-images/{filename}` | cover_images.py | KEEP |

### Settings & Health
| Method | Path | Source | Verdict |
|--------|------|--------|---------|
| GET | `/settings` | settings.py | KEEP |
| GET | `/settings/{key}` | settings.py | KEEP |
| PUT | `/settings/{key}` | settings.py | KEEP |
| GET | `/health` | health.py | KEEP |
| GET | `/ready` | health.py | KEEP |

---

## Yoto External API (Must Integrate)

### Authentication
- **OAuth2 Device Code Flow** (RFC 8628) via `login.yotoplay.com`
- Access + refresh tokens, automatic refresh at configurable intervals
- MQTT credentials fetched per-device

### REST API (`api.yotoplay.com`)
- **Devices:** `/device-v2/devices/mine`, `/device-v2/{id}/status`, `/device-v2/{id}/config`, `/device-v2/{id}/command`
- **Cards:** `/card/mine` (MYO), `/card/family/library`, `/card/{id}`, POST `/card`, DELETE `/card/{id}`
- **Media:** `/media/audio/upload-url`, POST `/media/cover-image`, `/media/displayIcons/public`
- **Groups:** Full CRUD at `/groups`
- **Family:** `/user/family`

### MQTT (`mqtt.yoto.io:8883`)
- **Subscribe:** `yoto/{deviceId}/status`, `yoto/{deviceId}/events`, `yoto/{deviceId}/response`
- **Publish:** `yoto/{deviceId}/command` — volume, ambient color, play card, pause, resume, stop, sleep timer
- Volume scale: 0-16 (device) mapped to 0-100% (UI)

### Card Structure (Streaming Pattern)
```json
{
  "title": "My Card",
  "content": {
    "chapters": [{
      "key": "01",
      "tracks": [{ "key": "01", "url": "https://your-server.com/audio/story.mp3" }]
    }]
  }
}
```

---

## Configuration (All Environment Variables)

### Core
| Variable | Default | Purpose |
|----------|---------|---------|
| `DEBUG` | false | Debug mode |
| `LOG_LEVEL` | INFO | Logging verbosity |
| `ENVIRONMENT` | (auto) | Railway env name |
| `HOST` | 0.0.0.0 | Bind host |
| `PORT` | 8080 | Bind port |
| `PUBLIC_URL` | (none) | External URL (ngrok, Railway) |
| `CORS_ORIGINS` | localhost:8080,3000 | Allowed origins |

### Yoto
| Variable | Default | Purpose |
|----------|---------|---------|
| `YOTO_CLIENT_ID` | (none) | OAuth client ID |
| `MQTT_ENABLED` | true | Enable MQTT |
| `TOKEN_REFRESH_INTERVAL_HOURS` | 12 | Token refresh interval |

### Storage
| Variable | Default | Purpose |
|----------|---------|---------|
| `STORAGE_BACKEND` | local | local or s3 |
| `AUDIO_FILES_DIR` | audio_files | Local path |
| `BUCKET_NAME` | (none) | S3 bucket |
| `BUCKET_ACCESS_KEY_ID` | (none) | S3 access key |
| `BUCKET_SECRET_ACCESS_KEY` | (none) | S3 secret key |
| `BUCKET_ENDPOINT` | storage.railway.app | S3 endpoint |
| `PRESIGNED_URL_EXPIRY` | 604800 | URL expiry (seconds) |

### Database
| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | sqlite:///./yoto_smart_stream.db | DB connection |
| `MYSQL_URL` | (auto) | Railway MySQL |

### Speech
| Variable | Default | Purpose |
|----------|---------|---------|
| `TRANSCRIPTION_ENABLED` | false | Enable STT |
| `TRANSCRIPTION_MODEL` | scribe_v2 | ElevenLabs model |
| `ELEVENLABS_API_KEY` | (none) | TTS/STT API key |

### Auth
| Variable | Default | Purpose |
|----------|---------|---------|
| `ADMIN_USERNAME` | (none) | Initial admin user |
| `ADMIN_PASSWORD` | (none) | Initial admin password |

---

## Business Logic Worth Preserving

### 1. Audio Streaming Architecture
The "stream from your own server" pattern (vs uploading to Yoto) is the core value proposition. Cards point to your URLs, enabling dynamic content, no file limits, and updates without card recreation.

### 2. MQTT Event Correlation
`mqtt_event_store.py` correlates device events with stream requests using lookback windows. This powers smart-stream detection and playback analytics.

### 3. Stream Queue Management
`stream_manager.py` provides named queues with persistence, atomic operations, and locking. Queues are serialized to JSON on disk and survive restarts.

### 4. Feature Toggle Pattern
Transcription uses a 3-tier override: env var > database setting > config default. This pattern with live-reload detection is reusable across all features.

### 5. Volume Cache with TTL
Players module caches volume (5s TTL) to prevent stale MQTT data from overwriting user-set values. Prevents race conditions in real-time control.

### 6. Railway-Aware Configuration
Config automatically detects Railway environment and adjusts paths (persistent volumes at `/data`), database URLs, and startup behavior. This multi-environment awareness is essential.

### 7. OAuth Device Code Flow
Full RFC 8628 implementation for Yoto authentication, with token persistence across restarts and automatic refresh.

---

## Critical Issues to Fix in Rewrite

1. **Hardcoded secret** in `auth.py` line 18 — must use env var
2. **Manual SQL migrations** in `database.py` — use proper migration framework (Drizzle, Prisma)
3. **Global state** in dependencies.py, transcription.py — use DI container
4. **Monolithic app.py** (477 lines) — split into factory, lifespan, routes, WebSocket handlers
5. **cards.py** (1981 lines) — split into AudioService, TtsService, CardService, TaskQueue
6. **streams.py** (1084 lines) — split into StreamQueueManager, PlaylistService, AudioStreamGenerator
7. **In-memory task tracking** in cards.py — use proper job queue (BullMQ, etc.)
8. **Debug endpoint** in user_auth.py — remove `/user/debug`
9. **requirements.txt** out of sync with pyproject.toml — consolidate
10. **Duplicate playlist logic** between cards.py and streams.py — consolidate

---

## TypeScript Rewrite Architecture Recommendation

### Suggested Module Split
```
src/
├── config/          ← Pydantic-style validated config (zod + env)
├── db/
│   ├── schema.ts    ← Drizzle/Prisma schema (User, AudioFile, Setting)
│   └── migrations/  ← Proper migration framework
├── services/
│   ├── yoto-client.ts       ← API wrapper + token lifecycle
│   ├── mqtt-client.ts       ← MQTT connection + event store
│   ├── audio.ts             ← Upload, search, stream, delete
│   ├── tts.ts               ← ElevenLabs TTS generation
│   ├── transcription.ts     ← STT with feature toggle
│   ├── cards.ts             ← Card/playlist CRUD via Yoto API
│   ├── stream-queue.ts      ← Named queues with persistence
│   ├── storage/             ← Local + S3 backends (interface)
│   └── cover-images.ts      ← Image validation + management
├── routes/
│   ├── auth.ts              ← OAuth + user auth
│   ├── admin.ts             ← User management
│   ├── audio.ts             ← Audio endpoints
│   ├── cards.ts             ← Card endpoints
│   ├── library.ts           ← Library sync
│   ├── players.ts           ← Player control
│   ├── streams.ts           ← Stream/queue endpoints
│   ├── settings.ts          ← Config endpoints
│   └── health.ts            ← Health checks
├── jobs/                    ← BullMQ: stitching, transcription
└── mcp-server/              ← MCP tools (keep separate)
```

### Key Architectural Changes
1. **Service layer** between routes and data — routes become thin
2. **Dependency injection** (tsyringe, inversify, or manual) — no globals
3. **Job queue** (BullMQ + Redis) for stitching/transcription — not in-memory dicts
4. **Proper migrations** (Drizzle Kit or Prisma Migrate)
5. **Consolidate playlist logic** into single CardService
6. **Type-safe Yoto API client** with response models (zod schemas)

---

## MCP Server Assessment

The MCP server (`mcp-server/server.py`, 841 lines) is **solid and battle-tested**:
- 7 tools: oauth, library_stats, list_cards, search_cards, list_playlists, get_metadata_keys, get_field_values
- Per-host authentication caching
- Playwright-based OAuth automation
- All core features validated against live deployment

**Verdict:** KEEP. Minor improvements: make Playwright optional dependency, parameterize OAuth poll timeout.

---

## Files to Delete

| File | Reason |
|------|--------|
| `yoto_smart_stream/api/utils.py` | Empty |
| `mcp-server/test_tools.py` | Broken imports, replaced by test_mcp_integration.py |
| Root `test_*.py` files (6) | Should be organized into tests/ directory |
| 24 root-level `.md` files | Delivery/summary docs — move useful ones to docs/, delete rest |

---

## Test Infrastructure

**Strong.** 4300+ lines across tests/, plus MCP-specific tests. Good mix of unit and integration tests with mocks and fixtures. Test organization needs cleanup (root-level tests should move to tests/) but coverage is solid.

---

*End of audit. This document serves as the reference for TypeScript rewrite planning.*
