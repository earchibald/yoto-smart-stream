const API_BASE = '/api';
const RESERVED_QUEUES = ['test-stream'];

// Store play mode preferences for each queue
const playModePreferences = {};

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
    // Load stored play mode preferences
    try {
        const saved = localStorage.getItem('smartStreamPlayModes');
        if (saved) {
            const parsed = JSON.parse(saved);
            if (parsed && typeof parsed === 'object') {
                Object.assign(playModePreferences, parsed);
            }
        }
    } catch (e) {
        // ignore storage errors
    }

    loadSystemInfo();
    loadManagedStreams();
    setupFormHandler();

    // Add Escape key listener to close modals
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            const audioPlayerModal = document.getElementById('audio-player-modal');
            const playlistModal = document.getElementById('create-playlist-modal');
            const scripterModal = document.getElementById('stream-scripter-modal');
            const deletePlaylistModal = document.getElementById('delete-playlist-modal');

            // Close whichever modal is currently open
            if (audioPlayerModal && audioPlayerModal.style.display === 'flex') {
                closeAudioPlayer();
            }
            if (playlistModal && playlistModal.style.display === 'flex') {
                closePlaylistModal();
            }
            if (scripterModal && scripterModal.style.display === 'flex') {
                closeStreamScripter();
            }
            if (deletePlaylistModal && deletePlaylistModal.style.display === 'flex') {
                closeDeletePlaylistModal();
            }
        }
    });
});

// Load system info
async function loadSystemInfo() {
    try {
        const response = await fetch(`${API_BASE}/status`);
        if (!response.ok) throw new Error('Failed to fetch status');

        const data = await response.json();

        // Update version
        document.getElementById('app-version').textContent = `v${data.version}`;

        // Update public URL (if available from settings)
        const urlDisplay = document.getElementById('url-display');
        urlDisplay.textContent = window.location.origin;

    } catch (error) {
        console.error('Error loading system info:', error);
    }
}

// Load audio files
async function loadAudioFiles() {
    const container = document.getElementById('audio-streams');
    const selectEl = document.getElementById('audio-file');

    try {
        const response = await fetch(`${API_BASE}/audio/list`);
        if (!response.ok) throw new Error('Failed to fetch audio files');

        const data = await response.json();
        const files = data.files || [];

        if (files.length === 0) {
            container.innerHTML = '<p class="loading">No audio files found. Add MP3 files to the audio_files directory.</p>';
            selectEl.innerHTML = '<option value="">No audio files available</option>';
            return;
        }

        // Populate select dropdown
        selectEl.innerHTML = '<option value="">Select an audio file...</option>' +
            files.map(file => `<option value="${escapeHtml(file.filename)}">${escapeHtml(file.filename)}</option>`).join('');

        // Display audio files as cards
        container.innerHTML = files.map(file => `
            <div class="stream-card">
                <div class="stream-header">
                    <h4>${escapeHtml(file.filename)}</h4>
                    <span class="stream-type">Static</span>
                </div>
                <p class="stream-url">/api/audio/${escapeHtml(file.filename)}</p>
                <p class="stream-size">Size: ${formatFileSize(file.size)}</p>
                <div class="stream-actions">
                    <button class="btn-small" data-action="copy" data-url="/api/audio/${escapeHtml(file.filename, true)}">📋 Copy URL</button>
                    <button class="btn-small" data-action="play" data-url="/api/audio/${escapeHtml(file.filename, true)}">▶️ Preview</button>
                </div>
            </div>
        `).join('');

        // Add event listeners to all action buttons
        container.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                const url = e.currentTarget.dataset.url;
                if (action === 'copy') {
                    copyUrl(url);
                } else if (action === 'play') {
                    playAudio(url);
                }
            });
        });

    } catch (error) {
        console.error('Error loading audio files:', error);
        container.innerHTML = '<p class="error-message">Failed to load audio files.</p>';
    }
}

