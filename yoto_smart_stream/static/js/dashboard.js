// Dashboard JavaScript

// API base URL
const API_BASE = '/api';

// Fuzzy match helper
function fuzzyMatch(query, text) {
    if (!query) return true;
    const q = query.toLowerCase();
    const t = text.toLowerCase();
    let qi = 0;
    for (let i = 0; i < t.length && qi < q.length; i++) {
        if (t[i] === q[qi]) qi++;
    }
    return qi === q.length;
}

// Apply fuzzy filter to library modal
function applyLibraryFilter() {
    const query = document.getElementById('libraryFilter')?.value || '';
    const cards = document.querySelectorAll('#libraryContent .library-card');
    let visibleCount = 0;
    cards.forEach(card => {
        const title = card.getAttribute('data-title') || '';
        const match = fuzzyMatch(query, title);
        card.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    });
    // Show "no results" message if nothing matches
    const grid = document.getElementById('libraryContent');
    if (visibleCount === 0 && query) {
        if (!grid.querySelector('.no-results')) {
            const msg = document.createElement('p');
            msg.className = 'no-results';
            msg.textContent = `No cards match "${query}"`;
            grid.appendChild(msg);
        }
    } else {
        const msg = grid.querySelector('.no-results');
        if (msg) msg.remove();
    }
}

// Auth polling state
let authPollInterval = null;
let deviceCode = null;

// Player refresh polling state
let playerRefreshInterval = null;
let isLoadingPlayers = false;

// Check user authentication first
async function checkUserAuth() {
    try {
        const response = await fetch('/api/user/session', { credentials: 'include' });
        const data = await response.json();
        
        if (!data.authenticated) {
            // Redirect to login page
            window.location.href = '/login';
            return false;
        }
        
        // Show logout button if authenticated
        const logoutBtn = document.getElementById('logout-button');
        if (logoutBtn) {
            logoutBtn.style.display = 'inline-block';
        }
        
        return true;
    } catch (error) {
        console.error('Error checking authentication:', error);
        window.location.href = '/login';
        return false;
    }
}

// User logout function
async function userLogout() {
    try {
        await fetch('/api/user/logout', { 
            method: 'POST',
            credentials: 'include' 
        });
        window.location.href = '/login';
    } catch (error) {
        console.error('Logout error:', error);
        window.location.href = '/login';
    }
}
// Track previous player states for change detection
let previousPlayerStates = {};

// Track active slider interactions to prevent updates during drag/change
let activeSliders = new Set();
let sliderCooldowns = new Map(); // playerId -> timestamp
let programmaticUpdates = new Set(); // playerId -> currently being updated programmatically

// Load initial data
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication before loading anything else
    const isAuthenticated = await checkUserAuth();
    if (!isAuthenticated) {
        return; // Stop loading if not authenticated
    }
    
    checkAuthStatus();
    loadSystemStatus();
    loadPlayers();
    loadAudioFiles();
    
    // Start auto-refresh for players every 5 seconds
    startPlayerAutoRefresh();
    
    // Setup TTS modal close handlers
    const ttsCloseBtn = document.getElementById('tts-modal-close-btn');
    const ttsModal = document.getElementById('tts-modal');
    
    if (ttsCloseBtn) {
        ttsCloseBtn.addEventListener('click', closeTTSModal);
    }
    
    // Close TTS modal when clicking outside
    if (ttsModal) {
        ttsModal.addEventListener('click', function(event) {
            if (event.target === ttsModal) {
                closeTTSModal();
            }
        });
    }
    
    // Setup TTS form
    const ttsForm = document.getElementById('tts-form');
    if (ttsForm) {
        ttsForm.addEventListener('submit', handleTTSSubmit);
    }
    
    // Setup filename preview
    const filenameInput = document.getElementById('tts-filename');
    if (filenameInput) {
        filenameInput.addEventListener('input', updateFilenamePreview);
    }
    
    // Setup text length counter
    const textInput = document.getElementById('tts-text');
    if (textInput) {
        textInput.addEventListener('input', updateTextLength);
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    stopPlayerAutoRefresh();
});

// Check authentication status
async function checkAuthStatus() {
    try {
        const response = await fetch(`${API_BASE}/auth/status`);
        if (!response.ok) throw new Error('Failed to check auth status');
        
        const data = await response.json();
        
        if (data.authenticated) {
            // Hide auth section, show logout button
            document.getElementById('auth-section').style.display = 'none';
            document.getElementById('logout-button').style.display = 'inline-block';
        } else {
            // Show auth section, hide logout button
            document.getElementById('auth-section').style.display = 'block';
            document.getElementById('logout-button').style.display = 'none';
        }
    } catch (error) {
        console.error('Error checking auth status:', error);
        // Show auth section on error
        document.getElementById('auth-section').style.display = 'block';
    }
}

// Start authentication flow
async function startAuth() {
    const loginButton = document.getElementById('login-button');
    const authWaiting = document.getElementById('auth-waiting');
    const authActions = document.getElementById('auth-actions');
    const authMessage = document.getElementById('auth-message');
    
    loginButton.disabled = true;
    loginButton.textContent = 'Starting...';
    
    try {
        const response = await fetch(`${API_BASE}/auth/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to start authentication');
        }
        
        const data = await response.json();
        deviceCode = data.device_code;
        
        // Update UI with auth details
        document.getElementById('auth-url').href = data.verification_uri_complete || data.verification_uri;
        document.getElementById('auth-url').textContent = data.verification_uri;
        document.getElementById('user-code').textContent = data.user_code;
        
        // Show waiting section
        authWaiting.style.display = 'block';
        authActions.style.display = 'none';
        authMessage.textContent = 'Complete the authorization in your browser, then we\'ll automatically connect.';
        
        // Start polling for completion
        startAuthPolling();
        
    } catch (error) {
        console.error('Error starting auth:', error);
        alert('Failed to start authentication: ' + error.message);
        loginButton.disabled = false;
        loginButton.textContent = '🔑 Connect Yoto Account';
    }
}

// Poll for auth completion
function startAuthPolling() {
    // Clear any existing interval
    if (authPollInterval) {
        clearInterval(authPollInterval);
    }
    
    // Poll every 3 seconds
    authPollInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/auth/poll`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_code: deviceCode })
            });
            
            if (!response.ok) throw new Error('Failed to poll auth status');
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // Authentication successful!
                clearInterval(authPollInterval);
                authPollInterval = null;
                
                // Show success message
                const authWaiting = document.getElementById('auth-waiting');
                authWaiting.innerHTML = `
                    <div class="auth-success">
                        <div class="success-icon">✓</div>
                        <p>Successfully connected!</p>
                    </div>
                `;
                
                // Reload the page after a short delay
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
                
            } else if (data.status === 'expired') {
                // Token expired
                clearInterval(authPollInterval);
                authPollInterval = null;
                alert('Authentication expired. Please try again.');
                window.location.reload();
                
            }
            // Otherwise keep polling (status === 'pending')
            
        } catch (error) {
            console.error('Error polling auth:', error);
            // Continue polling even on errors
        }
    }, 3000);
}

