"""
Database configuration and session management.

Provides SQLAlchemy database setup and session management for the application.
"""

import logging
import os
from typing import Any, Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .storage.dynamodb_store import DynamoStore, get_store

logger = logging.getLogger(__name__)

settings = get_settings()
use_dynamo = bool(settings.dynamodb_table or os.getenv("DYNAMODB_TABLE"))

# SQLAlchemy primitives are only initialized when a SQL database URL is provided
engine = None
SessionLocal = None
Base = declarative_base()

if not use_dynamo and settings.database_url:
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[DynamoStore | Session, None, None]:
    """Yield DynamoDB store or SQLAlchemy session depending on configuration."""
    if use_dynamo or not settings.database_url:
        store = get_store(settings.dynamodb_table, region_name=settings.dynamodb_region)
        yield store
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize persistence layer."""
    if use_dynamo or not settings.database_url:
        logger.info("DynamoDB mode: no SQL schema initialization required")
        return

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
                    connection.execute(text("ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0"))
                    connection.commit()
                    logger.info("✓ Added is_admin column to users table")
                
                # Always ensure admin user has is_admin=True (in case column was added with DEFAULT 0)
                logger.info("Ensuring admin user has is_admin=True...")
                result = connection.execute(text("UPDATE users SET is_admin = 1 WHERE username = 'admin'"))
                connection.commit()
                if result.rowcount > 0:
                    logger.info(f"✓ Updated {result.rowcount} admin user(s) with is_admin=True")
                else:
                    logger.info("✓ Admin user already has is_admin=True")
            except Exception as e:
                logger.debug(f"Is_admin column migration info: {e}")
                # Column may already exist, which is fine

