# Foundations + Story Domain Core — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish a clean foundation for the Yoto Smart Stream redesign and build the highest-risk piece — the story-graph → Yoto interactive-card serializer and its validator — as pure, golden-tested domain logic with no network dependency.

**Architecture:** A single FastAPI service (built in later plans). This plan delivers only the persistence layer (SQLite + SQLAlchemy 2.0 + Alembic), the Pydantic schemas for the story graph and the Yoto card payload, and the deterministic serializer/validator that converts one into the other. Everything here is unit-testable offline; correctness here is what makes cards actually work on-device.

**Tech Stack:** Python 3.11, Pydantic 2, SQLAlchemy 2.0, Alembic, pytest (`asyncio_mode=auto`), ruff.

**Spec:** `docs/superpowers/specs/2026-05-30-yoto-smart-stream-redesign-design.md` (§4 architecture, §5 data model, §6 editor/serializer, §14 cleanup)

---

## File Structure

This plan creates a new clean source tree **alongside** v1 code (v1 Python modules are retired in their respective later plans; only clearly-dead non-code cruft is deleted now). New files:

- `yoto_smart_stream/db/__init__.py` — package marker
- `yoto_smart_stream/db/base.py` — SQLAlchemy `DeclarativeBase`
- `yoto_smart_stream/db/session.py` — engine factory (WAL), `sessionmaker`
- `yoto_smart_stream/db/models.py` — `Story` ORM model
- `yoto_smart_stream/schemas/__init__.py` — package marker
- `yoto_smart_stream/schemas/story.py` — `StoryGraph`, `StoryNode`, `StoryEdge`, `Track` (the editor's data model)
- `yoto_smart_stream/schemas/card.py` — `YotoCard`, `Chapter`, `CardTrack`, `TrackEvents` (the Yoto `/content` payload)
- `yoto_smart_stream/stories/__init__.py` — package marker
- `yoto_smart_stream/stories/keys.py` — node-id → unique chapter-key derivation
- `yoto_smart_stream/stories/validator.py` — `validate_graph(graph) -> list[str]`
- `yoto_smart_stream/stories/serializer.py` — `serialize_story(...) -> dict`
- `alembic.ini`, `alembic/env.py`, `alembic/versions/` — migrations
- `tests/stories/` — tests for the above

---

## Task 1: Delete dead cruft

Removes the ~24 root-level AI "delivery summary" docs, `.backup` files, and duplicate root-level test files (spec §14). These are non-code and deleting them cannot break imports. Port-worthy v1 Python modules are left untouched for later plans.

**Files:**
- Delete: root `*.md` except `README.md`; `*.backup` files; root `test_*.py`; `yoto_smart_stream/api/utils.py` (empty); `yoto_smart_stream/static/css/style-original-backup.css`; `yoto_smart_stream/static/js/audio-library.js.backup`

- [ ] **Step 1: Delete root-level summary docs (keep README.md)**

Run:
```bash
cd /Users/earchibald/Code/yoto-smart-stream
git rm -q COVER_ART_TEST_REPORT.md DELIVERY_SUMMARY.md DEPLOY_AND_TEST_INSTRUCTIONS.md \
  DEPLOY_TO_DEVELOPMENT.md DEPLOYMENT_NEXT_STEPS.md DEPLOYMENT_TEST_PLAN.md \
  DUAL_MODE_PLAYLIST_COMPLETE.md GITHUB_SECRETS_SETUP.md INTERACTIVE_CARD_ANALYSIS.md \
  MCP_COMPLETION_SUMMARY.md MCP_FASTMCP_MIGRATION.md MCP_IMPLEMENTATION_COMPLETE.md \
  MCP_REFACTORING_GUIDE.md MCP_REFACTORING_SUMMARY.md MCP_SERVER_FIX.md \
  MCP_SERVER_IMPLEMENTATION.md PR_SUMMARY.md PWA_IMPLEMENTATION_SUMMARY.md \
  RAILWAY_PR_TEST_RESULTS.md TRANSCRIPTION_FIX_RELEASE.md UI_COMPONENTS.md \
  YOTO_API_REFERENCE.md YOTO_APP_URLS.md
```
Expected: each path staged for deletion, no errors.

- [ ] **Step 2: Delete backup files and duplicate root tests**

Run:
```bash
git rm -q yoto_smart_stream/api/utils.py \
  yoto_smart_stream/static/css/style-original-backup.css \
  yoto_smart_stream/static/js/audio-library.js.backup \
  test_api_integration.py test_env_override.py test_mcp_comprehensive.py \
  test_mcp_startup.py test_mcp_structure.py test_mcp_tools.py \
  test_oauth_status_field.py test_settings.py
```
Expected: staged for deletion, no errors.

- [ ] **Step 3: Verify the test suite still collects**

Run: `python -m pytest --co -q tests/ 2>&1 | tail -5`
Expected: collection succeeds (some v1 tests may import retired-but-still-present modules; that is fine — no collection error referencing the deleted files).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: delete v1 delivery-summary cruft, backups, and duplicate root tests"
```

---

## Task 2: Add dependencies and create the new package skeleton

Bumps Python to 3.11, adds Alembic, and creates the empty packages the rest of the plan fills in.

**Files:**
- Modify: `pyproject.toml`
- Create: `yoto_smart_stream/db/__init__.py`, `yoto_smart_stream/schemas/__init__.py`, `yoto_smart_stream/stories/__init__.py`, `tests/stories/__init__.py`

- [ ] **Step 1: Bump Python and ruff target in `pyproject.toml`**

`alembic>=1.12.0` is already in `[project].dependencies` — no need to add it. In `pyproject.toml`, change `requires-python = ">=3.9"` to:
```toml
requires-python = ">=3.11"
```
In `[tool.ruff]` change `target-version = "py39"` to `target-version = "py311"`. (Optionally also update `[tool.black].target-version` and `[tool.mypy].python_version` to match, but that is not required for this plan.)

- [ ] **Step 2: Create the empty package markers**

```bash
mkdir -p yoto_smart_stream/db yoto_smart_stream/schemas yoto_smart_stream/stories tests/stories
printf '"""Persistence layer (SQLAlchemy 2.0)."""\n' > yoto_smart_stream/db/__init__.py
printf '"""Pydantic schemas: story graph and Yoto card payloads."""\n' > yoto_smart_stream/schemas/__init__.py
printf '"""Story domain: keys, validation, serialization to Yoto cards."""\n' > yoto_smart_stream/stories/__init__.py
printf '' > tests/stories/__init__.py
```

- [ ] **Step 3: Install and verify**

Run: `pip install -e ".[dev]" && python -c "import alembic; print(alembic.__version__)"`
Expected: prints an Alembic version ≥ 1.13.

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml yoto_smart_stream/db yoto_smart_stream/schemas yoto_smart_stream/stories tests/stories
git commit -m "build: add alembic, bump to py311, scaffold db/schemas/stories packages"
```

---

## Task 3: Database base + session (WAL)

**Files:**
- Create: `yoto_smart_stream/db/base.py`
- Create: `yoto_smart_stream/db/session.py`
- Test: `tests/stories/test_session.py`

- [ ] **Step 1: Write the failing test**

Create `tests/stories/test_session.py`:
```python
from sqlalchemy import text

from yoto_smart_stream.db.session import make_engine


def test_make_engine_enables_wal(tmp_path):
    db_path = tmp_path / "test.db"
    engine = make_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        mode = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert mode.lower() == "wal"


def test_make_engine_memory_is_usable():
    engine = make_engine("sqlite://")
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/stories/test_session.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yoto_smart_stream.db.session'`.

- [ ] **Step 3: Write `db/base.py`**

Create `yoto_smart_stream/db/base.py`:
```python
"""Declarative base for all ORM models."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class all ORM models inherit from."""
```

- [ ] **Step 4: Write `db/session.py`**

Create `yoto_smart_stream/db/session.py`:
```python
"""SQLite engine factory (WAL) and session maker."""
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def make_engine(url: str) -> Engine:
    """Create a SQLite engine with WAL journaling and foreign keys on.

    A file-backed SQLite database gets WAL mode for better read/write
    concurrency. In-memory databases (``sqlite://``) do not support WAL and
    are left at their default journal mode.
    """
    engine = create_engine(url, future=True)
    is_memory = url in ("sqlite://", "sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        if not is_memory:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a configured session factory bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/stories/test_session.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Commit**

```bash
git add yoto_smart_stream/db/base.py yoto_smart_stream/db/session.py tests/stories/test_session.py
git commit -m "feat(db): add declarative base and WAL-enabled sqlite engine factory"
```

---

## Task 4: `Story` ORM model

Stores the editor graph as JSON plus publish state (spec §5).

**Files:**
- Create: `yoto_smart_stream/db/models.py`
- Test: `tests/stories/test_models.py`

- [ ] **Step 1: Write the failing test**

Create `tests/stories/test_models.py`:
```python
from yoto_smart_stream.db.base import Base
from yoto_smart_stream.db.models import Story
from yoto_smart_stream.db.session import make_engine, make_session_factory


def _session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)()


