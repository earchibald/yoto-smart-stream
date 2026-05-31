from yoto_smart_stream.db.base import Base
from yoto_smart_stream.db.models import Story
from yoto_smart_stream.db.session import make_engine, make_session_factory


def _session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    return make_session_factory(engine)()


def test_story_roundtrip_persists_graph_json():
    session = _session()
    story = Story(
        title="Adventure",
        graph={"start_node_id": "intro", "nodes": [], "edges": []},
        hosting_mode="stream",
    )
    session.add(story)
    session.commit()

    loaded = session.query(Story).one()
    assert loaded.id is not None
    assert loaded.title == "Adventure"
    assert loaded.graph["start_node_id"] == "intro"
    assert loaded.hosting_mode == "stream"
    assert loaded.status == "draft"
    assert loaded.yoto_card_id is None
    assert loaded.created_at is not None
