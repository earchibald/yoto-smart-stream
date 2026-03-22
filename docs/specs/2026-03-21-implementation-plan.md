# Implementation Plan: Yoto Smart Stream v2

**Date:** 2026-03-21
**Author:** specExpert (crew)
**Bead:** yo-63h
**Status:** Draft

**Inputs:**
- Codebase Audit: `docs/CODEBASE_AUDIT.md` (yo-i4b)
- Interactive Cards API: `docs/INTERACTIVE_CARDS_API_REFERENCE.md` (yo-px1)
- Story Graph Editors Research: `docs/STORY_GRAPH_EDITORS_RESEARCH.md` (yo-9vl)
- TypeScript Stack Selection: yo-qd0 comments (webResearcher)

---

## Architecture Overview

Three Docker services in a pnpm monorepo, communicating over a shared Docker network:

```
┌─────────────────────────────────────────────────────────┐
│  Docker Compose                                         │
│                                                         │
│  ┌──────────┐   ┌──────────┐   ┌──────────────────┐   │
│  │  Engine   │   │  Studio  │   │  Media Pipeline  │   │
│  │ (Fastify) │   │ (React)  │   │ (Fastify/Hono)   │   │
│  │ :3001     │   │ :5173    │   │ :3002            │   │
│  └────┬──────┘   └────┬─────┘   └────┬─────────────┘   │
│       │               │              │                  │
│       └───────┬───────┘──────┬───────┘                  │
│               │              │                          │
│         ┌─────┴──────┐  ┌───┴───┐                      │
│         │  SQLite DB  │  │ mDNS  │                      │
│         │  (shared)   │  │ Avahi │                      │
│         └────────────┘  └───────┘                      │
└─────────────────────────────────────────────────────────┘
```

**Engine** — Headless API: Yoto integration, auth, library, player control, MQTT, card CRUD
**Studio** — Web UI: story graph editor, audio recorder, card producer, admin
**Media Pipeline** — Audio processing: TTS, transcription, stitching, format conversion

---

## Technology Stack (from yo-qd0 research)

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Package Manager | pnpm workspaces | 70% less disk, content-addressable |
| Monorepo | Turborepo | Parallel builds with caching |
| Runtime | Node.js 22 LTS | Consistency across services |
| Engine Framework | Fastify | 70-80K req/s, TypeBox type provider, OpenAPI |
| Media Framework | Fastify | Same ecosystem, plugin compatibility |
| ORM | Drizzle ORM | 7.4KB, zero codegen, SQLite JSON columns work |
| DB Driver | better-sqlite3 | Fastest Node.js SQLite, synchronous API |
| Database | SQLite (WAL) | Local-first, single file, zero ops |
| UI Framework | React 19 + Vite 7 | Largest ecosystem, concurrent rendering |
| Graph Editor | React Flow (@xyflow/react) | 24K stars, MIT, custom node types |
| UI Components | shadcn/ui + Radix | Accessible, customizable |
| Audio Processing | FFmpeg (native) | Industry standard, Docker install |
| TTS | Google Cloud TTS (prod) / edge-tts (free) | Tiered cost |
| Backend Bundler | tsdown | Successor to tsup |
| Shared Types | `@yoto/shared` package | Monorepo internal package |

---

## Monorepo Structure