def test_story_roundtrip_persists_graph_json():
    session = _session()
    story = Story(
        title="Adventure",
        graph={"start_node_id": "intro", "nodes": [], "edges": []},
        hosting_mode="stream",
    )
    session.add(story)
    session.commit()

    loaded = session.query(Story).one()
    assert loaded.id is not None
    assert loaded.title == "Adventure"
    assert loaded.graph["start_node_id"] == "intro"
    assert loaded.hosting_mode == "stream"
    assert loaded.status == "draft"
    assert loaded.yoto_card_id is None
    assert loaded.created_at is not None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/stories/test_models.py -v`
Expected: FAIL — `ImportError: cannot import name 'Story'`.

- [ ] **Step 3: Write `db/models.py`**

Create `yoto_smart_stream/db/models.py`:
```python
"""ORM models for the redesign. Story is the unit of authoring work."""
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yoto_smart_stream.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Story(Base):
    """An interactive story: its editor graph plus Yoto publish state."""

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # React Flow nodes/edges + start node, validated by schemas.story.StoryGraph.
    graph: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    hosting_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="stream")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    yoto_card_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/stories/test_models.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add yoto_smart_stream/db/models.py tests/stories/test_models.py
git commit -m "feat(db): add Story model (graph JSON + publish state)"
```

---

## Task 5: Alembic migrations

Replaces v1's manual SQL with version-controlled migrations (spec §1, §11).

**Files:**
- Create: `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/.gitkeep`
- Test: `tests/stories/test_migrations.py`

- [ ] **Step 1: Initialize Alembic**

Run: `python -m alembic init alembic`
Expected: creates `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako`, `alembic/versions/`.

- [ ] **Step 2: Point `alembic/env.py` at our metadata**

In `alembic/env.py`, replace the `target_metadata = None` line with:
```python
from yoto_smart_stream.db.base import Base
from yoto_smart_stream.db import models  # noqa: F401 — register models on Base.metadata

