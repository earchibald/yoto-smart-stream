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

// Check if user is admin and hide admin nav if not
async function checkAdminStatus() {
    try {
        const response = await fetch('/api/user/session', { credentials: 'include' });
        if (response.ok) {
            const data = await response.json();
            if (!data.is_admin) {
                // Hide admin nav link for non-admin users
                const adminLink = document.querySelector('a[href="/admin"]');
                if (adminLink) {
                    adminLink.parentElement.style.display = 'none';
                }
            }
        }
    } catch (error) {
        console.error('Error checking admin status:', error);
    }
}

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
    checkAdminStatus();
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

        // Add Escape key listener to close modals
        if (event.key === 'Escape') {
            const contentModal = document.getElementById('content-modal');
            const rawDataModal = document.getElementById('raw-data-modal');

            // Close whichever modal is currently open
            if (contentModal && contentModal.style.display === 'flex') {
                closeContentModal();
            }
            if (rawDataModal && rawDataModal.style.display === 'flex') {
                closeRawDataModal();
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
        const skeleton = document.getElementById('cards-skeleton');

        // Hide skeleton and show error message
        if (skeleton) {
            skeleton.style.display = 'none';
        }

        cardsGrid.innerHTML = `
            <div class="error-boundary error">
                <div class="icon">⚠️</div>
                <div class="content">
                    <strong>Failed to load library</strong>
                    <p>${error.message || 'An unexpected error occurred'}</p>
                </div>
            </div>
        `;
    }
}

