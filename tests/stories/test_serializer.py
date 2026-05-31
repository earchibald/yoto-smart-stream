import pytest

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


def test_dangling_goto_target_raises_valueerror():
    # An edge points at a node id that does not exist in the graph. Serializing
    # must fail loudly with a ValueError that names the bad target — not a raw
    # KeyError/IndexError — so the failure is diagnosable rather than silent.
    graph = StoryGraph(
        start_node_id="scene",
        nodes=[
            StoryNode(id="scene", type=NodeType.segment, title="Scene",
                      tracks=[Track(key="a", title="A")], on_end=OnEnd.next),
        ],
        edges=[StoryEdge(id="e1", source="scene", target="ghost", handle=EdgeHandle.next)],
    )
    with pytest.raises(ValueError, match="ghost"):
        serialize_story(graph, story_id=1, base_url="https://s", title="T")