target_metadata = Base.metadata
```

- [ ] **Step 3: Set a default sqlite URL in `alembic.ini`**

In `alembic.ini`, set:
```ini
sqlalchemy.url = sqlite:///./yoto_smart_stream.db
```

- [ ] **Step 4: Autogenerate the first migration**

Run: `python -m alembic revision --autogenerate -m "create stories table"`
Expected: a new file under `alembic/versions/` whose `upgrade()` calls `op.create_table("stories", ...)` with the columns from Task 4.

- [ ] **Step 5: Write the migration test**

Create `tests/stories/test_migrations.py`:
```python
import subprocess
import sys
from sqlalchemy import create_engine, inspect


def test_migrations_create_stories_table(tmp_path):
    db = tmp_path / "m.db"
    url = f"sqlite:///{db}"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", f"url={url}", "upgrade", "head"],
        capture_output=True,
        text=True,
        env={"ALEMBIC_SQLALCHEMY_URL": url, "PATH": __import__("os").environ["PATH"]},
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(url)
    tables = inspect(engine).get_table_names()
    assert "stories" in tables
    cols = {c["name"] for c in inspect(engine).get_columns("stories")}
    assert {"id", "title", "graph", "hosting_mode", "status", "yoto_card_id"} <= cols
```

- [ ] **Step 6: Make `alembic/env.py` honor an override URL**

So the test can target a temp DB, in `alembic/env.py` add, immediately after `config = context.config`:
```python
import os

_override = context.get_x_argument(as_dictionary=True).get("url") or os.environ.get(
    "ALEMBIC_SQLALCHEMY_URL"
)
if _override:
    config.set_main_option("sqlalchemy.url", _override)
```

- [ ] **Step 7: Run the migration test**

Run: `python -m pytest tests/stories/test_migrations.py -v`
Expected: PASS — `stories` table created on the temp DB.

- [ ] **Step 8: Commit**

```bash
git add alembic.ini alembic/ tests/stories/test_migrations.py
git commit -m "feat(db): add alembic migrations with stories table"
```

---

## Task 6: Story graph schema (`schemas/story.py`)

The editor's data model: nodes, edges, tracks (spec §6). Validation here is structural (types/shapes); semantic validation is Task 9.

**Files:**
- Create: `yoto_smart_stream/schemas/story.py`
- Test: `tests/stories/test_schema_story.py`

- [ ] **Step 1: Write the failing test**

Create `tests/stories/test_schema_story.py`:
```python
import pytest
from pydantic import ValidationError

from yoto_smart_stream.schemas.story import (
    EdgeHandle,
    NodeType,
    OnEnd,
    StoryEdge,
    StoryGraph,
    StoryNode,
    Track,
)


def test_minimal_graph_parses():
    graph = StoryGraph(
        start_node_id="intro",
        nodes=[
            StoryNode(
                id="intro",
                type=NodeType.ending,
                title="Intro",
                tracks=[Track(key="t1", title="Intro audio")],
            )
        ],
        edges=[],
    )
    assert graph.start_node_id == "intro"
    assert graph.nodes[0].on_end == OnEnd.next  # default


def test_edge_handle_and_node_type_are_enums():
    edge = StoryEdge(id="e1", source="a", target="b", handle="left")
    assert edge.handle is EdgeHandle.left
    node = StoryNode(id="a", type="choice", title="A", tracks=[Track(key="k", title="x")])
    assert node.type is NodeType.choice


def test_unknown_node_type_rejected():
    with pytest.raises(ValidationError):
        StoryNode(id="a", type="banana", title="A", tracks=[Track(key="k", title="x")])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/stories/test_schema_story.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yoto_smart_stream.schemas.story'`.

- [ ] **Step 3: Write `schemas/story.py`**

