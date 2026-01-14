"""
Database configuration and session management.

Provides SQLAlchemy database setup and session management for the application.
"""

import logging
from sqlalchemy import create_engine, inspect
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
        
        db = SessionLocal()
        try:
            # Add email column if missing
            if "email" not in users_columns:
                logger.info("Migrating database: Adding 'email' column to users table...")
                engine.execute("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
                logger.info("✓ Added email column to users table")
            
            # Add is_admin column if missing
            if "is_admin" not in users_columns:
                logger.info("Migrating database: Adding 'is_admin' column to users table...")
                engine.execute("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0")
                logger.info("✓ Added is_admin column to users table")
        except Exception as e:
            logger.debug(f"Column migration info: {e}")
            # Columns may already exist, which is fine
        finally:
            db.close()