```
yoto-v2/
├── package.json                 # pnpm workspace root
├── pnpm-workspace.yaml          # workspace: packages/*, services/*
├── turbo.json                   # build pipeline config
├── tsconfig.base.json           # strict: true, shared compiler options
├── docker-compose.yml           # all three services + mDNS
├── docker-compose.dev.yml       # dev overrides (hot reload, volumes)
├── .env.example
│
├── packages/
│   └── shared/                  # @yoto/shared
│       ├── package.json
│       ├── tsconfig.json
│       └── src/
│           ├── index.ts
│           ├── schemas/         # Zod schemas (Yoto API responses, config)
│           │   ├── card.ts      # Card, Chapter, Track, Event schemas
│           │   ├── player.ts    # Player, DeviceStatus schemas
│           │   ├── library.ts   # Library item schemas
│           │   ├── auth.ts      # OAuth token schemas
│           │   └── config.ts    # App config schema
│           ├── types/           # TypeScript types derived from schemas
│           ├── constants.ts     # Yoto API URLs, MQTT topics, audio formats
│           └── utils.ts         # Shared utilities (env masking, etc.)
│
├── services/
│   ├── engine/                  # @yoto/engine
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── Dockerfile
│   │   └── src/
│   │       ├── index.ts         # Fastify app factory
│   │       ├── config.ts        # Env-validated config (zod)
│   │       ├── db/
│   │       │   ├── schema.ts    # Drizzle schema (users, audio_files, settings, stories)
│   │       │   ├── migrate.ts   # Drizzle Kit migrations
│   │       │   └── client.ts    # DB client singleton
│   │       ├── services/
│   │       │   ├── yoto-api.ts      # Yoto REST client (typed responses)
│   │       │   ├── yoto-auth.ts     # OAuth device code flow + token lifecycle
│   │       │   ├── mqtt.ts          # MQTT client + event store
│   │       │   ├── library.ts       # Library sync + caching
│   │       │   ├── players.ts       # Player control + volume cache
│   │       │   ├── cards.ts         # Card/playlist CRUD via Yoto API
│   │       │   ├── stream-queue.ts  # Named queues with JSON persistence
│   │       │   ├── storage.ts       # Storage interface + local/S3 backends
│   │       │   └── user-auth.ts     # Local user auth (argon2 + JWT)
│   │       ├── routes/
│   │       │   ├── auth.ts
│   │       │   ├── admin.ts
│   │       │   ├── library.ts
│   │       │   ├── players.ts
│   │       │   ├── cards.ts
│   │       │   ├── streams.ts
│   │       │   ├── audio.ts
│   │       │   ├── settings.ts
│   │       │   └── health.ts
│   │       └── plugins/
│   │           ├── auth.ts          # Auth decorators/hooks
│   │           └── error-handler.ts # Centralized error handling
│   │
│   ├── studio/                  # @yoto/studio
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   ├── Dockerfile
│   │   ├── vite.config.ts
│   │   └── src/
│   │       ├── main.tsx
│   │       ├── App.tsx
│   │       ├── api/             # Engine API client (typed fetch)
│   │       ├── components/
│   │       │   ├── ui/          # shadcn/ui components
│   │       │   ├── layout/      # Shell, sidebar, header
│   │       │   ├── audio/       # Recorder, player, waveform
│   │       │   ├── library/     # Card grid, filters, search
│   │       │   ├── player/      # Device control panel
│   │       │   └── admin/       # User management, settings
│   │       ├── features/
│   │       │   └── story-editor/    # React Flow graph editor
│   │       │       ├── StoryCanvas.tsx
│   │       │       ├── nodes/       # Custom node types
│   │       │       │   ├── DialogueNode.tsx
│   │       │       │   ├── ChoiceNode.tsx
│   │       │       │   ├── SfxNode.tsx
│   │       │       │   └── EndingNode.tsx
│   │       │       ├── edges/
│   │       │       ├── panels/      # Inspector, properties
│   │       │       ├── hooks/       # useStoryGraph, usePlayback
│   │       │       └── store.ts     # Zustand store for graph state
│   │       ├── hooks/
│   │       └── stores/
│   │
│   └── media-pipeline/          # @yoto/media-pipeline
│       ├── package.json
│       ├── tsconfig.json
│       ├── Dockerfile
│       └── src/
│           ├── index.ts         # Fastify app factory
│           ├── config.ts
│           ├── services/
│           │   ├── ffmpeg.ts        # FFmpeg wrapper (spawn + streams)
│           │   ├── tts.ts           # TTS providers (Google, edge-tts, Piper)
│           │   ├── transcription.ts # STT (ElevenLabs scribe)
│           │   ├── stitcher.ts      # Audio concatenation/mixing
│           │   └── cover-images.ts  # Image validation + processing
│           ├── routes/
│           │   ├── tts.ts
│           │   ├── transcribe.ts
│           │   ├── stitch.ts
│           │   ├── images.ts
│           │   └── health.ts
│           └── jobs/
│               ├── queue.ts         # BullMQ job queue
│               ├── stitch.worker.ts
│               └── transcribe.worker.ts
│
└── infra/
    ├── avahi/                   # mDNS registration
    │   └── Dockerfile
    └── scripts/
        └── dev-setup.sh
```

---

## Phased Implementation Plan

