# Research: Interactive Story Graph Editors and Narrative Design Tools

**Bead:** yo-9vl | **Date:** 2026-03-21 | **Author:** yoto/crew/skillFinder

## Executive Summary

No open-source tool currently combines a modern node-graph UI (React Flow caliber) with narrative-specific semantics (dialogue nodes, character annotations, SFX cues, state tracking) in the browser. This is the gap. The building blocks exist and are mature.

**Recommended stack for a browser-based story graph editor:**
- **React Flow** (@xyflow/react) — graph UI foundation
- **Ink JSON + inkjs** — narrative engine and in-browser playback
- **JSON** — native data format (industry consensus)

---

## 1. Twine

| | |
|---|---|
| **Type** | Open source (GPL) |
| **Platform** | Browser + desktop (Electron) |
| **Data format** | Twee 3 (plain text), publishes to single HTML file, new JSON spec approved |
| **Community** | Very large — intfiction.org, education, game jams |

Twine IS a browser-based story graph editor. Stories are "passages" (content chunks) connected by links, visualized as a spatial map. Four story formats (Harlowe, SugarCube, Chapbook, Snowman) control scripting/rendering.

**Strengths:** Zero-code entry, single-file HTML output, widely known, anyone can inspect source from compiled story.

**Weaknesses:** No real-time collaboration, browser localStorage limit (5MB), story format syntax is non-transferable, limited multimedia.

**Relevant to us:** Passage-map metaphor is proven prior art. Twee 3 spec and new JSON format could serve as interchange targets.

---

## 2. Ink (Inkle Studios)

