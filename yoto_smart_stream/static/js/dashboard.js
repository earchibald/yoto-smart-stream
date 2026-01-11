// Dashboard JavaScript

// API base URL
const API_BASE = '/api';

// Auth polling state
let authPollInterval = null;
let deviceCode = null;

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
    loadSystemStatus();
    loadPlayers();
    loadAudioFiles();
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
            <div class="list-item">
                <div class="list-item-header">
                    <span class="list-item-title">${escapeHtml(player.name)}</span>
                    <span class="badge ${player.online ? 'online' : 'offline'}">
                        ${player.online ? 'Online' : 'Offline'}
                    </span>
                </div>
                <div class="list-item-details">
                    <span>ID: ${escapeHtml(player.id)}</span>
                    <span>Volume: ${player.volume}/16</span>
                    ${player.battery_level ? `<span>Battery: ${player.battery_level}%</span>` : ''}
                    <span>${player.playing ? '▶️ Playing' : '⏸️ Paused'}</span>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading players:', error);
        container.innerHTML = '<p class="error-message">Failed to load players. Check your Yoto API authentication.</p>';
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