// Logout
async function logout() {
    if (!confirm('Are you sure you want to logout?')) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/auth/logout`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        if (!response.ok) throw new Error('Failed to logout');
        
        // Reload the page
        window.location.reload();
        
    } catch (error) {
        console.error('Error logging out:', error);
        alert('Failed to logout: ' + error.message);
    }
}


// Load system status
async function loadSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (!response.ok) throw new Error('Failed to fetch status');
        
        const data = await response.json();
        
        // Update version
        document.getElementById('app-version').textContent = `v${data.version}`;
        
        // Update status indicator
        const statusEl = document.getElementById('status');
        const statusTextEl = document.getElementById('status-text');
        statusEl.classList.remove('error');
        statusTextEl.textContent = 'System Running';
        
        // Update stats - leave audio count for loadAudioFiles to set
        document.getElementById('mqtt-status').textContent = data.features?.mqtt_events ? 'Enabled' : 'Disabled';
        document.getElementById('environment').textContent = data.environment || 'Unknown';
        
    } catch (error) {
        console.error('Error loading status:', error);
        const statusEl = document.getElementById('status');
        const statusTextEl = document.getElementById('status-text');
        statusEl.classList.add('error');
        statusTextEl.textContent = 'Error';
    }
}

// Load players list
async function loadPlayers() {
    const container = document.getElementById('players-list');
    
    // Prevent concurrent API calls
    if (isLoadingPlayers) {
        return;
    }
    
    isLoadingPlayers = true;
    
    try {
        const response = await fetch(`${API_BASE}/players`);
        if (!response.ok) throw new Error('Failed to fetch players');
        
        const players = await response.json();
        
        // Console logging for MQTT events and status changes
        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false, fractionalSecondDigits: 3 });
        console.log(`%c[${timestamp}] 📡 Player Status Update`, 'color: #4CAF50; font-weight: bold');
        
        // Detect and log changes for each player
        players.forEach(player => {
            const prevState = previousPlayerStates[player.id];
            const changes = [];
            
            if (prevState) {
                // Volume change (likely MQTT event)
                if (prevState.volume !== player.volume) {
                    changes.push(`Volume: ${prevState.volume}/16 → ${player.volume}/16`);
                }
                // Playing status change
                if (prevState.playing !== player.playing) {
                    changes.push(`Playback: ${prevState.playing ? 'Playing' : 'Stopped'} → ${player.playing ? 'Playing' : 'Stopped'}`);
                }
                // Battery change
                if (prevState.battery_level !== player.battery_level) {
                    changes.push(`Battery: ${prevState.battery_level}% → ${player.battery_level}%`);
                }
                // Card change
                if (prevState.active_card !== player.active_card) {
                    changes.push(`Card: ${prevState.active_card || 'none'} → ${player.active_card || 'none'}`);
                }
                // Online status change
                if (prevState.online !== player.online) {
                    changes.push(`Status: ${prevState.online ? 'Online' : 'Offline'} → ${player.online ? 'Online' : 'Offline'}`);
                }
            }
            
            if (changes.length > 0) {
                console.log(`%c  🎮 ${player.name}:`, 'color: #2196F3; font-weight: bold');
                changes.forEach(change => {
                    console.log(`    • ${change}`);
                });
            } else if (!prevState) {
                // First load
                console.log(`  🎮 ${player.name}: Online=${player.online}, Volume=${player.volume}/16, Playing=${player.playing}`);
            }
            
            // Store current state for next comparison
            previousPlayerStates[player.id] = {
                volume: player.volume,
                playing: player.playing,
                battery_level: player.battery_level,
                active_card: player.active_card,
                online: player.online
            };
        });
        
        // Update player count
        document.getElementById('player-count').textContent = players.length;
        
        if (players.length === 0) {
            container.innerHTML = '<p class="loading">No players connected</p>';
            return;
        }
        
        // Check if we need to do a full rebuild or just update values
        const existingPlayerIds = new Set(
            Array.from(container.querySelectorAll('.player-card')).map(card => card.dataset.playerId)
        );
        const newPlayerIds = new Set(players.map(p => p.id));
        const needsRebuild = existingPlayerIds.size !== newPlayerIds.size || 
                            ![...newPlayerIds].every(id => existingPlayerIds.has(id));
        
        if (needsRebuild) {
            // Full rebuild needed (player added/removed)
            container.innerHTML = players.map(player => createPlayerCardHTML(player)).join('');
        } else {
            // Just update existing cards without rebuilding
            players.forEach(player => {
                updatePlayerCard(player);
            });
        }
        
        // Update smart stream track information for all players
        players.forEach(player => {
            updateSmartStreamTrack(player.id);
        });
    } catch (error) {
        console.error('Error loading players:', error);
        document.getElementById('players-list').innerHTML = 
            `<p class="error">Failed to load players: ${error.message}</p>`;
    } finally {
        isLoadingPlayers = false;
    }
}

/**
 * Create HTML for a player card
 */
function createPlayerCardHTML(player) {
    // Build additional status indicators
    const indicators = [];
    
    // Battery with charging
    if (player.battery_level !== null && player.battery_level !== undefined) {
        const chargingIcon = player.is_charging ? '⚡' : '';
        const batteryIcon = player.battery_level < 20 ? '🪫' : '🔋';
        indicators.push(`${batteryIcon} ${player.battery_level}%${chargingIcon}`);
    }
    
    // Temperature if available
    if (player.temperature !== null && player.temperature !== undefined) {
        indicators.push(`🌡️ ${player.temperature}°C`);
    }
    
    // Sleep timer if active
    if (player.sleep_timer_active && player.sleep_timer_seconds_remaining) {
        const minutes = Math.floor(player.sleep_timer_seconds_remaining / 60);
        indicators.push(`😴 ${minutes}m`);
    }
    
    // Audio connections
    if (player.bluetooth_audio_connected) {
        indicators.push('🎧 BT');
    }
    
    // Build media display (what's playing)
    let mediaInfo = '';
    if (player.active_card) {
        // Card/Album info (like yoto_ha media_album_name, media_artist)
        const cardTitle = player.card_title || 'Unknown Card';
        const cardAuthor = player.card_author ? ` by ${player.card_author}` : '';
        
        // Chapter/Track info (like yoto_ha media_title)
        let trackInfo = '';
        if (player.chapter_title || player.track_title) {
            const title = player.chapter_title && player.track_title && player.chapter_title !== player.track_title
                ? `${player.chapter_title} - ${player.track_title}`
                : (player.chapter_title || player.track_title);
            trackInfo = `<div class="now-playing-track">${escapeHtml(title)}</div>`;
        }
        
        mediaInfo = `
            <div class="now-playing">
                <span class="now-playing-label">♫</span>
                <div class="now-playing-info">
                    <div class="now-playing-title">${escapeHtml(cardTitle)}${escapeHtml(cardAuthor)}</div>
                    ${trackInfo}
                </div>
            </div>
        `;
    }
    
    return `
        <div class="list-item player-card" data-player-id="${escapeHtml(player.id)}">
            <div class="list-item-header">
                <span class="list-item-title">${escapeHtml(player.name)}</span>
                <span class="badge status-badge ${player.online ? 'online' : 'offline'}">
                    ${player.online ? '🟢 Online' : '🔴 Offline'}
                </span>
            </div>
            ${mediaInfo}
            <div class="smart-stream-track" data-player-id="${escapeHtml(player.id)}" style="display: none;">
                <div class="stream-track-label">🎵 Now Playing:</div>
                <div class="stream-track-name" id="stream-track-${escapeHtml(player.id)}">Loading...</div>
            </div>
            <div class="list-item-details">
                <span>${player.playing ? '▶️ Playing' : '⏸️ Paused'}</span>
                ${indicators.map(ind => `<span>${ind}</span>`).join('')}
            </div>
            <div class="player-controls">
                <button class="control-btn" onclick="controlPlayer('${escapeHtml(player.id)}', 'play')" title="Play" ${!player.online ? 'disabled' : ''}>
                    ▶️
                </button>
                <button class="control-btn" onclick="controlPlayer('${escapeHtml(player.id)}', 'pause')" title="Pause" ${!player.online ? 'disabled' : ''}>
                    ⏸️
                </button>
                <button class="control-btn" onclick="controlPlayer('${escapeHtml(player.id)}', 'stop')" title="Stop" ${!player.online ? 'disabled' : ''}>
                    ⏹️
                </button>
                <div class="volume-control" data-player-id="${escapeHtml(player.id)}">
                    <input type="range" 
                        id="volume-slider-${escapeHtml(player.id)}"
                        class="volume-slider" 
                        min="0" 
                        max="16" 
                        value="${player.volume}" 
                        onmousedown="startSliderInteraction('${escapeHtml(player.id)}')"
                        ontouchstart="startSliderInteraction('${escapeHtml(player.id)}')"
                        oninput="setPlayerVolume('${escapeHtml(player.id)}', this.value)"
                        onmouseup="endSliderInteraction('${escapeHtml(player.id)}')"
                        ontouchend="endSliderInteraction('${escapeHtml(player.id)}')"
                        ${!player.online ? 'disabled' : ''}>
                    <span class="volume-label" id="volume-label-${escapeHtml(player.id)}">${player.volume}/16</span>
                </div>
                <button class="control-btn library-btn" onclick="showLibraryBrowser('${escapeHtml(player.id)}')" title="Select from Library" ${!player.online ? 'disabled' : ''}>
                    📚
                </button>
                <button class="control-btn info-btn" onclick="showPlayerDetail('${escapeHtml(player.id)}')" title="Player Details">
                    ℹ️
                </button>
            </div>
        </div>
    `;
}

/**
 * Update an existing player card without rebuilding (for smooth slider interaction)
 */
function updatePlayerCard(player) {
    const card = document.querySelector(`.player-card[data-player-id="${player.id}"]`);
    if (!card) return;
    
    // Update online status
    const statusBadge = card.querySelector('.status-badge');
    if (statusBadge) {
        statusBadge.className = `badge status-badge ${player.online ? 'online' : 'offline'}`;
        statusBadge.textContent = player.online ? '🟢 Online' : '🔴 Offline';
    }
    
    // Update now playing info (card and chapter titles)
    const existingMediaInfo = card.querySelector('.now-playing');
    if (player.active_card && player.active_card !== 'none') {
        // Card/Album info
        const cardTitle = player.card_title || 'Unknown Card';
        const cardAuthor = player.card_author ? ` by ${player.card_author}` : '';
        
        // Chapter/Track info
        let trackInfo = '';
        if (player.chapter_title || player.track_title) {
            const title = player.chapter_title && player.track_title && player.chapter_title !== player.track_title
                ? `${player.chapter_title} - ${player.track_title}`
                : (player.chapter_title || player.track_title);
            trackInfo = `<div class="now-playing-track">${escapeHtml(title)}</div>`;
        }
        
        const mediaInfoHtml = `
            <div class="now-playing">
                <span class="now-playing-label">♫</span>
                <div class="now-playing-info">
                    <div class="now-playing-title">${escapeHtml(cardTitle)}${escapeHtml(cardAuthor)}</div>
                    ${trackInfo}
                </div>
            </div>
        `;
        
        if (existingMediaInfo) {
            // Update existing media info
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = mediaInfoHtml;
            existingMediaInfo.replaceWith(tempDiv.firstElementChild);
        } else {
            // Insert new media info after header
            const header = card.querySelector('.list-item-header');
            if (header) {
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = mediaInfoHtml;
                header.insertAdjacentElement('afterend', tempDiv.firstElementChild);
            }
        }
    } else if (existingMediaInfo) {
        // Remove media info if no active card
        existingMediaInfo.remove();
    }
    
    // Update playing/paused status in details
    const details = card.querySelector('.list-item-details');
    if (details) {
        const playingSpan = details.querySelector('span:first-child');
        if (playingSpan) {
            playingSpan.textContent = player.playing ? '▶️ Playing' : '⏸️ Paused';
        }
    }
    
    // Update volume slider and label only if not being interacted with
    if (canUpdateSlider(player.id)) {
        const slider = document.getElementById(`volume-slider-${player.id}`);
        const label = document.getElementById(`volume-label-${player.id}`);
        if (slider && label && slider.value != player.volume) {
            // Mark as programmatic update to prevent feedback loop
            programmaticUpdates.add(player.id);
            slider.value = player.volume;
            label.textContent = `${player.volume}/16`;
            // Clear flag after a brief delay to allow oninput to check it
            setTimeout(() => programmaticUpdates.delete(player.id), 10);
        }
    }
    
    // Update control buttons enabled/disabled state
    const controls = card.querySelectorAll('.player-controls button:not(.library-btn):not(.info-btn)');
    controls.forEach(btn => {
        if (!player.online) {
            btn.setAttribute('disabled', '');
        } else {
            btn.removeAttribute('disabled');
        }
    });
}

/**
 * Detect and display smart stream track information for a player
 */
async function updateSmartStreamTrack(playerId) {
    try {
        const response = await fetch(`${API_BASE}/streams/detect-smart-stream/${playerId}`);
        if (!response.ok) return;
        
        const data = await response.json();
        const card = document.querySelector(`.player-card[data-player-id="${playerId}"]`);
        if (!card) return;
        
        const streamTrackElement = card.querySelector('.smart-stream-track');
        const trackNameElement = card.querySelector(`#stream-track-${playerId}`);
        
        if (!streamTrackElement || !trackNameElement) return;
        
        if (data.is_playing_smart_stream && data.current_track_name) {
            // Show the smart stream track display
            let displayText = escapeHtml(data.current_track_name);
            
            // Add track number if available
            if (data.current_track_index !== null && data.total_tracks !== null) {
                displayText += ` (${data.current_track_index + 1}/${data.total_tracks})`;
            }
            
            trackNameElement.textContent = displayText;
            streamTrackElement.style.display = 'block';
        } else {
            // Hide the smart stream track display
            streamTrackElement.style.display = 'none';
        }
    } catch (error) {
        // Silently fail - not all players will be playing smart streams
    }
}