// Load managed streams (queues)
async function loadManagedStreams() {
    const container = document.getElementById('managed-streams');

    try {
        const response = await fetch(`${API_BASE}/streams/queues`);
        if (!response.ok) throw new Error('Failed to fetch managed streams');

        const data = await response.json();
        const queues = data.queues || [];

        if (queues.length === 0) {
            container.innerHTML = '<p class="loading">No managed streams available.</p>';
            return;
        }

        // Fetch details for each queue
        const queueDetails = await Promise.all(
            queues.map(async (queueName) => {
                try {
                    const res = await fetch(`${API_BASE}/streams/${queueName}/queue`);
                    if (res.ok) {
                        return await res.json();
                    }
                    return null;
                } catch (err) {
                    console.error(`Error fetching queue ${queueName}:`, err);
                    return null;
                }
            })
        );

        // Display queue cards
        container.innerHTML = queueDetails
            .filter(queue => queue !== null)
            .map(queue => `
                <div class="stream-card">
                    <div class="stream-header">
                        <h4>${escapeHtml(queue.name)}</h4>
                        <span class="stream-type ${queue.name === 'test-stream' ? 'test' : 'managed'}">
                            ${queue.name === 'test-stream' ? 'Test Stream' : 'Managed'}
                        </span>
                    </div>
                    <p class="stream-url">/api/streams/${escapeHtml(queue.name)}/stream.mp3</p>
                    <p class="stream-description">
                        ${queue.file_count} file(s) in queue
                        ${queue.name === 'test-stream' ? ' • Always available for testing' : ''}
                    </p>
                    ${queue.name !== 'test-stream' ? `
                    <div class="stream-modes" style="margin: 1rem 0; padding: 0.75rem; background: #f5f5f5; border-radius: 4px;">
                        <div style="font-size: 0.9rem; color: #666; margin-bottom: 0.5rem;">Play Mode:</div>
                        <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                            <button class="mode-btn mode-sequential" data-queue="${escapeHtml(queue.name, true)}" data-mode="sequential" title="Play in order">📻 Sequential</button>
                            <button class="mode-btn mode-loop" data-queue="${escapeHtml(queue.name, true)}" data-mode="loop" title="Loop indefinitely">🔁 Loop</button>
                            <button class="mode-btn mode-shuffle" data-queue="${escapeHtml(queue.name, true)}" data-mode="shuffle" title="Random order">🔀 Shuffle</button>
                            <button class="mode-btn mode-endless-shuffle" data-queue="${escapeHtml(queue.name, true)}" data-mode="endless-shuffle" title="Shuffle forever">♾️ Endless Shuffle</button>
                        </div>
                    </div>
                    ` : ''}
                    <details class="stream-details">
                        <summary>Show queue contents</summary>
                        <ul class="queue-files">
                            ${queue.files.map(file => `<li>${escapeHtml(file)}</li>`).join('')}
                        </ul>
                    </details>
                    <div class="stream-actions">
                        <button class="btn-small" data-action="copy" data-url="/api/streams/${escapeHtml(queue.name, true)}/stream.mp3">📋 Copy URL</button>
                        <button class="btn-small" data-action="play" data-url="/api/streams/${escapeHtml(queue.name, true)}/stream.mp3" data-queue="${escapeHtml(queue.name, true)}">▶️ Preview</button>
                        ${queue.name !== 'test-stream' ? `
                            <button class="btn-small btn-playlist" data-action="create-playlist" data-queue="${escapeHtml(queue.name, true)}">📋 Create Playlist</button>
                            <button class="btn-small btn-delete" data-action="delete" data-queue="${escapeHtml(queue.name, true)}">🗑️ Delete</button>
                        ` : ''}
                    </div>
                </div>
            `).join('');

        // Add event listeners to action buttons
        container.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = e.currentTarget.dataset.action;
                const url = e.currentTarget.dataset.url;
                const queueName = e.currentTarget.dataset.queue;
                if (action === 'copy') {
                    copyUrl(url);
                } else if (action === 'play') {
                    // Try to infer queue name from the URL if not provided
                    let qName = queueName;
                    if (!qName && url) {
                        const match = url.match(/\/streams\/([^/]+)\/stream\.mp3/);
                        if (match) qName = match[1];
                    }
                    playAudio(url, qName);
                } else if (action === 'create-playlist') {
                    openPlaylistModal(queueName);
                } else if (action === 'delete') {
                    deleteStreamFromCard(queueName);
                }
            });
        });

    } catch (error) {
        console.error('Error loading managed streams:', error);
        container.innerHTML = '<p class="error-message">Failed to load managed streams.</p>';
    }
}

// Setup form handler
function setupFormHandler() {
    const form = document.getElementById('create-card-form');
    if (!form) {
        // Old form removed - Stream Scripter is the new way to create cards
        return;
    }
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const submitBtn = form.querySelector('button[type="submit"]');
        const resultEl = document.getElementById('card-result');

        // Get form values
        const title = document.getElementById('card-title').value;
        const description = document.getElementById('card-description').value;
        const audioFilename = document.getElementById('audio-file').value;

        if (!audioFilename) {
            showResult('Please select an audio file', 'error');
            return;
        }

        // Disable submit button
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';

        try {
            const response = await fetch(`${API_BASE}/cards/create-streaming`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    title: title,
                    description: description,
                    audio_filename: audioFilename,
                }),
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.detail || 'Failed to create card');
            }

            showResult(`✅ Card created successfully! Card ID: ${result.card_id}`, 'success');
            form.reset();

        } catch (error) {
            console.error('Error creating card:', error);
            showResult(`❌ ${error.message}`, 'error');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create Card';
        }
    });
}

// Show result message
function showResult(message, type) {
    const resultEl = document.getElementById('card-result');
    resultEl.textContent = message;
    resultEl.className = `result-message ${type}`;
    resultEl.style.display = 'block';

    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            resultEl.style.display = 'none';
        }, 5000);
    }
}

