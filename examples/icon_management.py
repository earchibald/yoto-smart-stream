#!/usr/bin/env python3
"""
Example script demonstrating icon management for Yoto Smart Stream.

This script shows how to:
1. List public icons from the Yoto repository
2. Upload custom icons for Yoto Mini
3. Search and filter icons
4. Assign icons to card chapters

Note: Icons only display on Yoto Mini devices (16x16 pixel display).
Original Yoto Players do not have displays.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from yoto_smart_stream.icons import IconClient, IconService


async def main():
    """Main example function."""
    # Get access token (you would obtain this from YotoManager authentication)
    access_token = "your_access_token_here"

    # Initialize icon client and service
    async with IconClient(access_token) as client:
        service = IconService(client)

        print("=" * 60)
        print("Yoto Smart Stream - Icon Management Example")
        print("=" * 60)
        print()

        # Example 1: List public icons
        print("1. Listing public icons from Yoto repository...")
        print("-" * 60)
        public_icons = await service.get_public_icons(page=1, per_page=10)
        print(f"Found {public_icons.total} public icons")
        print(f"Showing page {public_icons.page} ({len(public_icons.icons)} icons):\n")

        for icon in public_icons.icons[:5]:  # Show first 5
            print(f"  - {icon.name}")
            print(f"    ID: {icon.id}")
            print(f"    Category: {icon.category or 'None'}")
            print(f"    Tags: {', '.join(icon.tags) if icon.tags else 'None'}")
            print(f"    URL: {icon.url}")
            print()

        # Example 2: Search for specific icons
        print("\n2. Searching for 'music' icons...")
        print("-" * 60)
        music_icons = await service.get_public_icons(search="music", per_page=5)
        print(f"Found {len(music_icons.icons)} icons matching 'music':\n")

        for icon in music_icons.icons:
            print(f"  - {icon.name}")

        # Example 3: Filter by category
        print("\n3. Filtering icons by category...")
        print("-" * 60)
        bedtime_icons = await service.get_public_icons(category="bedtime", per_page=5)
        print(f"Found {len(bedtime_icons.icons)} bedtime icons:\n")

        for icon in bedtime_icons.icons:
            print(f"  - {icon.name}")

        # Example 4: List user's custom icons
        print("\n4. Listing user's custom icons...")
        print("-" * 60)
        user_icons = await service.get_user_icons()
        print(f"You have {user_icons.total} custom icon(s):\n")

        for icon in user_icons.icons:
            print(f"  - {icon.name} (ID: {icon.id})")

        # Example 5: Upload a custom icon (commented out - requires actual file)
        print("\n5. Uploading a custom icon...")
        print("-" * 60)
        print("To upload a custom icon:")
        print("  - Icon must be PNG format")
        print("  - Icon must be exactly 16x16 pixels")
        print("  - Icon must be under 10KB")
        print()
        print("Example code:")
        print(
            """
        icon = await service.upload_custom_icon(
            icon_path=Path("my_icon.png"),
            name="My Custom Icon",
            tags=["custom", "special"],
            category="misc"
        )
        print(f"Uploaded icon: {icon.id}")
        """
        )

        # Example 6: Get a specific icon
        if public_icons.icons:
            print("\n6. Getting details for a specific icon...")
            print("-" * 60)
            first_icon = public_icons.icons[0]
            icon_details = await service.get_icon_by_id(first_icon.id)
            print(f"Icon: {icon_details.name}")
            print(f"  ID: {icon_details.id}")
            print(f"  URL: {icon_details.url}")
            print(f"  Is Public: {icon_details.is_public}")
            print(f"  Tags: {', '.join(icon_details.tags)}")

        print("\n" + "=" * 60)
        print("Device Compatibility Notes:")
        print("=" * 60)
        print("✓ Yoto Mini: Has 16x16 pixel display - shows icons")
        print("✗ Yoto Player (original): No display - icons not shown")
        print()
        print("Neither device has a microphone, so voice control")
        print("features are not available.")
        print("=" * 60)


if __name__ == "__main__":
    # Run the example
    print("\nNote: You need a valid Yoto API access token to run this example.")
    print("Obtain one using the YotoManager authentication flow.\n")

    # Uncomment the following line to actually run the example:
    # asyncio.run(main())

    print("This is a demonstration script. Update 'access_token' and")
    print("uncomment the asyncio.run(main()) line to execute.")