| | |
|---|---|
| **Type** | Open source (MIT) |
| **Platform** | C# compiler + Inky desktop editor; **inkjs** for browser |
| **Data format** | `.ink` source → compiled JSON |
| **Community** | ~4k+ GitHub stars, used in commercial games (80 Days, Heaven's Vault) |

Purpose-built scripting language for interactive narrative. Structure: knots (major sections) → stitches (subdivisions) → diverts (flow redirects) → choices. Supports variables, functions, conditional content, powerful list/set system.

**inkjs** is a zero-dependency JavaScript port of the full runtime, available on npm. Can compile and run stories entirely in the browser.

**Strengths:** Writer-friendly syntax, battle-tested at scale (millions of words), JSON compilation target, MIT licensed, browser-ready via inkjs.

**Weaknesses:** No visual/graph editor (text-only authoring), C# primary toolchain.

**Relevant to us:** inkjs runtime is directly embeddable. A visual graph editor could generate Ink source or consume its JSON. State tracking model (visit counts, conditional content) is proven.

---

## 3. Yarn Spinner

| | |
|---|---|
| **Type** | Open source (MIT) |
| **Platform** | Unity/C# (no browser runtime) |
| **Data format** | `.yarn` (plain text with metadata headers) |
| **Community** | ~3k+ GitHub stars, active Discord |

Screenplay-like syntax where the fundamental unit is a **node** — a named block with header metadata and dialogue body. Nodes connect via `<<jump>>` commands.

**Notable:** Yarn Spinner 3.1 (Dec 2025) introduced **storylets** — proceduralized narrative where the most contextually relevant content is selected based on game state. This is a sophisticated alternative to fixed branching trees.

**Relevant to us:** Node-based mental model and storylet architecture are instructive. Plain-text format shows how to keep content human-readable yet machine-parseable. No browser runtime limits direct reuse.

---

## 4. Visual Node-Based Browser Editors

### React Flow (@xyflow/react) — **Recommended**

| | |
|---|---|
| **Type** | Open source (MIT) |
| **Stars** | ~24,000 GitHub, 100k+ weekly npm downloads |
| **Framework** | React (also Svelte Flow 1.0 as of May 2025) |

The dominant library for building node-based UIs in React. Features: drag-and-drop, zoom/pan, custom node/edge types, minimap, keyboard shortcuts, plugin system. New in 2025: pre-built shadcn/ui components, Workflow Editor UI Template with auto-layout.

Nodes and edges are plain JS objects (trivially JSON-serializable). Custom nodes can contain any React component. Used to build workflow editors, ML pipeline tools, database designers.

**This is the strongest candidate for our graph UI foundation.**

### Alternatives

| Library | Stars | Notes |
|---------|-------|-------|
| **Rete.js** | ~12k | Framework-agnostic (React/Vue/Angular/Svelte/Lit), separates viz from processing, more complex setup |
| **Litegraph.js** | ~8k | Canvas/WebGL, used in ComfyUI, more performant for huge graphs, less React-friendly |
| **JsPlumb Toolkit** | Commercial | Enterprise positioning |
| **Flume** | Smaller | Lightweight React option, less maintained |

---

## 5. Branching Dialogue in Professional Games

**Key patterns studios use:**

- **Hub-and-spoke** — players return to central node after each branch, limiting exponential growth
- **State-based gating** — track variables, gate content on conditions (vs tracking every path)
- **Storylets/quality-based narrative** — dynamic content selection based on preconditions (Fallen London, Disco Elysium)
- **Visual editors are universally preferred** — problems (orphan nodes, dead ends) are immediately visible

**Professional tools:** articy:draft (AAA standard), Dialogue System for Unity (used in Disco Elysium), custom internal tools (BioWare, CDPR, Naughty Dog), Ink (indies), Unreal Blueprints.

---

## 6. Other Notable Tools

### Browser-Based (direct competitors)

| Tool | Open Source | Collab | JSON Export | Notes |
|------|-----------|--------|-------------|-------|
| **Arcweave** | No (freemium) | Real-time | Yes | Most feature-complete browser narrative tool. Scripting, AI analysis, embeddable Play Mode. Unity/Unreal/Godot plugins. |
| **Homer** | Free-to-use | Multi-user | Yes | Dual page/flow editing. JS and Unity plugins. Smaller community. |
| **NarrativeFlow** | No | No | Yes (plaintext) | Vue.js-based, runs locally. Unlimited branching. |
| **Drafft** | No | Yes | Unclear | GDDs + scripts + dialogue trees in one place. |

### Desktop-Only

| Tool | License | Notes |
|------|---------|-------|
| **articy:draft X** | Commercial ($7+/mo) | AAA industry standard. Visual flowcharts, character/item DBs, simulation mode, localization. Windows only. |
| **Chat Mapper** | Commercial ($420+/yr) | Tree-graph dialogue, Lua scripting, conversation simulator. Windows only. |
| **StoryFlow Editor** | Commercial | Blueprint-style visual scripting (launched Nov 2025 on Steam/itch). |

### Engine-Specific

| Tool | Engine | Notes |
|------|--------|-------|
| **Dialogic** | Godot 4.3+ | Open source (MIT). Visual timeline editor + text editor. Active community. |

---

## 7. Browser Story Editor Landscape — The Gap

| Tool | Browser-Native | Open Source | Real-time Collab | JSON | Embeddable |
|------|---------------|-------------|-----------------|------|------------|
| Twine 2 | Yes | Yes (GPL) | No | Via addon | No |
| Arcweave | Yes | No | Yes | Yes | Yes |
| Homer | Yes | Free-to-use | Yes | Yes | Yes |
| NarrativeFlow | Yes (local) | No | No | Yes | No |

**No tool combines:** React Flow-caliber graph UX + narrative semantics (dialogue types, character management, SFX cues, state tracking) + open source + extensible + browser-native.

**Arcweave** is the closest competitor but is closed-source and commercial.

---

## 8. Professional Audio Drama Workflows

### Production Phases

**1. Development (Scripting)**
- **Google Docs** — most common for indie/podcast audio drama
- **Final Draft** ($250+) — industry standard for film/TV, overkill for audio drama
- **Highland 2** — Mac-only, well-regarded
- **Fountain format** — plain-text screenplay markup, tool-agnostic
- **BBC Radio Drama format** — numbered lines, character cues, SFX/music annotations

**2. Pre-production**
- **Trello/Kanban** — episode cards through columns (Script → Recording → Editing → Sound Design → Mix → Published)
- **Dramatify** ($29+/mo) — professional cloud production management (script breakdown, scheduling, cast booking, call sheets)
- **Spreadsheets** — actor availability, scene grouping by cast

**3. Production (Recording)**
- Record lead characters first
- Group actors by shared scenes (not chronological order)
- Line numbers in scripts for session reference

**4. Post-production**
- **Audacity** — free, widely used by indie producers
- **Pro Tools / Logic Pro / Reaper** — professional DAWs
- **Freesound.org** — public domain SFX library
- **Soniss** — royalty-free commercial SFX

### Key Insight

Audio drama scripts describe ONLY what is heard. A script editor needs first-class support for: SFX cue annotations inline with dialogue, music cues, character voice/expression notes, scene ambience descriptions, line numbering, cast grouping for scheduling.

**No integrated tool exists** that combines narrative branching (for interactive audio drama) with production management (casting, scheduling, sound design annotation). This is an open space.

---

## Recommendations

1. **Foundation:** React Flow (@xyflow/react) for graph UI — proven, 24k stars, MIT, infinitely customizable
2. **Narrative engine:** Ink JSON format + inkjs runtime for in-browser story playback/testing
3. **Data format:** JSON-native (industry consensus across Ink, Arcweave, Homer, NarrativeFlow, new Twine spec)
4. **Study:** Yarn Spinner's storylet model for adaptive narrative beyond fixed trees
5. **Differentiate from Arcweave** by being open source and supporting audio drama production metadata (SFX cues, cast scheduling, recording annotations)
6. **Collaboration:** CRDTs (e.g., Yjs) for real-time multi-user editing
