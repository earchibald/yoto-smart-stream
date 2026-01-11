// Dashboard JavaScript

// API base URL
const API_BASE = '/api';

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
    loadSystemStatus();
    loadPlayers();
    loadAudioFiles();
});

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
        
        // Update stats
        document.getElementById('audio-count').textContent = data.features?.audio_streaming ? 'Enabled' : 'Disabled';
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