### Phase 0: Scaffolding
**Goal:** Monorepo skeleton, build pipeline, Docker Compose, CI
**Dependencies:** None
**Duration estimate:** Foundation work

#### Deliverables
1. pnpm workspace with `packages/shared`, `services/engine`, `services/studio`, `services/media-pipeline`
2. `turbo.json` with build/dev/test/lint pipeline
3. `tsconfig.base.json` with strict mode, path aliases
4. Docker Compose with all three services + SQLite volume
5. `@yoto/shared` package with initial Zod schemas (card, player, auth)
6. GitHub Actions CI: typecheck, lint, test, Docker build
7. `.env.example` with all config vars

#### Acceptance Criteria
- `pnpm install` succeeds from clean checkout
- `pnpm turbo build` compiles all three services without errors
- `docker compose up` starts all services, each responds on `/health`
- `pnpm turbo typecheck` passes with strict mode
- Shared types importable from all three services: `import { CardSchema } from '@yoto/shared'`

#### Key Decisions
- SQLite file lives in a Docker volume mounted at `/data/yoto.db` — same persistence model as v1
- Engine owns the database; Studio and Media Pipeline call Engine's API (no direct DB access)
- All inter-service communication via HTTP (not shared DB)

---

### Phase 1: Engine Core
**Goal:** Headless API replacing v1's FastAPI backend — auth, library, players, cards, streams
**Dependencies:** Phase 0
**Ref:** Codebase Audit verdict matrix — all KEEP modules ported, REWRITE modules rebuilt

#### 1A: Database + Config
**Deliverables:**
1. Drizzle schema: `users`, `audio_files`, `settings`, `stories` tables
   - Ref: Codebase Audit § Data Model — preserve all fields from v1
   - New: `stories` table for graph editor data (JSON column for React Flow graph)
2. Drizzle Kit migrations setup with `drizzle-kit push` for dev
3. Config module using Zod + `@yoto/shared/schemas/config`
   - Ref: v1 `config.py` — preserve all env vars, Railway detection, path logic
4. Database client with WAL mode enabled

**Acceptance Criteria:**
- `drizzle-kit push` creates schema from scratch
- Config validates all env vars with helpful errors on missing required values
- WAL mode confirmed via `PRAGMA journal_mode`

#### 1B: Auth
**Deliverables:**
1. Yoto OAuth service: device code flow (RFC 8628), token persistence, auto-refresh
   - Ref: v1 `core/yoto_client.py` + `api/routes/auth.py` — preserve flow, fix hardcoded secret
   - Ref: Interactive Cards API § Authentication Quick Reference
2. Local user auth: argon2 hashing, JWT tokens (secret from env var)
   - Ref: v1 `auth.py` — rewrite with proper secret management
3. Routes: `POST /auth/start`, `POST /auth/poll`, `GET /auth/status`, `POST /auth/logout`
4. Routes: `POST /user/login`, `POST /user/logout`, `GET /user/session`
5. Fastify auth plugin for route-level protection

**Acceptance Criteria:**
- OAuth device code flow works end-to-end against `login.yotoplay.com`
- Token refresh runs automatically at configured interval
- JWT secret sourced from `JWT_SECRET` env var — startup fails if missing
- Auth cookie httpOnly, secure, sameSite=strict

#### 1C: Yoto API Client
**Deliverables:**
1. Type-safe Yoto REST client using `@yoto/shared` Zod schemas
   - Ref: Codebase Audit § Yoto External API — all endpoints
   - Ref: Interactive Cards API § Complete Card Payload Schema
2. Response parsing with Zod (runtime validation of Yoto API responses)
3. Automatic auth header injection from stored tokens
4. Methods: `getDevices()`, `getLibrary()`, `getCard(id)`, `createCard(payload)`, `updateCard(id, payload)`, `deleteCard(id)`, `uploadMedia()`, `getDeviceStatus(id)`, `sendCommand(id, cmd)`

**Acceptance Criteria:**
- All Yoto API endpoints callable with typed responses
- Invalid API responses throw with detailed error messages (Zod parse errors)
- Token automatically refreshed before expired requests

#### 1D: MQTT + Player Control
**Deliverables:**
1. MQTT client service with connect/subscribe/publish
   - Ref: v1 `core/yoto_client.py` MQTT section + `api/mqtt_event_store.py`
