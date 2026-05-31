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
from yoto_smart_stream.stories.validator import validate_graph


def serialize_story(
    graph: StoryGraph,
    *,
    story_id: int,
    base_url: str,
    title: str,
    description: str | None = None,
    author: str | None = None,
) -> YotoCard:
    errors = validate_graph(graph)
    if errors:
        raise ValueError(
            "Cannot serialize an invalid story graph:\n  - " + "\n  - ".join(errors)
        )

    chapter_keys = build_chapter_keys(graph.nodes)
    nodes_by_id = {n.id: n for n in graph.nodes}

    def goto(
        source_node_id: str, handle: EdgeHandle, target_node_id: str
    ) -> GotoCommand:
        target = nodes_by_id.get(target_node_id)
        if target is None:
            raise ValueError(
                f"Node '{source_node_id}' has a {handle.value} edge to unknown "
                f"target node '{target_node_id}'."
            )
        if not target.tracks:
            raise ValueError(
                f"goto target node '{target_node_id}' has no track to land on."
            )
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
        if node.type in (NodeType.choice, NodeType.ending):
            left = first_edge_target(node.id, EdgeHandle.left)
            right = first_edge_target(node.id, EdgeHandle.right)
            return TrackEvents(
                onEnd=StopCommand(),
                onLhb=goto(node.id, EdgeHandle.left, left) if left else None,
                onRhb=goto(node.id, EdgeHandle.right, right) if right else None,
            )
        # segment
        if node.on_end is OnEnd.stop:
            return TrackEvents(onEnd=StopCommand())
        if node.on_end is OnEnd.repeat:
            return TrackEvents(onEnd=RepeatCommand())
        nxt = first_edge_target(node.id, EdgeHandle.next)
        return TrackEvents(onEnd=goto(node.id, EdgeHandle.next, nxt)) if nxt else None

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
