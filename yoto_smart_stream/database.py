"""
Database configuration and session management.

Provides SQLAlchemy database setup and session management for the application.
"""

import logging

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Create engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Get database session.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables and handle schema migrations."""
    # Create all tables from models
    Base.metadata.create_all(bind=engine)

    # Handle schema migrations for existing tables
    inspector = inspect(engine)

    # Check and add missing columns to users table
    if "users" in inspector.get_table_names():
        users_columns = [col["name"] for col in inspector.get_columns("users")]

        # Create a connection to execute raw SQL
        with engine.connect() as connection:
            try:
                # Add email column if missing
                if "email" not in users_columns:
                    logger.info("Migrating database: Adding 'email' column to users table...")
                    connection.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(255)"))
                    connection.commit()
                    logger.info("✓ Added email column to users table")
            except Exception as e:
                logger.debug(f"Email column migration info: {e}")
                # Column may already exist, which is fine

            try:
                # Add is_admin column if missing
                if "is_admin" not in users_columns:
                    logger.info("Migrating database: Adding 'is_admin' column to users table...")
                    connection.execute(
                        text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
                    )
                    connection.commit()
                    logger.info("✓ Added is_admin column to users table")

                # Always ensure admin user has is_admin=True (in case column was added with DEFAULT 0)
                logger.info("Ensuring admin user has is_admin=True...")
                result = connection.execute(
                    text("UPDATE users SET is_admin = 1 WHERE username = 'admin'")
                )
                connection.commit()
                if result.rowcount > 0:
                    logger.info(f"✓ Updated {result.rowcount} admin user(s) with is_admin=True")
                else:
                    logger.info("✓ Admin user already has is_admin=True")
            except Exception as e:
                logger.debug(f"Is_admin column migration info: {e}")
                # Column may already exist, which is fine

    # Check and add missing columns to audio_files table
    if "audio_files" in inspector.get_table_names():
        audio_files_columns = [col["name"] for col in inspector.get_columns("audio_files")]

        with engine.connect() as connection:
            try:
                # Add TTS provider column if missing
                if "tts_provider" not in audio_files_columns:
                    logger.info(
                        "Migrating database: Adding 'tts_provider' column to audio_files table..."
                    )
                    connection.execute(
                        text("ALTER TABLE audio_files ADD COLUMN tts_provider VARCHAR(50)")
                    )
                    connection.commit()
                    logger.info("✓ Added tts_provider column to audio_files table")
            except Exception as e:
                logger.debug(f"TTS provider column migration info: {e}")

            try:
                # Add TTS voice_id column if missing
                if "tts_voice_id" not in audio_files_columns:
                    logger.info(
                        "Migrating database: Adding 'tts_voice_id' column to audio_files table..."
                    )
                    connection.execute(
                        text("ALTER TABLE audio_files ADD COLUMN tts_voice_id VARCHAR(255)")
                    )
                    connection.commit()
                    logger.info("✓ Added tts_voice_id column to audio_files table")
            except Exception as e:
                logger.debug(f"TTS voice_id column migration info: {e}")

            try:
                # Add TTS model column if missing
                if "tts_model" not in audio_files_columns:
                    logger.info(
                        "Migrating database: Adding 'tts_model' column to audio_files table..."
                    )
                    connection.execute(
                        text("ALTER TABLE audio_files ADD COLUMN tts_model VARCHAR(100)")
                    )
                    connection.commit()
                    logger.info("✓ Added tts_model column to audio_files table")
            except Exception as e:
                logger.debug(f"TTS model column migration info: {e}")
