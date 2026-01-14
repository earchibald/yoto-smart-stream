// Library JavaScript

// API base URL
const API_BASE = '/api';

// Fuzzy matching helper
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

// Apply filter to cards
function applyCardsFilter() {
    const query = document.getElementById('cards-filter')?.value || '';
    const cards = document.querySelectorAll('#cards-grid .library-card');
    let visibleCount = 0;
    cards.forEach(card => {
        const title = card.getAttribute('data-content-title') || '';
        const match = fuzzyMatch(query, title);
        card.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    });
    // Show "no results" message if nothing matches
    const grid = document.getElementById('cards-grid');
    if (visibleCount === 0 && query) {
        if (!grid.querySelector('.no-results')) {
            const msg = document.createElement('p');
            msg.className = 'no-results loading';
            msg.textContent = `No cards match "${query}"`;
            grid.appendChild(msg);
        }
    } else {
        const msg = grid.querySelector('.no-results');
        if (msg) msg.remove();
    }
}

// Apply filter to playlists
function applyPlaylistsFilter() {
    const query = document.getElementById('playlists-filter')?.value || '';
    const items = document.querySelectorAll('#playlists-list .list-item');
    let visibleCount = 0;
    items.forEach(item => {
        const title = item.getAttribute('data-content-title') || '';
        const match = fuzzyMatch(query, title);
        item.style.display = match ? '' : 'none';
        if (match) visibleCount++;
    });
    // Show "no results" message if nothing matches
    const list = document.getElementById('playlists-list');
    if (visibleCount === 0 && query) {
        if (!list.querySelector('.no-results')) {
            const msg = document.createElement('p');
            msg.className = 'no-results loading';
            msg.textContent = `No playlists match "${query}"`;
            list.appendChild(msg);
        }
    } else {
        const msg = list.querySelector('.no-results');
        if (msg) msg.remove();
    }
}

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
    loadSystemStatus();
    loadLibrary();
    
    // Setup modal close handlers
    const closeBtn = document.getElementById('modal-close-btn');
    const modal = document.getElementById('content-modal');
    
    if (closeBtn) {
        closeBtn.addEventListener('click', closeContentModal);
    }
    
    // Close modal when clicking outside
    if (modal) {
        modal.addEventListener('click', function(event) {
            if (event.target === modal) {
                closeContentModal();
            }
        });
    }
    
    // Setup filter listeners
    const cardsFilter = document.getElementById('cards-filter');
    const playlistsFilter = document.getElementById('playlists-filter');
    const freshToggle = document.getElementById('fresh-toggle');
    if (cardsFilter) {
        cardsFilter.addEventListener('input', applyCardsFilter);
    }
    if (playlistsFilter) {
        playlistsFilter.addEventListener('input', applyPlaylistsFilter);
    }
    
    // Add keyboard shortcut: '/' key focuses the filter input
    document.addEventListener('keydown', (event) => {
        // Check if '/' key is pressed and not in an input field
        if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
            event.preventDefault();
            // Focus the cards filter if visible, otherwise the playlists filter
            const cardsFilter = document.getElementById('cards-filter');
            const playlistsFilter = document.getElementById('playlists-filter');
            if (cardsFilter && cardsFilter.offsetParent !== null) {
                cardsFilter.focus();
            } else if (playlistsFilter && playlistsFilter.offsetParent !== null) {
                playlistsFilter.focus();
            }
        }
    });
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
            <div class="library-card" data-content-id="${escapeHtml(card.id)}" data-content-title="${escapeHtml(card.title)}">
                <div class="library-card-image">
                    <img src="${escapeHtml(coverImage)}" alt="${escapeHtml(card.title)}" onerror="this.src='https://via.placeholder.com/150?text=No+Image'">
                </div>
                <div class="library-card-content">
                    <h4 class="library-card-title">${escapeHtml(card.title)}</h4>
                    ${card.author ? `<p class="library-card-author">by ${escapeHtml(card.author)}</p>` : ''}
                    ${card.description ? `<p class="library-card-description">${escapeHtml(card.description)}</p>` : ''}
                </div>
                <button class="library-card-info-btn" onclick="event.stopPropagation(); showCardRawData('${escapeHtml(card.id)}', '${escapeHtml(card.title)}');" title="View Raw Data">ℹ️</button>
            </div>
        `;
    }).join('');
    
    // Add event listeners using delegation
    cardsGrid.addEventListener('click', function(event) {
        const card = event.target.closest('.library-card');
        if (card && !event.target.closest('.library-card-info-btn')) {
            const contentId = card.getAttribute('data-content-id');
            const contentTitle = card.getAttribute('data-content-title');
            showContentDetails(contentId, contentTitle);
        }
    });
}

// Display playlists
function displayPlaylists(playlists) {
    const playlistsList = document.getElementById('playlists-list');
    
    if (!playlists || playlists.length === 0) {
        playlistsList.innerHTML = '<p class="loading">No playlists found in your library.</p>';
        return;
    }
    
    playlistsList.innerHTML = playlists.map(playlist => `
        <div class="list-item" data-content-id="${escapeHtml(playlist.id)}" data-content-title="${escapeHtml(playlist.name)}">
            <div class="list-item-header">
                <span class="list-item-title">📁 ${escapeHtml(playlist.name)}</span>
                <div style="display: flex; gap: 0.5rem; align-items: center;">
                    <span class="badge enabled">${escapeHtml(String(playlist.itemCount))} items</span>
                    <button class="info-btn-small" onclick="event.stopPropagation(); showCardRawData('${escapeHtml(playlist.id)}', '${escapeHtml(playlist.name)}');" title="View Raw Data">ℹ️</button>
                </div>
            </div>
            ${playlist.imageId ? `<div class="list-item-details"><span>Image ID: ${escapeHtml(playlist.imageId)}</span></div>` : ''}
        </div>
    `).join('');
    
    // Add event listeners using delegation
    playlistsList.addEventListener('click', function(event) {
        const listItem = event.target.closest('.list-item');
        if (listItem && !event.target.closest('.info-btn-small')) {
            const contentId = listItem.getAttribute('data-content-id');
            const contentTitle = listItem.getAttribute('data-content-title');
            showContentDetails(contentId, contentTitle);
        }
    });
}

// Refresh library
function refreshLibrary() {
    loadLibrary();
}

// Show content details in modal
async function showContentDetails(contentId, contentTitle) {
    const modal = document.getElementById('content-modal');
    const modalTitle = document.getElementById('modal-content-title');
    const modalBody = document.getElementById('modal-content-body');
    
    // Show modal with loading state
    modalTitle.textContent = contentTitle;
    modalBody.innerHTML = '<p class="loading">Loading content details...</p>';
    modal.style.display = 'flex';
    
    try {
        // Use the chapters endpoint which uses local cache
        const response = await fetch(`${API_BASE}/library/${contentId}/chapters`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch content details: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Map the chapters response to content format
        const content = {
            title: data.card_title,
            author: data.card_author,
            coverImageLarge: data.card_cover,
            coverImage: data.card_cover,
            chapters: data.chapters ? data.chapters.map(ch => ({
                title: ch.title,
                display: ch.title,
                duration: ch.duration,
                icon: ch.icon
            })) : []
        };
        
        // Build content details HTML
        let detailsHtml = '';
        
        // Show cover image if available
        if (content.coverImage || content.coverImageLarge) {
            const coverUrl = content.coverImageLarge || content.coverImage;
            detailsHtml += `
                <div class="modal-cover-image">
                    <img src="${escapeHtml(coverUrl)}" alt="${escapeHtml(contentTitle)}" onerror="this.style.display='none'">
                </div>
            `;
        }
        
        // Show basic information
        detailsHtml += '<div class="modal-info-section">';
        if (content.author) {
            detailsHtml += `<p><strong>Author:</strong> ${escapeHtml(content.author)}</p>`;
        }
        if (content.description) {
            detailsHtml += `<p><strong>Description:</strong> ${escapeHtml(content.description)}</p>`;
        }
        if (content.language) {
            detailsHtml += `<p><strong>Language:</strong> ${escapeHtml(content.language)}</p>`;
        }
        if (content.duration) {
            const minutes = Math.floor(content.duration / 60);
            detailsHtml += `<p><strong>Duration:</strong> ${minutes} minutes</p>`;
        }
        detailsHtml += '</div>';
        
        // Show chapters/tracks if available
        if (content.chapters && content.chapters.length > 0) {
            detailsHtml += `
                <div class="modal-chapters-section">
                    <h4>Chapters (${escapeHtml(String(content.chapters.length))})</h4>
                    <div class="chapters-list">
                        ${content.chapters.map((chapter, index) => `
                            <div class="chapter-item">
                                <span class="chapter-number">${escapeHtml(String(index + 1))}</span>
                                <div class="chapter-info">
                                    <div class="chapter-title">${escapeHtml(chapter.title || chapter.display || 'Untitled')}</div>
                                    ${chapter.duration ? `<div class="chapter-duration">${escapeHtml(formatDuration(chapter.duration))}</div>` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }
        
        modalBody.innerHTML = detailsHtml;
        
    } catch (error) {
        console.error('Error loading content details:', error);
        modalBody.innerHTML = `<p class="error-message">Failed to load content details: ${error.message}</p>`;
    }
}

// Close modal
function closeContentModal() {
    const modal = document.getElementById('content-modal');
    modal.style.display = 'none';
}

// Format duration in seconds to readable format
function formatDuration(seconds) {
    if (!seconds) return '';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Show raw card data in JSON format
async function showCardRawData(cardId, cardTitle) {
    const modal = document.getElementById('raw-data-modal');
    const modalTitle = document.getElementById('raw-data-title');
    const modalBody = document.getElementById('raw-data-body');
    const copyBtn = document.getElementById('copy-raw-data-btn');
    
    // Show modal with loading state
    modalTitle.textContent = `Raw Data: ${cardTitle}`;
    modalBody.innerHTML = '<p class="loading">Loading all card data...</p>';
    modal.style.display = 'flex';
    
    try {
        // Fetch comprehensive card data from new endpoint
        const response = await fetch(`${API_BASE}/library/${cardId}/raw`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch raw data: ${response.statusText}`);
        }
        
        const rawData = await response.json();
        
        // Display formatted JSON
        modalBody.innerHTML = `<pre class="json-content">${escapeHtml(JSON.stringify(rawData, null, 2))}</pre>`;
        
        // Setup copy button
        copyBtn.onclick = function() {
            navigator.clipboard.writeText(JSON.stringify(rawData, null, 2)).then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = '✓ Copied!';
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy:', err);
                alert('Failed to copy to clipboard');
            });
        };
        
    } catch (error) {
        console.error('Error loading raw card data:', error);
        modalBody.innerHTML = `<p class="error-message">Failed to load raw data: ${error.message}</p>`;
    }
}

// Close raw data modal
function closeRawDataModal() {
    document.getElementById('raw-data-modal').style.display = 'none';
}

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