Create `yoto_smart_stream/schemas/story.py`:
```python
"""The story-editor data model (what React Flow manipulates)."""
from enum import Enum

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    segment = "segment"  # linear audio; advances, stops, or repeats at end
    choice = "choice"  # narrates a choice; waits for a button press
    ending = "ending"  # terminal; stops (optional restart button)


class OnEnd(str, Enum):
    next = "next"  # follow the single "next" edge
    stop = "stop"
    repeat = "repeat"


class EdgeHandle(str, Enum):
    next = "next"  # sequential flow (onEnd -> goto)
    left = "left"  # left hardware button (onLhb -> goto)
    right = "right"  # right hardware button (onRhb -> goto)


class Track(BaseModel):
    """One audio segment within a node. URL is derived by the serializer."""

    key: str = Field(min_length=1)
    title: str = Field(min_length=1)
    audio_id: str | None = None  # links to an AudioAsset in a later plan


class StoryNode(BaseModel):
    id: str = Field(min_length=1)
    type: NodeType
    title: str = Field(min_length=1)
    tracks: list[Track] = Field(default_factory=list)
    on_end: OnEnd = OnEnd.next  # used for segment nodes; choice/ending force stop


class StoryEdge(BaseModel):
    id: str = Field(min_length=1)
    source: str = Field(min_length=1)  # node id
    target: str = Field(min_length=1)  # node id
    handle: EdgeHandle = EdgeHandle.next


class StoryGraph(BaseModel):
    start_node_id: str = Field(min_length=1)
    nodes: list[StoryNode] = Field(default_factory=list)
    edges: list[StoryEdge] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/stories/test_schema_story.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add yoto_smart_stream/schemas/story.py tests/stories/test_schema_story.py
git commit -m "feat(schemas): add story graph schema (nodes, edges, tracks)"
```

---

## Task 7: Yoto card schema (`schemas/card.py`)

Pydantic models mirroring the Yoto `/content` interactive-card payload (spec §6; `docs/INTERACTIVE_CARDS_API_REFERENCE.md`). These give the serializer a typed target and let tests assert structure.

**Files:**
- Create: `yoto_smart_stream/schemas/card.py`
- Test: `tests/stories/test_schema_card.py`

- [ ] **Step 1: Write the failing test**

Create `tests/stories/test_schema_card.py`:
```python
from yoto_smart_stream.schemas.card import (
    CardContent,
    CardTrack,
    Chapter,
    GotoCommand,
    StopCommand,
    TrackEvents,
    YotoCard,
)


def test_interactive_config_defaults_match_reference():
    content = CardContent(chapters=[])
    assert content.playbackType == "interactive"
    assert content.config.autoadvance == "none"
    assert content.config.disableTrackNav is True
    assert content.config.disableChapterNav is True
    assert content.config.onlineOnly is True
    assert content.editSettings.interactiveContent is True


def test_card_with_choice_track_serializes_events():
    track = CardTrack(
        key="t",
        title="Intro",
        trackUrl="https://x/y.mp3",
        events=TrackEvents(
            onEnd=StopCommand(),
            onLhb=GotoCommand(params={"chapterKey": "cave", "trackKey": "t"}),
        ),
    )
    card = YotoCard(
        title="Adventure",
        content=CardContent(chapters=[Chapter(key="intro", title="Intro", tracks=[track])]),
    )
    dumped = card.model_dump(exclude_none=True)
    ev = dumped["content"]["chapters"][0]["tracks"][0]["events"]
    assert ev["onEnd"] == {"cmd": "stop"}
    assert ev["onLhb"] == {"cmd": "goto", "params": {"chapterKey": "cave", "trackKey": "t"}}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/stories/test_schema_card.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yoto_smart_stream.schemas.card'`.

- [ ] **Step 3: Write `schemas/card.py`**