2. Event store: in-memory with correlation and lookback windows
   - Ref: v1 `mqtt_event_store.py` — preserve MQTTEvent/StreamRequestEvent pattern
3. Volume cache with 5s TTL (ref: v1 `api/routes/players.py`)
4. Routes: `GET /players`, `GET /players/:id`, `GET /players/:id/status`, `GET /players/:id/config`, `POST /players/:id/control`, `POST /players/:id/play-card`
5. Routes: `GET /mqtt/device-state`, `GET /mqtt/analyzer`

**Acceptance Criteria:**
- MQTT connects to `mqtt.yoto.io:8883`, receives device events
- Player list shows online/offline status, battery, volume
- Volume control round-trips: API → MQTT publish → MQTT event → API reflects new value
- Event correlation links stream requests to preceding MQTT events

#### 1E: Library + Cards
**Deliverables:**
1. Library service: sync from Yoto API, caching (5-min TTL)
   - Ref: v1 `api/routes/library.py` — rewrite with service abstraction
2. Card service: create, update, delete cards via Yoto API
   - Ref: v1 `api/routes/cards.py` card endpoints
   - Ref: Interactive Cards API — full payload schema for interactive cards
3. Playlist consolidation: single service for playlist CRUD (was split across cards.py and streams.py in v1)
4. Routes: `GET /library`, `GET /library/:id`, `DELETE /library/:id`, `GET /library/:cardId/chapters`, `POST /library/:cardId/edit-check`
5. Routes: `POST /cards`, `PUT /cards/:id`, `DELETE /cards/:id`, `POST /cards/playlist`

**Acceptance Criteria:**
- Library loads and caches user's card collection
- Card creation works with both streaming URLs and Yoto-hosted audio
- Interactive card creation works with events (onEnd, onLhb, onRhb) — ref: Interactive Cards API § Events
- MYO editability check works

#### 1F: Streams + Audio Serving
**Deliverables:**
1. Stream queue manager: named queues with JSON persistence
   - Ref: v1 `api/stream_manager.py` — preserve pattern exactly
2. Storage service: local filesystem + S3 backends
   - Ref: v1 `storage/` — preserve interface, rewrite for Node.js fs.promises + AWS SDK v3
3. Audio file CRUD (upload, list, search, stream, delete)
   - Ref: v1 `api/routes/cards.py` audio endpoints
4. Routes: full streams/queues API surface (14 endpoints — ref: Codebase Audit § Streams & Queues)
5. Routes: audio management (ref: Codebase Audit § Audio Management)

**Acceptance Criteria:**
- Audio upload stores file and creates DB record
- `GET /streams/:name/stream.mp3` dynamically concatenates queue files
- Queue operations (add, remove, reorder, clear) persist to disk
- S3 backend generates presigned URLs with configurable expiry

#### 1G: Admin + Settings + Health
**Deliverables:**
1. Admin routes: user CRUD with RBAC
2. Settings routes: key-value store with env var override precedence
   - Ref: v1 feature toggle pattern (env > DB > config default)
3. Health/readiness routes
4. Cover image management (upload, validate dimensions, serve)
   - Ref: v1 `api/routes/cover_images.py` — preserve Yoto dimension validation (661x1054, 784x1248)

**Acceptance Criteria:**
- Admin can create/update/list users
- Settings show override source (env vs DB)
- `/health` returns service status, `/ready` returns readiness
- Cover images validated against Yoto dimension specs

---

### Phase 2: Media Pipeline
**Goal:** Separate service for audio processing, replacing v1's in-process approach
**Dependencies:** Phase 0, Phase 1A (shared schemas)

#### 2A: FFmpeg Integration
**Deliverables:**
1. FFmpeg service: spawn wrapper with stdin/stdout streaming
2. Audio format detection and validation
3. MP3 encoding with configurable bitrate
4. Concatenation via concat demuxer
5. Health route confirming FFmpeg binary available

**Acceptance Criteria:**
- FFmpeg operations run as child processes with proper stream piping
- Format conversion works: wav/aac/flac → mp3
- Concatenation handles files with different sample rates (via filter_complex)
- Processing errors propagate with meaningful messages

#### 2B: TTS Service
**Deliverables:**
1. TTS provider interface (strategy pattern)
2. Google Cloud TTS provider (production)
3. edge-tts provider (free/prototyping)
4. Voice listing endpoint
5. Route: `POST /tts/generate`, `GET /tts/voices`

