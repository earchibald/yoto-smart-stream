"""Tests for deterministic, collision-free chapter-key derivation."""
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


def test_suffix_collision_still_unique():
    # "a" and "a!" both slugify to "a"; a third node's id is literally "a-2",
    # which is exactly the disambiguation suffix that would be generated.
    # The result must still contain 3 globally-unique keys (no silent collision).
    nodes = [_node("a"), _node("a!"), _node("a-2")]
    keys = build_chapter_keys(nodes)
    assert len(set(keys.values())) == 3
    assert keys["a"] == "a"  # first occurrence keeps the base slug
    # order is preserved and every node id is present
    assert list(keys.keys()) == ["a", "a!", "a-2"]
