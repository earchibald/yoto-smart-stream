> **⚠️ DEPRECATED**: This documentation has been consolidated into the [yoto-smart-stream skill](../.github/skills/yoto-smart-stream/SKILL.md). Please refer to the skill for current information.
>
> **New location:** Content merged into `.github/skills/yoto-smart-stream/SKILL.md` and reference files

---

# Yoto Smart Stream - Open Planning Questions

This document captures key questions and decisions that need to be made during the implementation of Yoto Smart Stream.

## 1. User Experience & Features

### Authentication & Multi-User Support
- **Q1.1**: Should the system support multiple Yoto accounts/families?
  - Single user (personal use) is simpler
  - Multi-user requires authentication, user isolation, and more complex database schema
  - **Recommendation**: Start single-user, add multi-user later if needed

- **Q1.2**: How should users authenticate to the web UI?
  - Simple password protection?
  - OAuth integration?
  - No authentication (local network only)?
  - **Recommendation**: Start with no auth for MVP, add basic auth for production

### Interactive Features Priority
- **Q2.1**: What interactive features are highest priority?
  - Choose Your Own Adventure (CYOA) style stories
  - Time-based content (morning vs. evening stories)
  - Conditional logic based on previous choices
  - Display icon sequences for Yoto Mini
  - **Recommendation**: Start with basic CYOA button navigation
  - **Note**: Voice-activated responses are NOT possible as Yoto devices do not have microphones

- **Q2.2**: Should scripts support variables and state persistence?
  - Example: Remember user's name, previous choices across sessions
  - Adds complexity but enables richer experiences
  - **Recommendation**: Include basic state persistence in initial design

### Audio Management
- **Q3.1**: What audio sources should be supported?
  - User uploads only
  - Integration with external services (Spotify, Audible, podcast feeds)
  - Text-to-speech generation
  - Recording directly in the app
  - **Recommendation**: Start with uploads, add TTS as second feature

- **Q3.2**: Should the system automatically convert/optimize audio files?
  - Target format: MP3, 128-192 kbps
  - Normalize volume levels
  - Add fade in/out
  - **Recommendation**: Yes, auto-convert to MP3 for compatibility

- **Q3.3**: Maximum file size limits?
  - Single file: 100MB? 500MB? 1GB?
  - Total storage: Configurable limit
  - **Recommendation**: 500MB per file, configurable total storage

## 2. Technical Architecture

### Deployment Environment
- **Q4.1**: What is the primary deployment target?
  - Home server / Raspberry Pi (local network)
  - Cloud service (Heroku, Railway, Fly.io)
  - Docker container (portable)
  - **Recommendation**: Support all three with Docker as standard packaging

- **Q4.2**: How should audio files be stored and served?
  - Local file system
  - Cloud storage (S3, R2)
  - Database BLOBs (not recommended)
  - **Recommendation**: Local filesystem for self-hosted, S3 for cloud

### Database Choice
- **Q5.1**: Which database for production use?
  - SQLite (simple, file-based)
  - PostgreSQL (robust, scalable)
  - MySQL/MariaDB
  - **Recommendation**: SQLite for MVP, PostgreSQL option for scale

- **Q5.2**: How to handle database migrations?
  - Alembic (standard for SQLAlchemy)
  - Manual SQL scripts
  - **Recommendation**: Use Alembic for version-controlled migrations

### MQTT Connection Management
- **Q6.1**: How to handle MQTT disconnections?
  - Automatic reconnection with exponential backoff
  - Alert user of connection issues
  - Queue commands during disconnection
  - **Recommendation**: All three - reconnect, alert, and queue

- **Q6.2**: Should MQTT events be persisted?
  - Store all events in database for debugging/analytics
  - Store only important events (state changes)
  - Don't store (memory only)
  - **Recommendation**: Store important events with configurable retention

### API Design
- **Q7.1**: REST API only or add GraphQL?
  - REST is simpler and well-understood
  - GraphQL offers flexibility for complex queries
  - **Recommendation**: Start with REST, add GraphQL if needed

- **Q7.2**: Real-time updates: WebSocket, SSE, or polling?
  - WebSocket: Full duplex, more complex
  - Server-Sent Events (SSE): Simpler, one-way
  - Polling: Simplest, less efficient
  - **Recommendation**: SSE for event stream, WebSocket if bidirectional needed