/**
 * Mark slider as being actively interacted with
 */
function startSliderInteraction(playerId) {
    activeSliders.add(playerId);
    console.log(`%c🎚️ Slider interaction started`, 'color: #9C27B0', `Player: ${playerId}`);
}

/**
 * Mark slider interaction as complete and set cooldown
 */
function endSliderInteraction(playerId) {
    activeSliders.delete(playerId);
    // Set cooldown to prevent updates for 3 seconds after interaction ends
    sliderCooldowns.set(playerId, Date.now() + 3000);
    console.log(`%c🎚️ Slider interaction ended (3s cooldown)`, 'color: #9C27B0', `Player: ${playerId}`);
}

/**
 * Check if a slider should be updated (not active and not in cooldown)
 */
function canUpdateSlider(playerId) {
    // Don't update if actively being dragged
    if (activeSliders.has(playerId)) {
        return false;
    }
    
    // Don't update if in cooldown period
    const cooldownUntil = sliderCooldowns.get(playerId);
    if (cooldownUntil && Date.now() < cooldownUntil) {
        return false;
    }
    
    // Cleanup expired cooldown
    if (cooldownUntil) {
        sliderCooldowns.delete(playerId);
    }
    
    return true;
}

// Start automatic player refresh every 5 seconds
function startPlayerAutoRefresh() {
    // Clear any existing interval
    if (playerRefreshInterval) {
        clearInterval(playerRefreshInterval);
    }
    
    // Refresh players every 5 seconds
    playerRefreshInterval = setInterval(async () => {
        try {
            await loadPlayers();
        } catch (error) {
            // Log error but don't stop the interval
            console.error('%c[MQTT] ❌ Auto-refresh error:', 'color: #f44336; font-weight: bold', error);
        }
    }, 5000);
}