// Copy URL to clipboard
async function copyUrl(url) {
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

// Play audio preview
function playAudio(url, queueName = null) {
    // Build URL with play mode if available
    let fullUrl = window.location.origin + url;
    if (queueName && playModePreferences[queueName]) {
        const mode = playModePreferences[queueName];
        const separator = url.includes('?') ? '&' : '?';
        fullUrl = window.location.origin + url + separator + 'play_mode=' + encodeURIComponent(mode);
    }

    // Get modal and audio elements
    const modal = document.getElementById('audio-player-modal');
    const audio = document.getElementById('audio-element');
    const source = document.getElementById('audio-source');
    const urlDisplay = document.getElementById('player-url');
    const title = document.getElementById('player-title');

    // Stop any currently playing audio
    audio.pause();
    audio.currentTime = 0;

    // Set new source
    source.src = fullUrl;
    audio.load();

    // Update display
    urlDisplay.textContent = url;
    const mode = playModePreferences[queueName] ? ` (${playModePreferences[queueName]})` : '';
    title.textContent = 'Audio Preview: ' + url.split('/').pop() + mode;

    // Show modal
    modal.style.display = 'flex';

    // Play audio
    audio.play().catch(error => {
        console.error('Error playing audio:', error);
        alert('Failed to play audio. The file may not be compatible with your browser.');
        closeAudioPlayer();
    });
}

// Close audio player
function closeAudioPlayer() {
    const modal = document.getElementById('audio-player-modal');
    const audio = document.getElementById('audio-element');

    // Stop audio
    audio.pause();
    audio.currentTime = 0;

    // Hide modal
    modal.style.display = 'none';
}

// Close modal when clicking outside
window.onclick = function(event) {
    const modal = document.getElementById('audio-player-modal');
    if (event.target === modal) {
        closeAudioPlayer();
    }
}

// Utility functions
function escapeHtml(text, forAttribute = false) {
    if (forAttribute) {
        return text.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }
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

// Stream Scripter Functions
let currentQueueName = null;
let currentQueueFiles = []; // Legacy: flat file list
let currentChapters = []; // New: structured chapters with tracks
let availableFiles = [];
let cardMetadata = {
    title: '',
    description: '',
    author: 'Yoto Smart Stream',
    coverImageId: null
};
let useChapterStructure = false; // Toggle between flat and chapter structure

async function deleteStreamFromCard(queueName) {
    if (!confirm(`Are you sure you want to delete the queue "${queueName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/streams/${queueName}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete queue');
        }

        // Reload managed streams to reflect the deletion
        await loadManagedStreams();

        // Show success message briefly
        const container = document.getElementById('managed-streams');
        const message = document.createElement('div');
        message.className = 'result-message success-message';
        message.textContent = `Queue "${queueName}" deleted successfully!`;
        message.style.marginBottom = '1rem';
        container.insertBefore(message, container.firstChild);

        setTimeout(() => {
            message.remove();
        }, 3000);

    } catch (error) {
        console.error('Failed to delete queue:', error);
        alert('Failed to delete queue: ' + error.message);
    }
}

async function openStreamScripter() {
    const modal = document.getElementById('stream-scripter-modal');
    modal.style.display = 'flex';

    // Load available queues and files
    await loadStreamQueues();
    await loadAvailableFilesForScripter();

    // Start with new queue
    startNewQueue();
}

function closeStreamScripter() {
    const modal = document.getElementById('stream-scripter-modal');
    modal.style.display = 'none';
    currentQueueName = null;
    currentQueueFiles = [];
    currentChapters = [];
    cardMetadata = {
        title: '',
        description: '',
        author: 'Yoto Smart Stream',
        coverImageId: null
    };
    document.getElementById('scripter-result').style.display = 'none';
}

async function loadStreamQueues() {
    try {
        const response = await fetch(`${API_BASE}/streams/queues`);
        const data = await response.json();

        const editableQueues = (data.queues || []).filter(name => !RESERVED_QUEUES.includes(name));

        const selector = document.getElementById('queue-selector');
        selector.innerHTML = '<option value="">-- Select Queue --</option>';

        editableQueues.forEach(queueName => {
            const option = document.createElement('option');
            option.value = queueName;
            option.textContent = queueName;
            selector.appendChild(option);
        });

        // Add change listener
        selector.onchange = async (e) => {
            if (e.target.value) {
                await loadQueueForEditing(e.target.value);
            } else {
                startNewQueue();
            }
        };
    } catch (error) {
        console.error('Failed to load queues:', error);
    }
}

async function loadAvailableFilesForScripter() {
    try {
        const response = await fetch(`${API_BASE}/audio/list`);
        const data = await response.json();
        availableFiles = data.files;

        const container = document.getElementById('file-selector');
        container.innerHTML = '';

        data.files.forEach(file => {
            const fileDiv = document.createElement('div');
            fileDiv.className = 'file-checkbox-item';
            fileDiv.innerHTML = `
                <label>
                    <input type="checkbox" value="${escapeHtml(file.filename, true)}" onchange="toggleFileSelection('${escapeHtml(file.filename, true)}')">
                    <span>${escapeHtml(file.filename)}</span>
                </label>
            `;
            container.appendChild(fileDiv);
        });
    } catch (error) {
        console.error('Failed to load files:', error);
        document.getElementById('file-selector').innerHTML = '<p class="error">Failed to load files</p>';
    }
}

async function startNewQueue() {
    currentQueueName = null;
    currentQueueFiles = [];
    currentChapters = [];
    cardMetadata = {
        title: '',
        description: '',
        author: 'Yoto Smart Stream',
        coverImageId: null
    };

    // Refresh queue list to ensure it's up to date
    await loadStreamQueues();

    const queueNameValue = `stream-${crypto.randomUUID().split('-')[0]}`;
    document.getElementById('queue-selector').value = '';
    document.getElementById('queue-name').value = queueNameValue;
    document.getElementById('delete-queue-btn').style.display = 'none';

    // Reset metadata fields
    document.getElementById('card-title').value = '';
    document.getElementById('card-description').value = '';
    document.getElementById('card-author').value = 'Yoto Smart Stream';
    document.getElementById('card-cover-image').value = '';
    document.getElementById('cover-image-preview').style.display = 'none';
    document.getElementById('cover-image-status').style.display = 'none';

    updateQueueDisplay();
    clearFileCheckboxes();
}

async function loadQueueForEditing(queueName) {
    if (RESERVED_QUEUES.includes(queueName)) {
        showScripterResult('This queue is reserved and cannot be edited', 'error');
        startNewQueue();
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/streams/${queueName}/queue`);
        if (!response.ok) throw new Error('Failed to load queue');

        const data = await response.json();
        currentQueueName = queueName;
        currentQueueFiles = [...data.files];

        document.getElementById('queue-name').value = queueName;
        document.getElementById('delete-queue-btn').style.display = 'inline-block';

        // Try to load metadata from session storage (from library import)
        if (typeof sessionStorage !== 'undefined') {
            const storedMetadata = sessionStorage.getItem(`stream_metadata_${queueName}`);
            if (storedMetadata) {
                try {
                    const metadata = JSON.parse(storedMetadata);
                    populateMetadataFromImport(queueName, metadata);
                    // Clear the stored metadata after loading
                    sessionStorage.removeItem(`stream_metadata_${queueName}`);
                } catch (e) {
                    console.error('Failed to parse stored metadata:', e);
                }
            }
        }

        updateQueueDisplay();
        clearFileCheckboxes();
    } catch (error) {
        console.error('Failed to load queue for editing:', error);
        showScripterResult('Failed to load queue: ' + error.message, 'error');
    }
}

// Populate metadata fields from imported library card
function populateMetadataFromImport(streamName, metadataParam = null) {
    console.log('[POPULATE METADATA] Starting for stream:', streamName);

    let metadata = metadataParam;

    // If no metadata provided, try to load from session storage
    if (!metadata && typeof sessionStorage !== 'undefined') {
        const storedMetadata = sessionStorage.getItem(`stream_metadata_${streamName}`);
        if (storedMetadata) {
            try {
                metadata = JSON.parse(storedMetadata);
                console.log('[POPULATE METADATA] Loaded from session storage:', metadata);
            } catch (e) {
                console.error('[POPULATE METADATA] Failed to parse stored metadata:', e);
                return;
            }
        }
    }

    if (!metadata) {
        console.log('[POPULATE METADATA] No metadata found');
        return;
    }

    // Populate form fields
    if (metadata.title) {
        document.getElementById('card-title').value = metadata.title;
        console.log('[POPULATE METADATA] ✓ Title:', metadata.title);
    }

    if (metadata.description) {
        document.getElementById('card-description').value = metadata.description;
        console.log('[POPULATE METADATA] ✓ Description:', metadata.description);
    }

    if (metadata.author) {
        document.getElementById('card-author').value = metadata.author;
        console.log('[POPULATE METADATA] ✓ Author:', metadata.author);
    }

    if (metadata.coverImageId) {
        cardMetadata.coverImageId = metadata.coverImageId;
        console.log('[POPULATE METADATA] ✓ Cover image ID stored:', metadata.coverImageId);
        // Note: Cover image display requires fetching from Yoto API (future enhancement)
    }

    // If we have chapter structure with titles, apply them
    if (metadata.chapters && metadata.chapters.length > 0) {
        console.log('[POPULATE METADATA] Applying chapter titles...');

        // Wait a bit for the queue display to render
        setTimeout(() => {
            metadata.chapters.forEach((chapter, index) => {
                const titleInput = document.querySelector(`.chapter-title-input[data-index="${index}"]`);
                if (titleInput && chapter.title) {
                    titleInput.value = chapter.title;
                    console.log(`[POPULATE METADATA] ✓ Chapter ${index + 1} title: ${chapter.title}`);
                }
            });
        }, 100);
    }

    console.log('[POPULATE METADATA] ✓✓✓ Metadata population complete! ✓✓✓');
}

function toggleFileSelection(filename) {
    const checkbox = document.querySelector(`input[value="${filename}"]`);
    if (checkbox.checked) {
        addFileToQueue(filename);
    }
}

function addFileToQueue(filename) {
    if (!currentQueueFiles.includes(filename)) {
        currentQueueFiles.push(filename);
        updateQueueDisplay();
    }
}

function removeFileFromQueue(index) {
    currentQueueFiles.splice(index, 1);
    updateQueueDisplay();
}

function moveFileInQueue(fromIndex, toIndex) {
    const file = currentQueueFiles[fromIndex];
    currentQueueFiles.splice(fromIndex, 1);
    currentQueueFiles.splice(toIndex, 0, file);
    updateQueueDisplay();
}

function updateQueueDisplay() {
    const container = document.getElementById('queue-list');
    const countSpan = document.getElementById('queue-count');

    // Use chapter structure if available, otherwise fall back to flat file list
    const itemCount = useChapterStructure ? currentChapters.length : currentQueueFiles.length;
    countSpan.textContent = itemCount;

    if (itemCount === 0) {
        container.innerHTML = '<p style="color: #999; text-align: center; padding: 2rem;">No files added yet. Select files above to add them.</p>';
        return;
    }

    container.innerHTML = '';

    if (useChapterStructure) {
        // Display chapter structure with tracks
        currentChapters.forEach((chapter, chapterIndex) => {
            const chapterDiv = document.createElement('div');
            chapterDiv.className = 'chapter-item';
            chapterDiv.style.cssText = 'border: 1px solid #ddd; border-radius: 4px; margin-bottom: 0.75rem; padding: 0.75rem; background: #f9f9f9;';

            chapterDiv.innerHTML = `
                <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;">
                    <span style="font-weight: 600; color: #666; font-size: 0.85rem;">Chapter ${chapterIndex + 1}</span>
                    <input
                        type="text"
                        value="${escapeHtml(chapter.title)}"
                        onchange="updateChapterTitle(${chapterIndex}, this.value)"
                        onclick="this.select()"
                        style="flex: 1; padding: 0.25rem 0.5rem; border: 1px solid #ddd; border-radius: 3px; font-size: 0.9rem;"
                        placeholder="Chapter Title"
                    >
                    <button class="btn-icon" onclick="addTrackToChapter(${chapterIndex})" title="Add track">+</button>
                    <button class="btn-icon btn-remove" onclick="removeChapter(${chapterIndex})" title="Remove chapter">✕</button>
                </div>
                <div class="chapter-tracks" style="margin-left: 1rem;">
                    ${chapter.tracks.map((track, trackIndex) => `
                        <div class="track-item" style="display: flex; align-items: center; gap: 0.5rem; padding: 0.35rem; background: white; border-radius: 3px; margin-bottom: 0.25rem;">
                            <span style="color: #999; font-size: 0.85rem; width: 60px;">Track ${trackIndex + 1}</span>
                            <input
                                type="text"
                                value="${escapeHtml(track.title)}"
                                onchange="updateTrackTitle(${chapterIndex}, ${trackIndex}, this.value)"
                                onclick="this.select()"
                                style="flex: 1; padding: 0.25rem 0.5rem; border: 1px solid #ddd; border-radius: 3px; font-size: 0.85rem;"
                                placeholder="Track Title"
                            >
                            <span style="color: #999; font-size: 0.8rem;">${escapeHtml(track.filename)}</span>
                            <button class="btn-icon btn-remove" onclick="removeTrack(${chapterIndex}, ${trackIndex})">✕</button>
                        </div>
                    `).join('')}
                </div>
            `;
            container.appendChild(chapterDiv);
        });
    } else {
        // Display flat file list (legacy mode) with editable "chapter" titles
        currentQueueFiles.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'queue-file-item';
            item.draggable = true;
            item.dataset.index = index;

            // Extract clean filename without extension for default title
            const defaultTitle = file.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');

            item.innerHTML = `
                <span class="drag-handle">☰</span>
                <div style="flex: 1; display: flex; flex-direction: column; gap: 0.25rem;">
                    <input
                        type="text"
                        class="chapter-title-input"
                        data-index="${index}"
                        value="${escapeHtml(defaultTitle)}"
                        onchange="updateFileChapterTitle(${index}, this.value)"
                        onclick="this.select()"
                        style="padding: 0.25rem 0.5rem; border: 1px solid #ddd; border-radius: 3px; font-size: 0.9rem; font-weight: 500;"
                        placeholder="Chapter Title"
                    >
                    <span class="file-name" style="font-size: 0.8rem; color: #999;">${escapeHtml(file)}</span>
                </div>
                <div class="file-actions">
                    <button class="btn-icon" onclick="moveFileInQueue(${index}, ${Math.max(0, index - 1)})" ${index === 0 ? 'disabled' : ''}>↑</button>
                    <button class="btn-icon" onclick="moveFileInQueue(${index}, ${Math.min(currentQueueFiles.length - 1, index + 1)})" ${index === currentQueueFiles.length - 1 ? 'disabled' : ''}>↓</button>
                    <button class="btn-icon btn-remove" onclick="removeFileFromQueue(${index})">✕</button>
                </div>
            `;

            // Drag and drop handlers
            item.addEventListener('dragstart', handleDragStart);
            item.addEventListener('dragover', handleDragOver);
            item.addEventListener('drop', handleDrop);
            item.addEventListener('dragend', handleDragEnd);
            item.addEventListener('dragleave', handleDragLeave);

            container.appendChild(item);
        });
    }
}

