// Library JavaScript

// API base URL
const API_BASE = '/api';

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
            </div>
        `;
    }).join('');
    
    // Add event listeners using delegation
    cardsGrid.addEventListener('click', function(event) {
        const card = event.target.closest('.library-card');
        if (card) {
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
                <span class="badge enabled">${escapeHtml(String(playlist.itemCount))} items</span>
            </div>
            ${playlist.imageId ? `<div class="list-item-details"><span>Image ID: ${escapeHtml(playlist.imageId)}</span></div>` : ''}
        </div>
    `).join('');
    
    // Add event listeners using delegation
    playlistsList.addEventListener('click', function(event) {
        const listItem = event.target.closest('.list-item');
        if (listItem) {
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
        const response = await fetch(`${API_BASE}/library/content/${contentId}`);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch content details: ${response.statusText}`);
        }
        
        const content = await response.json();
        
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

// Utility functions
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// TTS Generator Functions

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
        const filename = filenameInput.value.trim() || 'my-story';
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
        
        // Refresh library to show new file
        setTimeout(() => {
            refreshLibrary();
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