// Stop automatic player refresh
function stopPlayerAutoRefresh() {
    if (playerRefreshInterval) {
        clearInterval(playerRefreshInterval);
        playerRefreshInterval = null;
    }
}

// Slider Interaction Tracking

/**
 * Mark slider as being actively interacted with
 */
function startSliderInteraction(playerId) {
    activeSliders.add(playerId);
}

/**
 * Mark slider interaction as complete and set cooldown
 */
function endSliderInteraction(playerId) {
    activeSliders.delete(playerId);
    // Set cooldown to prevent updates for 3 seconds after interaction ends
    sliderCooldowns.set(playerId, Date.now() + 3000);
}

/**
 * Check if a slider should be updated (not active and not in cooldown)
 */
function canUpdateSlider(playerId) {
    // Don't update if actively being dragged
    if (activeSliders.has(playerId)) {
        return false;
    }
    
    // Don't update if in cooldown period
    const cooldownUntil = sliderCooldowns.get(playerId);
    if (cooldownUntil && Date.now() < cooldownUntil) {
        return false;
    }
    
    // Cleanup expired cooldown
    if (cooldownUntil) {
        sliderCooldowns.delete(playerId);
    }
    
    return true;
}

// Player Control Functions

/**
 * Control a player (play, pause, stop)
 */
async function controlPlayer(playerId, action) {
    try {
        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false, fractionalSecondDigits: 3 });
        console.log(`%c[${timestamp}] 🎮 Control: ${action}`, 'color: #FF9800; font-weight: bold', `Player: ${playerId}`);
        
        const response = await fetch(`${API_BASE}/players/${playerId}/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || `Failed to ${action} player`);
        }
        
        // Refresh players to update UI
        await loadPlayers();
        
    } catch (error) {
        console.error(`Error controlling player:`, error);
        alert(`Failed to ${action} player: ${error.message}`);
    }
}

/**
 * Set player volume
 */
async function setPlayerVolume(playerId, volume) {
    // Skip if this is a programmatic update (to prevent feedback loop)
    if (programmaticUpdates.has(playerId)) {
        console.log(`%c🔇 Skipping programmatic volume update`, 'color: #999', `Player: ${playerId}`);
        return;
    }
    
    try {
        const timestamp = new Date().toLocaleTimeString('en-US', { hour12: false, fractionalSecondDigits: 3 });
        const prevVolume = previousPlayerStates[playerId]?.volume || '?';
        console.log(`%c[${timestamp}] 🔊 Volume Control`, 'color: #9C27B0; font-weight: bold', `${prevVolume}/16 → ${volume}/16`, `(Player: ${playerId})`);
        
        // Update the volume label immediately for responsiveness
        const volumeControl = document.querySelector(`.volume-control[data-player-id="${playerId}"]`);
        if (volumeControl) {
            const volumeLabel = volumeControl.querySelector('.volume-label');
            if (volumeLabel) {
                volumeLabel.textContent = `${volume}/16`;
            }
        }
        
        const response = await fetch(`${API_BASE}/players/${playerId}/control`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'volume', volume: parseInt(volume) })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to set volume');
        }
        
        // Wait 2 seconds for MQTT to propagate before refreshing
        // This prevents the old volume value from overwriting the UI
        setTimeout(() => {
            loadPlayers();
        }, 2000);
        
    } catch (error) {
        console.error('Error setting volume:', error);
        alert(`Failed to set volume: ${error.message}`);
    }
}

// Load audio files
async function loadAudioFiles() {
    const container = document.getElementById('audio-list');
    
    try {
        const response = await fetch(`${API_BASE}/audio/list`);
        if (!response.ok) throw new Error('Failed to fetch audio files');
        
        const data = await response.json();
        const files = data.files || [];
        
        // Update audio count stat
        document.getElementById('audio-count').textContent = files.length;
        
        if (files.length === 0) {
            container.innerHTML = '<p class="loading">No audio files found. Add MP3 files to the audio_files directory.</p>';
            return;
        }
        
        container.innerHTML = files.map(file => `
            <div class="list-item">
                <div class="list-item-header">
                    <span class="list-item-title">🎵 ${escapeHtml(file.filename)}</span>
                </div>
                <div class="list-item-details">
                    <span>Size: ${formatFileSize(file.size)}</span>
                    <button class="control-btn" onclick="copyAudioUrl('${escapeHtml(file.url)}', event)" title="Copy Full URL">
                        📋
                    </button>
                    <audio controls preload="none" style="width: 100%; max-width: 300px; margin-top: 8px;">
                        <source src="${escapeHtml(file.url)}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading audio files:', error);
        container.innerHTML = '<p class="error-message">Failed to load audio files.</p>';
    }
}