// Chapter/Track management functions
function updateChapterTitle(chapterIndex, newTitle) {
    if (currentChapters[chapterIndex]) {
        currentChapters[chapterIndex].title = newTitle;
    }
}

function updateTrackTitle(chapterIndex, trackIndex, newTitle) {
    if (currentChapters[chapterIndex] && currentChapters[chapterIndex].tracks[trackIndex]) {
        currentChapters[chapterIndex].tracks[trackIndex].title = newTitle;
    }
}

function updateFileChapterTitle(index, newTitle) {
    // Store custom title in a parallel array or convert to chapter structure
    if (!currentQueueFiles._titles) {
        currentQueueFiles._titles = [];
    }
    currentQueueFiles._titles[index] = newTitle;
}

function addTrackToChapter(chapterIndex) {
    // Prompt user to select a file
    const filename = prompt('Enter audio filename to add as a track:');
    if (filename && currentChapters[chapterIndex]) {
        const defaultTitle = filename.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
        currentChapters[chapterIndex].tracks.push({
            filename: filename,
            title: defaultTitle
        });
        updateQueueDisplay();
    }
}

function removeChapter(chapterIndex) {
    if (confirm('Remove this chapter and all its tracks?')) {
        currentChapters.splice(chapterIndex, 1);
        updateQueueDisplay();
    }
}

