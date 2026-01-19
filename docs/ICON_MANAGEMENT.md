> **⚠️ DEPRECATED**: This documentation has been consolidated into the [yoto-smart-stream skill](../.github/skills/yoto-smart-stream/SKILL.md). Please refer to the skill for current information.
>
> **New location:** `.github/skills/yoto-smart-stream/reference/icon_management.md`

---

# Display Icon Management for Yoto Smart Stream

## Overview

This document describes how to manage display icons for Yoto devices, particularly for the Yoto Mini which has a 16x16 pixel display.

## Device Compatibility

### Yoto Mini
- **Display**: 16x16 pixel screen
- **Microphone**: None (voice control not supported)
- **Icons**: Fully supported - shows custom icons during playback

### Yoto Player (Original)
- **Display**: None - no screen
- **Microphone**: None (voice control not supported)
- **Icons**: Not applicable - device has no display

## Icon Specifications

Icons for Yoto Mini must meet the following requirements:

- **Format**: PNG
- **Resolution**: Exactly 16x16 pixels
- **File Size**: Maximum 10KB
- **Color Depth**: 24-bit RGB or 32-bit RGBA

## Icon Sources

### 1. Public Icon Repository

Yoto provides a public repository of icons that are available to all users:

```python
from yoto_smart_stream.icons import IconClient, IconService

# Initialize
async with IconClient(access_token) as client:
    service = IconService(client)
    
    # Get public icons
    public_icons = await service.get_public_icons(
        category="music",  # Optional: filter by category
        search="note",     # Optional: search term
        page=1,
        per_page=50
    )
    
    for icon in public_icons.icons:
        print(f"{icon.name}: {icon.url}")
```

### 2. Custom User Icons

Users can upload their own custom icons:

```python
# Upload a custom icon
icon = await service.upload_custom_icon(
    icon_path=Path("my_icon.png"),
    name="My Custom Icon",
    tags=["custom", "special"],
    category="misc"
)

print(f"Uploaded icon ID: {icon.id}")
```

## API Endpoints

### List Public Icons

**Endpoint**: `GET /media/displayIcons/public`

**Parameters**:
- `category` (optional): Filter by category
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 50)

**Response**:
```json
{
  "icons": [
    {
      "id": "icon-music-001",
      "name": "Music Note",
      "url": "https://cdn.yotoplay.com/icons/music-001.png",
      "category": "music",
      "tags": ["music", "note", "audio"],
      "is_public": true
    }
  ],
  "total": 150,
  "page": 1,
  "per_page": 50,
  "has_next": true
}
```

### List User Icons

**Endpoint**: `GET /media/displayIcons/user/me`

**Parameters**:
- `page` (optional): Page number (default: 1)
- `per_page` (optional): Items per page (default: 50)

**Response**: Same format as public icons, with `is_public: false`

### Upload Custom Icon

**Endpoint**: `POST /media/displayIcons/upload`

**Content-Type**: `multipart/form-data`

**Parameters**:
- `icon` (file): PNG image file (16x16 pixels)
- `name` (string): Icon name
- `tags` (string): Comma-separated tags
- `category` (string, optional): Icon category

**Response**:
```json
{
  "id": "user-icon-abc123",
  "name": "My Custom Icon",
  "url": "https://cdn.yotoplay.com/user-icons/abc123.png",
  "category": "custom",
  "tags": ["custom"],
  "is_public": false,
  "created_at": "2026-01-10T12:00:00Z"
}
```

### Get Icon Details

**Endpoint**: `GET /media/displayIcons/{iconId}`

**Response**: Single icon object

### Delete Custom Icon

**Endpoint**: `DELETE /media/displayIcons/{iconId}`

**Response**: `204 No Content` on success

## Usage Examples

### Example 1: Browse and Select Icon

```python
async def select_icon_for_chapter(service: IconService):
    """Let user select an icon from the repository."""
    
    # Show available icons
    icons = await service.get_public_icons(category="story", per_page=20)
    
    print("Available story icons:")
    for i, icon in enumerate(icons.icons):
        print(f"{i+1}. {icon.name}")
    
    # User selects an icon
    selection = int(input("Select icon number: ")) - 1
    selected_icon = icons.icons[selection]
    
    return selected_icon.url
```

### Example 2: Create and Upload Custom Icon