// Refresh all data
function refreshData() {
    loadSystemStatus();
    loadPlayers();
    loadAudioFiles();
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

// Copy audio URL to clipboard
async function copyAudioUrl(url, event) {
    event.preventDefault();
    const fullUrl = window.location.origin + url;
    try {
        await navigator.clipboard.writeText(fullUrl);
        alert('URL copied to clipboard!');
    } catch (error) {
        console.error('Error copying URL:', error);
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = fullUrl;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        alert('URL copied to clipboard!');
    }
}

// Player Detail Modal Functions

/**
 * Show player detail modal with comprehensive information
 */
async function showPlayerDetail(playerId) {
    const modal = document.getElementById('playerModal');
    const loadingEl = document.getElementById('modalPlayerLoading');
    const contentEl = document.getElementById('modalPlayerContent');
    const technicalInfoEl = document.getElementById('modalTechnicalInfo');
    
    // Show modal and reset to loading state
    modal.style.display = 'flex';
    loadingEl.style.display = 'block';
    contentEl.style.display = 'none';
    technicalInfoEl.style.display = 'none';
    
    // Reset info button state
    const infoButton = document.getElementById('modalInfoButton');
    if (infoButton) {
        infoButton.classList.remove('active');
    }
    
    try {
        // Clear previous technical info
        clearTechnicalInfo();
        
        // Fetch combined player data from our API
        const playerUrl = `${API_BASE}/players/${playerId}`;
        const playerResponse = await fetch(playerUrl);
        if (!playerResponse.ok) throw new Error('Failed to fetch player data');
        const playerData = await playerResponse.json();
        
        // Store our combined endpoint (for reference)
        addTechnicalInfo('GET Player (Combined)', playerUrl, playerData);
        
        // Fetch device status from Yoto API
        const statusUrl = `${API_BASE}/players/${playerId}/status`;
        try {
            const statusResponse = await fetch(statusUrl);
            if (statusResponse.ok) {
                const statusData = await statusResponse.json();
                addTechnicalInfo('GET Device Status (Yoto API)', statusUrl, statusData);
            } else {
                const errorData = await statusResponse.text();
                console.error('Device status request failed:', statusResponse.status, errorData);
                addTechnicalInfo('GET Device Status (FAILED)', statusUrl, {
                    error: true,
                    status: statusResponse.status,
                    statusText: statusResponse.statusText,
                    details: errorData
                });
            }
        } catch (statusError) {
            console.error('Failed to fetch device status:', statusError);
            addTechnicalInfo('GET Device Status (ERROR)', statusUrl, {
                error: true,
                message: statusError.message || String(statusError)
            });
        }
        
        // Fetch device config from Yoto API
        const configUrl = `${API_BASE}/players/${playerId}/config`;
        try {
            const configResponse = await fetch(configUrl);
            if (configResponse.ok) {
                const configData = await configResponse.json();
                addTechnicalInfo('GET Device Config (Yoto API)', configUrl, configData);
            } else {
                const errorData = await configResponse.text();
                console.error('Device config request failed:', configResponse.status, errorData);
                addTechnicalInfo('GET Device Config (FAILED)', configUrl, {
                    error: true,
                    status: configResponse.status,
                    statusText: configResponse.statusText,
                    details: errorData
                });
            }
        } catch (configError) {
            console.error('Failed to fetch device config:', configError);
            addTechnicalInfo('GET Device Config (ERROR)', configUrl, {
                error: true,
                message: configError.message || String(configError)
            });
        }
        
        // Update modal with player data
        populatePlayerModal(playerData);
        
        // Show content, hide loading
        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
        
    } catch (error) {
        console.error('Error loading player details:', error);
        loadingEl.innerHTML = '<p class="error-message">Failed to load player details. Please try again.</p>';
    }
}

/**
 * Close the player detail modal
 */
function closePlayerModal() {
    const modal = document.getElementById('playerModal');
    modal.style.display = 'none';
}

/**
 * Populate modal with player data
 */
function populatePlayerModal(player) {
    // Header
    document.getElementById('modalPlayerName').textContent = player.name;
    
    // Status Overview
    const statusBadge = document.getElementById('modalPlayerStatus');
    statusBadge.textContent = player.online ? 'Online' : 'Offline';
    statusBadge.className = `detail-value badge ${player.online ? 'online' : 'offline'}`;
    
    document.getElementById('modalPlayerPlayback').textContent = player.playing ? '▶️ Playing' : '⏸️ Paused';
    document.getElementById('modalPlayerVolume').textContent = `${player.volume}%`;
    
    // Battery with indicator
    const batteryEl = document.getElementById('modalPlayerBattery');
    if (player.battery_level !== null && player.battery_level !== undefined) {
        const batteryClass = player.battery_level < 20 ? 'low' : player.battery_level < 50 ? 'medium' : '';
        const chargingIcon = player.is_charging ? ' ⚡' : '';
        batteryEl.innerHTML = `
            <span class="battery-indicator">
                <span class="battery-icon">
                    <span class="battery-fill ${batteryClass}" style="width: ${player.battery_level}%"></span>
                </span>
                ${player.battery_level}%${chargingIcon}
            </span>
        `;
    } else {
        batteryEl.textContent = 'N/A';
    }
    
    // Device Information
    document.getElementById('modalPlayerId').textContent = player.id;
    document.getElementById('modalPlayerDeviceType').textContent = player.device_type || 'N/A';
    document.getElementById('modalPlayerFirmware').textContent = player.firmware_version || 'N/A';
    document.getElementById('modalPlayerPowerSource').textContent = player.power_source || 'N/A';
    
    // Network & Environment
    const wifiEl = document.getElementById('modalPlayerWifi');
    if (player.wifi_strength !== null && player.wifi_strength !== undefined) {
        // WiFi strength in dBm (typically -30 to -90)
        // -30 = Excellent, -50 = Good, -60 = Fair, -70 = Weak, -90+ = Very Weak
        let signalQuality = 'Weak';
        let activeBars = 1;
        if (player.wifi_strength >= -50) {
            signalQuality = 'Excellent';
            activeBars = 4;
        } else if (player.wifi_strength >= -60) {
            signalQuality = 'Good';
            activeBars = 3;
        } else if (player.wifi_strength >= -70) {
            signalQuality = 'Fair';
            activeBars = 2;
        }
        
        wifiEl.innerHTML = `
            <span class="wifi-indicator">
                <span class="wifi-bars">
                    ${[1,2,3,4].map(i => `<span class="wifi-bar ${i <= activeBars ? 'active' : ''}"></span>`).join('')}
                </span>
                ${player.wifi_strength} dBm (${signalQuality})
            </span>
        `;
    } else {
        wifiEl.textContent = 'N/A';
    }
    
    const tempEl = document.getElementById('modalPlayerTemperature');
    if (player.temperature !== null && player.temperature !== undefined) {
        const fahrenheit = (player.temperature * 9/5) + 32;
        tempEl.textContent = `${player.temperature}°C (${fahrenheit.toFixed(1)}°F)`;
    } else {
        tempEl.textContent = 'N/A';
    }
    
    // Ambient Light
    const ambientLightEl = document.getElementById('modalPlayerAmbientLight');
    if (player.ambient_light !== null && player.ambient_light !== undefined) {
        ambientLightEl.textContent = `${player.ambient_light} lux`;
    } else {
        ambientLightEl.textContent = 'N/A';
    }
    
    // Day Mode
    document.getElementById('modalPlayerDayMode').textContent = 
        player.day_mode !== null ? (player.day_mode ? 'Day' : 'Night') : 'N/A';
    
    // Nightlight
    const nightlightEl = document.getElementById('modalPlayerNightlight');
    if (player.nightlight_mode) {
        nightlightEl.textContent = player.nightlight_mode === 'off' ? 'Off' : player.nightlight_mode;
    } else {
        nightlightEl.textContent = 'N/A';
    }
    
    // Last Updated
    const lastUpdatedEl = document.getElementById('modalPlayerLastUpdated');
    if (player.last_updated_at) {
        const date = new Date(player.last_updated_at);
        lastUpdatedEl.textContent = date.toLocaleString();
    } else {
        lastUpdatedEl.textContent = 'N/A';
    }
    
    // Audio Connections
    document.getElementById('modalPlayerBluetoothAudio').textContent = 
        player.bluetooth_audio_connected !== null ? 
        (player.bluetooth_audio_connected ? '🎧 Connected' : 'Not Connected') : 'N/A';
    
    document.getElementById('modalPlayerAudioDevice').textContent = 
        player.audio_device_connected !== null ? 
        (player.audio_device_connected ? '🔊 Connected' : 'Not Connected') : 'N/A';
    
    // Sleep Timer Section
    const sleepTimerSection = document.getElementById('modalSleepTimerSection');
    if (player.sleep_timer_active && player.sleep_timer_seconds_remaining) {
        sleepTimerSection.style.display = 'block';
        const hours = Math.floor(player.sleep_timer_seconds_remaining / 3600);
        const minutes = Math.floor((player.sleep_timer_seconds_remaining % 3600) / 60);
        const seconds = player.sleep_timer_seconds_remaining % 60;
        
        let timeStr = '';
        if (hours > 0) timeStr += `${hours}h `;
        if (minutes > 0) timeStr += `${minutes}m `;
        if (seconds > 0 || timeStr === '') timeStr += `${seconds}s`;
        
        document.getElementById('modalPlayerSleepTimer').textContent = `😴 ${timeStr}`;
    } else {
        sleepTimerSection.style.display = 'none';
    }
    
    // Playback Information (show section only if there's active playback)
    const playbackSection = document.getElementById('modalPlaybackSection');
    if (player.active_card && player.active_card !== 'none') {
        playbackSection.style.display = 'block';
        document.getElementById('modalPlayerActiveCard').textContent = player.active_card;
        
        // Card info from library
        const cardTitleRow = document.getElementById('modalCardTitleRow');
        const cardAuthorRow = document.getElementById('modalCardAuthorRow');
        if (player.card_title) {
            cardTitleRow.style.display = 'flex';
            document.getElementById('modalCardTitle').textContent = player.card_title;
        } else {
            cardTitleRow.style.display = 'none';
        }
        if (player.card_author) {
            cardAuthorRow.style.display = 'flex';
            document.getElementById('modalCardAuthor').textContent = player.card_author;
        } else {
            cardAuthorRow.style.display = 'none';
        }
        
        // Chapter with title
        const chapterEl = document.getElementById('modalPlayerChapter');
        if (player.chapter_title && player.current_chapter) {
            chapterEl.textContent = `${player.chapter_title} (${player.current_chapter})`;
        } else if (player.current_chapter) {
            chapterEl.textContent = player.current_chapter;
        } else {
            chapterEl.textContent = 'N/A';
        }
        
        // Track with title
        const trackEl = document.getElementById('modalPlayerTrack');
        if (player.track_title && player.current_track) {
            trackEl.textContent = `${player.track_title} (${player.current_track})`;
        } else if (player.current_track) {
            trackEl.textContent = player.current_track;
        } else {
            trackEl.textContent = 'N/A';
        }
        
        const positionEl = document.getElementById('modalPlayerPosition');
        if (player.playback_position !== null && player.track_length !== null) {
            const position = formatTime(player.playback_position);
            const length = formatTime(player.track_length);
            const percent = Math.floor((player.playback_position / player.track_length) * 100);
            positionEl.textContent = `${position} / ${length} (${percent}%)`;
        } else if (player.playback_position !== null) {
            positionEl.textContent = formatTime(player.playback_position);
        } else {
            positionEl.textContent = 'N/A';
        }
    } else {
        playbackSection.style.display = 'none';
    }
}

/**
 * Format seconds to MM:SS or HH:MM:SS
 */
function formatTime(seconds) {
    if (seconds === null || seconds === undefined) return 'N/A';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
        return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }
    return `${minutes}:${String(secs).padStart(2, '0')}`;
}