**Acceptance Criteria:**
- TTS generates audio from text, returns MP3
- Provider selectable via config
- Voice list reflects available voices for selected provider
- Generated audio metadata stored (provider, voice, model)

#### 2C: Transcription Service
**Deliverables:**
1. STT service with feature toggle (ref: v1 transcription.py 3-tier override)
2. ElevenLabs scribe integration
3. Route: `POST /transcribe`, `GET /transcribe/:id/status`

**Acceptance Criteria:**
- Transcription can be enabled/disabled via env, DB setting, or config
- Status tracking: pending → processing → completed/error
- Graceful degradation when disabled or API key missing

#### 2D: Audio Stitching + Job Queue
**Deliverables:**
1. BullMQ job queue for long-running operations
2. Stitch worker: concatenate multiple audio files with crossfade options
3. Preview generation (temporary stitched output)
4. Progress tracking via job events
5. Routes: `POST /stitch`, `GET /stitch/:id/status`, `POST /stitch/:id/cancel`, `POST /stitch/preview`, `DELETE /stitch/preview/:id`

**Acceptance Criteria:**
- Stitching jobs queued and processed asynchronously
- Progress reported via polling (percentage, current file)
- Cancellation stops FFmpeg process and cleans up
- Preview files auto-expire after configurable TTL

#### 2E: Cover Image Processing
**Deliverables:**
1. Image validation (dimensions, aspect ratio, file type)
2. Remote image fetching
3. Image serving
4. Routes: `GET /images`, `GET /images/:filename`, `POST /images/upload`, `POST /images/fetch`, `DELETE /images/:filename`

**Acceptance Criteria:**
- Uploaded images validated against Yoto specs (661x1054 or 784x1248)
- Remote fetch downloads and validates
- Default images protected from deletion

---

### Phase 3: Studio UI
**Goal:** React web application replacing v1's Jinja templates + static files
**Dependencies:** Phase 1 (Engine API), Phase 2 (Media Pipeline API)

#### 3A: Shell + Auth
**Deliverables:**
1. Vite + React app with routing (React Router or TanStack Router)
2. App shell: sidebar navigation, header with user info
3. Login page + auth context (JWT from Engine)
4. API client layer: typed fetch against Engine + Media Pipeline
5. Dark/light theme via shadcn/ui

**Acceptance Criteria:**
- Login flow works against Engine's auth endpoints
- Protected routes redirect to login
- API client automatically attaches auth headers
- Responsive layout (desktop + tablet)

#### 3B: Library + Player Control
**Deliverables:**
1. Library view: card grid with cover images, search, filters
2. Card detail view: chapters, tracks, metadata
3. Player control panel: device list, volume, play/pause/skip
4. Real-time player status (polling or WebSocket from Engine)

**Acceptance Criteria:**
- Library loads from Engine, displays card covers
- Search filters by title, author, category
- Player volume slider reflects actual device volume (via MQTT)
- Play-card sends command and shows playback status

#### 3C: Audio Management
**Deliverables:**
1. Audio library view: list, search, upload
2. Audio player component with waveform visualization
3. Upload with drag-and-drop + progress
4. Transcription trigger + display
5. TTS generation form (text input, voice selection, preview)

**Acceptance Criteria:**
- Audio files uploadable via drag-and-drop
- Upload progress shown in real-time
- Audio plays in browser with waveform
- TTS generates audio and adds to library

#### 3D: Story Graph Editor (Core Feature)
**Deliverables:**
1. React Flow canvas with custom node types:
   - **DialogueNode**: text content, audio attachment, character
   - **ChoiceNode**: branching point (left button / right button)
   - **SfxNode**: sound effect cue
   - **EndingNode**: story terminus
   - Ref: Story Graph Editors Research § React Flow recommendation
2. Edge types: flow (sequential), choice-left (onLhb), choice-right (onRhb)
3. Node inspector panel: edit text, attach audio, set events
4. Graph ↔ Yoto card serialization:
   - Graph nodes → chapters (one chapter per node)
   - Graph edges → track events (onEnd/onLhb/onRhb → goto)
   - Ref: Interactive Cards API § Events — The Interactive Navigation System
