# Playlist Feature Implementation

## Overview

The Streams UI now includes a "Create Playlist" button that allows users to create Yoto playlists directly from managed streams. This feature integrates with the Yoto API to create playlists that point to server-managed audio streams.

## Features

### Create Playlist
- **Button Location**: Each managed stream card (except test-stream) now has a "📋 Create Playlist" button
- **Dialog**: Clicking the button opens a modal dialog where users can:
  - Select which stream to create a playlist from
  - Enter a custom name for the playlist
  - Confirm creation
- **Backend Integration**: The playlist is created via the Yoto API and points to the stream's audio URL
- **User Feedback**: Success/error messages inform the user of the result and provide the playlist ID

### Delete Playlist
- **Endpoint**: `DELETE /api/streams/playlists/{playlist_id}`
- **Authentication**: Requires valid user authentication
- **Confirmation**: Users are prompted to confirm deletion before proceeding
- **Feedback**: Success or error messages are shown after deletion

## API Endpoints

### Create Playlist
```
POST /api/streams/{stream_name}/create-playlist
```

**Request Body**:
```json
{
  "playlist_name": "My Custom Playlist",
  "stream_name": "my-stream"
}
```

**Response** (201 Created):
```json
{
  "success": true,
  "playlist_id": "playlist-uuid-here",
  "playlist_name": "My Custom Playlist",
  "stream_name": "my-stream",
  "streaming_url": "https://example.com/api/streams/my-stream/stream.mp3",
  "message": "Playlist 'My Custom Playlist' created successfully!"
}
```

**Error Response**:
```json
{
  "detail": "Stream queue 'my-stream' not found. Create the stream first."
}
```

### Delete Playlist
```
DELETE /api/streams/playlists/{playlist_id}
```

**Response** (200 OK):
```json
{
  "success": true,
  "playlist_id": "playlist-uuid-here",
  "message": "Playlist deleted successfully!"
}
```

## UI Components

### Streams Page Changes

**New Button in Stream Cards**:
- Added "📋 Create Playlist" button next to each managed stream
- Only shown for non-reserved streams (not test-stream)
- Styled consistently with other action buttons

**New Modal Dialog**:
- Modal ID: `create-playlist-modal`
- Components:
  - Stream selector dropdown
  - Playlist name input field
  - Result/error message display area
  - Create and Cancel buttons

### JavaScript Functions

**New Functions in `streams.js`**:

1. **`openPlaylistModal(selectedStream)`**
   - Opens the create playlist modal
   - Optionally pre-selects a stream
   - Loads available streams into selector

2. **`closePlaylistModal()`**
   - Closes the create playlist modal
   - Clears form and results

3. **`loadPlaylistStreamSelector(selectedStream)`**
   - Fetches list of available streams
   - Populates the stream selector dropdown
   - Filters out test-stream

4. **`createPlaylist()`**
   - Validates form inputs
   - Sends POST request to create playlist API
   - Shows success/error messages
   - Reloads managed streams on success

5. **`deletePlaylist(playlistId)`**
   - Prompts user for confirmation
   - Sends DELETE request to API
   - Shows success/error messages
   - Reloads managed streams on success

6. **`showPlaylistResult(message, type)`**
   - Displays result messages in the modal
   - Auto-hides error messages after 5 seconds
   - Keeps success messages visible

## Backend Implementation

### Python Changes

**File**: `yoto_smart_stream/api/routes/streams.py`

**New Request Models**:
```python
class CreatePlaylistRequest(BaseModel):
    playlist_name: str
    stream_name: str

class DeletePlaylistRequest(BaseModel):
    playlist_id: str
```

**New Endpoints**:

1. **Create Playlist**
   - Route: `POST /api/streams/{stream_name}/create-playlist`
   - Verifies stream exists and has files
   - Constructs playlist data structure
   - Makes authenticated API call to Yoto API
   - Returns playlist ID and confirmation