// Close modal when clicking outside of it
window.addEventListener('click', function(event) {
    const modal = document.getElementById('playerModal');
    if (modal && event.target === modal) {
        closePlayerModal();
    }
});

/**
 * Store technical information about the API request and response
 */
/**
 * Clear all technical information
 */
function clearTechnicalInfo() {
    const container = document.getElementById('technicalInfoContent');
    if (container) {
        container.innerHTML = '';
    }
}

/**
 * Add a technical information entry for an API call
 */
function addTechnicalInfo(title, url, responseData) {
    const container = document.getElementById('technicalInfoContent');
    if (!container) return;
    
    const requestInfo = `GET ${url}`;
    const responseJson = JSON.stringify(responseData, null, 2);
    const itemId = `tech-info-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    
    const itemHtml = `
        <div class="technical-info-item">
            <h5>${title}</h5>
            <div class="code-block">
                <div class="code-header">
                    <span>Method & URL</span>
                    <button class="copy-button" onclick="copyToClipboard('${itemId}-url', this)">Copy</button>
                </div>
                <pre id="${itemId}-url" class="code-content">${requestInfo}</pre>
            </div>
            <div class="code-block" style="margin-top: 0.5rem;">
                <div class="code-header">
                    <span>Response Data</span>
                    <button class="copy-button" onclick="copyToClipboard('${itemId}-json', this)">Copy</button>
                </div>
                <pre id="${itemId}-json" class="code-content">${responseJson}</pre>
            </div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', itemHtml);
}

