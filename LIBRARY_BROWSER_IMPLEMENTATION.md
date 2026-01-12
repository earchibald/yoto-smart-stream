# Library Browser Implementation

## Overview

Added a "Select from Library" feature to the player controls that allows users to browse their Yoto library, select a card, view its chapters, and play a specific chapter on any online player.

## Features

- **Library Browser**: Grid view of all cards in the user's library with cover images
- **Chapter Selection**: List view of chapters for a selected card with icons and durations
- **Direct Playback**: Click to play any chapter on the target player
- **Clean UI**: Modal-based interface matching the existing player detail modal style

## Implementation Details

### Backend API Endpoints

#### 1. GET /api/library/{card_id}/chapters

Returns chapter information for a specific card.

**Response:**
```json
{
  "card_id": "abc123",
  "card_title": "Story Title",
  "card_author": "Author Name",
  "card_cover": "https://...",
  "chapters": [
    {
      "key": "01",
      "title": "Chapter 1",
      "duration": 120,
      "icon": "https://..."
    }
  ],
  "total_chapters": 10
}
```

**Location:** `yoto_smart_stream/api/routes/library.py`

#### 2. POST /api/players/{player_id}/play-card

Starts playback of a specific card and chapter on a player.

**Request Body:**
```json
{
  "card_id": "abc123",
  "chapter": 1
}
```

**Location:** `yoto_smart_stream/api/routes/players.py`

### Frontend Components

#### 1. Library Button

Added a "📚" button to each player's control panel that opens the library browser.

**Location:** `yoto_smart_stream/static/js/dashboard.js` (line ~322)

#### 2. Library Browser Modal

Modal displaying a grid of library cards with cover images and titles.

- Fetches library data from `/api/library`
- Shows card covers, titles, and authors
- Click on a card to view its chapters

**HTML:** `yoto_smart_stream/static/index.html`
**CSS:** `yoto_smart_stream/static/css/style.css`
**JavaScript:** `dashboard.js` - `showLibraryBrowser(playerId)`

#### 3. Chapter Browser Modal

Modal displaying a list of chapters for the selected card.

- Fetches chapter data from `/api/library/{card_id}/chapters`
- Shows chapter icons, titles, and durations
- Click on a chapter to start playback

**HTML:** `yoto_smart_stream/static/index.html`
**CSS:** `yoto_smart_stream/static/css/style.css`
**JavaScript:** `dashboard.js` - `selectCard(playerId, cardId)`, `playChapter(playerId, cardId, chapterKey)`

### Key JavaScript Functions

1. **showLibraryBrowser(playerId)**: Opens library modal and fetches cards
2. **closeLibraryBrowser()**: Closes library modal
3. **selectCard(playerId, cardId)**: Opens chapter modal and fetches chapters
4. **closeChapterBrowser()**: Closes chapter modal
5. **playChapter(playerId, cardId, chapterKey)**: Initiates playback
6. **formatDuration(seconds)**: Formats chapter duration as MM:SS

### Styling

#### Library Grid
- Responsive grid layout (150px minimum column width)
- Hover effects with lift animation
- Cover images with fallback emoji
- Truncated text for long titles

#### Chapter List
- Vertical list layout
- Chapter icons (48x48px)
- Duration display
- Play button with hover animation

### User Flow

1. User clicks "📚" button on a player control panel
2. Library browser modal opens, showing all cards
3. User clicks on a card
4. Chapter browser modal opens, showing chapters for that card
5. User clicks on a chapter to play
6. Playback starts on the player
7. Both modals close automatically
8. Player list refreshes after 1 second to show updated state

## Reference

Implementation follows patterns from `yoto_ha` Home Assistant integration:
- Media browsing with `async_browse_media`
- Chapter navigation
- Card playback via `async_play_card`

## Testing

To test the feature:

1. Start the application
2. Ensure you have authenticated with Yoto API
3. Ensure you have cards in your library
4. Open the dashboard
5. Click the "📚" button on an online player
6. Select a card from the library
7. Select a chapter to play
8. Verify playback starts on the player

## Files Modified

- `yoto_smart_stream/api/routes/library.py` - Added chapters endpoint
- `yoto_smart_stream/api/routes/players.py` - Added play-card endpoint
- `yoto_smart_stream/static/js/dashboard.js` - Added library browser functions
- `yoto_smart_stream/static/index.html` - Added library and chapter modals
- `yoto_smart_stream/static/css/style.css` - Added modal styling

## Future Enhancements

- Add search/filter for library cards
- Add playlist support
- Show currently playing card/chapter indicator
- Add chapter preview/description
- Support for playing from specific timestamp