2. **Delete Playlist**
   - Route: `DELETE /api/streams/playlists/{playlist_id}`
   - Requires authentication
   - Makes authenticated API call to Yoto API
   - Returns success confirmation

**API Integration**:
- Uses Yoto API endpoints:
  - `POST https://api.yotoplay.com/playlist` - Create playlist
  - `DELETE https://api.yotoplay.com/playlist/{id}` - Delete playlist
- Uses OAuth2 Bearer token authentication
- Handles token refresh automatically via YotoClient

## Data Flow

### Create Playlist Flow
1. User clicks "📋 Create Playlist" on a stream card
2. Modal opens, showing available streams
3. User selects stream and enters playlist name
4. Form validation ensures both fields are filled
5. Frontend sends POST request to `/api/streams/{stream_name}/create-playlist`
6. Backend verifies stream exists and has files
7. Backend creates OAuth2 Bearer token request
8. Backend calls Yoto API to create playlist
9. Yoto API returns playlist ID
10. Backend returns success response with playlist ID
11. Frontend shows success message and reloads streams

### Delete Playlist Flow
1. User clicks delete button on a linked playlist
2. Confirmation dialog appears
3. User confirms deletion
4. Frontend sends DELETE request to `/api/streams/playlists/{playlist_id}`
5. Backend authenticates and refreshes token if needed
6. Backend calls Yoto API to delete playlist
7. Yoto API confirms deletion
8. Backend returns success response
9. Frontend shows success message and reloads streams

## Requirements

- **Authentication**: User must be logged in to create/delete playlists
- **Yoto OAuth2**: Requires valid refresh token for Yoto API access
- **PUBLIC_URL**: Must be set in environment for generating correct streaming URLs
- **Stream State**: Stream must exist and contain at least one file

## Error Handling

**Frontend**:
- Form validation before submission
- Displays error messages from backend
- Disables buttons during submission

**Backend**:
- Validates stream exists
- Checks stream has files
- Verifies PUBLIC_URL is configured
- Handles Yoto API errors gracefully
- Logs all errors for debugging

## Testing

### Manual Testing Checklist

1. **Create Playlist**
   - [ ] Click "Create Playlist" button on a stream
   - [ ] Verify streams dropdown loads correctly
   - [ ] Select a stream and enter a name
   - [ ] Click "Create Playlist"
   - [ ] Verify success message shows playlist ID
   - [ ] Verify playlist appears in Yoto app

2. **Error Cases**
   - [ ] Try to create without selecting stream (error shown)
   - [ ] Try to create without entering name (error shown)
   - [ ] Try on empty stream (error: stream has no files)
   - [ ] Try without PUBLIC_URL set (error: URL not configured)

3. **Delete Playlist**
   - [ ] Attempt to delete playlist (confirmation shown)
   - [ ] Confirm deletion
   - [ ] Verify success message
   - [ ] Verify playlist removed from Yoto app

## Browser Compatibility

- Chrome/Chromium: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- Edge: ✅ Full support

## Security Considerations

- **Authentication**: All endpoints require valid user authentication
- **OAuth2**: Uses Bearer tokens for Yoto API access
- **Token Refresh**: Automatic token refresh on each request
- **Input Validation**: Playlist names and stream names validated
- **Authorization**: Only authenticated users can create/delete playlists

## Known Limitations

- Playlists must be linked to existing streams
- Playlist name cannot be changed after creation (create new playlist)
- Only users with valid Yoto API tokens can create playlists
- Playlist streaming uses the stream URL (dynamic content)

## Future Enhancements

- [ ] Edit playlist metadata (name, description)
- [ ] Link multiple streams to one playlist
- [ ] Browse and manage linked playlists
- [ ] Share playlist links
- [ ] Playlist statistics and usage tracking
- [ ] Custom playlist icons/cover art
- [ ] Batch playlist operations

## Related Documentation

- [Yoto API Reference](https://yoto.dev)
- [Smart Streams Guide](./README.md)
- [Dynamic Streaming](./docs/DYNAMIC_STREAMING.md)