Create `yoto_smart_stream/schemas/card.py`:
```python
"""Pydantic models for the Yoto /content interactive-card payload.

Mirrors docs/INTERACTIVE_CARDS_API_REFERENCE.md. Mandatory interactive flags
(playbackType, config.autoadvance/disableTrackNav/disableChapterNav, onlineOnly,
editSettings.interactiveContent) default to the values required for events to fire.
"""
from typing import Literal

from pydantic import BaseModel, Field


class StopCommand(BaseModel):
    cmd: Literal["stop"] = "stop"


class RepeatCommand(BaseModel):
    cmd: Literal["repeat"] = "repeat"


class GotoCommand(BaseModel):
    cmd: Literal["goto"] = "goto"
    params: dict[str, str]  # {"chapterKey": "...", "trackKey": "..."}


Command = StopCommand | RepeatCommand | GotoCommand


class TrackEvents(BaseModel):
    onEnd: Command | None = None
    onLhb: Command | None = None
    onRhb: Command | None = None


class CardTrack(BaseModel):
    key: str
    title: str
    type: Literal["stream", "audio"] = "stream"
    format: str = "mp3"
    trackUrl: str
    events: TrackEvents | None = None


class Chapter(BaseModel):
    key: str
    title: str
    tracks: list[CardTrack]


class CardConfig(BaseModel):
    autoadvance: Literal["next", "repeat", "none"] = "none"
    disableTrackNav: bool = True
    disableChapterNav: bool = True
    resumeTimeout: int = 2592000
    onlineOnly: bool = True


class CardEditSettings(BaseModel):
    autoOverlayLabels: str = "chapters"
    editKeys: bool = False
    interactiveContent: bool = True


class CardContent(BaseModel):
    version: str = "1"
    activity: str = "yoto_Player"
    playbackType: Literal["interactive"] = "interactive"
    config: CardConfig = Field(default_factory=CardConfig)
    editSettings: CardEditSettings = Field(default_factory=CardEditSettings)
    chapters: list[Chapter]


class CardMetadata(BaseModel):
    description: str | None = None
    author: str | None = None
    category: str = "stories"


class YotoCard(BaseModel):
    cardId: str | None = None
    title: str = Field(min_length=1, max_length=100)
    metadata: CardMetadata = Field(default_factory=CardMetadata)
    content: CardContent
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/stories/test_schema_card.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add yoto_smart_stream/schemas/card.py tests/stories/test_schema_card.py
git commit -m "feat(schemas): add typed Yoto interactive-card payload schema"
```

---

## Task 8: Chapter-key derivation (`stories/keys.py`)

Deterministic, collision-free chapter keys from node ids (spec §6 — "keys derived stably from node id, validated unique"). A `goto` to a wrong key silently fails on-device, so this must be deterministic and unique.

**Files:**
- Create: `yoto_smart_stream/stories/keys.py`
- Test: `tests/stories/test_keys.py`

- [ ] **Step 1: Write the failing test**

Create `tests/stories/test_keys.py`:
```python
from yoto_smart_stream.schemas.story import NodeType, StoryNode, Track
from yoto_smart_stream.stories.keys import build_chapter_keys, slugify_key


def _node(node_id: str) -> StoryNode:
    return StoryNode(
        id=node_id, type=NodeType.ending, title="t", tracks=[Track(key="k", title="x")]
    )


def test_slugify_basic():
    assert slugify_key("The Cave!") == "the-cave"
    assert slugify_key("intro") == "intro"
    assert slugify_key("___") == "node"  # fallback when nothing survives


def test_build_chapter_keys_is_stable_and_unique():
    nodes = [_node("The Cave"), _node("the cave"), _node("forest")]
    keys = build_chapter_keys(nodes)
    assert keys["forest"] == "forest"
    # Two nodes slugify to "the-cave"; the second is disambiguated.
    assert keys["The Cave"] == "the-cave"
    assert keys["the cave"] == "the-cave-2"
    assert len(set(keys.values())) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/stories/test_keys.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yoto_smart_stream.stories.keys'`.

- [ ] **Step 3: Write `stories/keys.py`**

Create `yoto_smart_stream/stories/keys.py`:
```python
"""Deterministic chapter-key derivation from node ids."""
import re
from collections.abc import Sequence

from yoto_smart_stream.schemas.story import StoryNode

_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def slugify_key(node_id: str) -> str:
    """Lowercase, hyphenate, strip. Returns ``"node"`` if nothing survives."""
    slug = _NON_ALNUM.sub("-", node_id.lower()).strip("-")
    return slug or "node"


def build_chapter_keys(nodes: Sequence[StoryNode]) -> dict[str, str]:
    """Map each node id to a unique chapter key, preserving input order.

    Collisions get a ``-2``, ``-3`` … suffix in order of appearance.
    """
    keys: dict[str, str] = {}
    seen: dict[str, int] = {}
    for node in nodes:
        base = slugify_key(node.id)
        seen[base] = seen.get(base, 0) + 1
        keys[node.id] = base if seen[base] == 1 else f"{base}-{seen[base]}"
    return keys
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/stories/test_keys.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add yoto_smart_stream/stories/keys.py tests/stories/test_keys.py
git commit -m "feat(stories): deterministic unique chapter-key derivation"
```

---

## Task 9: Graph validator (`stories/validator.py`)

Catches the failure modes that break a card silently on-device (spec §6 "Validation"). Returns a list of human-readable errors (empty = valid).

**Files:**
- Create: `yoto_smart_stream/stories/validator.py`
- Test: `tests/stories/test_validator.py`

- [ ] **Step 1: Write the failing test**