/**
 * Toggle the technical information section
 */
function toggleTechnicalInfo() {
    const technicalInfoEl = document.getElementById('modalTechnicalInfo');
    const infoButton = document.getElementById('modalInfoButton');
    
    if (technicalInfoEl.style.display === 'none' || technicalInfoEl.style.display === '') {
        technicalInfoEl.style.display = 'block';
        infoButton.classList.add('active');
    } else {
        technicalInfoEl.style.display = 'none';
        infoButton.classList.remove('active');
    }
}

/**
 * Copy text content to clipboard
 */
function copyToClipboard(elementId, buttonElement) {
    const element = document.getElementById(elementId);
    const text = element.textContent;
    
    // Get the button element - either passed as parameter or find it via event
    const button = buttonElement || window.event?.target;
    
    // Use the Clipboard API
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            if (button) {
                // Show a brief success indicator
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.style.background = '#48bb78';
                
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '';
                }, 2000);
            }
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            alert('Failed to copy to clipboard');
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        
        try {
            document.execCommand('copy');
            if (button) {
                const originalText = button.textContent;
                button.textContent = 'Copied!';
                button.style.background = '#48bb78';
                
                setTimeout(() => {
                    button.textContent = originalText;
                    button.style.background = '';
                }, 2000);
            }
        } catch (err) {
            console.error('Failed to copy text: ', err);
            alert('Failed to copy to clipboard');
        }
        
        document.body.removeChild(textarea);
    }
}

// TTS Generator Functions

// Default filename for TTS generator
const DEFAULT_TTS_FILENAME = 'my-story';

// Open TTS modal
function openTTSModal() {
    const modal = document.getElementById('tts-modal');
    const form = document.getElementById('tts-form');
    const result = document.getElementById('tts-result');
    const successDiv = document.getElementById('tts-success');
    const errorDiv = document.getElementById('tts-error');
    
    // Reset form and messages
    if (form) form.reset();
    if (result) result.style.display = 'none';
    if (successDiv) successDiv.style.display = 'none';
    if (errorDiv) errorDiv.style.display = 'none';
    
    // Update preview
    updateFilenamePreview();
    updateTextLength();
    
    // Show modal
    modal.style.display = 'flex';
}

// Close TTS modal
function closeTTSModal() {
    const modal = document.getElementById('tts-modal');
    modal.style.display = 'none';
}

// Update filename preview
function updateFilenamePreview() {
    const filenameInput = document.getElementById('tts-filename');
    const preview = document.getElementById('filename-preview');
    
    if (filenameInput && preview) {
        const filename = filenameInput.value.trim() || DEFAULT_TTS_FILENAME;
        // Remove .mp3 extension if user added it
        const cleanFilename = filename.replace(/\.mp3$/i, '');
        preview.textContent = `${cleanFilename}.mp3`;
    }
}

// Update text length counter
function updateTextLength() {
    const textInput = document.getElementById('tts-text');
    const lengthDisplay = document.getElementById('text-length');
    
    if (textInput && lengthDisplay) {
        const length = textInput.value.length;
        lengthDisplay.textContent = `${length} character${length !== 1 ? 's' : ''}`;
    }
}

// Handle TTS form submission
async function handleTTSSubmit(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = document.getElementById('tts-submit-btn');
    const submitText = document.getElementById('tts-submit-text');
    const submitSpinner = document.getElementById('tts-submit-spinner');
    const result = document.getElementById('tts-result');
    const successDiv = document.getElementById('tts-success');
    const errorDiv = document.getElementById('tts-error');
    const successMessage = document.getElementById('tts-success-message');
    const errorMessage = document.getElementById('tts-error-message');
    
    // Get form data
    const filename = document.getElementById('tts-filename').value.trim();
    const text = document.getElementById('tts-text').value.trim();
    
    if (!filename || !text) {
        showTTSError('Please fill in all fields');
        return;
    }
    
    // Show loading state
    submitBtn.disabled = true;
    submitText.style.display = 'none';
    submitSpinner.style.display = 'inline';
    result.style.display = 'none';
    successDiv.style.display = 'none';
    errorDiv.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/audio/generate-tts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                filename: filename,
                text: text,
            }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to generate TTS audio');
        }
        
        // Show success message
        successMessage.textContent = data.message || `Successfully generated ${data.filename}`;
        successDiv.style.display = 'block';
        result.style.display = 'block';
        
        // Reset form
        form.reset();
        updateFilenamePreview();
        updateTextLength();
        
        // Refresh audio files list to show new file
        setTimeout(() => {
            loadAudioFiles();
        }, 1000);
        
        // Auto-close modal after 3 seconds
        setTimeout(() => {
            closeTTSModal();
        }, 3000);
        
    } catch (error) {
        console.error('Error generating TTS audio:', error);
        errorMessage.textContent = error.message;
        errorDiv.style.display = 'block';
        result.style.display = 'block';
    } finally {
        // Reset button state
        submitBtn.disabled = false;
        submitText.style.display = 'inline';
        submitSpinner.style.display = 'none';
    }
}

