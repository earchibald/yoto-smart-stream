from yoto_smart_stream.schemas.card import (
    CardContent,
    CardTrack,
    Chapter,
    GotoCommand,
    StopCommand,
    TrackEvents,
    YotoCard,
)


def test_interactive_config_defaults_match_reference():
    content = CardContent(chapters=[])
    assert content.playbackType == "interactive"
    assert content.config.autoadvance == "none"
    assert content.config.disableTrackNav is True
    assert content.config.disableChapterNav is True
    assert content.config.onlineOnly is True
    assert content.editSettings.interactiveContent is True


def test_card_with_choice_track_serializes_events():
    track = CardTrack(
        key="t",
        title="Intro",
        trackUrl="https://x/y.mp3",
        events=TrackEvents(
            onEnd=StopCommand(),
            onLhb=GotoCommand(params={"chapterKey": "cave", "trackKey": "t"}),
        ),
    )
    card = YotoCard(
        title="Adventure",
        content=CardContent(chapters=[Chapter(key="intro", title="Intro", tracks=[track])]),
    )
    dumped = card.model_dump(exclude_none=True)
    ev = dumped["content"]["chapters"][0]["tracks"][0]["events"]
    assert ev["onEnd"] == {"cmd": "stop"}
    assert ev["onLhb"] == {"cmd": "goto", "params": {"chapterKey": "cave", "trackKey": "t"}}
