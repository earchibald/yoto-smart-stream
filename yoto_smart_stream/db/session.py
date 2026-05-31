"""SQLite engine factory (WAL) and session maker."""
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def make_engine(url: str) -> Engine:
    """Create a SQLite engine with WAL journaling and foreign keys on.

    A file-backed SQLite database gets WAL mode for better read/write
    concurrency. In-memory databases (``sqlite://``) do not support WAL and
    are left at their default journal mode.
    """
    engine = create_engine(url, future=True)
    is_memory = url in ("sqlite://", "sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        if not is_memory:
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a configured session factory bound to ``engine``."""
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)
