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
