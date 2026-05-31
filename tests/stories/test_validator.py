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


def test_orphan_node_flagged():
    # 'lonely' is an ending node (so it triggers no edge-requirement rules) but
    # nothing points to it — it is unreachable from the start node.
    g = _valid_graph()
    g.nodes.append(StoryNode(id="lonely", type=NodeType.ending, title="Lonely", tracks=[_track()]))
    errors = validate_graph(g)
    assert any("lonely" in e and ("unreachable" in e.lower() or "orphan" in e.lower()) for e in errors)


def test_valid_graph_has_no_orphans():
    # The standard valid graph must NOT produce any orphan/unreachable error.
    errors = validate_graph(_valid_graph())
    assert not any("unreachable" in e.lower() or "orphan" in e.lower() for e in errors)


def test_node_reachable_only_via_ignored_handle_is_orphan():
    # 'stray' is targeted only by a `next` edge out of a CHOICE node. The
    # serializer ignores a choice node's next handle, so 'stray' can never be
    # reached on-device even though a raw edge points at it.
    g = StoryGraph(
        start_node_id="intro",
        nodes=[
            StoryNode(id="intro", type=NodeType.choice, title="Intro", tracks=[_track()]),
            StoryNode(id="cave", type=NodeType.ending, title="Cave", tracks=[_track()]),
            StoryNode(id="forest", type=NodeType.ending, title="Forest", tracks=[_track()]),
            StoryNode(id="stray", type=NodeType.ending, title="Stray", tracks=[_track()]),
        ],
        edges=[
            StoryEdge(id="e1", source="intro", target="cave", handle=EdgeHandle.left),
            StoryEdge(id="e2", source="intro", target="forest", handle=EdgeHandle.right),
            StoryEdge(id="e3", source="intro", target="stray", handle=EdgeHandle.next),
        ],
    )
    errors = validate_graph(g)
    assert any("stray" in e and ("unreachable" in e.lower() or "orphan" in e.lower()) for e in errors)


def test_choice_with_duplicate_button_edge_flagged():
    g = _valid_graph()
    # intro already has one left + one right; add a SECOND left edge.
    g.edges.append(StoryEdge(id="e_dup", source="intro", target="end", handle=EdgeHandle.left))
    assert any("intro" in e and "left" in e.lower() for e in validate_graph(g))