```python
from PIL import Image

async def create_and_upload_icon(service: IconService):
    """Create a simple 16x16 icon and upload it."""
    
    # Create a 16x16 red square icon
    img = Image.new('RGBA', (16, 16), color='red')
    
    # Save to bytes
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    icon_data = buffer.getvalue()
    
    # Upload
    icon = await service.upload_custom_icon_bytes(
        icon_data=icon_data,
        name="Red Square",
        tags=["custom", "red", "square"],
        category="shapes"
    )
    
    print(f"Uploaded icon: {icon.id}")
    return icon
```

### Example 3: Assign Icon to Chapter

```python
# When creating a card with chapters
chapter_data = {
    "key": "chapter-01",
    "title": "Introduction",
    "duration": 180,
    "display": {
        "icon16x16": selected_icon_url  # URL from icon repository
    },
    "tracks": [...]
}
```

## Icon Categories

Common icon categories in the public repository:

- `music` - Musical notes, instruments
- `story` - Books, storytelling themes
- `bedtime` - Moon, stars, sleep-related
- `learning` - Educational icons
- `games` - Playful, game-related icons
- `nature` - Animals, plants, outdoor themes
- `transportation` - Cars, trains, planes
- `food` - Snacks and meals
- `emotions` - Facial expressions, feelings

## Best Practices

### 1. Use Descriptive Names
```python
# Good
name="Bedtime Moon"

# Bad
name="icon1"
```

### 2. Add Relevant Tags
```python
tags=["bedtime", "moon", "night", "sleep"]
```

### 3. Validate Before Upload
```python
try:
    service.validate_icon(icon_data)
    icon = await service.upload_custom_icon_bytes(...)
except ValueError as e:
    print(f"Icon validation failed: {e}")
```

### 4. Cache Frequently Used Icons
The `IconService` automatically caches icons retrieved by ID.

### 5. Test Icon Appearance
Since icons are only 16x16 pixels, test that they're recognizable at that size:

```python
from PIL import Image

img = Image.open("my_icon.png")
print(f"Size: {img.size}")  # Should be (16, 16)
img.show()  # View the icon
```

## Web UI Integration

### Icon Picker Component

The web UI should include an icon picker component:

```javascript
// React example
<IconPicker
  source="public"  // or "user" or "all"
  category="music"
  onSelect={(icon) => {
    setChapterIcon(icon.url);
  }}
/>
```

### Icon Preview

Always show a preview at actual size (16x16 pixels):

```html
<div class="icon-preview">
  <img src="{icon.url}" width="16" height="16" alt="{icon.name}" />
  <span>Preview on Yoto Mini</span>
</div>
```

### Upload Form

```html
<form enctype="multipart/form-data">
  <input type="file" accept=".png" />
  <input type="text" placeholder="Icon name" />
  <input type="text" placeholder="Tags (comma-separated)" />
  <select>
    <option value="">Select category...</option>
    <option value="music">Music</option>
    <option value="story">Story</option>
    <!-- ... -->
  </select>
  <button type="submit">Upload Icon</button>
</form>
```

## Troubleshooting

### Icon Not Displaying

**Problem**: Icon uploaded but not showing on Yoto Mini

**Solutions**:
1. Verify device is Yoto Mini (original Yoto Player has no display)
2. Check icon URL is correctly assigned to chapter's `display.icon16x16` field
3. Ensure icon is exactly 16x16 pixels
4. Verify PNG format is correct

### Upload Fails

**Problem**: Icon upload returns an error

**Solutions**:
1. Check file size is under 10KB
2. Verify resolution is exactly 16x16 pixels
3. Ensure format is PNG (not JPG, GIF, etc.)
4. Confirm access token is valid

### Icon Appears Blurry

**Problem**: Icon looks pixelated or unclear

**Solutions**:
1. Use simple, high-contrast designs
2. Avoid fine details that won't show at 16x16
3. Test icon at actual size before uploading
4. Consider using solid colors and bold shapes

## Related Documentation

- [Yoto API Reference](YOTO_API_REFERENCE.md)
- [Device Capabilities](#device-compatibility)
- [Card Creation Guide](ARCHITECTURE.md#card-creation)
- [Web UI Components](UI_COMPONENTS.md#iconpicker)

## Important Notes

⚠️ **Voice Control Not Available**: Neither Yoto Player nor Yoto Mini has a microphone, so voice control features cannot be implemented.

✓ **Icons Optional**: Icons enhance the Yoto Mini experience but are not required. Cards work fine without icons.

✓ **Public Repository**: Use the public repository when possible to save storage and provide consistent user experience.
