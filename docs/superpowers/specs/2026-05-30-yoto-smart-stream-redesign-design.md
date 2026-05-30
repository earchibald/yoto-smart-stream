# Yoto Smart Stream — Redesign Design

**Date:** 2026-05-30
**Status:** Approved (design); pending spec review → implementation plan
**Supersedes:** `docs/specs/2026-03-21-implementation-plan.md` (the 3-service TypeScript monorepo v2 plan — see "Why not the existing v2 plan")

---

## 1. Context

`yoto-smart-stream` is a working Python/FastAPI app that integrates with Yoto smart speakers: OAuth, streaming your own audio to players, MQTT monitoring/control, card creation, interactive "Choose Your Own Adventure" cards, a TTS/transcription/stitching audio pipeline, a Jinja+vanilla-JS web UI, a PWA, and an MCP server. It deploys on Railway with MySQL/SQLite + S3-compatible storage.

It was an early agentic-coding project and accumulated **sprawl**, not bad ideas: ~24 root-level AI "delivery summary" markdown files, monolithic route files (`cards.py` 1,981 lines, `streams.py` 1,084 lines), global state instead of DI, a hardcoded `SECRET_KEY`, manual SQL migrations, duplicated tests (root + `tests/` + `mcp-server/`), committed `.backup` files, and a UI that **rebuilds features Yoto's own app already provides**.

The integration code itself is good — a prior audit (`docs/CODEBASE_AUDIT.md`) flagged `core/yoto_client.py`, `api/mqtt_event_store.py`, `api/stream_manager.py`, and `storage/` as genuinely solid and worth preserving.

## 2. Goals

A **personal-scale** (me + my family) tool that:

1. **Nails interactive-story authoring** — a visual editor for branching, button-driven Yoto cards. This is the crown jewel and the thing Yoto offers no way to do.
2. **Streams my own audio** to Yoto players reliably, including dynamic/updatable content.
3. **Stays clean and maintainable** — small, well-bounded modules I can understand and extend without it sprawling again.

### Guiding principle (the lesson from v1)

> **Build only what Yoto does not provide. Do not rebuild what the Yoto app or API already does well.**

This is the central design constraint and the reason the redesign is ~60–70% smaller than v1.

## 3. Scope

### ✅ Build — the gap only this tool can fill

| Capability | Why Yoto can't do it |
|---|---|
| **Visual interactive-story (CYOA) editor** ⭐ | The API supports `events` (`onLhb`/`onRhb`/`onEnd` → `goto`/`stop`/`repeat`) but the consumer app has no branching-story authoring. |
| **In-browser story preview** | Simulate left/right button presses and play attached audio without touching a real card — fast iteration, no wasted card creations. |
| **Stream from this server** | App only supports *uploading* into Yoto. `type:"stream"` + your URL is API-only; enables no size limits + updatable content. |
| **Dynamic audio behind a stable URL** | Time-of-day / per-player / rotating content. The app has no such concept. |
| **TTS → story node** | Type text → generate narration → attach to a node. The app can't synthesize speech. |
| **Audio-hosting endpoint** | Range-request file serving the player fetches. Pure infrastructure. |
| **MQTT monitoring (read-only)** | Observe button/playback events to understand how a story is actually played, to iterate. |

### ❌ Do not build — the Yoto app already does these (cut from v1)