5. Story graph persistence (save/load via Engine API)
6. Minimap, auto-layout, zoom controls

**Acceptance Criteria:**
- Create story by placing and connecting nodes on canvas
- Choice nodes generate two outgoing edges (left/right button)
- Export graph as valid Yoto interactive card payload (ref: Interactive Cards API § Complete Interactive Card Example)
- Exported card plays correctly on Yoto Player with button-driven navigation
- Graph validates: no orphan nodes, no dead ends without EndingNode, all choices have targets
- Save/load round-trips without data loss

#### 3E: Story Editor Advanced Features
**Deliverables:**
1. Audio recording directly in editor (MediaRecorder API)
2. TTS generation per node (type text → generate audio → attach to node)
3. Story preview/playback (simulate button presses in browser using inkjs patterns)
   - Ref: Story Graph Editors Research § Ink — inkjs for in-browser story playback
4. Multi-track chapters (narration + choice prompt within single node)
   - Ref: Interactive Cards API § Multi-Track Chapters
5. Path convergence visualization (multiple edges into same node)
   - Ref: Interactive Cards API § Path Convergence
6. Story statistics: node count, path count, longest path, average path length

**Acceptance Criteria:**
- Record audio in browser, upload to Media Pipeline, attach to node
- TTS generates speech from node text and attaches as audio
- Preview walks through story, simulating left/right button presses
- Multi-track nodes correctly serialize (narration tracks before choice track)
- Statistics update in real-time as graph is edited

#### 3F: Card Producer
**Deliverables:**
1. Card creation wizard: metadata, cover image, content
2. Stream queue builder (drag-and-drop audio ordering)
3. Playlist creation from queue
4. Card publish flow: preview → create on Yoto → confirm
5. Batch operations: multi-card management

**Acceptance Criteria:**
- Create card with cover image, title, chapters from audio files
- Reorder chapters via drag-and-drop
- Publish card to Yoto account
- Edit existing MYO cards

#### 3G: Admin Panel
**Deliverables:**
1. User management (create, edit, activate/deactivate)
2. Settings management with override indicators
3. System status dashboard (health, MQTT, storage)
4. OAuth connection management

**Acceptance Criteria:**
- Admin can manage users and settings
- Settings show env var override status
- Dashboard shows real-time system health

---

### Phase 4: Docker + mDNS + Production Readiness
**Goal:** Production deployment, mDNS discovery, operational tooling
**Dependencies:** Phases 1-3

#### 4A: Docker Compose
**Deliverables:**
1. Multi-stage Dockerfiles for each service (build → runtime)
   - Engine: Node.js 22 slim + better-sqlite3 native build
   - Studio: Node.js build stage → nginx for static serving
   - Media Pipeline: Node.js 22 + FFmpeg + native build tools
2. `docker-compose.yml`: all services, shared SQLite volume, networking
3. `docker-compose.dev.yml`: hot reload, source mounts, debug ports
4. Health checks for all containers
5. Environment variable documentation

