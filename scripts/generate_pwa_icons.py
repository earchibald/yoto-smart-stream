#!/usr/bin/env python3
"""
Generate PWA icons in multiple sizes from a source image.
Creates all required icon sizes for Progressive Web App support.
"""

from pathlib import Path

from PIL import Image, ImageDraw

# Icon sizes required for PWA
ICON_SIZES = [72, 96, 128, 144, 152, 192, 384, 512]
MASKABLE_SIZES = [192, 512]

# Colors for the app icon
BG_COLOR = "#4A90E2"  # Blue
ICON_COLOR = "#FFFFFF"  # White


def create_icon_directory():
    """Create the icons directory if it doesn't exist."""
    icons_dir = Path(__file__).parent.parent / "static" / "icons"
    icons_dir.mkdir(parents=True, exist_ok=True)
    return icons_dir


def create_base_icon(size=512):
    """Create a base icon with the Yoto Smart Stream logo."""
    # Create image with rounded corners
    img = Image.new("RGB", (size, size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Draw music note emoji-style icon
    # This creates a simple, recognizable icon
    # For production, you'd want to use a proper logo/icon design

    # Draw a circle background
    margin = size // 8
    circle_bbox = [margin, margin, size - margin, size - margin]
    draw.ellipse(circle_bbox, fill=BG_COLOR)

    # Draw music note (simplified)
    center_x, center_y = size // 2, size // 2
    note_size = size // 3

    # Note stem
    stem_width = size // 20
    stem_height = note_size * 2
    stem_x1 = center_x + note_size // 3
    stem_y1 = center_y - stem_height // 2
    draw.rectangle([stem_x1, stem_y1, stem_x1 + stem_width, stem_y1 + stem_height], fill=ICON_COLOR)

    # Note head (circle)
    head_radius = note_size // 2
    head_x = center_x
    head_y = center_y + stem_height // 3
    draw.ellipse(
        [
            head_x - head_radius,
            head_y - head_radius // 2,
            head_x + head_radius,
            head_y + head_radius // 2,
        ],
        fill=ICON_COLOR,
    )

    return img


def create_maskable_icon(base_img, size):
    """
    Create a maskable icon with safe zone.
    Maskable icons need 40% safe zone padding.
    """
    # Create a new image with padding
    maskable = Image.new("RGB", (size, size), BG_COLOR)

    # Calculate safe zone (40% padding = 20% on each side)
    safe_zone = int(size * 0.2)
    inner_size = size - (2 * safe_zone)

    # Resize and paste the base icon in the center
    resized_base = base_img.resize((inner_size, inner_size), Image.Resampling.LANCZOS)
    maskable.paste(resized_base, (safe_zone, safe_zone))

    return maskable


def generate_icons():
    """Generate all required PWA icons."""
    print("🎨 Generating PWA icons...")

    icons_dir = create_icon_directory()
    print(f"📁 Icons directory: {icons_dir}")

    # Create base icon at highest resolution
    base_icon = create_base_icon(512)
    print("✅ Created base icon (512x512)")

    # Generate standard icons
    for size in ICON_SIZES:
        icon = base_icon.resize((size, size), Image.Resampling.LANCZOS)
        icon_path = icons_dir / f"icon-{size}x{size}.png"
        icon.save(icon_path, "PNG", optimize=True)
        print(f"✅ Generated icon-{size}x{size}.png")

    # Generate maskable icons
    for size in MASKABLE_SIZES:
        maskable = create_maskable_icon(base_icon, size)
        maskable_path = icons_dir / f"icon-maskable-{size}x{size}.png"
        maskable.save(maskable_path, "PNG", optimize=True)
        print(f"✅ Generated icon-maskable-{size}x{size}.png")

    # Generate favicon
    favicon = base_icon.resize((32, 32), Image.Resampling.LANCZOS)
    favicon_path = icons_dir.parent / "favicon.ico"
    favicon.save(favicon_path, "ICO")
    print("✅ Generated favicon.ico")

    # Generate apple-touch-icon
    apple_icon = base_icon.resize((180, 180), Image.Resampling.LANCZOS)
    apple_icon_path = icons_dir / "apple-touch-icon.png"
    apple_icon.save(apple_icon_path, "PNG", optimize=True)
    print("✅ Generated apple-touch-icon.png")

    print(f"\n🎉 Successfully generated {len(ICON_SIZES) + len(MASKABLE_SIZES) + 2} icons!")
    print(f"📦 Icons saved to: {icons_dir}")


if __name__ == "__main__":
    try:
        generate_icons()
    except Exception as e:
        print(f"❌ Error generating icons: {e}")
        raise