// Display cards in grid
function displayCards(cards) {
    const cardsGrid = document.getElementById('cards-grid');
    const skeleton = document.getElementById('cards-skeleton');

    // Hide skeleton loader once data is ready
    if (skeleton) {
        skeleton.style.display = 'none';
    }

    if (!cards || cards.length === 0) {
        cardsGrid.innerHTML = '<p class="loading">No cards found in your library.</p>';
        return;
    }

    // Create a nice placeholder SVG for cards without cover art
    const placeholderSVG = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300' viewBox='0 0 300 300'%3E%3Cdefs%3E%3ClinearGradient id='grad' x1='0%25' y1='0%25' x2='100%25' y2='100%25'%3E%3Cstop offset='0%25' style='stop-color:%23a5f3fc;stop-opacity:1' /%3E%3Cstop offset='100%25' style='stop-color:%2306b6d4;stop-opacity:1' /%3E%3C/linearGradient%3E%3C/defs%3E%3Crect width='300' height='300' fill='url(%23grad)'/%3E%3Ctext x='150' y='170' font-size='80' text-anchor='middle' fill='white' font-family='Arial, sans-serif'%3E🎵%3C/text%3E%3C/svg%3E`;

    cardsGrid.innerHTML = cards.map(card => {
        // Use cover image if available, otherwise use modern SVG placeholder
        const coverImage = card.cover || placeholderSVG;

        return `
            <div class="library-card" data-content-id="${escapeHtml(card.id)}" data-content-title="${escapeHtml(card.title)}">
                <div class="library-card-image">
                    <img src="${escapeHtml(coverImage)}" alt="${escapeHtml(card.title)}" onerror="this.src='${placeholderSVG}'">
                    <div class="library-card-buttons">
                        <button class="library-card-info-btn" onclick="event.stopPropagation(); showCardRawData('${escapeHtml(card.id)}', '${escapeHtml(card.title)}');" title="View Raw Data" aria-label="View Raw Data"></button>
                        <button class="library-card-edit-btn" onclick="event.stopPropagation(); editCard('${escapeHtml(card.id)}', '${escapeHtml(card.title)}');" title="Edit Card" aria-label="Edit Card">✏️</button>
                    </div>
                </div>
                <div class="library-card-content">
                    <h4 class="library-card-title">${escapeHtml(card.title)}</h4>
                    ${card.author ? `<p class="library-card-author">by ${escapeHtml(card.author)}</p>` : ''}
                    ${card.description ? `<p class="library-card-description">${escapeHtml(card.description)}</p>` : ''}
                </div>
            </div>
        `;
    }).join('');

    // Add event listeners using delegation
    cardsGrid.addEventListener('click', function(event) {
        const card = event.target.closest('.library-card');
        if (card && !event.target.closest('.library-card-info-btn') && !event.target.closest('.library-card-edit-btn')) {
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
// Delete Playlist Modal Functions for library.js

// Open delete playlist modal
function openDeletePlaylistModal() {
    const modal = document.getElementById('delete-playlist-modal');
    modal.style.display = 'flex';

    // Reset the modal state
    document.getElementById('delete-playlist-search').value = '';
    document.getElementById('delete-playlist-search-results').style.display = 'none';
    document.getElementById('delete-playlist-result').style.display = 'none';
}

// Close delete playlist modal
function closeDeletePlaylistModal() {
    const modal = document.getElementById('delete-playlist-modal');
    modal.style.display = 'none';
}

// Search for playlists to delete
async function searchPlaylistsForDelete() {
    const playlistName = document.getElementById('delete-playlist-search').value.trim();

    if (!playlistName) {
        alert('Please enter a playlist name to search for');
        return;
    }

    const loadingDiv = document.getElementById('delete-playlist-loading');
    const resultsDiv = document.getElementById('delete-playlist-search-results');
    const resultMessageDiv = document.getElementById('delete-playlist-result');

    loadingDiv.style.display = 'block';
    resultsDiv.style.display = 'none';
    resultMessageDiv.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/streams/playlists/search/${encodeURIComponent(playlistName)}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to search playlists');
        }

        loadingDiv.style.display = 'none';

        if (result.count === 0) {
            resultMessageDiv.textContent = `No playlists found matching "${playlistName}"`;
            resultMessageDiv.className = 'result-message info-message';
            resultMessageDiv.style.display = 'block';
            return;
        }

        // Display results
        displayPlaylistSearchResults(result.playlists);
        resultsDiv.style.display = 'block';

    } catch (error) {
        console.error('Failed to search playlists:', error);
        loadingDiv.style.display = 'none';
        resultMessageDiv.textContent = 'Failed to search playlists: ' + error.message;
        resultMessageDiv.className = 'result-message error-message';
        resultMessageDiv.style.display = 'block';
    }
}

function displayPlaylistSearchResults(playlists) {
    const listDiv = document.getElementById('delete-playlist-list');
    const countSpan = document.getElementById('delete-playlist-count');
    const selectAllBtn = document.getElementById('select-all-delete-btn');

    countSpan.textContent = playlists.length;
    selectAllBtn.style.display = playlists.length > 1 ? 'block' : 'none';

    listDiv.innerHTML = playlists.map((playlist, index) => `
        <div class="playlist-item" style="padding: 1rem; border: 1px solid #ddd; border-radius: 4px; margin-bottom: 0.5rem;">
            <div style="display: flex; align-items: flex-start; gap: 1rem;">
                <input
                    type="checkbox"
                    id="playlist-${index}"
                    data-playlist-id="${escapeHtml(playlist.id)}"
                    data-playlist-title="${escapeHtml(playlist.title)}"
                    onchange="updateDeleteSelection()"
                    style="margin-top: 0.25rem; cursor: pointer;"
                />
                <div style="flex: 1;">
                    <label for="playlist-${index}" style="cursor: pointer; font-weight: 500; margin-bottom: 0.25rem;">
                        ${escapeHtml(playlist.title)}
                    </label>
                    ${playlist.description ? `<p style="margin: 0.25rem 0; color: #666; font-size: 0.9rem;">${escapeHtml(playlist.description)}</p>` : ''}
                    <p style="margin: 0.25rem 0; color: #999; font-size: 0.85rem;">ID: ${escapeHtml(playlist.id)}</p>
                    ${playlist.created_at ? `<p style="margin: 0.25rem 0; color: #999; font-size: 0.85rem;">Created: ${new Date(playlist.created_at).toLocaleDateString()}</p>` : ''}
                </div>
            </div>
        </div>
    `).join('');
}

function updateDeleteSelection() {
    const checkboxes = document.querySelectorAll('#delete-playlist-list input[type="checkbox"]');
    const selectedCount = document.querySelectorAll('#delete-playlist-list input[type="checkbox"]:checked').length;
    const selectedCountSpan = document.getElementById('delete-selected-count');
    const deleteBtn = document.getElementById('delete-confirm-btn');

    selectedCountSpan.textContent = selectedCount;

    if (selectedCount > 0) {
        deleteBtn.disabled = false;
        deleteBtn.style.opacity = '1';
        deleteBtn.style.cursor = 'pointer';
    } else {
        deleteBtn.disabled = true;
        deleteBtn.style.opacity = '0.5';
        deleteBtn.style.cursor = 'not-allowed';
    }
}

function toggleSelectAllDelete() {
    const checkboxes = document.querySelectorAll('#delete-playlist-list input[type="checkbox"]');
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);

    checkboxes.forEach(cb => {
        cb.checked = !allChecked;
    });

    updateDeleteSelection();
}

async function deleteSelectedPlaylists() {
    const checkboxes = document.querySelectorAll('#delete-playlist-list input[type="checkbox"]:checked');

    if (checkboxes.length === 0) {
        alert('Please select at least one playlist to delete');
        return;
    }

    const playlistIds = Array.from(checkboxes).map(cb => cb.dataset.playlistId);
    const playlistTitles = Array.from(checkboxes).map(cb => cb.dataset.playlistTitle);

    const confirmMessage = `Are you sure you want to delete ${playlistIds.length} playlist(s)?\n\n` +
        playlistTitles.slice(0, 5).map(t => `• ${t}`).join('\n') +
        (playlistTitles.length > 5 ? `\n... and ${playlistTitles.length - 5} more` : '') +
        '\n\nThis action cannot be undone.';

    if (!confirm(confirmMessage)) {
        return;
    }

    const deleteBtn = document.getElementById('delete-confirm-btn');
    const originalText = deleteBtn.textContent;
    deleteBtn.disabled = true;
    deleteBtn.textContent = '⏳ Deleting...';

    try {
        const response = await fetch(`${API_BASE}/streams/playlists/delete-multiple`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                playlist_ids: playlistIds,
            }),
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to delete playlists');
        }

        // Show results
        const resultDiv = document.getElementById('delete-playlist-result');
        const successCount = result.success.length;
        const failedCount = result.failed.length;

        let message = `✓ Successfully deleted ${successCount} playlist(s)`;
        if (failedCount > 0) {
            message += `\n\n✗ Failed to delete ${failedCount} playlist(s):\n`;
            result.failed.forEach(f => {
                message += `• ${f.playlist_id}: ${f.error}\n`;
            });
        }

        resultDiv.textContent = message;
        resultDiv.className = 'result-message ' + (failedCount > 0 ? 'error-message' : 'success-message');
        resultDiv.style.display = 'block';

        // Refresh the library after successful deletion
        if (successCount > 0) {
            setTimeout(() => {
                refreshLibrary();
                closeDeletePlaylistModal();
            }, 2000);
        }

    } catch (error) {
        console.error('Failed to delete playlists:', error);
        const resultDiv = document.getElementById('delete-playlist-result');
        resultDiv.textContent = 'Failed to delete playlists: ' + error.message;
        resultDiv.className = 'result-message error-message';
        resultDiv.style.display = 'block';
    } finally {
        deleteBtn.disabled = false;
        deleteBtn.textContent = originalText;
    }
}

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    const modal = document.getElementById('delete-playlist-modal');
    if (event.target === modal) {
        closeDeletePlaylistModal();
    }
});