**Acceptance Criteria:**
- `docker compose up` starts all services from cold in < 60s
- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` enables hot reload
- SQLite DB persists across container restarts (volume mount)
- All services communicate over internal Docker network
- Container sizes: Engine < 200MB, Studio < 50MB, Media Pipeline < 500MB (includes FFmpeg)

#### 4B: mDNS Registration
**Deliverables:**
1. Avahi sidecar container for mDNS registration
2. Registers `yoto-engine.local`, `yoto-studio.local` on LAN
3. Configuration for custom service names
4. Note: mDNS is for LAN discovery by browsers/devices, NOT for Yoto Player streaming URLs
   - Ref: Interactive Cards API § Streaming URL Requirements — `.local` domains unreliable for Yoto Player

**Acceptance Criteria:**
- `yoto-studio.local` resolves on LAN to Studio UI
- `yoto-engine.local` resolves on LAN to Engine API
- mDNS registration survives container restarts
- Configurable service names via env vars

#### 4C: MCP Server Migration
**Deliverables:**
1. Port MCP server to TypeScript (ref: v1 `mcp-server/server.py` — verdict: KEEP)
2. All 7 tools preserved: oauth, library_stats, list_cards, search_cards, list_playlists, get_metadata_keys, get_field_values
3. Calls Engine API instead of direct Yoto API (Engine becomes the gateway)
4. Playwright made optional dependency

**Acceptance Criteria:**
- All 7 MCP tools work via Engine API
- Per-host authentication caching preserved
- Works with Claude Desktop and VS Code configurations

#### 4D: Testing + CI
**Deliverables:**
1. Unit tests for all services (Vitest)
2. Integration tests: Engine API against SQLite
3. E2E tests: Story editor → card creation → Yoto API (Playwright)
4. GitHub Actions: typecheck → lint → test → Docker build → (optional) deploy
5. Coverage targets: Engine 80%, Media Pipeline 70%, Studio 60%

**Acceptance Criteria:**
- `pnpm turbo test` runs all tests
- CI passes on PR
- Coverage meets targets
- Docker images build successfully in CI

---

## Dependency Graph

```
Phase 0: Scaffolding
    │
    ├── Phase 1: Engine Core
    │   ├── 1A: Database + Config
    │   │   ├── 1B: Auth
    │   │   │   └── 1C: Yoto API Client
    │   │   │       ├── 1D: MQTT + Players
    │   │   │       └── 1E: Library + Cards
    │   │   └── 1F: Streams + Audio
    │   └── 1G: Admin + Settings + Health
    │
    ├── Phase 2: Media Pipeline (can start after Phase 0)
    │   ├── 2A: FFmpeg Integration
    │   │   ├── 2D: Stitching + Job Queue
    │   │   └── 2E: Cover Images
    │   ├── 2B: TTS Service
    │   └── 2C: Transcription Service
    │
    ├── Phase 3: Studio UI (needs Phase 1 + 2 APIs)
    │   ├── 3A: Shell + Auth
    │   │   ├── 3B: Library + Player Control
    │   │   ├── 3C: Audio Management
    │   │   ├── 3D: Story Graph Editor ★ (core feature)
    │   │   │   └── 3E: Story Editor Advanced
    │   │   ├── 3F: Card Producer
    │   │   └── 3G: Admin Panel
    │
    └── Phase 4: Docker + mDNS + Production
        ├── 4A: Docker Compose
        ├── 4B: mDNS Registration
        ├── 4C: MCP Server Migration
        └── 4D: Testing + CI
```

**Parallelism opportunities:**
- Phase 1 and Phase 2 can run in parallel after Phase 0
- Phase 2A-2E are mostly independent of each other
- Phase 3A depends on Phase 1B (auth); 3B-3G can largely parallel after 3A
- Phase 4A can start as soon as any one service is functional

---

## Critical Path

The critical path runs through: **Phase 0 → 1A → 1B → 1C → 1E → 3A → 3D**

This path delivers the core value: story graph editor that creates interactive cards on Yoto.

**Minimum viable demo:** Phases 0, 1A, 1B, 1C, 1E, 3A, 3D
- User logs in (1B) → views library (1E) → opens story editor (3D) → creates interactive card → publishes to Yoto (1C/1E)

---

## Data Migration

### From v1 to v2

The v1 SQLite database has 3 tables (users, audio_files, settings). Migration strategy:

1. **Users:** Direct field mapping. Rehash passwords if algorithm changes (argon2 → argon2 = no change needed).
2. **AudioFiles:** Direct field mapping. Add new fields (story_id foreign key) with nullable defaults.
3. **Settings:** Direct key-value migration.
4. **Audio files on disk:** Copy from v1 `/data/audio_files` to v2 volume.
5. **New table: stories:** No migration needed — new in v2.

Write a one-time migration script (`infra/scripts/migrate-v1.ts`) that:
- Reads v1 SQLite DB
- Inserts into v2 schema via Drizzle
- Copies audio files
- Validates record counts match

---

## Shared Types Package (`@yoto/shared`)

### Core Schemas (Zod)

```typescript
// Card schema — matches Yoto API exactly
// Ref: Interactive Cards API § Complete Card Payload Schema
export const CardSchema = z.object({
  cardId: z.string().optional(),
  title: z.string().min(1).max(100),
  metadata: CardMetadataSchema,
  content: CardContentSchema,
})

// Event schema — the interactive navigation system
// Ref: Interactive Cards API § Events
export const TrackEventSchema = z.discriminatedUnion('cmd', [
  z.object({ cmd: z.literal('stop') }),
  z.object({ cmd: z.literal('repeat') }),
  z.object({ cmd: z.literal('goto'), params: z.object({
    chapterKey: z.string(),
    trackKey: z.string(),
  })}),
])

