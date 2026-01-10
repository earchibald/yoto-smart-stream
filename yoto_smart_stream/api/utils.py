"""Utility functions for the API."""

from datetime import datetime


def get_time_based_audio_file() -> str:
    """
    Get the appropriate audio filename based on current time of day.

    Returns:
        str: Audio filename (morning-story.mp3, afternoon-story.mp3, or bedtime-story.mp3)
    """
    hour = datetime.now().hour

    if 6 <= hour < 12:
        return "morning-story.mp3"
    elif 12 <= hour < 18:
        return "afternoon-story.mp3"
    else:
        return "bedtime-story.mp3"


def get_time_schedule() -> dict[str, str]:
    """
    Get the time schedule for dynamic audio.

    Returns:
        dict: Time schedule with morning, afternoon, and evening periods
    """
    return {
        "morning": "6:00 AM - 12:00 PM: morning-story.mp3",
        "afternoon": "12:00 PM - 6:00 PM: afternoon-story.mp3",
        "evening": "6:00 PM - 6:00 AM: bedtime-story.mp3",
    }
