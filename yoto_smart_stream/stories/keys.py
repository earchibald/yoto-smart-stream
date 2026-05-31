"""Deterministic, collision-free chapter-key derivation for Yoto cards.

A ``goto`` instruction on the Yoto hardware that references a non-existent or
duplicate chapter key fails *silently* — the device simply stops advancing the
story.  Global uniqueness is therefore safety-critical; this module guarantees
it by probing a ``used`` set rather than tracking a per-base counter (a counter
approach would silently collide when a node's literal id matches a generated
suffix such as ``"intro-2"``).
"""

import re
from collections.abc import Sequence

from yoto_smart_stream.schemas.story import StoryNode

_NON_ALPHANUM = re.compile(r"[^a-z0-9]+")


def slugify_key(node_id: str) -> str:
    """Return a URL-safe slug for *node_id*.

    Rules:
    - Lowercased.
    - Every run of characters outside ``[a-z0-9]`` is replaced with a single
      ``-``.
    - Leading and trailing ``-`` are stripped.
    - If nothing survives (e.g. the id was all punctuation), ``"node"`` is
      returned as a safe fallback.
    """
    slug = _NON_ALPHANUM.sub("-", node_id.lower()).strip("-")
    return slug or "node"


def build_chapter_keys(nodes: Sequence[StoryNode]) -> dict[str, str]:
    """Map each node's id to a globally-unique, deterministic chapter key.

    Keys are derived by :func:`slugify_key`.  When two or more nodes produce
    the same base slug, the second occurrence is disambiguated by probing
    ``f"{base}-{n}"`` for *n* = 2, 3, 4, … until a key that has **not** yet
    been assigned is found.  Because the probe checks the global ``used`` set
    (not just a per-base counter), a node whose literal id happens to equal a
    generated suffix (e.g. ``"the-cave-2"``) is also handled correctly —
    the probe simply continues to the next candidate until it finds one that
    is genuinely free.

    Returns a :class:`dict` whose insertion order matches *nodes*.
    """
    used: set[str] = set()
    keys: dict[str, str] = {}

    for node in nodes:
        base = slugify_key(node.id)
        if base not in used:
            chosen = base
        else:
            n = 2
            while True:
                candidate = f"{base}-{n}"
                if candidate not in used:
                    chosen = candidate
                    break
                n += 1

        used.add(chosen)
        keys[node.id] = chosen

    return keys
