import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect


def test_migrations_create_stories_table(tmp_path):
    db = tmp_path / "m.db"
    url = f"sqlite:///{db}"
    env = {**os.environ, "ALEMBIC_SQLALCHEMY_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "-x", f"url={url}", "upgrade", "head"],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr

    engine = create_engine(url)
    tables = inspect(engine).get_table_names()
    assert "stories" in tables
    cols = {c["name"] for c in inspect(engine).get_columns("stories")}
    assert {"id", "title", "graph", "hosting_mode", "status", "yoto_card_id"} <= cols