## 3. Security & Privacy

### Data Privacy
- **Q8.1**: What data should be logged?
  - Player events (all, summary only, configurable)
  - API requests
  - Error logs only
  - **Recommendation**: Configurable logging with privacy-conscious defaults

- **Q8.2**: How long to retain event logs?
  - 7 days, 30 days, indefinite
  - **Recommendation**: 30 days default, configurable

### Access Control
- **Q9.1**: Should there be role-based access?
  - Admin: Full access
  - User: Can manage own content
  - Viewer: Read-only
  - **Recommendation**: Not needed for MVP, add for multi-user

- **Q9.2**: How to secure audio streaming endpoints?
  - Public URLs (simple but less secure)
  - Signed URLs with expiration
  - Token-based authentication
  - **Recommendation**: Signed URLs for cloud, local network trust for self-hosted

### API Security
- **Q10.1**: Rate limiting strategy?
  - Per IP: 100 requests/minute
  - Per user: 1000 requests/hour
  - No limits (trust users)
  - **Recommendation**: Implement basic rate limiting, adjustable

## 4. User Interface Design

### Web UI Framework
- **Q11.1**: Which frontend approach?
  - SPA (React, Vue): Modern, smooth UX
  - Server-side rendering (HTMX, Jinja): Simpler, faster initial load
  - Hybrid: SSR + islands of interactivity
  - **Recommendation**: HTMX + Alpine.js for simplicity

- **Q11.2**: Mobile responsiveness required?
  - Yes: Design mobile-first
  - Desktop-focused: Simpler layouts
  - **Recommendation**: Yes, mobile-first design

### UI Features
- **Q12.1**: What's the minimum viable UI?
  - Player status dashboard
  - Card library browser
  - Upload audio form
  - Script editor
  - **Recommendation**: All four are core features

- **Q12.2**: Should there be a visual script editor?
  - Drag-and-drop flow chart editor (complex)
  - JSON editor with validation (simpler)
  - Form-based editor (middle ground)
  - **Recommendation**: Form-based for MVP, visual editor later

- **Q12.3**: Real-time preview during script editing?
  - Live preview pane showing script flow
  - Test mode to simulate playback
  - **Recommendation**: Test mode is essential, preview is nice-to-have

## 5. Audio Processing

### Format Conversion
- **Q13.1**: Which audio library to use?
  - FFmpeg (powerful, external dependency)
  - pydub (Python, uses FFmpeg)
  - sox (alternative)
  - **Recommendation**: pydub with FFmpeg for broad format support

- **Q13.2**: Audio quality targets?
  - 128 kbps MP3 (smaller files)
  - 192 kbps MP3 (better quality)
  - 256 kbps MP3 (highest quality)
  - VBR (variable bit rate)
  - **Recommendation**: 192 kbps CBR for balance

### Audio Enhancement
- **Q14.1**: Should audio be normalized?
  - Yes: Consistent volume across tracks
  - No: Preserve original audio
  - Optional: User choice
  - **Recommendation**: Yes, with option to disable

- **Q14.2**: Add silence detection/trimming?
  - Automatically trim long silences
  - Add standard gaps between chapters
  - **Recommendation**: Optional feature, off by default

## 6. Choose Your Own Adventure Specifics

### Script Capabilities
- **Q15.1**: What conditions should scripts support?
  - Time of day
  - Day of week
  - Previous choices
  - Random outcomes
  - External data (weather, etc.)
  - **Recommendation**: Start with previous choices, add others incrementally

- **Q15.2**: How complex should branching be?
  - Simple: 2 choices per decision point
  - Medium: 2-4 choices
  - Complex: Unlimited choices
  - **Recommendation**: Start with 2-4 choices

### State Management
- **Q16.1**: Where to store playback state?
  - Server-side: Persistent, survives card removal
  - Player-side: Would need custom Yoto card
  - Both: Redundant but reliable
  - **Recommendation**: Server-side only for MVP

- **Q16.2**: Should state be sharable across players?
  - Story continues on any family player
  - Story is player-specific
  - **Recommendation**: Player-specific for clarity

### Button Mapping
- **Q17.1**: How to map buttons for choices?
  - Left = Choice A, Right = Choice B
  - Numbers via button combos
  - **Recommendation**: Left/Right for binary choices
  - **Note**: Voice commands are not possible as Yoto devices lack microphones