Create `tests/stories/test_validator.py`:
```python
from yoto_smart_stream.schemas.story import (
    EdgeHandle,
    NodeType,
    OnEnd,
    StoryEdge,
    StoryGraph,
    StoryNode,
    Track,
)
from yoto_smart_stream.stories.validator import validate_graph


def _track(key="k"):
    return Track(key=key, title="x")


def _valid_graph() -> StoryGraph:
    return StoryGraph(
        start_node_id="intro",
        nodes=[
            StoryNode(id="intro", type=NodeType.choice, title="Intro", tracks=[_track()]),
            StoryNode(
                id="cave", type=NodeType.segment, title="Cave", tracks=[_track()],
                on_end=OnEnd.next,
            ),
            StoryNode(id="end", type=NodeType.ending, title="End", tracks=[_track()]),
        ],
        edges=[
            StoryEdge(id="e1", source="intro", target="cave", handle=EdgeHandle.left),
            StoryEdge(id="e2", source="intro", target="end", handle=EdgeHandle.right),
            StoryEdge(id="e3", source="cave", target="end", handle=EdgeHandle.next),
        ],
    )


def test_valid_graph_has_no_errors():
    assert validate_graph(_valid_graph()) == []


def test_missing_start_node_flagged():
    g = _valid_graph()
    g.start_node_id = "ghost"
    assert any("start node" in e.lower() for e in validate_graph(g))


def test_edge_to_unknown_node_flagged():
    g = _valid_graph()
    g.edges.append(StoryEdge(id="bad", source="cave", target="ghost"))
    assert any("ghost" in e for e in validate_graph(g))


def test_choice_without_both_buttons_flagged():
    g = _valid_graph()
    g.edges = [e for e in g.edges if e.id != "e2"]  # drop intro's right edge
    assert any("choice" in e.lower() and "intro" in e for e in validate_graph(g))


def test_segment_next_without_edge_flagged():
    g = _valid_graph()
    g.edges = [e for e in g.edges if e.id != "e3"]  # cave has on_end=next but no next edge
    assert any("cave" in e and "next" in e.lower() for e in validate_graph(g))


def test_node_without_track_flagged():
    g = _valid_graph()
    g.nodes[1].tracks = []
    assert any("cave" in e and "track" in e.lower() for e in validate_graph(g))


def test_duplicate_track_keys_flagged():
    g = _valid_graph()
    g.nodes[1].tracks = [_track("dup"), _track("dup")]
    assert any("cave" in e and "track key" in e.lower() for e in validate_graph(g))


def test_no_reachable_stop_flagged():
    g = StoryGraph(
        start_node_id="a",
        nodes=[
            StoryNode(id="a", type=NodeType.segment, title="A", tracks=[_track()], on_end=OnEnd.next),
        ],
        edges=[StoryEdge(id="loop", source="a", target="a", handle=EdgeHandle.next)],
    )
    assert any("stop" in e.lower() or "ending" in e.lower() for e in validate_graph(g))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/stories/test_validator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yoto_smart_stream.stories.validator'`.

- [ ] **Step 3: Write `stories/validator.py`**

Create `yoto_smart_stream/stories/validator.py`:
```python
"""Semantic validation of a story graph before serialization/publish.

Returns a list of human-readable error strings; empty means valid. These rules
catch mistakes that fail silently on the Yoto Player (e.g. a goto to a key that
does not exist).
"""
from yoto_smart_stream.schemas.story import (
    EdgeHandle,
    NodeType,
    OnEnd,
    StoryGraph,
    StoryNode,
)


def _outgoing(graph: StoryGraph, node_id: str, handle: EdgeHandle):
    return [e for e in graph.edges if e.source == node_id and e.handle == handle]


def _terminates(node: StoryNode) -> bool:
    return node.type is NodeType.ending or (
        node.type is NodeType.segment and node.on_end is OnEnd.stop
    )


def validate_graph(graph: StoryGraph) -> list[str]:
    errors: list[str] = []
    ids = [n.id for n in graph.nodes]
    id_set = set(ids)

    # Unique node ids.
    if len(ids) != len(id_set):
        errors.append("Node ids must be unique.")

    # Start node exists.
    if graph.start_node_id not in id_set:
        errors.append(f"Start node '{graph.start_node_id}' is not in the graph.")

    # Edge endpoints exist.
    for e in graph.edges:
        if e.source not in id_set:
            errors.append(f"Edge '{e.id}' has unknown source '{e.source}'.")
        if e.target not in id_set:
            errors.append(f"Edge '{e.id}' has unknown target '{e.target}'.")

    # Per-node structural rules.
    for n in graph.nodes:
        if not n.tracks:
            errors.append(f"Node '{n.id}' has no track.")
        track_keys = [t.key for t in n.tracks]
        if len(track_keys) != len(set(track_keys)):
            errors.append(f"Node '{n.id}' has duplicate track key.")

        if n.type is NodeType.choice:
            if not _outgoing(graph, n.id, EdgeHandle.left) or not _outgoing(
                graph, n.id, EdgeHandle.right
            ):
                errors.append(
                    f"Choice node '{n.id}' must have both a left and a right edge."
                )
        elif n.type is NodeType.segment and n.on_end is OnEnd.next:
            nexts = _outgoing(graph, n.id, EdgeHandle.next)
            if len(nexts) != 1:
                errors.append(
                    f"Segment node '{n.id}' with on_end=next needs exactly one next edge."
                )

    # At least one node terminates the story.
    if graph.nodes and not any(_terminates(n) for n in graph.nodes):
        errors.append("Story has no ending or stop — playback would never terminate.")

    return errors
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/stories/test_validator.py -v`
Expected: PASS (all eight cases).

