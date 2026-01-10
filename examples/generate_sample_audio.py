#!/usr/bin/env python3
"""
Generate sample MP3 audio files for testing

Creates audio files 1.mp3 through 10.mp3, where each file
contains someone saying that number five times.

Example: 1.mp3 contains "one. one. one. one. one."

Uses gTTS (Google Text-to-Speech) which doesn't require system dependencies.
Install with: pip install gtts pydub
"""

import os
import tempfile
from pathlib import Path

try:
    from gtts import gTTS
except ImportError:
    print("Error: gtts not installed")
    print("Install with: pip install gtts")
    exit(1)

try:
    from pydub import AudioSegment
except ImportError:
    print("Error: pydub not installed")
    print("Install with: pip install pydub")
    exit(1)


def number_to_word(num: int) -> str:
    """Convert number to word"""
    words = {
        1: "one",
        2: "two",
        3: "three",
        4: "four",
        5: "five",
        6: "six",
        7: "seven",
        8: "eight",
        9: "nine",
        10: "ten",
    }
    return words.get(num, str(num))


def generate_audio_file(number: int, output_dir: Path) -> Path:
    """
    Generate an audio file where the number is spoken five times
    
    Args:
        number: The number to speak (1-10)
        output_dir: Directory to save the MP3 file
        
    Returns:
        Path to the generated MP3 file
    """
    word = number_to_word(number)
    output_file = output_dir / f"{number}.mp3"

    print(f"Generating {output_file.name}...")

    # Create text: "one. one. one. one. one."
    text = ". ".join([word] * 5) + "."

    # Use a temporary MP3 file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_mp3:
        temp_mp3_path = temp_mp3.name

    try:
        # Generate speech using gTTS
        tts = gTTS(text=text, lang="en", slow=False)
        tts.save(temp_mp3_path)

        # Load and process with pydub
        audio = AudioSegment.from_mp3(temp_mp3_path)

        # Convert to mono and set appropriate settings
        audio = audio.set_channels(1)  # Mono
        audio = audio.set_frame_rate(44100)  # 44.1kHz sample rate

        # Export as optimized MP3
        audio.export(
            output_file,
            format="mp3",
            bitrate="192k",
            parameters=["-ac", "1"],  # Ensure mono
        )

        print(f"  ✓ Created: {output_file.name} ({output_file.stat().st_size} bytes)")

    except Exception as e:
        print(f"  ✗ Error: {e}")
        raise
    finally:
        # Clean up temporary file
        if os.path.exists(temp_mp3_path):
            os.remove(temp_mp3_path)

    return output_file


def generate_all_sample_files(output_dir: Path = None):
    """
    Generate all sample audio files (1.mp3 through 10.mp3)
    
    Args:
        output_dir: Directory to save files (defaults to audio_files/)
    """
    if output_dir is None:
        output_dir = Path("audio_files")

    output_dir.mkdir(exist_ok=True)

    print("\n" + "=" * 80)
    print("Generating Sample Audio Files")
    print("=" * 80)
    print(f"Output directory: {output_dir.absolute()}")
    print()

    generated_files = []

    for number in range(1, 11):
        try:
            file_path = generate_audio_file(number, output_dir)
            generated_files.append(file_path)
        except Exception as e:
            print(f"  ✗ Failed to generate {number}.mp3: {e}")

    print("\n" + "=" * 80)
    print(f"✓ Generated {len(generated_files)} audio files")
    print("=" * 80)
    print("\nFiles created:")
    for file_path in generated_files:
        size_kb = file_path.stat().st_size / 1024
        print(f"  - {file_path.name} ({size_kb:.1f} KB)")

    print("\nYou can now:")
    print("  1. Start the server: python examples/basic_server.py")
    print("  2. Access files at: http://localhost:8080/audio/1.mp3")
    print("  3. Create MYO cards using these files")
    print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate sample audio files for testing")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("audio_files"),
        help="Output directory (default: audio_files/)",
    )
    parser.add_argument(
        "--number",
        type=int,
        choices=range(1, 11),
        help="Generate a single number file (1-10)",
    )

    args = parser.parse_args()

    if args.number:
        # Generate single file
        output_dir = args.output_dir
        output_dir.mkdir(exist_ok=True)
        generate_audio_file(args.number, output_dir)
    else:
        # Generate all files
        generate_all_sample_files(args.output_dir)


if __name__ == "__main__":
    main()



def generate_all_sample_files(output_dir: Path = None):
    """
    Generate all sample audio files (1.mp3 through 10.mp3)
    
    Args:
        output_dir: Directory to save files (defaults to audio_files/)
    """
    if output_dir is None:
        output_dir = Path("audio_files")

    output_dir.mkdir(exist_ok=True)

    print("\n" + "=" * 80)
    print("Generating Sample Audio Files")
    print("=" * 80)
    print(f"Output directory: {output_dir.absolute()}")
    print()

    generated_files = []

    for number in range(1, 11):
        try:
            file_path = generate_audio_file(number, output_dir)
            generated_files.append(file_path)
        except Exception as e:
            print(f"  ✗ Failed to generate {number}.mp3: {e}")

    print("\n" + "=" * 80)
    print(f"✓ Generated {len(generated_files)} audio files")
    print("=" * 80)
    print("\nFiles created:")
    for file_path in generated_files:
        print(f"  - {file_path.name}")

    print("\nYou can now:")
    print("  1. Start the server: python examples/basic_server.py")
    print("  2. Access files at: http://localhost:8080/audio/1.mp3")
    print("  3. Create MYO cards using these files")
    print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Generate sample audio files for testing")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("audio_files"),
        help="Output directory (default: audio_files/)",
    )
    parser.add_argument(
        "--number",
        type=int,
        choices=range(1, 11),
        help="Generate a single number file (1-10)",
    )

    args = parser.parse_args()

    if args.number:
        # Generate single file
        output_dir = args.output_dir
        output_dir.mkdir(exist_ok=True)
        generate_audio_file(args.number, output_dir)
    else:
        # Generate all files
        generate_all_sample_files(args.output_dir)


if __name__ == "__main__":
    main()