function removeTrack(chapterIndex, trackIndex) {
    if (currentChapters[chapterIndex]) {
        currentChapters[chapterIndex].tracks.splice(trackIndex, 1);
        // Remove chapter if it has no tracks
        if (currentChapters[chapterIndex].tracks.length === 0) {
            currentChapters.splice(chapterIndex, 1);
        }
        updateQueueDisplay();
    }
}

function toggleChapterStructure() {
    if (useChapterStructure) {
        // Convert from chapter structure to flat list
        currentQueueFiles = [];
        currentChapters.forEach(chapter => {
            chapter.tracks.forEach(track => {
                currentQueueFiles.push(track.filename);
            });
        });
        useChapterStructure = false;
    } else {
        // Convert from flat list to chapter structure (1 file per chapter)
        currentChapters = currentQueueFiles.map(filename => {
            const defaultTitle = filename.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');
            return {
                title: defaultTitle,
                tracks: [{
                    filename: filename,
                    title: defaultTitle
                }]
            };
        });
        useChapterStructure = true;
    }
    updateQueueDisplay();
}

let draggedElement = null;

function handleDragStart(e) {
    draggedElement = this;
    this.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
}

function handleDragOver(e) {
    if (e.preventDefault) {
        e.preventDefault();
    }
    e.dataTransfer.dropEffect = 'move';

    if (this !== draggedElement) {
        this.classList.add('drag-over');
    }
    return false;
}

