"""
Database models for user authentication and Yoto token management.

This module defines SQLAlchemy models for users and their associated Yoto OAuth tokens.
"""

from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from .database import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Yoto OAuth tokens associated with this user
    yoto_access_token = Column(Text, nullable=True)
    yoto_refresh_token = Column(Text, nullable=True)
    yoto_token_expires_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, is_admin={self.is_admin})>"


class AudioFile(Base):
    """Audio file model for storing metadata and transcripts."""

    __tablename__ = "audio_files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), unique=True, index=True, nullable=False)
    size = Column(Integer, nullable=False)  # File size in bytes
    duration = Column(Integer, nullable=True)  # Duration in seconds
    transcript = Column(Text, nullable=True)  # Speech-to-text transcript
    transcript_status = Column(
        String(20), default="pending", nullable=False
    )  # pending, processing, completed, error, cancelled, disabled
    transcript_error = Column(Text, nullable=True)  # Error message if transcription failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    transcribed_at = Column(DateTime, nullable=True)  # When transcription completed

    # TTS metadata fields
    tts_provider = Column(String(50), nullable=True)  # e.g., 'elevenlabs', 'gtts'
    tts_voice_id = Column(String(255), nullable=True)  # Voice ID used for generation
    tts_model = Column(String(100), nullable=True)  # Model used for generation

    def __repr__(self):
        return f"<AudioFile(id={self.id}, filename={self.filename}, transcript_status={self.transcript_status})>"


class Setting(Base):
    """Application settings model for persistent configuration."""

    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Setting(key={self.key}, value={self.value})>"
