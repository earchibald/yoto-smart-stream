#!/usr/bin/env python3
"""List audio files in the /data/audio_files directory."""

from pathlib import Path

audio_dir = Path("/data/audio_files")

if not audio_dir.exists():
    print(f"Directory {audio_dir} does not exist")
    exit(0)

audio_files = list(audio_dir.glob("*.mp3"))

print(f"Found {len(audio_files)} MP3 files in {audio_dir}:")
for f in sorted(audio_files):
    size_mb = f.stat().st_size / (1024 * 1024)
    print(f"  {f.name} ({size_mb:.2f} MB)")