function handleDrop(e) {
    if (e.stopPropagation) {
        e.stopPropagation();
    }

    if (draggedElement !== this) {
        const fromIndex = parseInt(draggedElement.dataset.index);
        const toIndex = parseInt(this.dataset.index);
        moveFileInQueue(fromIndex, toIndex);
    }

    return false;
}

function handleDragEnd(e) {
    this.classList.remove('dragging');
    document.querySelectorAll('.queue-file-item').forEach(item => {
        item.classList.remove('drag-over');
    });
}

function handleDragLeave(e) {
    this.classList.remove('drag-over');
}

function clearFileCheckboxes() {
    document.querySelectorAll('#file-selector input[type="checkbox"]').forEach(cb => {
        cb.checked = false;
    });
}

function clearQueueSelection() {
    currentQueueFiles = [];
    updateQueueDisplay();
    clearFileCheckboxes();
}

async function saveQueue() {
    const queueNameInput = document.getElementById('queue-name');
    const queueName = queueNameInput.value.trim();

    // Validation
    if (!queueName) {
        showScripterResult('Please enter a queue name', 'error');
        return;
    }

    if (!/^[a-zA-Z0-9-]+$/.test(queueName)) {
        showScripterResult('Queue name must contain only alphanumeric characters and hyphens', 'error');
        return;
    }

    if (RESERVED_QUEUES.includes(queueName)) {
        showScripterResult('This queue is reserved and cannot be edited', 'error');
        return;
    }

    if (currentQueueFiles.length === 0) {
        showScripterResult('Please add at least one file to the queue', 'error');
        return;
    }

    // Check for duplicate name (only if creating new or renaming)
    if (queueName !== currentQueueName) {
        try {
            const response = await fetch(`${API_BASE}/streams/queues`);
            const data = await response.json();
            if (data.queues.includes(queueName)) {
                showScripterResult('A queue with this name already exists', 'error');
                return;
            }
        } catch (error) {
            console.error('Failed to check for duplicates:', error);
        }
    }

    try {
        // If editing existing queue with different name, delete old one first
        if (currentQueueName && currentQueueName !== queueName) {
            await fetch(`${API_BASE}/streams/${currentQueueName}`, { method: 'DELETE' });
        }

        // Clear the queue first (in case it exists)
        if (currentQueueName === queueName) {
            await fetch(`${API_BASE}/streams/${queueName}/queue`, { method: 'DELETE' });
        }

        // Add files to queue
        const response = await fetch(`${API_BASE}/streams/${queueName}/queue`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files: currentQueueFiles })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to save queue');
        }

        showScripterResult(`Queue "${queueName}" saved successfully!`, 'success');
        currentQueueName = queueName;

        // Reload queues list and managed streams
        await loadStreamQueues();
        await loadManagedStreams();

        // Update selector to show current queue
        document.getElementById('queue-selector').value = queueName;
        document.getElementById('delete-queue-btn').style.display = 'inline-block';

    } catch (error) {
        console.error('Failed to save queue:', error);
        showScripterResult('Failed to save queue: ' + error.message, 'error');
    }
}

async function confirmDeleteQueue() {
    if (!currentQueueName) {
        showScripterResult('No queue selected to delete', 'error');
        return;
    }

    if (RESERVED_QUEUES.includes(currentQueueName)) {
        showScripterResult('This queue is reserved and cannot be deleted', 'error');
        return;
    }

    if (!confirm(`Are you sure you want to delete the queue "${currentQueueName}"? This action cannot be undone.`)) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/streams/${currentQueueName}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to delete queue');
        }

        showScripterResult(`Queue "${currentQueueName}" deleted successfully!`, 'success');

        // Reload and reset
        await loadStreamQueues();
        await loadManagedStreams();
        startNewQueue();

    } catch (error) {
        console.error('Failed to delete queue:', error);
        showScripterResult('Failed to delete queue: ' + error.message, 'error');
    }
}

// Cover image handling
function previewCoverImage(input) {
    const preview = document.getElementById('cover-image-preview');
    const previewImg = document.getElementById('cover-image-preview-img');
    const statusDiv = document.getElementById('cover-image-status');

    if (input.files && input.files[0]) {
        const file = input.files[0];

        // Validate file type
        if (!file.type.startsWith('image/')) {
            statusDiv.textContent = '⚠️ Please select an image file';
            statusDiv.style.display = 'block';
            statusDiv.style.background = '#fff3cd';
            statusDiv.style.color = '#856404';
            return;
        }

        // Validate file size (max 5MB)
        if (file.size > 5 * 1024 * 1024) {
            statusDiv.textContent = '⚠️ Image must be smaller than 5MB';
            statusDiv.style.display = 'block';
            statusDiv.style.background = '#fff3cd';
            statusDiv.style.color = '#856404';
            input.value = '';
            return;
        }

        const reader = new FileReader();
        reader.onload = function(e) {
            previewImg.src = e.target.result;
            preview.style.display = 'block';
            statusDiv.textContent = '✓ Image ready for upload';
            statusDiv.style.display = 'block';
            statusDiv.style.background = '#d4edda';
            statusDiv.style.color = '#155724';
        };
        reader.readAsDataURL(file);
    } else {
        preview.style.display = 'none';
        statusDiv.style.display = 'none';
    }
}