- [ ] **Step 5: Commit**

```bash
git add yoto_smart_stream/stories/validator.py tests/stories/test_validator.py
git commit -m "feat(stories): graph validator catching silent on-device failures"
```

---

## Task 10: Graph → Yoto card serializer (`stories/serializer.py`)

The heart of the product (spec §6 "Serialization"). Converts a validated `StoryGraph` into a `YotoCard`. Golden-tested against a 4-node branching story.

**Files:**
- Create: `yoto_smart_stream/stories/serializer.py`
- Test: `tests/stories/test_serializer.py`

- [ ] **Step 1: Write the failing test**

Create `tests/stories/test_serializer.py`:
```python
from yoto_smart_stream.schemas.story import (
    EdgeHandle,
    NodeType,
    OnEnd,
    StoryEdge,
    StoryGraph,
    StoryNode,
    Track,
)
from yoto_smart_stream.stories.serializer import serialize_story


def _graph() -> StoryGraph:
    return StoryGraph(
        start_node_id="intro",
        nodes=[
            StoryNode(id="intro", type=NodeType.choice, title="Introduction",
                      tracks=[Track(key="a", title="Introduction")]),
            StoryNode(id="cave", type=NodeType.segment, title="The Cave",
                      tracks=[Track(key="a", title="The Cave")], on_end=OnEnd.next),
            StoryNode(id="forest", type=NodeType.segment, title="The Forest",
                      tracks=[Track(key="a", title="The Forest")], on_end=OnEnd.next),
            StoryNode(id="ending", type=NodeType.ending, title="The End",
                      tracks=[Track(key="a", title="The End")]),
        ],
        edges=[
            StoryEdge(id="e1", source="intro", target="cave", handle=EdgeHandle.left),
            StoryEdge(id="e2", source="intro", target="forest", handle=EdgeHandle.right),
            StoryEdge(id="e3", source="cave", target="ending", handle=EdgeHandle.next),
            StoryEdge(id="e4", source="forest", target="ending", handle=EdgeHandle.next),
        ],
    )


def test_serialize_produces_interactive_card():
    card = serialize_story(_graph(), story_id=7, base_url="https://srv", title="Choose Your Adventure")
    d = card.model_dump(exclude_none=True)

    assert d["title"] == "Choose Your Adventure"
    assert d["content"]["playbackType"] == "interactive"
    assert d["content"]["config"]["autoadvance"] == "none"
    assert d["content"]["config"]["onlineOnly"] is True

    chapters = {c["key"]: c for c in d["content"]["chapters"]}
    assert set(chapters) == {"intro", "cave", "forest", "ending"}

    # Stream URL derived from base_url + story id + node + track key.
    assert chapters["intro"]["tracks"][0]["trackUrl"] == "https://srv/stream/7/intro/a.mp3"
    assert chapters["intro"]["tracks"][0]["type"] == "stream"

    # Choice node: waits then branches on buttons.
    intro_ev = chapters["intro"]["tracks"][0]["events"]
    assert intro_ev["onEnd"] == {"cmd": "stop"}
    assert intro_ev["onLhb"] == {"cmd": "goto", "params": {"chapterKey": "cave", "trackKey": "a"}}
    assert intro_ev["onRhb"] == {"cmd": "goto", "params": {"chapterKey": "forest", "trackKey": "a"}}

    # Segment node: auto-advances on end.
    assert chapters["cave"]["tracks"][0]["events"]["onEnd"] == {
        "cmd": "goto", "params": {"chapterKey": "ending", "trackKey": "a"}
    }

    # Ending node: stops.
    assert chapters["ending"]["tracks"][0]["events"]["onEnd"] == {"cmd": "stop"}


def test_multitrack_events_only_on_last_track():
    graph = StoryGraph(
        start_node_id="scene",
        nodes=[
            StoryNode(id="scene", type=NodeType.segment, title="Scene",
                      tracks=[Track(key="narr", title="Narration"), Track(key="choice", title="Choice")],
                      on_end=OnEnd.stop),
        ],
        edges=[],
    )
    card = serialize_story(graph, story_id=1, base_url="https://s", title="T")
    tracks = card.model_dump(exclude_none=True)["content"]["chapters"][0]["tracks"]
    assert "events" not in tracks[0]  # first track has none
    assert tracks[1]["events"]["onEnd"] == {"cmd": "stop"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/stories/test_serializer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'yoto_smart_stream.stories.serializer'`.

- [ ] **Step 3: Write `stories/serializer.py`**

