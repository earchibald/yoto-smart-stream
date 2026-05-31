"""Semantic validation for a :class:`StoryGraph`.

These rules exist to catch mistakes that fail *silently* on the Yoto device.
A card with a dangling ``goto`` target, a choice node missing one of its two
hardware-button edges, or a graph that can never terminate will compile and
upload fine, then simply misbehave (frozen playback, dead buttons, an endless
loop) in a child's hands with no error surfaced. ``validate_graph`` runs the
structural checks the device cannot, returning human-readable error strings so
the editor can block a bad save before it ships.

Rules enforced:

* Node ids must be unique.
* The start node must exist in the graph.
* Every edge's source and target must reference an existing node.
* Each node must have at least one track, and track keys must be unique
  within a node.
* A ``choice`` node must have BOTH a left and a right outgoing edge.
* A ``segment`` node with ``on_end is OnEnd.next`` must have exactly one
  outgoing ``next`` edge.
* At least one node must terminate the story (an ``ending`` node, or a
  ``segment`` whose ``on_end is OnEnd.stop``); otherwise playback never ends.
* Every node must be reachable from the start node (no orphans / unreachable
  nodes), since unreachable nodes are dead authoring weight the device will
  never play and usually signal a wiring mistake.
"""
from collections import deque

from yoto_smart_stream.schemas.story import (
    EdgeHandle,
    NodeType,
    OnEnd,
    StoryGraph,
    StoryNode,
)


def _outgoing(graph: StoryGraph, node_id: str, handle: EdgeHandle) -> list:
    return [e for e in graph.edges if e.source == node_id and e.handle == handle]


def _terminates(node: StoryNode) -> bool:
    return node.type is NodeType.ending or (
        node.type is NodeType.segment and node.on_end is OnEnd.stop
    )


def _reachable_ids(graph: StoryGraph) -> set[str]:
    """Node ids reachable from the start node via directed edges (any handle)."""
    adjacency: dict[str, list[str]] = {}
    for edge in graph.edges:
        adjacency.setdefault(edge.source, []).append(edge.target)

    seen: set[str] = set()
    queue: deque[str] = deque([graph.start_node_id])
    while queue:
        current = queue.popleft()
        if current in seen:
            continue
        seen.add(current)
        queue.extend(adjacency.get(current, []))
    return seen


def validate_graph(graph: StoryGraph) -> list[str]:
    """Return human-readable validation errors; an empty list means valid."""
    errors: list[str] = []

    # Node ids must be unique.
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for node in graph.nodes:
        if node.id in seen_ids:
            duplicate_ids.add(node.id)
        seen_ids.add(node.id)
    for dup in sorted(duplicate_ids):
        errors.append(f"Duplicate node id '{dup}'.")

    node_ids = {node.id for node in graph.nodes}

    # Start node must exist.
    start_exists = graph.start_node_id in node_ids
    if not start_exists:
        errors.append(
            f"Start node '{graph.start_node_id}' does not exist in the graph."
        )

    # Every edge's source and target must exist.
    for edge in graph.edges:
        if edge.source not in node_ids:
            errors.append(
                f"Edge '{edge.id}' has unknown source node '{edge.source}'."
            )
        if edge.target not in node_ids:
            errors.append(
                f"Edge '{edge.id}' has unknown target node '{edge.target}'."
            )

    # Per-node checks: tracks, choice buttons, segment next edges.
    for node in graph.nodes:
        if not node.tracks:
            errors.append(f"Node '{node.id}' has no track.")
        else:
            track_seen: set[str] = set()
            track_dups: set[str] = set()
            for track in node.tracks:
                if track.key in track_seen:
                    track_dups.add(track.key)
                track_seen.add(track.key)
            for dup in sorted(track_dups):
                errors.append(
                    f"Node '{node.id}' has duplicate track key '{dup}'."
                )

        if node.type is NodeType.choice:
            if not _outgoing(graph, node.id, EdgeHandle.left):
                errors.append(
                    f"Choice node '{node.id}' is missing a left-button edge."
                )
            if not _outgoing(graph, node.id, EdgeHandle.right):
                errors.append(
                    f"Choice node '{node.id}' is missing a right-button edge."
                )

        if node.type is NodeType.segment and node.on_end is OnEnd.next:
            next_edges = _outgoing(graph, node.id, EdgeHandle.next)
            if len(next_edges) != 1:
                errors.append(
                    f"Segment node '{node.id}' has on_end=next but "
                    f"{len(next_edges)} next edge(s) (expected exactly one)."
                )

    # At least one node must terminate the story.
    if graph.nodes and not any(_terminates(node) for node in graph.nodes):
        errors.append(
            "No node terminates the story (need an ending node or a segment "
            "with on_end=stop); playback would never terminate."
        )

    # Reachability / orphan check. Only meaningful when the start node exists;
    # otherwise the missing-start error already covers the broken graph.
    if start_exists and graph.nodes:
        reachable = _reachable_ids(graph)
        for node in graph.nodes:
            if node.id not in reachable:
                errors.append(
                    f"Node '{node.id}' is unreachable from the start node (orphan)."
                )

    return errors