async function uploadCoverImage() {
    const fileInput = document.getElementById('card-cover-image');
    if (!fileInput.files || !fileInput.files[0]) {
        return null;
    }

    const formData = new FormData();
    formData.append('image', fileInput.files[0]);

    try {
        const response = await fetch(`${API_BASE}/media/cover-image`, {
            method: 'POST',
            body: formData,
            credentials: 'include'
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to upload cover image');
        }

        const data = await response.json();
        return data.image_id;
    } catch (error) {
        console.error('Failed to upload cover image:', error);
        throw error;
    }
}

// Create card from queue with full metadata
async function createCardFromQueue() {
    const queueNameInput = document.getElementById('queue-name');
    const queueName = queueNameInput.value.trim();

    // Validation
    if (!queueName) {
        showScripterResult('Please enter a queue name', 'error');
        return;
    }

    if (currentQueueFiles.length === 0 && currentChapters.length === 0) {
        showScripterResult('Please add at least one file to the queue', 'error');
        return;
    }

    // Get metadata from form
    const title = document.getElementById('card-title').value.trim() || queueName;
    const description = document.getElementById('card-description').value.trim();
    const author = document.getElementById('card-author').value.trim() || 'Yoto Smart Stream';

    try {
        showScripterResult('Creating card... Please wait', 'info');

        // Upload cover image if provided
        let coverImageId = null;
        const fileInput = document.getElementById('card-cover-image');
        if (fileInput.files && fileInput.files[0]) {
            showScripterResult('Uploading cover image...', 'info');
            try {
                coverImageId = await uploadCoverImage();
            } catch (error) {
                showScripterResult(`⚠️ Cover image upload failed: ${error.message}. Creating card without cover...`, 'warning');
            }
        }

        // Build chapters array with custom titles
        const chapters = [];

        if (useChapterStructure) {
            // Use structured chapter data
            currentChapters.forEach(chapter => {
                chapter.tracks.forEach(track => {
                    chapters.push({
                        filename: track.filename,
                        chapter_title: chapter.title || track.title
                        // Future: Add track_title for multi-track chapters
                        // Future: Add display icons, ambient colors, overlay labels
                    });
                });
            });
        } else {
            // Build from flat file list with custom titles
            currentQueueFiles.forEach((filename, index) => {
                const titleInput = document.querySelector(`.chapter-title-input[data-index="${index}"]`);
                const customTitle = titleInput ? titleInput.value.trim() : '';
                const defaultTitle = filename.replace(/\.[^/.]+$/, '').replace(/[-_]/g, ' ');

                chapters.push({
                    filename: filename,
                    chapter_title: customTitle || defaultTitle
                });
            });
        }

        // Call playlist creation API
        const response = await fetch(`${API_BASE}/cards/create-playlist-from-audio`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                title: title,
                description: description,
                author: author,
                chapters: chapters,
                mode: 'streaming',
                cover_image_id: coverImageId
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create card');
        }

        const result = await response.json();
        showScripterResult(`✓ Card "${title}" created successfully! Card ID: ${result.card_id}`, 'success');

        // Refresh managed streams
        await loadManagedStreams();

    } catch (error) {
        console.error('Failed to create card:', error);
        showScripterResult('Failed to create card: ' + error.message, 'error');
    }
}

// Handle play mode selection for managed streams
document.addEventListener('DOMContentLoaded', () => {
    // Delegate click handler for mode buttons
    document.addEventListener('click', (event) => {
        if (event.target.classList.contains('mode-btn')) {
            const mode = event.target.dataset.mode;
            const queue = event.target.dataset.queue;
            selectPlayMode(queue, mode, event.target);
        }
    });
});

function selectPlayMode(queue, mode, button) {
    // Update UI to show selected mode
    const modeContainer = button.closest('.stream-modes');
    if (modeContainer) {
        modeContainer.querySelectorAll('.mode-btn').forEach(btn => {
            btn.style.background = btn.dataset.mode === mode ? '#4CAF50' : '';
            btn.style.color = btn.dataset.mode === mode ? 'white' : '';
        });
    }

    // Persist preference locally for preview
    if (queue) {
        playModePreferences[queue] = mode;
        try {
            localStorage.setItem('smartStreamPlayModes', JSON.stringify(playModePreferences));
        } catch (e) {
            // ignore storage errors
        }
    }

    // Show mode description
    const modeDescriptions = {
        'sequential': 'Playing in order, once through',
        'loop': 'Looping the list indefinitely',
        'shuffle': 'Playing in random order, once through',
        'endless-shuffle': 'Shuffling forever (endless random play)'
    };

    console.log(`📻 Smart Stream "${queue}" set to: ${modeDescriptions[mode] || mode}`);
}

function showScripterResult(message, type) {
    const resultDiv = document.getElementById('scripter-result');
    resultDiv.textContent = message;

    // Support info, warning, error, and success types
    let className = 'result-message';
    if (type === 'error') {
        className += ' error-message';
    } else if (type === 'success') {
        className += ' success-message';
    } else if (type === 'warning') {
        className += ' warning-message';
    } else if (type === 'info') {
        className += ' info-message';
    }

    resultDiv.className = className;
    resultDiv.style.display = 'block';

    // Auto-hide after 5 seconds for non-error messages
    if (type !== 'info') {
        setTimeout(() => {
            resultDiv.style.display = 'none';
        }, 5000);
    }
}


// Playlist Management Functions

function openPlaylistModal(selectedStream = null) {
    const modal = document.getElementById('create-playlist-modal');
    const selector = document.getElementById('playlist-stream-selector');
    const resultDiv = document.getElementById('playlist-result');

    // Clear previous results
    resultDiv.style.display = 'none';
    resultDiv.textContent = '';

    // Clear form
    document.getElementById('playlist-name').value = '';

    // Load available streams
    loadPlaylistStreamSelector(selectedStream);

    // Show modal
    modal.style.display = 'flex';
}

function closePlaylistModal() {
    const modal = document.getElementById('create-playlist-modal');
    modal.style.display = 'none';
}

async function loadPlaylistStreamSelector(selectedStream = null) {
    const selector = document.getElementById('playlist-stream-selector');

    try {
        const response = await fetch(`${API_BASE}/streams/queues`);
        if (!response.ok) throw new Error('Failed to fetch streams');

        const data = await response.json();
        const queues = data.queues || [];

        // Filter out test-stream
        const availableStreams = queues.filter(q => q !== 'test-stream');

        if (availableStreams.length === 0) {
            selector.innerHTML = '<option value="">No streams available. Create a stream first.</option>';
            return;
        }

        selector.innerHTML = '<option value="">-- Select a stream --</option>' +
            availableStreams.map(q => `<option value="${escapeHtml(q)}">${escapeHtml(q)}</option>`).join('');

        // Select the provided stream if available
        if (selectedStream && availableStreams.includes(selectedStream)) {
            selector.value = selectedStream;
        }
    } catch (error) {
        console.error('Failed to load streams:', error);
        selector.innerHTML = '<option value="">Error loading streams</option>';
    }
}

async function createPlaylist() {
    const streamName = document.getElementById('playlist-stream-selector').value;
    const playlistName = document.getElementById('playlist-name').value.trim();
    const resultDiv = document.getElementById('playlist-result');
    const createBtn = document.querySelector('#create-playlist-modal .btn-primary');

    if (!streamName) {
        showPlaylistResult('Please select a stream', 'error');
        return;
    }

    if (!playlistName) {
        showPlaylistResult('Please enter a playlist name', 'error');
        return;
    }

    createBtn.disabled = true;
    createBtn.textContent = 'Creating...';

    try {
        const response = await fetch(`${API_BASE}/streams/${encodeURIComponent(streamName)}/create-playlist`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                playlist_name: playlistName,
                stream_name: streamName,
            }),
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to create playlist');
        }

        showPlaylistResult(
            `✅ Playlist "${playlistName}" created successfully! Playlist ID: ${result.playlist_id}`,
            'success'
        );

        // Clear form and close modal after a delay
        setTimeout(() => {
            closePlaylistModal();
            // Reload managed streams to show any updates
            loadManagedStreams();
        }, 2000);

    } catch (error) {
        console.error('Failed to create playlist:', error);
        showPlaylistResult('Failed to create playlist: ' + error.message, 'error');
    } finally {
        createBtn.disabled = false;
        createBtn.textContent = 'Create Playlist';
    }
}

