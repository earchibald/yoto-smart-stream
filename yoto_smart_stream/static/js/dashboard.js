// Dashboard JavaScript

// API base URL
const API_BASE = '/api';

// Auth polling state
let authPollInterval = null;
let deviceCode = null;

// Player refresh polling state
let playerRefreshInterval = null;
let isLoadingPlayers = false;

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    loadSystemStatus();
    loadPlayers();
    loadAudioFiles();
    
    // Start auto-refresh for players every 5 seconds
    startPlayerAutoRefresh();
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
        
        // Update player count
        document.getElementById('player-count').textContent = players.length;
        
        if (players.length === 0) {
            container.innerHTML = '<p class="loading">No players connected</p>';
            return;
        }
        
        container.innerHTML = players.map(player => `
            <div class="list-item" onclick="showPlayerDetail('${escapeHtml(player.id)}')">
                <div class="list-item-header">
                    <span class="list-item-title">${escapeHtml(player.name)}</span>
                    <span class="badge ${player.online ? 'online' : 'offline'}">
                        ${player.online ? 'Online' : 'Offline'}
                    </span>
                </div>
                <div class="list-item-details">
                    <span>ID: ${escapeHtml(player.id)}</span>
                    <span>Volume: ${player.volume}%</span>
                    ${player.battery_level ? `<span>Battery: ${player.battery_level}%</span>` : ''}
                    <span>${player.playing ? '▶️ Playing' : '⏸️ Paused'}</span>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading players:', error);
        container.innerHTML = '<p class="error-message">Failed to load players. Check your Yoto API authentication.</p>';
    } finally {
        isLoadingPlayers = false;
    }
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
            console.error('Auto-refresh error:', error);
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
                    <span>URL: ${escapeHtml(file.url)}</span>
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
        
        // Fetch player config from our API (includes combined data)
        const configUrl = `${API_BASE}/players/${playerId}`;
        const configResponse = await fetch(configUrl);
        if (!configResponse.ok) throw new Error('Failed to fetch player config');
        const playerConfig = await configResponse.json();
        
        // Store config technical info
        addTechnicalInfo('GET Device Config', configUrl, playerConfig);
        
        // Fetch device status directly from Yoto API
        const statusUrl = `${API_BASE}/players/${playerId}/status`;
        try {
            const statusResponse = await fetch(statusUrl);
            if (statusResponse.ok) {
                const playerStatus = await statusResponse.json();
                addTechnicalInfo('GET Device Status', statusUrl, playerStatus);
                
                // Merge status data into config for display
                Object.assign(playerConfig, playerStatus);
            }
        } catch (statusError) {
            console.warn('Failed to fetch device status:', statusError);
            // Continue with config data only
        }
        
        // Update modal with combined player data
        populatePlayerModal(playerConfig);
        
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
    
    document.getElementById('modalPlayerDayMode').textContent = 
        player.day_mode !== null ? (player.day_mode ? 'Day' : 'Night') : 'N/A';
    
    const nightlightEl = document.getElementById('modalPlayerNightlight');
    if (player.nightlight_mode) {
        // Nightlight mode is typically a hex color code
        nightlightEl.innerHTML = `
            <span style="display: inline-flex; align-items: center; gap: 0.5rem;">
                <span style="width: 20px; height: 20px; border-radius: 50%; background: ${player.nightlight_mode}; border: 1px solid #ccc;"></span>
                ${player.nightlight_mode}
            </span>
        `;
    } else {
        nightlightEl.textContent = 'N/A';
    }
    
    // Playback Information (show section only if there's active playback)
    const playbackSection = document.getElementById('modalPlaybackSection');
    if (player.active_card && player.active_card !== 'none') {
        playbackSection.style.display = 'block';
        document.getElementById('modalPlayerActiveCard').textContent = player.active_card;
        document.getElementById('modalPlayerChapter').textContent = player.current_chapter || 'N/A';
        
        const positionEl = document.getElementById('modalPlayerPosition');
        if (player.playback_position !== null && player.track_length !== null) {
            const position = formatTime(player.playback_position);
            const length = formatTime(player.track_length);
            positionEl.textContent = `${position} / ${length}`;
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
