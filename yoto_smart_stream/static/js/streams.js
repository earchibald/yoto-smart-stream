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
    loadAudioFiles();
    loadManagedStreams();
    setupFormHandler();
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
let currentQueueFiles = [];
let availableFiles = [];

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
    
    // Refresh queue list to ensure it's up to date
    await loadStreamQueues();
    
    document.getElementById('queue-selector').value = '';
    document.getElementById('queue-name').value = `stream-${crypto.randomUUID().split('-')[0]}`;
    document.getElementById('delete-queue-btn').style.display = 'none';
    
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
        
        updateQueueDisplay();
        clearFileCheckboxes();
    } catch (error) {
        console.error('Failed to load queue for editing:', error);
        showScripterResult('Failed to load queue: ' + error.message, 'error');
    }
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
    
    countSpan.textContent = currentQueueFiles.length;
    
    if (currentQueueFiles.length === 0) {
        container.innerHTML = '<p style="color: #999; text-align: center; padding: 2rem;">No files added yet. Select files above to add them.</p>';
        return;
    }
    
    container.innerHTML = '';
    currentQueueFiles.forEach((file, index) => {
        const item = document.createElement('div');
        item.className = 'queue-file-item';
        item.draggable = true;
        item.dataset.index = index;
        
        item.innerHTML = `
            <span class="drag-handle">☰</span>
            <span class="file-name">${escapeHtml(file)}</span>
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
    resultDiv.className = `result-message ${type === 'error' ? 'error-message' : 'success-message'}`;
    resultDiv.style.display = 'block';
    
    setTimeout(() => {
        resultDiv.style.display = 'none';
    }, 5000);
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
