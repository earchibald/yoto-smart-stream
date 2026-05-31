"""The story-editor data model (what React Flow manipulates)."""
from enum import StrEnum

from pydantic import BaseModel, Field


class NodeType(StrEnum):
    segment = "segment"  # linear audio; advances, stops, or repeats at end
    choice = "choice"  # narrates a choice; waits for a button press
    ending = "ending"  # terminal; stops (optional restart button)


class OnEnd(StrEnum):
    next = "next"  # follow the single "next" edge
    stop = "stop"
    repeat = "repeat"


class EdgeHandle(StrEnum):
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