Create `yoto_smart_stream/stories/serializer.py`:
```python
"""Convert a StoryGraph into a Yoto interactive-card payload.

One node -> one chapter; events live on the chapter's last track. Stream URLs
are derived as ``{base_url}/stream/{story_id}/{node_id}/{track_key}.mp3``.
"""
from yoto_smart_stream.schemas.card import (
    CardContent,
    CardMetadata,
    CardTrack,
    Chapter,
    GotoCommand,
    RepeatCommand,
    StopCommand,
    TrackEvents,
    YotoCard,
)
from yoto_smart_stream.schemas.story import (
    EdgeHandle,
    NodeType,
    OnEnd,
    StoryGraph,
    StoryNode,
)
from yoto_smart_stream.stories.keys import build_chapter_keys


def serialize_story(
    graph: StoryGraph,
    *,
    story_id: int,
    base_url: str,
    title: str,
    description: str | None = None,
    author: str | None = None,
) -> YotoCard:
    chapter_keys = build_chapter_keys(graph.nodes)
    nodes_by_id = {n.id: n for n in graph.nodes}

    def goto(target_node_id: str) -> GotoCommand:
        target = nodes_by_id[target_node_id]
        return GotoCommand(
            params={
                "chapterKey": chapter_keys[target_node_id],
                "trackKey": target.tracks[0].key,
            }
        )

    def first_edge_target(node_id: str, handle: EdgeHandle) -> str | None:
        for e in graph.edges:
            if e.source == node_id and e.handle == handle:
                return e.target
        return None

    def events_for(node: StoryNode) -> TrackEvents | None:
        if node.type is NodeType.choice:
            left = first_edge_target(node.id, EdgeHandle.left)
            right = first_edge_target(node.id, EdgeHandle.right)
            return TrackEvents(
                onEnd=StopCommand(),
                onLhb=goto(left) if left else None,
                onRhb=goto(right) if right else None,
            )
        if node.type is NodeType.ending:
            left = first_edge_target(node.id, EdgeHandle.left)
            right = first_edge_target(node.id, EdgeHandle.right)
            return TrackEvents(
                onEnd=StopCommand(),
                onLhb=goto(left) if left else None,
                onRhb=goto(right) if right else None,
            )
        # segment
        if node.on_end is OnEnd.stop:
            return TrackEvents(onEnd=StopCommand())
        if node.on_end is OnEnd.repeat:
            return TrackEvents(onEnd=RepeatCommand())
        nxt = first_edge_target(node.id, EdgeHandle.next)
        return TrackEvents(onEnd=goto(nxt)) if nxt else None

    chapters: list[Chapter] = []
    for node in graph.nodes:
        ckey = chapter_keys[node.id]
        card_tracks: list[CardTrack] = []
        for i, t in enumerate(node.tracks):
            is_last = i == len(node.tracks) - 1
            card_tracks.append(
                CardTrack(
                    key=t.key,
                    title=t.title,
                    type="stream",
                    format="mp3",
                    trackUrl=f"{base_url}/stream/{story_id}/{node.id}/{t.key}.mp3",
                    events=events_for(node) if is_last else None,
                )
            )
        chapters.append(Chapter(key=ckey, title=node.title, tracks=card_tracks))

    return YotoCard(
        title=title,
        metadata=CardMetadata(description=description, author=author),
        content=CardContent(chapters=chapters),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/stories/test_serializer.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Run the whole story suite + ruff**

Run: `python -m pytest tests/stories/ -v && ruff check yoto_smart_stream/db yoto_smart_stream/schemas yoto_smart_stream/stories`
Expected: all green, ruff clean.

- [ ] **Step 6: Commit**

```bash
git add yoto_smart_stream/stories/serializer.py tests/stories/test_serializer.py
git commit -m "feat(stories): graph->Yoto interactive-card serializer (golden-tested)"
```

---

## Self-Review

**Spec coverage (this plan's slice):**
- §5 data model → `Story` model (Task 4); other tables (audio_asset, job, event_log, setting, user) belong to later plans — intentional.
- §6 serializer/validator/keys → Tasks 8–10; mandatory interactive config flags → Task 7.
- §11 real migrations → Task 5 (Alembic, replacing v1 manual SQL).
- §14 cruft deletion → Task 1 (non-code cruft; v1 Python module removal deferred to the plans that replace each module).
- In-browser preview, HTTP API, Yoto auth/publish, audio/streaming, jobs/TTS, frontend, MQTT → **out of scope for Plan 1**, covered by Plans 2–6.

**Placeholder scan:** none — every code/test step contains complete code and exact commands.

**Type consistency:** `StoryGraph/StoryNode/StoryEdge/Track/NodeType/OnEnd/EdgeHandle` defined in Task 6 are used unchanged in Tasks 8–10. `YotoCard/CardContent/Chapter/CardTrack/TrackEvents/GotoCommand/StopCommand/RepeatCommand` defined in Task 7 are the exact symbols the serializer imports in Task 10. `build_chapter_keys`/`slugify_key` (Task 8) and `validate_graph` (Task 9) signatures match their call sites. `make_engine`/`make_session_factory` (Task 3) match their use in Task 4.

---

## Execution Handoff

See the bottom of this message for execution options.
