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