// Helper function to show TTS error
function showTTSError(message) {
    const result = document.getElementById('tts-result');
    const errorDiv = document.getElementById('tts-error');
    const errorMessage = document.getElementById('tts-error-message');
    
    errorMessage.textContent = message;
    errorDiv.style.display = 'block';
    result.style.display = 'block';
}

// ============================================================================
// Library Browser Functions
// ============================================================================

/**
 * Show library browser modal for selecting cards
 */
async function showLibraryBrowser(playerId) {
    const modal = document.getElementById('libraryModal');
    const loadingEl = document.getElementById('libraryLoading');
    const contentEl = document.getElementById('libraryContent');
    const filterEl = document.getElementById('libraryFilter');
    
    // Show modal and reset to loading state
    modal.style.display = 'flex';
    loadingEl.style.display = 'block';
    contentEl.style.display = 'none';
    contentEl.innerHTML = '';
    filterEl.value = '';
    
    // Store player ID for later use
    modal.dataset.playerId = playerId;
    
    try {
        const response = await fetch('/api/library');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const library = await response.json();
        
        // Hide loading, show content
        loadingEl.style.display = 'none';
        contentEl.style.display = 'grid';
        
        if (!library.cards || library.cards.length === 0) {
            contentEl.innerHTML = '<p class="no-content">No cards found in your library.</p>';
            return;
        }
        
        // Render cards
        contentEl.innerHTML = library.cards.map(card => `
            <div class="library-card" data-title="${escapeHtml(card.title || 'Untitled')}" onclick="selectCard('${escapeHtml(playerId)}', '${escapeHtml(card.id)}')">
                ${card.cover ? `<img src="${escapeHtml(card.cover)}" alt="${escapeHtml(card.title)}" />` : '<div class="no-cover">📚</div>'}
                <div class="library-card-info">
                    <div class="library-card-title">${escapeHtml(card.title || 'Untitled')}</div>
                    ${card.author ? `<div class="library-card-author">${escapeHtml(card.author)}</div>` : ''}
                </div>
            </div>
        `).join('');
        
        // Setup filter listener
        filterEl.removeEventListener('input', applyLibraryFilter);
        filterEl.addEventListener('input', applyLibraryFilter);
        
    } catch (error) {
        console.error('Error loading library:', error);
        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
        contentEl.innerHTML = '<p class="error-message">Failed to load library.</p>';
    }
}

/**
 * Close library browser modal
 */
function closeLibraryBrowser() {
    document.getElementById('libraryModal').style.display = 'none';
}

/**
 * Select a card and show chapters
 */
async function selectCard(playerId, cardId) {
    const modal = document.getElementById('chapterModal');
    const loadingEl = document.getElementById('chapterLoading');
    const contentEl = document.getElementById('chapterContent');
    const titleEl = document.getElementById('chapterModalTitle');
    
    // Show modal and reset to loading state
    modal.style.display = 'flex';
    loadingEl.style.display = 'block';
    contentEl.style.display = 'none';
    contentEl.innerHTML = '';
    titleEl.textContent = 'Loading...';
    
    // Store player and card IDs
    modal.dataset.playerId = playerId;
    modal.dataset.cardId = cardId;
    
    try {
        const response = await fetch(`/api/library/${cardId}/chapters`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        
        // Update modal title
        titleEl.textContent = data.card_title || 'Select Chapter';
        
        // Hide loading, show content
        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
        
        if (!data.chapters || data.chapters.length === 0) {
            contentEl.innerHTML = '<p class="no-content">No chapters available.</p>';
            return;
        }
        
        // Render chapters
        contentEl.innerHTML = data.chapters.map(chapter => `
            <div class="chapter-item" onclick="playChapter('${escapeHtml(playerId)}', '${escapeHtml(cardId)}', '${escapeHtml(chapter.key)}')">
                ${chapter.icon ? `<img src="${escapeHtml(chapter.icon)}" alt="Chapter ${escapeHtml(chapter.key)}" class="chapter-icon" />` : ''}
                <div class="chapter-info">
                    <div class="chapter-title">${escapeHtml(chapter.title || `Chapter ${chapter.key}`)}</div>
                    ${chapter.duration ? `<div class="chapter-duration">${formatDuration(chapter.duration)}</div>` : ''}
                </div>
                <button class="chapter-play-btn" title="Play">▶️</button>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading chapters:', error);
        loadingEl.style.display = 'none';
        contentEl.style.display = 'block';
        contentEl.innerHTML = '<p class="error-message">Failed to load chapters.</p>';
    }
}

/**
 * Close chapter modal
 */
function closeChapterBrowser() {
    document.getElementById('chapterModal').style.display = 'none';
}

/**
 * Play a chapter on the specified player
 */
async function playChapter(playerId, cardId, chapterKey) {
    try {
        // Convert chapter key to number (removing leading zeros)
        const chapterNum = parseInt(chapterKey, 10);
        
        console.log(`🎵 Playing chapter ${chapterNum} from card ${cardId} on player ${playerId}`);
        
        // Load the card and chapter (card/start triggers playback itself)
        const loadResponse = await fetch(`/api/players/${playerId}/play-card?card_id=${encodeURIComponent(cardId)}&chapter=${chapterNum}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!loadResponse.ok) {
            const errorData = await loadResponse.json().catch(() => ({}));
            throw new Error(errorData.detail || `HTTP error! status: ${loadResponse.status}`);
        }
        
        console.log('✓ Playback started via card/start');
        
        // Close both modals
        closeChapterBrowser();
        closeLibraryBrowser();
        
        // Refresh players to show updated state
        setTimeout(() => loadPlayers(), 1000);
        
    } catch (error) {
        console.error('Error playing chapter:', error);
        alert(`Failed to play chapter: ${error.message}`);
    }
}

/**
 * Format duration in seconds to MM:SS
 */
function formatDuration(seconds) {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}
