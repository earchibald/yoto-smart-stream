// Streams Page JavaScript

const API_BASE = '/api';

// Load initial data
document.addEventListener('DOMContentLoaded', () => {
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
                    <details class="stream-details">
                        <summary>Show queue contents</summary>
                        <ul class="queue-files">
                            ${queue.files.map(file => `<li>${escapeHtml(file)}</li>`).join('')}
                        </ul>
                    </details>
                    <div class="stream-actions">
                        <button class="btn-small" data-action="copy" data-url="/api/streams/${escapeHtml(queue.name, true)}/stream.mp3">📋 Copy URL</button>
                        <button class="btn-small" data-action="play" data-url="/api/streams/${escapeHtml(queue.name, true)}/stream.mp3">▶️ Preview</button>
                    </div>
                </div>
            `).join('');
        
        // Add event listeners to action buttons
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
function playAudio(url) {
    const fullUrl = window.location.origin + url;
    const audio = new Audio(fullUrl);
    audio.play().catch(error => {
        console.error('Error playing audio:', error);
        alert('Failed to play audio. The file may not be compatible with your browser.');
    });
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