async function deletePlaylist(playlistId) {
    if (!confirm('Are you sure you want to delete this playlist? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/streams/playlists/${encodeURIComponent(playlistId)}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.detail || 'Failed to delete playlist');
        }

        // Show success message and reload
        alert('Playlist deleted successfully!');
        loadManagedStreams();

    } catch (error) {
        console.error('Failed to delete playlist:', error);
        alert('Failed to delete playlist: ' + error.message);
    }
}

function showPlaylistResult(message, type) {
    const resultDiv = document.getElementById('playlist-result');
    resultDiv.textContent = message;
    resultDiv.className = `result-message ${type === 'error' ? 'error-message' : 'success-message'}`;
    resultDiv.style.display = 'block';

    if (type === 'error') {
        setTimeout(() => {
            resultDiv.style.display = 'none';
        }, 5000);
    }
}

// Delete Yoto Playlist Functions

function openDeletePlaylistModal() {
    const modal = document.getElementById('delete-playlist-modal');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('delete-playlist-search').value = '';
        document.getElementById('delete-playlist-search-results').style.display = 'none';
        document.getElementById('delete-playlist-result').style.display = 'none';
        document.getElementById('delete-playlist-loading').style.display = 'none';
        document.getElementById('delete-playlist-list').innerHTML = '';
    }
}

function closeDeletePlaylistModal() {
    const modal = document.getElementById('delete-playlist-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

async function searchPlaylistsForDelete() {
    const searchInput = document.getElementById('delete-playlist-search');
    const playlistName = searchInput.value.trim();

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

        // Reset search after successful deletion
        if (successCount > 0) {
            setTimeout(() => {
                document.getElementById('delete-playlist-search').value = '';
                document.getElementById('delete-playlist-search-results').style.display = 'none';
                searchPlaylistsForDelete();
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