// Edit card - test if it's a MYO card, load it to managed streams, and open Stream Scripter
async function editCard(cardId, cardTitle) {
    console.log('[EDIT CARD] Starting edit for card:', cardId, cardTitle);
    
    try {
        // Step 1: Check if card is editable (MYO card) using the edit-check endpoint
        // This endpoint attempts to update the card with NO CHANGES
        console.log('[EDIT CARD] Checking if card is editable (testing with no-change update)...');
        
        const checkResponse = await fetch(`${API_BASE}/library/${cardId}/edit-check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        });
        
        if (!checkResponse.ok) {
            throw new Error(`Failed to check card editability: ${checkResponse.statusText}`);
        }
        
        const checkResult = await checkResponse.json();
        console.log('[EDIT CARD] Edit check response:', checkResult);
        
        // Check if the card is editable
        if (!checkResult.editable) {
            console.error('[EDIT CARD] Card is not editable (commercial card)');
            alert(`Cannot edit "${cardTitle}".\n\n${checkResult.message}`);
            return;
        }
        
        console.log('[EDIT CARD] ✓ Card is editable! (MYO card confirmed)');
        
        // Step 2: Fetch the full card data to extract audio files
        console.log('[EDIT CARD] Fetching full card details...');
        const detailsResponse = await fetch(`${API_BASE}/library/content/${cardId}`);
        if (!detailsResponse.ok) {
            throw new Error(`Failed to fetch card details: ${detailsResponse.statusText}`);
        }
        
        const cardData = await detailsResponse.json();
        console.log('[EDIT CARD] Card data fetched:', cardData);
        
        // Step 3: Extract audio files from the card's chapters/tracks
        console.log('[EDIT CARD] Extracting audio files from card...');
        
        const chapters = cardData.content?.chapters || [];
        const audioFiles = [];
        
        // Extract audio filenames from tracks in chapters
        for (const chapter of chapters) {
            const tracks = chapter.tracks || [];
            for (const track of tracks) {
                // Check for trackUrl or url field
                const trackUrl = track.trackUrl || track.url || '';
                console.log('[EDIT CARD] Processing track URL:', trackUrl);
                
                if (trackUrl.startsWith('yoto:#')) {
                    // Yoto-hosted content - pass through as-is
                    audioFiles.push(trackUrl);
                    console.log('[EDIT CARD] ✓ Found yoto:# URL:', trackUrl);
                } else {
                    // Extract filename from our streaming URL (e.g., https://domain/audio/filename.mp3 -> filename.mp3)
                    const urlMatch = trackUrl.match(/\/audio\/([^?#]+)/);
                    if (urlMatch) {
                        const filename = decodeURIComponent(urlMatch[1]);
                        audioFiles.push(filename);
                        console.log('[EDIT CARD] ✓ Extracted audio file:', filename);
                    } else if (trackUrl) {
                        console.log('[EDIT CARD] Skipping external URL:', trackUrl);
                    }
                }
            }
        }
        
        console.log('[EDIT CARD] Total audio files extracted:', audioFiles.length, audioFiles);
        
        if (audioFiles.length === 0) {
            console.warn('[EDIT CARD] No audio files found in card');
            alert(`No audio files found in card "${cardTitle}".\n\nThis card may not contain any playable audio content.`);
            return;
        }
        
        // Step 4: Create or update a managed stream with this card's content
        const streamName = `edit_${cardId}`;
        console.log('[EDIT CARD] Creating/updating managed stream:', streamName);
        
        // Create the stream with the extracted files
        const createStreamResponse = await fetch(`${API_BASE}/streams/${streamName}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                files: audioFiles,
                mode: 'sequential'  // Default to sequential playback
            }),
        });
        
        if (!createStreamResponse.ok) {
            const errorText = await createStreamResponse.text();
            console.error('[EDIT CARD] Failed to create stream:', errorText);
            throw new Error(`Failed to create managed stream: ${createStreamResponse.statusText}`);
        }
        
        console.log('[EDIT CARD] ✓ Managed stream created/updated:', streamName);
        
        // Step 5: Navigate to Stream Scripter with this stream selected
        console.log('[EDIT CARD] Navigating to Stream Scripter...');
        
        // Switch to Streams tab
        const streamsTab = document.querySelector('[data-tab="streams"]');
        if (streamsTab) {
            streamsTab.click();
            console.log('[EDIT CARD] ✓ Switched to Streams tab');
        } else {
            console.error('[EDIT CARD] Could not find Streams tab');
        }
        
        // Wait a moment for the tab to load
        setTimeout(() => {
            // Open the Stream Scripter modal
            if (typeof openStreamScripter === 'function') {
                openStreamScripter();
                console.log('[EDIT CARD] ✓ Stream Scripter opened');
                
                // Wait for the scripter to load, then select our stream
                setTimeout(() => {
                    const queueSelector = document.getElementById('queue-selector');
                    if (queueSelector) {
                        queueSelector.value = streamName;
                        queueSelector.dispatchEvent(new Event('change'));
                        console.log('[EDIT CARD] ✓ Stream selected in scripter:', streamName);
                    } else {
                        console.error('[EDIT CARD] Could not find queue selector');
                    }
                }, 500);
            } else {
                console.error('[EDIT CARD] openStreamScripter function not found');
                alert('Stream created, but could not open Stream Scripter. Please navigate to Streams tab manually.');
            }
        }, 300);
        
        console.log('[EDIT CARD] ✓✓✓ Edit workflow complete! ✓✓✓');
        
    } catch (error) {
        console.error('[EDIT CARD] Error:', error);
        alert(`Failed to edit card: ${error.message}`);
    }
}

