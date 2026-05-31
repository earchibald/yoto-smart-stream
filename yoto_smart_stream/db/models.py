"""ORM models for the redesign. Story is the unit of authoring work."""
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from yoto_smart_stream.db.base import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Story(Base):
    """An interactive story: its editor graph plus Yoto publish state."""

    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # React Flow nodes/edges + start node, validated by schemas.story.StoryGraph.
    graph: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    hosting_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="stream")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    yoto_card_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