- **Q17.2**: What about more than 2 choices?
  - Present 2 at a time, more after
  - Use pause button as "more options"
  - **Recommendation**: Present 2, allow replay to see more

## 7. Performance & Scalability

### Caching Strategy
- **Q18.1**: What should be cached and for how long?
  - Player status: 5 minutes
  - Library data: 15 minutes
  - Audio metadata: 1 hour
  - **Recommendation**: As above, configurable

- **Q18.2**: Cache implementation?
  - In-memory (simple, lost on restart)
  - Redis (persistent, faster)
  - Database (simplest, slower)
  - **Recommendation**: In-memory for MVP, Redis for scale

### Audio Streaming Optimization
- **Q19.1**: Support byte-range requests?
  - Yes: Enables seeking, required for large files
  - No: Simpler but poor UX
  - **Recommendation**: Yes, use FileResponse with range support

- **Q19.2**: CDN or direct serving?
  - CDN: Better for multiple users, cloud hosting
  - Direct: Simpler for self-hosted
  - **Recommendation**: Direct for self-hosted, CDN optional for cloud

## 8. Testing & Quality Assurance

### Test Coverage
- **Q20.1**: What test coverage target?
  - 80%+ (comprehensive)
  - 60%+ (important paths)
  - Best effort
  - **Recommendation**: 60%+ for core logic

- **Q20.2**: Integration tests with real Yoto API?
  - Yes: More realistic but requires credentials
  - No: Mock everything
  - Optional: Flag for real API tests
  - **Recommendation**: Mock for unit tests, optional integration tests

### Device Testing
- **Q21.1**: Which Yoto models to support?
  - Yoto Player (original) - No display screen, no microphone
  - Yoto Mini - 16x16 pixel display, no microphone
  - Both
  - **Recommendation**: Both, document differences in display capabilities
  - **Note**: Neither device has a microphone, so voice control features are not applicable

- **Q21.2**: How to handle display icons for Yoto Mini?
  - Support public icon repository from Yoto API
  - Allow custom icon uploads (16x16 PNG)
  - Provide icon selection in card/chapter editor
  - Show icon preview at actual size
  - **Recommendation**: Full support for both public and custom icons
  - **Note**: Icons only display on Yoto Mini, not on original Yoto Player

## 9. Documentation

### User Documentation
- **Q22.1**: What format for user docs?
  - Markdown in repo
  - Separate documentation site
  - In-app help
  - **Recommendation**: Markdown + in-app tooltips

- **Q22.2**: Documentation priorities?
  1. Quick start guide
  2. Card creation tutorial
  3. Script writing guide
  4. API reference
  5. Troubleshooting
  - **Recommendation**: Deliver in this order

### Developer Documentation
- **Q23.1**: API documentation format?
  - OpenAPI/Swagger (auto-generated)
  - Manual markdown
  - **Recommendation**: OpenAPI with FastAPI auto-docs

## 10. Future Enhancements

### Potential Features
- **Q24.1**: What features to consider for future releases?
  - Text-to-speech integration
  - Podcast feed import
  - Voice recording in browser
  - Music library integration
  - Social features (share cards)
  - Cloud backup/sync
  - Mobile app
  - **Recommendation**: Prioritize based on user feedback

### Community & Ecosystem
- **Q25.1**: Open source or proprietary?
  - Fully open source
  - Source available
  - Closed source
  - **Recommendation**: Open source for community contributions

- **Q25.2**: Accept community card scripts?
  - Built-in card library
  - User-submitted scripts
  - Marketplace
  - **Recommendation**: Support imports, community library phase 2

## Decision Log

| Question | Decision | Date | Rationale |
|----------|----------|------|-----------|
| TBD | TBD | TBD | TBD |

---

## How to Use This Document

1. **During Planning**: Review questions and make decisions
2. **During Development**: Reference decisions when implementing features
3. **During Review**: Update with actual decisions made
4. **After Launch**: Track what worked and what to revisit

## Next Steps

- [ ] Review questions with stakeholders
- [ ] Make initial decisions for MVP scope
- [ ] Document decisions in the table above
- [ ] Update architecture doc based on decisions
- [ ] Begin implementation

---

*This document should be updated as decisions are made and new questions arise.*