- Library browser / card grid / search
- Player control panel (play/pause/volume/skip) & device-status dashboards
- Cover-art galleries & icon-catalog browsing (call Yoto's image/icon endpoints at publish time; no management UI)
- Generic "upload file → plain MYO card" flows
- Transcription (Whisper/scribe), PWA, dark mode, mobile polish
- Multi-user / RBAC / billing (single-household tool)

### Decisions locked during brainstorming

- **Audience:** just me / my family.
- **Architecture:** single FastAPI service serving a React SPA (Approach A). Reuse the good Python integration code; put the new effort into the editor.
- **Audio hosting:** **stream from this tool** is the default and primary path.
- **MQTT:** **monitoring only** — read-only event capture for analytics. No control UI.
- **Stack:** Python (FastAPI) backend + React (Vite) + React Flow frontend. SQLite. No Redis/BullMQ/MySQL/microservices/mDNS.

## 4. Architecture

A **single FastAPI process** that serves both the JSON API and the built React SPA as static files. One deployable, one SQLite file, one set of env vars.

```
┌──────────────────────────────────────────────┐
│  Single FastAPI service (1 process)           │
│                                                │
│  React + Vite SPA ──build──▶ /static          │
│   • Story editor (React Flow)  ⭐             │
│   • In-browser preview/simulator              │
│   • TTS / audio attach UI                     │
│   • MQTT analytics view (read-only)           │
│        │ typed client (generated from OpenAPI) │
│  ┌─────┴──────────────────────────────────┐  │
│  │ routes (thin)                           │  │
│  │ services:                               │  │
│  │   yoto_auth · yoto_api · stories ·      │  │
│  │   cards(publish) · audio · tts ·        │  │
│  │   storage · jobs · mqtt_monitor         │  │
│  └─────┬───────────────────────────────────┘  │
│   SQLite (WAL)   ·   local FS storage (S3 opt) │
│   in-proc job table + asyncio worker (no Redis)│
└──────────────────────────────────────────────┘
   Yoto player ──HTTPS GET──▶ /stream/...mp3
   Deploy: 1 Railway service  /  1 Docker  /  Raspberry Pi
```

**Boundaries:** routes are thin (validate input, call a service, shape the response). Services own business logic and are independently testable. No global mutable state — dependencies are passed in (FastAPI `Depends`) or held on the app instance, not module globals.

### Repo / module structure

A clean rebuild **in-place on a new branch**, new source tree, cruft deleted, git history kept.

```
yoto_smart_stream/
├── app.py                  # FastAPI app factory + lifespan (small)
├── config.py               # pydantic-settings; keep v1's Railway-aware logic
├── db/
│   ├── models.py           # SQLAlchemy models
│   ├── session.py          # engine/session, WAL pragma
│   └── migrations/         # Alembic
├── schemas/                # Pydantic request/response + the Yoto card schema
│   ├── story.py            # graph nodes/edges
│   ├── card.py             # Yoto /content payload models
│   └── ...
├── services/
│   ├── yoto_auth.py        # OAuth device flow + token lifecycle (port from v1)
│   ├── yoto_api.py         # typed Yoto REST client (port + tighten v1 client)
│   ├── stories.py          # story CRUD + graph→card serialization + validation
│   ├── cards.py            # publish/update/delete on Yoto via yoto_api
│   ├── audio.py            # asset CRUD, range-serving
│   ├── tts.py              # TTS provider(s)
│   ├── storage.py          # local FS + optional S3 (port v1 storage interface)
│   ├── jobs.py             # SQLite-backed job queue + asyncio worker
│   └── mqtt_monitor.py     # read-only MQTT subscriber → event_log
├── api/routes/
│   ├── auth.py  stories.py  audio.py  cards.py  stream.py  analytics.py  health.py
└── static/                 # built React bundle (output of frontend build)

frontend/                   # Vite + React + React Flow (separate build, baked into static/)
├── src/
│   ├── editor/             # React Flow canvas, node types, inspector
│   ├── preview/            # in-browser story simulator
│   ├── api/                # typed client generated from FastAPI OpenAPI
│   └── ...
```

## 5. Data model

Slim. SQLite with WAL.

- **user** — single admin for login (username, argon2 hash, is_admin). Yoto OAuth tokens stored here (`yoto_access_token`, `yoto_refresh_token`, `yoto_token_expires_at`). Multi-user is out of scope but the table stays so auth isn't special-cased.
- **story** — the unit of work. `id`, `title`, `metadata` (author/description/age/category), `graph` (JSON: React Flow nodes + edges), `hosting_mode` (`stream` default), `yoto_card_id` (nullable, set on publish), `status` (draft/published), timestamps.
- **audio_asset** — `id`, `filename`, `source` (`upload`/`tts`/`recording`), `duration`, `size`, `format`, optional `story_id` + `node_id` link, TTS metadata (`tts_provider`, `tts_voice_id`, `tts_model`), timestamps.
- **job** — background work. `id`, `type` (`tts`/`stitch`/`publish`/`yoto_upload`), `status` (pending/running/done/error/cancelled), `payload` (JSON), `progress`, `error`, `result` (JSON), timestamps.
- **event_log** — captured MQTT events for analytics. `id`, `device_id`, `topic`, `event_type`, `payload` (JSON), `received_at`. Capped retention (configurable; default 30 days).
- **setting** — key/value with env-override precedence (port v1's 3-tier toggle: env > DB > default).

## 6. Interactive story editor (crown jewel)

### Graph model (what the user manipulates)

A **node = a chapter** in the Yoto card. An **edge = a `goto` event**. Node types:

- **Segment node** — one or more audio tracks (narration). Has an `onEnd` behavior: `next` (goto a single outgoing edge), `stop`, or `repeat`.
- **Choice node** — a Segment whose audio narrates a choice, with two outgoing edges: **left** (`onLhb` → goto) and **right** (`onRhb` → goto). `onEnd` is `stop` (player waits for a button).
- **Ending node** — terminal; `onEnd: stop`, optional "press a button to restart" edge back to start.

Each node carries: title, attached audio (upload / pick existing / generate via TTS), and (for choice nodes) the left/right prompt mapping. The inspector panel edits the selected node.

### Serialization: graph → Yoto `/content` payload

Deterministic and lossless.

- `content.playbackType = "interactive"`, `config = { autoadvance:"none", disableTrackNav:true, disableChapterNav:true, onlineOnly:true, resumeTimeout:2592000 }`, `editSettings.interactiveContent = true`. (Per `docs/INTERACTIVE_CARDS_API_REFERENCE.md` — these are mandatory or events are ignored.)
- Each node → one chapter; `chapterKey`/`trackKey` derived stably from node id (simple slugs, validated unique).
- Multi-track segment → multiple tracks in the chapter; events live only on the **last** track (earlier tracks auto-advance within the chapter).
- Edges → `events` on the relevant track: `onEnd`→goto next, `onLhb`→goto left target, `onRhb`→goto right target; `stop`/`repeat` where set.
- Track `type:"stream"` + `trackUrl` = this server's `/stream/{story}/{node}.mp3` (stream mode). `format:"mp3"`.
- Path convergence (multiple edges into one node) and loops (`repeat` / goto self) are supported because they're just edges.

### Validation (before publish)

- All `goto` targets resolve to existing nodes (a typo silently fails on-device — must catch here).
- No orphan nodes; every choice node has both left and right targets (or an explicit warning to proceed).
- At least one reachable ending / `stop`.
- Keys unique; every node has at least one audio track.

### In-browser preview/simulator

Pure client-side: walk the graph from the start node, play each node's attached audio in the browser, surface **Left / Right** buttons at choice nodes, follow `goto`. No Yoto round-trip, no card creation burned. This is the core iteration loop.

### Publish

Serialize → validate → `POST /content` (create if no `yoto_card_id`, else update). Store the returned `cardId` on the story. Idempotent re-publish. Cover art and chapter icons: optionally selected from Yoto's catalog/endpoints at publish time (call Yoto, don't build a gallery).

## 7. Streaming + dynamic content

- `GET /stream/{story_id}/{node_id}.mp3` — serves the node's audio with `Accept-Ranges: bytes`, correct `Content-Type`, range support (port v1's working file-serving). HTTPS via the deploy platform (Railway/own domain). `.local`/mDNS explicitly **not** used — unreliable for the player (per API docs).
- **Dynamic nodes:** a node can be marked dynamic with a simple rule (time-of-day / round-robin / per-player), and the server selects the underlying file at request time behind the stable URL. v1 had ad-hoc versions of this; here it's a first-class, declared node property.
- Storage: local filesystem by default (Railway volume / Pi disk), S3-compatible optional (port v1's storage interface).

## 8. Background jobs (no Redis)

A **SQLite-backed `job` table** + a single asyncio worker task started in the app lifespan. Handles TTS generation, audio stitching (FFmpeg via subprocess), and the multi-step Yoto upload/transcode-poll flow. Durable: on startup, requeue `pending`/`running` jobs. Progress and cancellation via the `job` row, polled by the UI. This replaces v1's in-memory task dicts and the v2 plan's BullMQ+Redis with something appropriate to single-household scale.

## 9. MQTT monitoring (read-only)

`mqtt_monitor` connects to `mqtt.yoto.io:8883`, subscribes to device status/events, and writes to `event_log` (capped retention). One **analytics view** in the UI: per-story, correlate button-press/playback events (reuse v1's `mqtt_event_store` correlation idea) to see which paths were taken — directly serving "understand how it's actually played so I can iterate." **No publishing / no control endpoints.** Reconnect with backoff; failure is non-fatal (analytics is best-effort).

## 10. Yoto integration

- **Auth:** OAuth2 device-code flow (RFC 8628) against `login.yotoplay.com`; persist + auto-refresh tokens (port v1's working flow; **fix** the hardcoded secret — JWT secret from `JWT_SECRET`, startup fails if missing).
- **API client (`yoto_api`):** typed wrapper over the endpoints actually needed — `POST /content` (create/update), `GET /content/{id}`, `DELETE /content/{id}`, media/icon upload at publish time, device list for the analytics correlation. Validate responses with Pydantic; surface clear errors on schema drift.

## 11. Auth & config

- Single-user login: admin from env (`ADMIN_USERNAME`/`ADMIN_PASSWORD`), argon2 hashing, JWT in an httpOnly/secure/sameSite cookie, secret from env.
- Config: `pydantic-settings`, keep v1's Railway-aware path/DB detection. Document every env var in `.env.example`.
- Remove v1's `/user/debug` endpoint and any debug leaks.

## 12. Deployment

One container image (multi-stage: build React → copy into `static/` → Python runtime with FFmpeg). Runs as a single process via `uvicorn`. Targets, in order of likely use: **Railway** (current), **Docker on a home server / Raspberry Pi**, or local. SQLite on a persistent volume. No multi-service orchestration.

## 13. Testing

- **pytest** for services (the valuable layer): graph→card serialization (golden-file the JSON against the API reference examples), validation rules, job lifecycle, audio range-serving, Yoto client against mocked responses.
- **Frontend:** Vitest for the serializer/preview logic; a couple of Playwright happy-path E2E (build a 3-node story → preview → publish against a mocked Yoto).
- Consolidate v1's scattered tests; delete dead/duplicated ones. Target meaningful coverage on serialization + validation (the parts where a bug silently breaks a card on-device).

## 14. Repo cleanup (part of the work)

- Delete ~24 root-level `.md` "delivery summary" files; keep only `README.md` + a real `docs/` set.
- Delete `.backup` files, duplicate root `test_*.py`, the empty `api/utils.py`, and `style-original-backup.css`.
- Remove PWA assets, dark-mode JS, Jinja templates, and the cut routes (`players`, `library`, `cover_images`, transcription).
- Consolidate `requirements`/`pyproject` into one source of truth.

## 15. MCP server disposition

The v1 MCP server (7 tools for AI-assistant access to the library) is **out of v1 scope** but not deleted — it's a "nice to have," not part of the authoring/streaming gap. Park it; revisit later. If kept, it should call this app's API rather than Yoto directly.

## 16. Migration from v1

Personal scale → no migration tooling. Practical steps: re-run the Yoto OAuth device flow once (tokens persist after), and optionally copy existing audio files into the new storage dir. Stories are new (v1 had no story graphs). No data-migration code to write or maintain.

## 17. Why not the existing v2 plan

`docs/specs/2026-03-21-implementation-plan.md` proposes a 3-service TypeScript monorepo (Engine/Studio/Media-Pipeline) with Turborepo, Drizzle, BullMQ+Redis, an Avahi mDNS sidecar, and per-service Dockerfiles. That is sound engineering for a **product**, but for a single household it's the same mistake as v1 in the opposite direction — operational complexity with no payoff. This redesign deliberately collapses it to one service, one DB file, one process, and reuses the working Python rather than rewriting fiddly OAuth/MQTT/FFmpeg code.

## 18. Risks

| Risk | Mitigation |
|---|---|
| `goto` key typos silently break a card on-device | Validate all targets resolve before publish; golden-file the serializer. |
| Streaming requires the server be up when a card plays | Document the trade-off; allow per-story upload-to-Yoto as an offline fallback later. |
| Yoto API drift | Validate responses with Pydantic; pin a User-Agent; fail loudly on mismatch. |
| Re-sprawl | Hard scope rule (build only the gap); thin routes + service boundaries; no global state. |
| FFmpeg subprocess zombies | Timeouts, process-group cleanup, cancellation via the job row. |

## 19. Out of scope (v1 of the redesign)

Multi-user/RBAC, billing, transcription, PWA/mobile, player control UI, library/device dashboards, cover-art/icon galleries, MCP server, server-side cross-session story state (stateful "remember choices" stories), community sharing.

## 20. Suggested build order (detail → implementation plan)

1. **Foundations** — clean repo, app factory, config, SQLite+Alembic, single-user auth, `.env.example`, CI.
2. **Yoto integration** — port `yoto_auth` + `yoto_api`; device-code login working end-to-end.
3. **Stories backend** — story CRUD, graph schema, **graph→card serializer + validation** (golden-tested), publish to Yoto.
4. **Audio + streaming** — asset CRUD, storage, `/stream/...mp3` range serving, dynamic nodes.
5. **Jobs + TTS** — SQLite job queue + worker; TTS provider; FFmpeg stitching.
6. **Frontend** — Vite/React shell + auth; **React Flow editor + inspector**; **in-browser preview**; publish UI; TTS/attach UI.
7. **MQTT analytics** — read-only subscriber + event_log + per-story analytics view.
8. **Polish** — deploy (Docker/Railway), tests, docs, delete v1 cruft.

The detailed, dependency-ordered implementation plan follows from this spec via the writing-plans step.
