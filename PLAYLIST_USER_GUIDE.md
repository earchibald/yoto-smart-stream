# Create Playlist Feature - User Guide

## Overview

The "Create Playlist" feature allows you to turn your managed audio streams into Yoto playlists that appear in your personal Yoto library. This is perfect for creating custom audio experiences for your Yoto devices.

## Quick Start

### Step 1: Create a Managed Stream
1. Go to **Smart Streams** page
2. Click **"🎬 Stream Scripter"** button
3. Create a new queue:
   - Enter queue name (e.g., "bedtime-stories")
   - Select audio files from the available list
   - Click "Save Queue"

### Step 2: Create a Playlist from the Stream
1. Find your newly created stream in the "Managed Streams" section
2. Click the **"📋 Create Playlist"** button on the stream card
3. A modal dialog will appear with:
   - **Stream selector**: Your stream should be pre-selected
   - **Playlist name**: Enter a name (e.g., "Bedtime Stories")
4. Click **"Create Playlist"** button
5. Success! You'll see a message with your playlist ID

### Step 3: Use Your Playlist
1. Open your Yoto app
2. Go to your library
3. Find the new playlist with the name you created
4. Play it on any of your Yoto devices!

## Understanding the UI

### Stream Card Actions

Each managed stream shows these buttons:

| Button | Action | For |
|--------|--------|-----|
| 📋 Copy URL | Copies the stream URL to clipboard | Sharing/documentation |
| ▶️ Preview | Plays a preview of the stream | Listening/testing |
| 📋 Create Playlist | Opens the create playlist dialog | Making Yoto playlists |
| 🗑️ Delete | Removes the stream entirely | Cleanup |

*Note: Test streams don't have create/delete options (reserved)*

### Create Playlist Modal

When you click "Create Playlist", a modal appears:

```
┌─────────────────────────────────────────┐
│ 📋 Create Playlist              [✕]     │
├─────────────────────────────────────────┤
│                                         │
│ Select Stream:                          │
│ [▼ my-stream          ▼]               │
│ Choose a managed stream to link         │
│                                         │
│ Playlist Name:                          │
│ [My Favorite Stories           ]       │
│ This will be the name shown in Yoto    │
│                                         │
│ [✓ Create Playlist]  [Cancel]          │
│                                         │
└─────────────────────────────────────────┘
```

**Fields**:
- **Select Stream**: Dropdown showing available streams (excluding test-stream)
- **Playlist Name**: Text input for your custom name
- **Buttons**: Create to submit, Cancel to close

**Result Message** (appears above buttons after submission):
- Success: "✅ Playlist created! ID: playlist_..." (green)
- Error: "Failed to create: [error details]" (red)

## Features & Benefits

### Automatic Streaming
- Your playlist automatically streams from your server
- No need to re-upload audio files
- Changes to stream content update the playlist

### Dynamic Content
- Playlists can have different play modes:
  - **Sequential**: Play in order once
  - **Loop**: Repeat indefinitely
  - **Shuffle**: Random order, once through
  - **Endless Shuffle**: Random forever
- These modes are set on the stream, not the playlist

### Easy Management
- Create multiple playlists from the same stream
- Each playlist has its own name in your Yoto library
- Delete playlists directly from Yoto app

## Example Workflows

### Example 1: Bedtime Story Playlist

1. **Create Stream**:
   - Stream name: `bedtime-stories`
   - Add files: sleepy-time.mp3, goodnight-moon.mp3, gentle-rest.mp3
   - Set play mode: Loop

2. **Create Playlist**:
   - Stream: bedtime-stories
   - Playlist name: "Bedtime Stories"

3. **Result**:
   - Playlist appears in Yoto app
   - Set as nighttime routine
   - Plays all 3 stories on repeat every night

### Example 2: Morning Routine Playlist

1. **Create Stream**:
   - Stream name: `morning-routine`
   - Add files: wake-up.mp3, breakfast-time.mp3, get-ready.mp3
   - Set play mode: Sequential

2. **Create Playlist**:
   - Stream: morning-routine
   - Playlist name: "Morning Routine"

3. **Result**:
   - Plays stories in order during morning routine
   - Automatically progresses through files

### Example 3: Relaxation Playlist (Loop)

1. **Create Stream**:
   - Stream name: `relaxation-mix`
   - Add files: meditation1.mp3, meditation2.mp3, meditation3.mp3
   - Set play mode: Endless Shuffle

2. **Create Playlist**:
   - Stream: relaxation-mix
   - Playlist name: "Relaxation Mix"

3. **Result**:
   - Plays random meditation track
   - Automatically picks next random track
   - Never repeats same track twice in a row

## Troubleshooting

### Issue: "No streams available. Create a stream first."

**Solution**: You need to create a managed stream before creating a playlist.
1. Click "🎬 Stream Scripter"
2. Create a new queue
3. Add audio files
4. Save the queue
5. Try creating the playlist again

### Issue: "Stream queue has no files"

**Solution**: Your stream exists but is empty. Add files to it:
1. Click "🎬 Stream Scripter"
2. Select your stream from the dropdown
3. Add audio files from the available list
4. Click "Save Queue"
5. Try creating the playlist again

### Issue: "Failed to authenticate with Yoto API"

**Solution**: Your login session has expired or invalid. 
1. Logout from the Yoto Smart Stream app
2. Login again
3. Try creating the playlist again

### Issue: Playlist doesn't appear in Yoto app

**Solution**: The playlist was created but may not be visible yet.
1. Refresh your Yoto app
2. Log out and back in
3. Check if playlist appears in "Your Playlists" section
4. Try creating a new test playlist to see if it works

### Issue: "PUBLIC_URL not configured"

**Solution**: Your server administrator needs to set the PUBLIC_URL:
1. This is an environment variable that tells the system your public URL
2. Example: `https://example.ngrok.io` or `https://yoto.example.com`
3. Contact your system administrator to set this up

## Tips & Best Practices

### Naming Conventions
- Use clear, descriptive names for playlists
- Examples: "Bedtime Stories", "Learning Adventures", "Music Mix"
- Avoid special characters - stick to letters, numbers, spaces

### Stream Organization
- One stream per audio experience
- Group related files in one stream
- Use meaningful stream names (bedtime-stories, learning, music)

### Play Mode Selection
- **Sequential**: Stories, audiobooks, lessons
- **Loop**: Recurring routines, meditation, sleep aids
- **Shuffle**: Music mixes, variety
- **Endless Shuffle**: Variety without immediate repeats

### Testing
- Use "Preview" button to test stream before creating playlist
- Try a short test playlist first
- Verify in Yoto app before sharing

### Sharing
- Playlists created with this feature are personal
- Share access to your Yoto devices through Yoto's family sharing
- Each family member can create their own playlists

## Technical Notes

- Playlists are created in your Yoto account
- They link to your server's streaming URL
- Your server must be accessible from the internet
- Deletion removes from Yoto, but keeps stream for reuse

## Support & Questions

For issues or feature requests:
1. Check the troubleshooting section above
2. Review stream settings and available files
3. Verify PUBLIC_URL is configured
4. Check browser console for detailed error messages
5. Contact your system administrator for server-side issues

## Related Features

- **Smart Streams**: Create and manage audio streams
- **Play Modes**: Control how content is played (Sequential, Loop, Shuffle, Endless Shuffle)
- **Stream Scripter**: GUI for creating and managing streams
- **Audio Files**: Upload and manage audio content
- **Text-to-Speech**: Generate audio from text

---

**Version**: 1.0  
**Last Updated**: January 2026  
**Status**: Production Ready