// Story graph schema — React Flow serialization
export const StoryGraphSchema = z.object({
  nodes: z.array(StoryNodeSchema),
  edges: z.array(StoryEdgeSchema),
  viewport: ViewportSchema.optional(),
})
```

### Type Exports
All Zod schemas export inferred types:
```typescript
export type Card = z.infer<typeof CardSchema>
export type TrackEvent = z.infer<typeof TrackEventSchema>
export type StoryGraph = z.infer<typeof StoryGraphSchema>
```

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Yoto API changes without notice | High — breaks card creation | Zod runtime validation catches mismatches early; version-pin User-Agent header |
| mDNS unreliable on Yoto Player | Medium — LAN streaming fails | Use IP addresses or proper hostnames for streaming URLs; mDNS only for browser discovery |
| React Flow performance with large story graphs (200+ nodes) | Medium — editor lag | Virtualization built into React Flow; lazy render off-screen nodes |
| FFmpeg child process management | Medium — zombie processes | Proper signal handling, timeout enforcement, process group cleanup |
| SQLite concurrent write contention | Low — WAL mode handles this | WAL mode + single-writer pattern (Engine owns DB exclusively) |
| BullMQ requires Redis | Medium — adds infrastructure | Use BullMQ with in-memory adapter for dev; Redis only for production multi-instance |

---

## Beads to File for Implementation

Once this plan is approved, file the following beads with dependency chains:

```
Phase 0: yo-scaffold     "Scaffold pnpm monorepo with Turborepo, Docker Compose, shared types"
Phase 1A: yo-engine-db   "Engine: Drizzle schema + config + migrations" → depends on yo-scaffold
Phase 1B: yo-engine-auth "Engine: OAuth device code flow + local user auth" → depends on yo-engine-db
Phase 1C: yo-engine-yoto "Engine: Type-safe Yoto API client" → depends on yo-engine-auth
Phase 1D: yo-engine-mqtt "Engine: MQTT client + event store + player control" → depends on yo-engine-yoto
Phase 1E: yo-engine-lib  "Engine: Library sync + card CRUD + playlists" → depends on yo-engine-yoto
Phase 1F: yo-engine-strm "Engine: Stream queues + audio serving + storage" → depends on yo-engine-db
Phase 1G: yo-engine-admin "Engine: Admin + settings + health + cover images" → depends on yo-engine-db
Phase 2A: yo-media-ffmpeg "Media Pipeline: FFmpeg integration" → depends on yo-scaffold
Phase 2B: yo-media-tts   "Media Pipeline: TTS providers" → depends on yo-scaffold
Phase 2C: yo-media-stt   "Media Pipeline: Transcription service" → depends on yo-scaffold
Phase 2D: yo-media-stitch "Media Pipeline: Stitching + BullMQ jobs" → depends on yo-media-ffmpeg
Phase 2E: yo-media-images "Media Pipeline: Cover image processing" → depends on yo-scaffold
Phase 3A: yo-studio-shell "Studio: App shell + auth + API client" → depends on yo-engine-auth
Phase 3B: yo-studio-lib   "Studio: Library view + player control" → depends on yo-studio-shell
Phase 3C: yo-studio-audio "Studio: Audio management + upload + TTS" → depends on yo-studio-shell
Phase 3D: yo-studio-graph "Studio: Story graph editor (React Flow)" → depends on yo-studio-shell
Phase 3E: yo-studio-adv   "Studio: Advanced editor (recording, preview, stats)" → depends on yo-studio-graph
Phase 3F: yo-studio-cards "Studio: Card producer + publish flow" → depends on yo-studio-lib
Phase 3G: yo-studio-admin "Studio: Admin panel" → depends on yo-studio-shell
Phase 4A: yo-docker       "Docker multi-stage builds + compose" → depends on any service
Phase 4B: yo-mdns         "mDNS registration (Avahi sidecar)" → depends on yo-docker
Phase 4C: yo-mcp-ts       "MCP server TypeScript port" → depends on yo-engine-lib
Phase 4D: yo-testing      "Test infrastructure + CI" → depends on all phases
```

---

*End of implementation plan. Ready for overseer review.*
