// Library JavaScript

// API base URL
const API_BASE = '/api';

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
    loadSystemStatus();
    loadLibrary();
});

// Load system status
async function loadSystemStatus() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (!response.ok) throw new Error('Failed to fetch status');
        
        const data = await response.json();
        
        // Update version
        document.getElementById('app-version').textContent = `v${data.version}`;
        
    } catch (error) {
        console.error('Error loading status:', error);
    }
}

// Load library data
async function loadLibrary() {
    const statusEl = document.getElementById('status');
    const statusTextEl = document.getElementById('status-text');
    const authMessage = document.getElementById('auth-message');
    const statsGrid = document.getElementById('stats-grid');
    const cardsSection = document.getElementById('cards-section');
    const playlistsSection = document.getElementById('playlists-section');
    const actionsSection = document.getElementById('actions-section');
    
    statusTextEl.textContent = 'Loading library...';
    
    try {
        const response = await fetch(`${API_BASE}/library`);
        
        if (response.status === 401) {
            // Not authenticated
            statusEl.classList.add('error');
            statusTextEl.textContent = 'Not Authenticated';
            authMessage.style.display = 'block';
            return;
        }
        
        if (!response.ok) throw new Error('Failed to fetch library');
        
        const data = await response.json();
        
        // Update status
        statusEl.classList.remove('error');
        statusTextEl.textContent = 'Library Loaded';
        
        // Update stats
        document.getElementById('card-count').textContent = data.totalCards;
        document.getElementById('playlist-count').textContent = data.totalPlaylists;
        
        // Show sections
        statsGrid.style.display = 'grid';
        cardsSection.style.display = 'block';
        playlistsSection.style.display = 'block';
        actionsSection.style.display = 'block';
        
        // Display cards
        displayCards(data.cards);
        
        // Display playlists
        displayPlaylists(data.playlists);
        
    } catch (error) {
        console.error('Error loading library:', error);
        statusEl.classList.add('error');
        statusTextEl.textContent = 'Error Loading Library';
        
        const cardsGrid = document.getElementById('cards-grid');
        cardsGrid.innerHTML = '<p class="error-message">Failed to load library. Please try again.</p>';
    }
}

// Display cards in grid
function displayCards(cards) {
    const cardsGrid = document.getElementById('cards-grid');
    
    if (!cards || cards.length === 0) {
        cardsGrid.innerHTML = '<p class="loading">No cards found in your library.</p>';
        return;
    }
    
    cardsGrid.innerHTML = cards.map(card => {
        // Use cover image if available, otherwise use placeholder
        const coverImage = card.cover || 'https://via.placeholder.com/150?text=No+Cover';
        
        return `
            <div class="library-card">
                <div class="library-card-image">
                    <img src="${escapeHtml(coverImage)}" alt="${escapeHtml(card.title)}" onerror="this.src='https://via.placeholder.com/150?text=No+Image'">
                </div>
                <div class="library-card-content">
                    <h4 class="library-card-title">${escapeHtml(card.title)}</h4>
                    ${card.author ? `<p class="library-card-author">by ${escapeHtml(card.author)}</p>` : ''}
                    ${card.description ? `<p class="library-card-description">${escapeHtml(card.description)}</p>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// Display playlists
function displayPlaylists(playlists) {
    const playlistsList = document.getElementById('playlists-list');
    
    if (!playlists || playlists.length === 0) {
        playlistsList.innerHTML = '<p class="loading">No playlists found in your library.</p>';
        return;
    }
    
    playlistsList.innerHTML = playlists.map(playlist => `
        <div class="list-item">
            <div class="list-item-header">
                <span class="list-item-title">📁 ${escapeHtml(playlist.name)}</span>
                <span class="badge enabled">${playlist.itemCount} items</span>
            </div>
            ${playlist.imageId ? `<div class="list-item-details"><span>Image ID: ${escapeHtml(playlist.imageId)}</span></div>` : ''}
        </div>
    `).join('');
}

// Refresh library
function refreshLibrary() {
    loadLibrary();
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
