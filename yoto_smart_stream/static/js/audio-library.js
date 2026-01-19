// Audio Library JavaScript

// API base URL
const API_BASE = '/api';

// Default filename for TTS generator
const DEFAULT_TTS_FILENAME = 'my-story';

// Audio Recorder State
let mediaRecorder = null;
let audioChunks = [];
let recordingStartTime = null;
let timerInterval = null;
let audioContext = null;
let analyser = null;
let animationFrameId = null;
let recordedBlob = null;
let recorderModalKeyHandler = null;

// ============================================================================
// Recorder Modal Functions (defined early for global access)
// ============================================================================

// Open recorder modal
function openRecorderModal() {
    const modal = document.getElementById('recorderModal');
    if (modal) {
        modal.style.display = 'flex';

        // Setup keyboard handler for Escape key
        recorderModalKeyHandler = (e) => {
            if (e.key === 'Escape') {
                closeRecorderModal();
            }
        };
        document.addEventListener('keydown', recorderModalKeyHandler);
    }
}

// Close recorder modal
function closeRecorderModal() {
    const modal = document.getElementById('recorderModal');

    // Remove keyboard handler
    if (recorderModalKeyHandler) {
        document.removeEventListener('keydown', recorderModalKeyHandler);
        recorderModalKeyHandler = null;
    }

    if (modal) {
        modal.style.display = 'none';

        // Reset recorder if not recording
        if (!mediaRecorder || mediaRecorder.state === 'inactive') {
            reRecord();
        }
    }
}

// Check user authentication first
async function checkUserAuth() {
    try {
        const response = await fetch('/api/user/session', { credentials: 'include' });
        const data = await response.json();

        if (!data.authenticated) {
            // Redirect to login page
            window.location.href = '/login';
            return false;
        }

        return true;
    } catch (error) {
        console.error('Error checking authentication:', error);
        window.location.href = '/login';
        return false;
    }
}

// Load initial data
document.addEventListener('DOMContentLoaded', async () => {
    // Check authentication before loading anything else
    const isAuthenticated = await checkUserAuth();
    if (!isAuthenticated) {
        return; // Stop loading if not authenticated
    }

    loadSystemStatus();
    loadAudioFiles();
    loadTTSVoices(); // Load available voices from ElevenLabs

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

    // Initial preview update
    updateFilenamePreview();
    updateTextLength();

    // Setup audio recorder
    setupRecorder();

    // Setup upload form
    const uploadForm = document.getElementById('upload-form');
    if (uploadForm) {
        uploadForm.addEventListener('submit', handleUploadSubmit);
    }

    // Setup upload filename preview
    const uploadFilenameInput = document.getElementById('upload-filename');
    if (uploadFilenameInput) {
        uploadFilenameInput.addEventListener('input', updateUploadFilenamePreview);
    }

    // Setup file input change handler
    const uploadFileInput = document.getElementById('upload-file');
    if (uploadFileInput) {
        uploadFileInput.addEventListener('change', handleFileSelect);
    }

    // Initial upload preview update
    updateUploadFilenamePreview();

    // Setup playlist modal
    const createPlaylistBtn = document.getElementById('create-playlist-btn');
    if (createPlaylistBtn) {
        createPlaylistBtn.addEventListener('click', openPlaylistModal);
    }

    // Setup recorder modal
    const openRecorderBtn = document.getElementById('open-recorder-btn');
    if (openRecorderBtn) {
        openRecorderBtn.addEventListener('click', openRecorderModal);
    }

    // Setup audio editor
    const openAudioEditorBtn = document.getElementById('open-audio-editor-btn');
    if (openAudioEditorBtn) {
        openAudioEditorBtn.addEventListener('click', openAudioEditor);
    }

    // Setup playlist mode selector
    const playlistMode = document.getElementById('playlist-mode');
    if (playlistMode) {
        playlistMode.addEventListener('change', (e) => {
            const description = document.getElementById('mode-description');
            if (e.target.value === 'streaming') {
                description.textContent = 'Hosted on our server using direct URLs';
            } else {
                description.textContent = 'Uploaded to Yoto infrastructure with automatic transcoding';
            }
        });
    }

    const audioSearch = document.getElementById('audio-search');
    if (audioSearch) {
        audioSearch.addEventListener('input', searchAudioFiles);
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

        // Update status indicator
        const statusEl = document.getElementById('status');
        const statusTextEl = document.getElementById('status-text');
        statusEl.classList.remove('error');
        statusTextEl.textContent = 'System Running';

    } catch (error) {
        console.error('Error loading status:', error);
        const statusEl = document.getElementById('status');
        const statusTextEl = document.getElementById('status-text');
        statusEl.classList.add('error');
        statusTextEl.textContent = 'Error';
    }
}

// Load TTS voices from ElevenLabs
async function loadTTSVoices() {
    const voiceSelect = document.getElementById('tts-voice');
    const voiceDescription = document.getElementById('voice-description');

    if (!voiceSelect) {
        console.warn('TTS voice select element not found');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/audio/tts/voices`);

        if (!response.ok) {
            throw new Error('Failed to fetch voices');
        }

        const data = await response.json();

        // Clear loading option
        voiceSelect.innerHTML = '';

        if (data.voices && data.voices.length > 0) {
            // Add voices to select
            data.voices.forEach(voice => {
                const option = document.createElement('option');
                option.value = voice.voice_id;
                option.textContent = voice.name;
                option.dataset.description = voice.description || '';
                option.dataset.category = voice.category || '';
                voiceSelect.appendChild(option);
            });

            // Set default voice (Rachel)
            const defaultVoice = data.voices.find(v => v.voice_id === '21m00Tcm4TlvDq8ikWAM');
            if (defaultVoice) {
                voiceSelect.value = defaultVoice.voice_id;
                if (voiceDescription) {
                    voiceDescription.textContent = defaultVoice.description || 'Professional female voice';
                }
            }

            // Add change listener to update description
            voiceSelect.addEventListener('change', (e) => {
                const selectedOption = e.target.options[e.target.selectedIndex];
                if (voiceDescription && selectedOption) {
                    const desc = selectedOption.dataset.description || '';
                    const category = selectedOption.dataset.category || '';
                    voiceDescription.textContent = desc || (category ? `${category} voice` : '');
                }
            });

        } else {
            // No voices available
            const option = document.createElement('option');
            option.value = '';
            option.textContent = 'No voices available';
            voiceSelect.appendChild(option);
            voiceSelect.disabled = true;
        }

    } catch (error) {
        console.error('Error loading TTS voices:', error);
        voiceSelect.innerHTML = '<option value="">Failed to load voices</option>';
        voiceSelect.disabled = true;

        if (voiceDescription) {
            voiceDescription.textContent = 'Unable to load voices. Please check your connection.';
            voiceDescription.style.color = '#d32f2f';
        }
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

        if (files.length === 0) {
            container.innerHTML = '<p class="loading">No audio files found. Add MP3 files to the audio_files directory or generate TTS audio below.</p>';
            return;
        }

        container.innerHTML = files.map(file => {
            const transcriptBadge = getTranscriptBadge(file);

            return `
                <div class="list-item" data-filename="${escapeHtml(file.filename)}">
                    <div class="list-item-header">
                        <span class="list-item-title">
                            🎵 ${escapeHtml(file.filename)}
                            ${file.is_static ? '<span class="badge badge-static">Static</span>' : ''}
                            ${transcriptBadge}
                        </span>
                    </div>
                    <div class="list-item-details">
                        <span>Duration: ${file.duration}s | Size: ${file.size} bytes (${formatFileSize(file.size)})</span>
                        <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem; flex-wrap: wrap;">
                            <button class="control-btn" onclick="copyAudioUrl('${escapeHtml(file.url)}', event)" title="Copy Full URL">
                                📋
                            </button>
                            <button class="control-btn" onclick="viewMetadata('${escapeHtml(file.filename)}', event)" title="View Metadata">
                                📊
                            </button>
                            ${!file.is_static ? `<button class="control-btn control-btn-danger" onclick="deleteAudioFile('${escapeHtml(file.filename)}', event)" title="Delete Audio File">
                                🗑️
                            </button>` : ''}
                        </div>
                        <audio controls preload="none" style="width: 100%; max-width: 300px; margin-top: 8px;">
                            <source src="${escapeHtml(file.url)}" type="audio/mpeg">
                            Your browser does not support the audio element.
                        </audio>
                    </div>
                </div>
            `;
        }).join('');

        // Start auto-refresh if any files are processing
        checkAndStartAutoRefresh();

    } catch (error) {
        console.error('Error loading audio files:', error);
        container.innerHTML = '<p class="error-message">Failed to load audio files.</p>';
    }
}

// Get transcript badge HTML based on transcript state
function getTranscriptBadge(file) {
    if (!file.transcript || file.transcript.status === 'pending') {
        return `<span class="badge badge-transcript badge-no-transcript"
                      onclick="handleTranscriptBadgeClick('${escapeHtml(file.filename)}', 'pending', event)"
                      title="Click to start transcription">
                    No Transcript
                </span>`;
    }

    if (file.transcript.has_transcript && file.transcript.status === 'completed') {
        return `<span class="badge badge-transcript badge-completed"
                      onclick="handleTranscriptBadgeClick('${escapeHtml(file.filename)}', 'completed', event)"
                      title="Click to view or delete transcript">
                    ✓ Transcript
                </span>`;
    }

    if (file.transcript.status === 'processing') {
        return `<span class="badge badge-transcript badge-processing"
                      onclick="handleTranscriptBadgeClick('${escapeHtml(file.filename)}', 'processing', event)"
                      title="Click to cancel transcription">
                    ⏳ Generating...
                </span>`;
    }

    if (file.transcript.status === 'error') {
        return `<span class="badge badge-transcript badge-error"
                      onclick="handleTranscriptBadgeClick('${escapeHtml(file.filename)}', 'error', event)"
                      title="Click to retry transcription">
                    ⚠️ Error
                </span>`;
    }

    if (file.transcript.status === 'cancelled') {
        return `<span class="badge badge-transcript badge-cancelled"
                      onclick="handleTranscriptBadgeClick('${escapeHtml(file.filename)}', 'cancelled', event)"
                      title="Click to start transcription">
                    Cancelled
                </span>`;
    }

    // Default: no transcript
    return `<span class="badge badge-transcript badge-no-transcript"
                  onclick="handleTranscriptBadgeClick('${escapeHtml(file.filename)}', 'pending', event)"
                  title="Click to start transcription">
                No Transcript
            </span>`;
}

// Handle transcript badge clicks
async function handleTranscriptBadgeClick(filename, status, event) {
    console.log(`handleTranscriptBadgeClick called: filename=${filename}, status=${status}`);
    event.preventDefault();
    event.stopPropagation();

    if (status === 'completed') {
        // Show options: View or Delete
        showTranscriptOptions(filename);
    } else if (status === 'processing') {
        // Cancel transcription
        await cancelTranscription(filename);
    } else if (status === 'pending' || status === 'cancelled' || status === 'error') {
        // Start transcription
        console.log('Calling startTranscription...');
        await startTranscription(filename, event);
    }
}

// Show transcript options (view or delete)
function showTranscriptOptions(filename) {
    const modal = document.createElement('div');
    modal.className = 'transcript-options-modal';
    modal.innerHTML = `
        <div class="transcript-options-content">
            <h3>Transcript Options</h3>
            <p>What would you like to do with the transcript for <strong>${escapeHtml(filename)}</strong>?</p>
            <div class="transcript-options-buttons">
                <button class="btn-primary" onclick="viewTranscriptAndCloseOptions('${escapeHtml(filename)}')">
                    📝 View Transcript
                </button>
                <button class="btn-danger" onclick="deleteTranscriptConfirm('${escapeHtml(filename)}')">
                    🗑️ Delete Transcript
                </button>
                <button class="btn-secondary" onclick="closeTranscriptOptions()">
                    Cancel
                </button>
            </div>
        </div>
    `;
    modal.onclick = function(e) {
        if (e.target === modal) {
            closeTranscriptOptions();
        }
    };
    document.body.appendChild(modal);
    modal.style.display = 'flex';
}

function viewTranscriptAndCloseOptions(filename) {
    closeTranscriptOptions();
    viewTranscript(filename);
}

function closeTranscriptOptions() {
    const modal = document.querySelector('.transcript-options-modal');
    if (modal) {
        modal.remove();
    }
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

// Copy audio URL to clipboard
async function copyAudioUrl(url, event) {
    event.preventDefault();
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

// Delete audio file
// Global variable to store modal keyboard handlers
let deleteConfirmKeyHandler = null;
let resultMessageKeyHandler = null;

async function deleteAudioFile(filename, event) {
    event.preventDefault();
    event.stopPropagation();

    // Show confirmation modal
    showDeleteConfirmModal(filename);
}

function showDeleteConfirmModal(filename) {
    const modal = document.getElementById('deleteConfirmModal');
    const message = document.getElementById('deleteConfirmMessage');
    const confirmBtn = document.getElementById('confirmDeleteBtn');

    message.textContent = `Are you sure you want to delete "${filename}"?`;

    // Remove any existing event listeners
    const newConfirmBtn = confirmBtn.cloneNode(true);
    confirmBtn.parentNode.replaceChild(newConfirmBtn, confirmBtn);

    // Add click handler for confirm button
    newConfirmBtn.onclick = async () => {
        closeDeleteConfirmModal();
        await performDelete(filename);
    };

    // Remove previous keyboard handler if exists
    if (deleteConfirmKeyHandler) {
        document.removeEventListener('keydown', deleteConfirmKeyHandler);
    }

    // Setup keyboard handler
    deleteConfirmKeyHandler = (e) => {
        if (e.key === 'Escape') {
            closeDeleteConfirmModal();
        }
    };
    document.addEventListener('keydown', deleteConfirmKeyHandler);

    // Show modal
    modal.style.display = 'flex';

    // Focus the confirm button
    setTimeout(() => newConfirmBtn.focus(), 100);
}

function closeDeleteConfirmModal() {
    const modal = document.getElementById('deleteConfirmModal');

    // Remove keyboard handler
    if (deleteConfirmKeyHandler) {
        document.removeEventListener('keydown', deleteConfirmKeyHandler);
        deleteConfirmKeyHandler = null;
    }

    if (modal) {
        modal.style.display = 'none';
    }
}

async function performDelete(filename) {
    try {
        const response = await fetch(`${API_BASE}/audio/${encodeURIComponent(filename)}`, {
            method: 'DELETE',
            credentials: 'include'
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `Failed to delete file: ${response.statusText}`);
        }

        const result = await response.json();

        // Remove the file item from the UI with animation
        const fileItem = document.querySelector(`[data-filename="${CSS.escape(filename)}"]`);
        if (fileItem) {
            fileItem.style.opacity = '0.5';
            fileItem.style.transition = 'opacity 0.3s ease-out';
            setTimeout(() => {
                fileItem.remove();

                // Check if list is empty
                const container = document.getElementById('audio-list');
                const remainingItems = container.querySelectorAll('.list-item');
                if (remainingItems.length === 0) {
                    container.innerHTML = '<p class="loading">No audio files found. Add MP3 files to the audio_files directory or generate TTS audio below.</p>';
                }
            }, 300);
        }

        // Show success message
        showResultMessage('success', '✓ File Deleted', `Successfully deleted "${filename}"`);

    } catch (error) {
        console.error('Error deleting audio file:', error);
        showResultMessage('error', '❌ Deletion Failed', `Failed to delete audio file: ${error.message}`);
    }
}

function showResultMessage(type, title, message) {
    const modal = document.getElementById('resultMessageModal');
    const header = document.getElementById('resultModalHeader');
    const titleEl = document.getElementById('resultModalTitle');
    const messageEl = document.getElementById('resultModalMessage');

    // Set content
    titleEl.textContent = title;
    messageEl.textContent = message;

    // Set header color based on type
    if (type === 'success') {
        header.style.background = 'linear-gradient(135deg, #38a169 0%, #2f855a 100%)';
    } else if (type === 'error') {
        header.style.background = 'linear-gradient(135deg, #c53030 0%, #9b2c2c 100%)';
    } else {
        header.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
    }

    // Remove previous keyboard handler if exists
    if (resultMessageKeyHandler) {
        document.removeEventListener('keydown', resultMessageKeyHandler);
    }

    // Setup keyboard handler
    resultMessageKeyHandler = (e) => {
        if (e.key === 'Escape' || e.key === 'Enter') {
            closeResultMessageModal();
        }
    };
    document.addEventListener('keydown', resultMessageKeyHandler);

    // Show modal
    modal.style.display = 'flex';

    // Focus the OK button
    const okBtn = modal.querySelector('.btn-primary');
    setTimeout(() => okBtn?.focus(), 100);
}

function closeResultMessageModal() {
    const modal = document.getElementById('resultMessageModal');

    // Remove keyboard handler
    if (resultMessageKeyHandler) {
        document.removeEventListener('keydown', resultMessageKeyHandler);
        resultMessageKeyHandler = null;
    }

    if (modal) {
        modal.style.display = 'none';
    }
}

// Confirmation Modal Functions
let confirmModalKeyHandler = null;
let confirmModalCallback = null;

function showConfirmModal(title, message, onConfirm) {
    console.log('showConfirmModal called', {title, message, hasCallback: !!onConfirm});
    const modal = document.getElementById('confirmModal');
    const header = document.getElementById('confirmModalHeader');
    const titleEl = document.getElementById('confirmModalTitle');
    const messageEl = document.getElementById('confirmModalMessage');
    const confirmBtn = document.getElementById('confirmModalBtn');

    console.log('Modal elements:', {
        modal: !!modal,
        header: !!header,
        titleEl: !!titleEl,
        messageEl: !!messageEl,
        confirmBtn: !!confirmBtn
    });

    // Set content
    titleEl.textContent = title;
    messageEl.textContent = message;

    // Set header color (info style)
    header.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';

    // Store callback
    confirmModalCallback = onConfirm;
    console.log('Stored callback, confirmModalCallback is now:', !!confirmModalCallback);

    // Remove previous keyboard handler if exists
    if (confirmModalKeyHandler) {
        document.removeEventListener('keydown', confirmModalKeyHandler);
    }

    // Setup keyboard handler
    confirmModalKeyHandler = (e) => {
        if (e.key === 'Escape') {
            closeConfirmModal();
        } else if (e.key === 'Enter') {
            handleConfirmModalOk();
        }
    };
    document.addEventListener('keydown', confirmModalKeyHandler);

    // Setup button handler
    confirmBtn.onclick = handleConfirmModalOk;

    // Show modal
    modal.style.display = 'flex';

    // Focus the confirm button
    setTimeout(() => confirmBtn?.focus(), 100);
}

function handleConfirmModalOk() {
    console.log('handleConfirmModalOk called');
    console.log('confirmModalCallback exists:', !!confirmModalCallback);
    console.log('typeof confirmModalCallback:', typeof confirmModalCallback);

    // Save callback reference before closeConfirmModal clears it
    const callback = confirmModalCallback;

    closeConfirmModal();

    if (callback) {
        console.log('Executing callback');
        try {
            callback();
            console.log('Callback executed successfully');
        } catch (error) {
            console.error('Error executing callback:', error);
        }
    } else {
        console.warn('No callback to execute!');
    }
}

function closeConfirmModal() {
    const modal = document.getElementById('confirmModal');

    // Remove keyboard handler
    if (confirmModalKeyHandler) {
        document.removeEventListener('keydown', confirmModalKeyHandler);
        confirmModalKeyHandler = null;
    }

    // Clear callback
    confirmModalCallback = null;

    if (modal) {
        modal.style.display = 'none';
    }
}

// TTS Generator Functions

// Update filename preview
function updateFilenamePreview() {
    const filenameInput = document.getElementById('tts-filename');
    const preview = document.getElementById('filename-preview');

    if (filenameInput && preview) {
        const filename = filenameInput.value.trim() || DEFAULT_TTS_FILENAME;
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
    const voiceId = document.getElementById('tts-voice').value;

    if (!filename || !text) {
        showTTSError('Please fill in all fields');
        return;
    }

    if (!voiceId) {
        showTTSError('Please select a voice');
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
                voice_id: voiceId,
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

        // Reset form (but preserve voice selection)
        const selectedVoice = document.getElementById('tts-voice').value;
        form.reset();
        document.getElementById('tts-voice').value = selectedVoice;
        updateFilenamePreview();
        updateTextLength();

        // Refresh audio files list to show new file
        setTimeout(() => {
            loadAudioFiles();
        }, 1000);

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

// ============================================================================
// Audio Recorder Functions
// ============================================================================

function setupRecorder() {
    const recordBtn = document.getElementById('record-btn');
    const stopBtn = document.getElementById('stop-btn');
    const rerecordBtn = document.getElementById('rerecord-btn');
    const saveBtn = document.getElementById('save-btn');

    if (recordBtn) recordBtn.addEventListener('click', startRecording);
    if (stopBtn) stopBtn.addEventListener('click', stopRecording);
    if (rerecordBtn) rerecordBtn.addEventListener('click', reRecord);
    if (saveBtn) saveBtn.addEventListener('click', saveRecording);

    // Setup keyboard shortcuts
    document.addEventListener('keydown', handleRecorderKeyboard);

    // Check browser support
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showRecorderError('Your browser does not support audio recording. Please use a modern browser like Chrome, Firefox, or Edge.');
        if (recordBtn) recordBtn.disabled = true;
    }
}

function handleRecorderKeyboard(event) {
    // Ctrl/Cmd + R: Start recording
    if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
        event.preventDefault();
        const recordBtn = document.getElementById('record-btn');
        if (recordBtn && !recordBtn.disabled) {
            startRecording();
        }
    }

    // Ctrl/Cmd + S: Stop recording
    if ((event.ctrlKey || event.metaKey) && event.key === 's') {
        event.preventDefault();
        const stopBtn = document.getElementById('stop-btn');
        if (stopBtn && !stopBtn.disabled) {
            stopRecording();
        }
    }

    // Ctrl/Cmd + Delete: Re-record
    if ((event.ctrlKey || event.metaKey) && event.key === 'Delete') {
        event.preventDefault();
        const rerecordBtn = document.getElementById('rerecord-btn');
        if (rerecordBtn && !rerecordBtn.disabled) {
            reRecord();
        }
    }

    // Ctrl/Cmd + Enter: Save recording
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
        event.preventDefault();
        const saveBtn = document.getElementById('save-btn');
        if (saveBtn && !saveBtn.disabled) {
            saveRecording();
        }
    }
}

async function startRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

        // Create MediaRecorder
        const options = { mimeType: 'audio/webm' };
        mediaRecorder = new MediaRecorder(stream, options);
        audioChunks = [];

        mediaRecorder.addEventListener('dataavailable', event => {
            audioChunks.push(event.data);
        });

        mediaRecorder.addEventListener('stop', () => {
            recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
            showPreview();

            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());

            // Stop visualization
            stopVisualization();
        });

        mediaRecorder.start();
        recordingStartTime = Date.now();

        // Setup audio visualization
        setupVisualization(stream);

        // Start timer
        startTimer();

        // Update UI
        updateRecorderUI('recording');
        updateRecorderStatus('Recording...', '#ef4444');

    } catch (error) {
        console.error('Error starting recording:', error);
        showRecorderError('Failed to access microphone. Please allow microphone access and try again.');
    }
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
        stopTimer();
        updateRecorderUI('stopped');
        updateRecorderStatus('Recording stopped', '#10b981');
    }
}

function reRecord() {
    // Clear previous recording
    recordedBlob = null;
    audioChunks = [];

    // Hide preview
    const preview = document.getElementById('recorder-preview');
    if (preview) preview.style.display = 'none';

    // Reset UI
    updateRecorderUI('ready');
    updateRecorderStatus('Ready to record', '#667eea');
    resetTimer();

    // Clear canvas
    const canvas = document.getElementById('waveform');
    if (canvas) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
    }

    // Hide result messages
    hideRecorderResult();
}

async function saveRecording() {
    if (!recordedBlob) {
        showRecorderError('No recording to save');
        return;
    }

    const filenameInput = document.getElementById('recording-filename');
    const descriptionInput = document.getElementById('recording-description');
    const saveBtn = document.getElementById('save-btn');
    const saveText = document.getElementById('save-text');
    const saveSpinner = document.getElementById('save-spinner');

    const filename = filenameInput.value.trim();
    const description = descriptionInput.value.trim();

    if (!filename) {
        showRecorderError('Please enter a filename');
        return;
    }

    // Show loading state
    saveBtn.disabled = true;
    saveText.style.display = 'none';
    saveSpinner.style.display = 'inline';
    hideRecorderResult();

    try {
        // Create FormData
        const formData = new FormData();
        formData.append('file', recordedBlob, 'recording.webm');
        formData.append('filename', filename);
        formData.append('description', description);

        // Upload to server
        const response = await fetch(`${API_BASE}/audio/upload`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to save recording');
        }

        // Show success message
        showRecorderSuccess(data.message || `Successfully saved ${data.filename}`);

        // Clear form
        filenameInput.value = '';
        descriptionInput.value = '';

        // Refresh audio files list
        setTimeout(() => {
            loadAudioFiles();
        }, 1000);

        // Close modal and reset recorder after delay
        setTimeout(() => {
            closeRecorderModal();
            reRecord();
        }, 2000);

    } catch (error) {
        console.error('Error saving recording:', error);
        showRecorderError(error.message);
    } finally {
        saveBtn.disabled = false;
        saveText.style.display = 'inline';
        saveSpinner.style.display = 'none';
    }
}

function setupVisualization(stream) {
    const canvas = document.getElementById('waveform');
    if (!canvas) return;

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);

    analyser.fftSize = 2048;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    function draw() {
        animationFrameId = requestAnimationFrame(draw);

        analyser.getByteTimeDomainData(dataArray);

        // Clear canvas with dark background
        ctx.fillStyle = '#1e293b';
        ctx.fillRect(0, 0, width, height);

        // Draw waveform
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#667eea';
        ctx.beginPath();

        const sliceWidth = width / bufferLength;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            const v = dataArray[i] / 128.0;
            const y = v * height / 2;

            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }

            x += sliceWidth;
        }

        ctx.lineTo(width, height / 2);
        ctx.stroke();
    }

    draw();
}

function stopVisualization() {
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
}

function startTimer() {
    const timerElement = document.getElementById('recorder-timer');
    if (!timerElement) return;

    timerInterval = setInterval(() => {
        const elapsed = Date.now() - recordingStartTime;
        const minutes = Math.floor(elapsed / 60000);
        const seconds = Math.floor((elapsed % 60000) / 1000);
        timerElement.textContent = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }, 100);
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

function resetTimer() {
    const timerElement = document.getElementById('recorder-timer');
    if (timerElement) {
        timerElement.textContent = '00:00';
    }
}

function updateRecorderUI(state) {
    const recordBtn = document.getElementById('record-btn');
    const stopBtn = document.getElementById('stop-btn');
    const rerecordBtn = document.getElementById('rerecord-btn');

    if (state === 'recording') {
        recordBtn.disabled = true;
        stopBtn.disabled = false;
        rerecordBtn.disabled = true;
    } else if (state === 'stopped') {
        recordBtn.disabled = true;
        stopBtn.disabled = true;
        rerecordBtn.disabled = false;
    } else {
        // ready
        recordBtn.disabled = false;
        stopBtn.disabled = true;
        rerecordBtn.disabled = true;
    }
}

function updateRecorderStatus(text, color) {
    const statusText = document.getElementById('recorder-status');
    if (statusText) {
        statusText.textContent = text;
        statusText.style.color = color;
    }
}

function showPreview() {
    const preview = document.getElementById('recorder-preview');
    const audio = document.getElementById('preview-audio');
    const filenameInput = document.getElementById('recording-filename');

    if (preview && audio && recordedBlob) {
        // Create URL for recorded audio
        const url = URL.createObjectURL(recordedBlob);
        audio.src = url;

        // Generate default filename with readable timestamp
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hour = String(now.getHours()).padStart(2, '0');
        const minute = String(now.getMinutes()).padStart(2, '0');
        const second = String(now.getSeconds()).padStart(2, '0');
        const timestamp = `${year}${month}${day}_${hour}${minute}${second}`;
        filenameInput.value = `recording_${timestamp}`;

        // Show preview
        preview.style.display = 'block';
    }
}

function showRecorderSuccess(message) {
    const result = document.getElementById('recorder-result');
    const successDiv = document.getElementById('recorder-success');
    const errorDiv = document.getElementById('recorder-error');
    const successMessage = document.getElementById('recorder-success-message');

    successMessage.textContent = message;
    successDiv.style.display = 'block';
    errorDiv.style.display = 'none';
    result.style.display = 'block';
}

function showRecorderError(message) {
    const result = document.getElementById('recorder-result');
    const successDiv = document.getElementById('recorder-success');
    const errorDiv = document.getElementById('recorder-error');
    const errorMessage = document.getElementById('recorder-error-message');

    errorMessage.textContent = message;
    errorDiv.style.display = 'block';
    successDiv.style.display = 'none';
    result.style.display = 'block';
}

function hideRecorderResult() {
    const result = document.getElementById('recorder-result');
    const successDiv = document.getElementById('recorder-success');
    const errorDiv = document.getElementById('recorder-error');

    if (result) result.style.display = 'none';
    if (successDiv) successDiv.style.display = 'none';
    if (errorDiv) errorDiv.style.display = 'none';
}

// Transcript functions

async function viewTranscript(filename, event) {
    if (event) event.preventDefault();

    try {
        const response = await fetch(`${API_BASE}/audio/${encodeURIComponent(filename)}/transcript`);
        if (!response.ok) {
            throw new Error('Failed to fetch transcript');
        }

        const data = await response.json();

        // Show modal with transcript
        const modal = document.getElementById('transcriptModal');
        const content = document.getElementById('transcriptContent');

        if (data.transcript) {
            content.innerHTML = `
                <div class="transcript-header">
                    <h4>${escapeHtml(filename)}</h4>
                    <p class="transcript-meta">Transcribed: ${data.transcribed_at ? new Date(data.transcribed_at).toLocaleString() : 'N/A'}</p>
                </div>
                <div class="transcript-text">
                    <p>${escapeHtml(data.transcript)}</p>
                </div>
            `;
        } else if (data.status === 'error') {
            content.innerHTML = `
                <div class="error-message">
                    <p>Transcription failed: ${escapeHtml(data.error || 'Unknown error')}</p>
                    <button class="btn-primary" onclick="retryTranscription('${escapeHtml(filename)}', event)">
                        Retry Transcription
                    </button>
                </div>
            `;
        } else {
            content.innerHTML = `
                <div class="loading">
                    <p>Transcript is being processed...</p>
                    <button class="btn-secondary" onclick="closeTranscriptModal()">Close</button>
                </div>
            `;
        }

        modal.style.display = 'block';

    } catch (error) {
        console.error('Error fetching transcript:', error);
        alert('Failed to load transcript. Please try again.');
    }
}

function closeTranscriptModal() {
    const modal = document.getElementById('transcriptModal');
    modal.style.display = 'none';
}

// ============================================================================
// Metadata Modal Functions
// ============================================================================

let metadataModalKeyHandler = null;

async function viewMetadata(filename, event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }

    const modal = document.getElementById('metadataModal');
    const content = document.getElementById('metadataContent');

    modal.style.display = 'flex';
    content.innerHTML = '<p class="loading">Loading metadata...</p>';

    // Setup keyboard handler for Escape key
    metadataModalKeyHandler = (e) => {
        if (e.key === 'Escape') {
            closeMetadataModal();
        }
    };
    document.addEventListener('keydown', metadataModalKeyHandler);

    try {
        // Fetch the audio file list to get metadata
        const response = await fetch(`${API_BASE}/audio/list`);
        if (!response.ok) throw new Error('Failed to fetch metadata');

        const data = await response.json();
        const file = data.files.find(f => f.filename === filename);

        if (!file) {
            content.innerHTML = '<p class="error-message">File not found</p>';
            return;
        }

        // Format metadata for display
        let html = `
            <div class="metadata-section">
                <h4>📄 File Information</h4>
                <table class="metadata-table">
                    <tr>
                        <td class="metadata-label">Filename:</td>
                        <td class="metadata-value">${escapeHtml(file.filename)}</td>
                    </tr>
                    <tr>
                        <td class="metadata-label">Size:</td>
                        <td class="metadata-value">${formatFileSize(file.size)} (${file.size.toLocaleString()} bytes)</td>
                    </tr>
                    <tr>
                        <td class="metadata-label">Duration:</td>
                        <td class="metadata-value">${file.duration} seconds</td>
                    </tr>
                    <tr>
                        <td class="metadata-label">Static File:</td>
                        <td class="metadata-value">${file.is_static ? 'Yes' : 'No'}</td>
                    </tr>
                    ${file.created_at ? `
                    <tr>
                        <td class="metadata-label">Created:</td>
                        <td class="metadata-value">${formatDateTime(file.created_at)}</td>
                    </tr>
                    ` : ''}
                    ${file.updated_at ? `
                    <tr>
                        <td class="metadata-label">Updated:</td>
                        <td class="metadata-value">${formatDateTime(file.updated_at)}</td>
                    </tr>
                    ` : ''}
                </table>
            </div>
        `;

        // Add TTS metadata if available
        if (file.tts_metadata) {
            html += `
                <div class="metadata-section">
                    <h4>🎤 Text-to-Speech Generation</h4>
                    <table class="metadata-table">
                        <tr>
                            <td class="metadata-label">Provider:</td>
                            <td class="metadata-value">${escapeHtml(file.tts_metadata.provider || 'N/A')}</td>
                        </tr>
                        ${file.tts_metadata.voice_id ? `
                        <tr>
                            <td class="metadata-label">Voice ID:</td>
                            <td class="metadata-value">${escapeHtml(file.tts_metadata.voice_id)}</td>
                        </tr>
                        ` : ''}
                        ${file.tts_metadata.model ? `
                        <tr>
                            <td class="metadata-label">Model:</td>
                            <td class="metadata-value">${escapeHtml(file.tts_metadata.model)}</td>
                        </tr>
                        ` : ''}
                    </table>
                </div>
            `;
        }

        // Add transcript metadata if available
        if (file.transcript) {
            html += `
                <div class="metadata-section">
                    <h4>📝 Transcript Information</h4>
                    <table class="metadata-table">
                        <tr>
                            <td class="metadata-label">Status:</td>
                            <td class="metadata-value">${formatTranscriptStatus(file.transcript.status)}</td>
                        </tr>
                        <tr>
                            <td class="metadata-label">Has Transcript:</td>
                            <td class="metadata-value">${file.transcript.has_transcript ? 'Yes' : 'No'}</td>
                        </tr>
                    </table>
                </div>
            `;
        }

        content.innerHTML = html;

    } catch (error) {
        console.error('Error loading metadata:', error);
        content.innerHTML = '<p class="error-message">Failed to load metadata</p>';
    }
}

function closeMetadataModal() {
    const modal = document.getElementById('metadataModal');
    modal.style.display = 'none';

    // Remove keyboard handler
    if (metadataModalKeyHandler) {
        document.removeEventListener('keydown', metadataModalKeyHandler);
        metadataModalKeyHandler = null;
    }
}

function formatDateTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

function formatTranscriptStatus(status) {
    const statusMap = {
        'pending': '⏸️ Pending',
        'processing': '⏳ Processing',
        'completed': '✅ Completed',
        'error': '❌ Error',
        'cancelled': '🚫 Cancelled',
        'disabled': '🔒 Disabled'
    };
    return statusMap[status] || status;
}

// ============================================================================
// Transcription Functions
// ============================================================================

async function startTranscription(filename, event) {
    console.log('startTranscription called for:', filename);
    if (event) event.preventDefault();

    // Check if modal function exists
    if (typeof showConfirmModal !== 'function') {
        console.error('showConfirmModal function not found');
        if (!confirm(`Start transcription for ${filename}? This may take a few moments.`)) {
            return;
        }
        // Fall back to direct API call without modal
        console.log('Calling executeTranscription (fallback)');
        await executeTranscription(filename);
        return;
    }

    console.log('Showing confirmation modal');
    showConfirmModal(
        '🎤 Start Transcription',
        `Start transcription for ${filename}? This may take a few moments.`,
        async () => {
            console.log('Modal confirmed, calling executeTranscription');
            await executeTranscription(filename);
        }
    );
}


async function executeTranscription(filename) {
    console.log('executeTranscription starting for:', filename);
    console.log('API_BASE:', API_BASE);
    console.log('Making fetch request to:', `${API_BASE}/audio/${encodeURIComponent(filename)}/transcribe`);

    try {
        const response = await fetch(`${API_BASE}/audio/${encodeURIComponent(filename)}/transcribe`, {
            method: 'POST'
        });

        console.log('Fetch response received:', response.status, response.statusText);

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || 'Failed to start transcription';
            console.error('Transcription request failed:', errorMessage, errorData);
            throw new Error(errorMessage);
        }

        const data = await response.json();
        console.log('Transcription response data:', data);

        if (data.success) {
            if (typeof showResultMessage === 'function') {
                showResultMessage('success', '✓ Transcription Complete',
                    `Transcription completed successfully! Length: ${data.transcript_length} characters`);
            } else {
                alert(`Transcription completed successfully! Length: ${data.transcript_length} characters`);
            }
        } else {
            if (typeof showResultMessage === 'function') {
                showResultMessage('error', '❌ Transcription Failed',
                    data.error || 'Unknown error occurred during transcription');
            } else {
                alert(`Transcription failed: ${data.error || 'Unknown error'}`);
            }
        }

        // Reload the audio files list to update button states
        console.log('Reloading audio files list');
        await loadAudioFiles();

    } catch (error) {
        console.error('Error in executeTranscription:', error);
        if (typeof showResultMessage === 'function') {
            showResultMessage('error', '❌ Transcription Failed',
                error.message || 'Failed to start transcription. Please try again.');
        } else {
            alert('Failed to start transcription. Please try again.');
        }
    }
}


async function retryTranscription(filename, event) {
    return startTranscription(filename, event);
}

// Cancel transcription
async function cancelTranscription(filename) {
    showConfirmModal(
        '⚠️ Cancel Transcription',
        `Cancel transcription for ${filename}?`,
        async () => {
            try {
                const response = await fetch(`${API_BASE}/audio/${encodeURIComponent(filename)}/transcript/cancel`, {
                    method: 'POST'
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail || 'Failed to cancel transcription');
                }

                showResultMessage('success', '✓ Cancelled', 'Transcription cancelled successfully');

                // Reload the audio files list to update badge
                await loadAudioFiles();

            } catch (error) {
                console.error('Error cancelling transcription:', error);
                showResultMessage('error', '❌ Cancellation Failed',
                    `Failed to cancel transcription: ${error.message}`);
            }
        }
    );
}

// Delete transcript
async function deleteTranscriptConfirm(filename) {
    closeTranscriptOptions();

    showConfirmModal(
        '⚠️ Delete Transcript',
        `Delete transcript for ${filename}? The audio file will remain, but you'll need to re-transcribe it.`,
        async () => {
            try {
                const response = await fetch(`${API_BASE}/audio/${encodeURIComponent(filename)}/transcript`, {
                    method: 'DELETE'
                });

                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.detail || 'Failed to delete transcript');
                }

                showResultMessage('success', '✓ Deleted', 'Transcript deleted successfully');

                // Reload the audio files list to update badge
                await loadAudioFiles();

            } catch (error) {
                console.error('Error deleting transcript:', error);
                showResultMessage('error', '❌ Deletion Failed',
                    `Failed to delete transcript: ${error.message}`);
            }
        }
    );
}

// Auto-refresh functionality for processing transcripts
let autoRefreshInterval = null;

function checkAndStartAutoRefresh() {
    // Check if any files are processing
    const container = document.getElementById('audio-list');
    if (!container) return;

    const hasProcessing = container.innerHTML.includes('badge-processing');

    if (hasProcessing && !autoRefreshInterval) {
        // Start auto-refresh every 3 seconds
        autoRefreshInterval = setInterval(() => {
            loadAudioFiles();
        }, 3000);
        console.log('Auto-refresh started for processing transcripts');
    } else if (!hasProcessing && autoRefreshInterval) {
        // Stop auto-refresh
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
        console.log('Auto-refresh stopped - no processing transcripts');
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const transcriptModal = document.getElementById('transcriptModal');
    if (event.target === transcriptModal) {
        closeTranscriptModal();
    }

    const recorderModal = document.getElementById('recorderModal');
    if (event.target === recorderModal) {
        closeRecorderModal();
    }

    const audioEditorModal = document.getElementById('audioEditorModal');
    if (event.target === audioEditorModal) {
        closeAudioEditor();
    }
}

// ============================================================================
// Audio Upload Functions
// ============================================================================

// Handle file selection
function handleFileSelect(event) {
    const fileInput = event.target;
    const file = fileInput.files[0];

    if (file) {
        // Auto-populate filename from selected file (without extension)
        const filenameInput = document.getElementById('upload-filename');
        if (filenameInput && !filenameInput.value) {
            const baseName = file.name.replace(/\.[^/.]+$/, ''); // Remove extension
            // Sanitize filename
            const sanitized = baseName.replace(/[^a-zA-Z0-9\s_-]/g, '-');
            filenameInput.value = sanitized;
            updateUploadFilenamePreview();
        }
    }
}

// Update upload filename preview
function updateUploadFilenamePreview() {
    const filenameInput = document.getElementById('upload-filename');
    const preview = document.getElementById('upload-filename-preview');

    if (filenameInput && preview) {
        const filename = filenameInput.value.trim() || 'my-audio';
        // Remove .mp3 extension if user added it
        const cleanFilename = filename.replace(/\.mp3$/i, '');
        preview.textContent = `${cleanFilename}.mp3`;
    }
}

// Handle upload form submission
async function handleUploadSubmit(event) {
    event.preventDefault();

    const form = event.target;
    const submitBtn = document.getElementById('upload-submit-btn');
    const submitText = document.getElementById('upload-submit-text');
    const submitSpinner = document.getElementById('upload-submit-spinner');
    const result = document.getElementById('upload-result');
    const successDiv = document.getElementById('upload-success');
    const errorDiv = document.getElementById('upload-error');
    const successMessage = document.getElementById('upload-success-message');
    const errorMessage = document.getElementById('upload-error-message');

    // Get form data
    const fileInput = document.getElementById('upload-file');
    const filenameInput = document.getElementById('upload-filename');
    const descriptionInput = document.getElementById('upload-description');

    const file = fileInput.files[0];
    const filename = filenameInput.value.trim();
    const description = descriptionInput.value.trim();

    if (!file) {
        showUploadError('Please select a file to upload');
        return;
    }

    if (!filename) {
        showUploadError('Please enter a filename');
        return;
    }

    // Validate file type (MP3)
    const validTypes = ['audio/mpeg', 'audio/mp3'];
    if (!validTypes.includes(file.type) && !file.name.toLowerCase().endsWith('.mp3')) {
        if (!confirm('This file may not be in MP3 format. The server will attempt to convert it. Continue?')) {
            return;
        }
    }

    // Show loading state
    submitBtn.disabled = true;
    submitText.style.display = 'none';
    submitSpinner.style.display = 'inline';
    result.style.display = 'none';
    successDiv.style.display = 'none';
    errorDiv.style.display = 'none';

    try {
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('file', file);
        formData.append('filename', filename);
        formData.append('description', description);

        const response = await fetch(`${API_BASE}/audio/upload`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Failed to upload audio file');
        }

        // Show success message
        successMessage.textContent = data.message || `Successfully uploaded ${data.filename}`;
        successDiv.style.display = 'block';
        result.style.display = 'block';

        // Reset form
        form.reset();
        updateUploadFilenamePreview();

        // Refresh audio files list to show new file
        setTimeout(() => {
            loadAudioFiles();
        }, 1000);

    } catch (error) {
        console.error('Error uploading audio:', error);
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

// Helper function to show upload error
function showUploadError(message) {
    const result = document.getElementById('upload-result');
    const errorDiv = document.getElementById('upload-error');
    const errorMessage = document.getElementById('upload-error-message');

    errorMessage.textContent = message;
    errorDiv.style.display = 'block';
    result.style.display = 'block';
}

// Playlist functionality
let playlistChapters = [];

// Debounce helper function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}
let allAudioFiles = [];

// Open playlist creation modal
function openPlaylistModal() {
    const modal = document.getElementById('playlistModal');
    if (modal) {
        modal.style.display = 'flex';
        playlistChapters = [];
        // Reset form fields
        document.getElementById('playlist-title').value = '';
        document.getElementById('playlist-description').value = '';
        document.getElementById('audio-search').value = '';
        document.getElementById('search-results').innerHTML = '<p class="placeholder">Type to search audio files...</p>';
        // Reset chapters display
        document.getElementById('chapter-count').textContent = '0';
        document.getElementById('chapters-list').innerHTML = '<p class="placeholder">No chapters added yet. Search and add audio files above.</p>';
        // Disable submit button
        const submitBtn = document.getElementById('create-playlist-submit-btn');
        if (submitBtn) submitBtn.disabled = true;
    }
}

// Close playlist modal
function closePlaylistModal() {
    const modal = document.getElementById('playlistModal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Close modal when clicking outside or pressing Escape
window.addEventListener('click', (event) => {
    const playlistModal = document.getElementById('playlistModal');
    if (event.target === playlistModal) {
        closePlaylistModal();
    }
});

// Close modal with Escape key
window.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
        const playlistModal = document.getElementById('playlistModal');
        if (playlistModal && playlistModal.style.display === 'block') {
            closePlaylistModal();
        }
    }
});

// Search audio files with fuzzy matching
async function searchAudioFiles() {
    const query = document.getElementById('audio-search').value.trim();
    const resultsDiv = document.getElementById('search-results');

    if (!query) {
        resultsDiv.innerHTML = '<p class="placeholder">Type to search audio files...</p>';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/audio/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Search failed');
        }

        if (!data.results || data.results.length === 0) {
            resultsDiv.innerHTML = '<p class="placeholder">No files found matching your search.</p>';
            return;
        }

        let html = '<div class="search-results-list">';
        for (const file of data.results) {
            const isAdded = playlistChapters.some(ch => ch.filename === file.filename);
            const duration = formatDuration(file.duration);
            const title = file.filename.replace('.mp3', '');

            html += `
                <div class="search-result-item ${isAdded ? 'added' : ''}">
                    <div class="result-info">
                        <div class="result-filename">${title}</div>
                        <div class="result-meta">
                            <span class="result-duration">⏱️ ${duration}</span>
                            <span class="result-size">📦 ${formatFileSize(file.size)}</span>
                        </div>
                        ${file.transcript ? `<div class="result-transcript"><strong>Transcript:</strong> ${file.transcript.substring(0, 100)}...</div>` : ''}
                    </div>
                    <button
                        class="btn-small ${isAdded ? 'btn-disabled' : 'btn-add'}"
                        onclick="addChapterFromSearch('${file.filename.replace(/'/g, "\\'")}', '${title.replace(/'/g, "\\'")}')"
                        ${isAdded ? 'disabled' : ''}
                    >
                        ${isAdded ? '✓ Added' : '+ Add'}
                    </button>
                </div>
            `;
        }
        html += '</div>';
        resultsDiv.innerHTML = html;

    } catch (error) {
        console.error('Search error:', error);
        resultsDiv.innerHTML = `<p class="error">Search error: ${error.message}</p>`;
    }
}

// Add chapter from search result
function addChapterFromSearch(filename, defaultTitle) {
    const chapter = {
        filename: filename,
        chapter_title: defaultTitle
    };

    playlistChapters.push(chapter);
    updateChaptersList();

        // Update just the specific button state without re-searching
        const buttons = document.querySelectorAll('.search-result-item button[onclick*="' + filename.replace(/'/g, "\\'") + '"]');
        buttons.forEach(btn => {
            btn.textContent = '✓ Added';
            btn.classList.remove('btn-add');
            btn.classList.add('btn-disabled');
            btn.disabled = true;
            // Also add 'added' class to parent item
            const item = btn.closest('.search-result-item');
            if (item) item.classList.add('added');
        });

    // Enable create button if we have chapters
    const submitBtn = document.getElementById('create-playlist-submit-btn');
    if (submitBtn && playlistChapters.length > 0) {
        submitBtn.disabled = false;
    }
}

// Update chapters list display
function updateChaptersList() {
    const list = document.getElementById('chapters-list');
    const count = document.getElementById('chapter-count');

    count.textContent = playlistChapters.length;

    if (playlistChapters.length === 0) {
        list.innerHTML = '<p class="placeholder">No chapters added yet. Search and add audio files above.</p>';
        return;
    }

    let html = '<div class="chapters-items">';
    for (let i = 0; i < playlistChapters.length; i++) {
        const chapter = playlistChapters[i];
        html += `
            <div class="chapter-item">
                <div class="chapter-number">
                    <span class="chapter-index">${i + 1}</span>
                </div>
                <div class="chapter-details">
                    <div class="chapter-filename">${chapter.filename}</div>
                    <div class="chapter-title-input">
                        <label>Chapter Title:</label>
                        <input
                            type="text"
                            class="chapter-title-edit"
                            value="${chapter.chapter_title}"
                            onchange="updateChapterTitle(${i}, this.value)"
                            placeholder="Chapter title..."
                        >
                    </div>
                </div>
                <div class="chapter-actions">
                    <button class="btn-remove" onclick="removeChapter(${i})" title="Remove this chapter">
                        🗑️ Remove
                    </button>
                </div>
            </div>
        `;
    }
    html += '</div>';
    list.innerHTML = html;
}

// Update chapter title
function updateChapterTitle(index, newTitle) {
    if (playlistChapters[index]) {
        playlistChapters[index].chapter_title = newTitle;
    }
}

// Remove chapter
function removeChapter(index) {
    playlistChapters.splice(index, 1);
    updateChaptersList();
    searchAudioFiles(); // Refresh search results

    // Disable create button if no chapters
    const submitBtn = document.getElementById('create-playlist-submit-btn');
    if (submitBtn && playlistChapters.length === 0) {
        submitBtn.disabled = true;
    }
}

// Submit playlist creation
async function submitPlaylist() {
    const title = document.getElementById('playlist-title').value.trim();
    const description = document.getElementById('playlist-description').value.trim();

    if (!title) {
        alert('Please enter a playlist title');
        return;
    }

    if (playlistChapters.length === 0) {
        alert('Please add at least one chapter');
        return;
    }

    const submitBtn = document.getElementById('create-playlist-submit-btn');
    const originalText = submitBtn.textContent;
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Creating...';

    try {
        const mode = document.getElementById('playlist-mode').value;

        const payload = {
            title: title,
            description: description,
            author: 'Yoto Smart Stream',
            chapters: playlistChapters,
            mode: mode
        };

        console.log(`Creating ${mode} playlist with payload:`, JSON.stringify(payload, null, 2));

        // Show upload progress section for standard mode
        if (mode === 'standard') {
            const progressSection = document.getElementById('upload-progress-section');
            const progressList = document.getElementById('upload-progress-list');
            progressSection.style.display = 'block';

            // Initialize progress items
            let html = '<div class="upload-progress-items">';
            for (const chapter of playlistChapters) {
                html += `
                    <div class="upload-progress-item" id="progress-${chapter.filename}">
                        <span class="filename">${chapter.filename}</span>
                        <div class="progress-bar">
                            <div class="progress-fill" style="width: 0%"></div>
                        </div>
                        <span class="status">⏳ Queued</span>
                    </div>
                `;
            }
            html += '</div>';
            progressList.innerHTML = html;
        }

        const response = await fetch(`${API_BASE}/cards/create-playlist-from-audio`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (!response.ok) {
            // Handle authentication errors specially
            if (response.status === 401) {
                const goToDashboard = confirm(`${data.detail || 'Your Yoto session has expired.'}\n\nWould you like to go to the Dashboard to log in?`);
                if (goToDashboard) {
                    window.location.href = '/';
                    return;
                }
            }
            throw new Error(data.detail || 'Failed to create playlist');
        }

        alert(`✓ ${data.message}\nCard ID: ${data.card_id}`);
        closePlaylistModal();

    } catch (error) {
        console.error('Error creating playlist:', error);
        alert(`Error: ${error.message}`);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

// Helper function to format duration
function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// (use existing formatFileSize defined earlier in file)

// ============================================================================
// Audio Editor Functions
// ============================================================================

let editorFiles = []; // [{filename, delaySeconds}]
let activeStitchTaskId = null;
let stitchWS = null;
let editorModalKeyHandler = null;

function openAudioEditor() {
    const modal = document.getElementById('audioEditorModal');
    if (!modal) return;
    modal.style.display = 'flex';
    editorFiles = [];
    activeStitchTaskId = null;
    renderEditorSelected();
    const searchInput = document.getElementById('editor-audio-search');
    if (searchInput) {
        searchInput.addEventListener('input', searchEditorAudioFiles);
        searchInput.value = '';
    }
    // Setup keyboard handler for Escape key
    editorModalKeyHandler = (e) => {
        if (e.key === 'Escape') {
            closeAudioEditor();
        }
    };
    document.addEventListener('keydown', editorModalKeyHandler);
    // Check for active stitch task to reconnect
    checkActiveStitchTask();
}

function closeAudioEditor() {
    const modal = document.getElementById('audioEditorModal');
    // Remove keyboard handler
    if (editorModalKeyHandler) {
        document.removeEventListener('keydown', editorModalKeyHandler);
        editorModalKeyHandler = null;
    }
    if (modal) modal.style.display = 'none';
    // Cleanup preview
    const previewAudio = document.getElementById('editor-preview-audio');
    const previewContainer = document.getElementById('editor-preview-player');
    if (previewAudio && previewAudio.dataset.previewId) {
        fetch(`${API_BASE}/audio/preview-stitch/${encodeURIComponent(previewAudio.dataset.previewId)}`, { method: 'DELETE' })
            .catch(() => {});
        previewAudio.removeAttribute('data-preview-id');
    }
    if (previewContainer) previewContainer.style.display = 'none';
    // Close websocket
    if (stitchWS) {
        try { stitchWS.close(); } catch (e) {}
        stitchWS = null;
    }
}

async function searchEditorAudioFiles() {
    const query = document.getElementById('editor-audio-search').value.trim();
    const resultsDiv = document.getElementById('editor-search-results');
    if (!query) {
        resultsDiv.innerHTML = '<p class="placeholder">Type to search audio files...</p>';
        return;
    }
    try {
        const response = await fetch(`${API_BASE}/audio/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Search failed');
        if (!data.results || data.results.length === 0) {
            resultsDiv.innerHTML = '<p class="placeholder">No files found.</p>';
            return;
        }
        let html = '<div class="search-results-list">';
        for (const file of data.results) {
            const isAdded = editorFiles.some(f => f.filename === file.filename);
            html += `
                <div class="search-result-item ${isAdded ? 'added' : ''}">
                    <div class="result-info">
                        <div class="result-filename">${escapeHtml(file.filename.replace('.mp3',''))}</div>
                        <div class="result-meta">
                            <span class="result-duration">⏱️ ${formatDuration(file.duration)}</span>
                            <span class="result-size">📦 ${formatFileSize(file.size)}</span>
                        </div>
                        ${file.transcript ? `<div class="result-transcript"><strong>Transcript:</strong> ${escapeHtml((file.transcript||'').substring(0,100))}...</div>` : ''}
                    </div>
                    <button class="btn-small ${isAdded ? 'btn-disabled' : 'btn-add'}" onclick="addFileToEditor('${file.filename.replace(/'/g, "\\'")}')" ${isAdded ? 'disabled' : ''}>${isAdded ? '✓ Added' : '+ Add'}</button>
                </div>`;
        }
        html += '</div>';
        resultsDiv.innerHTML = html;
    } catch (error) {
        console.error('Editor search error:', error);
        resultsDiv.innerHTML = `<p class="error-message">${error.message}</p>`;
    }
}

function addFileToEditor(filename) {
    editorFiles.push({ filename, delaySeconds: 1.0 });
    renderEditorSelected();
    // Enable create if at least 2 files
    const createBtn = document.getElementById('editor-create-btn');
    if (createBtn) createBtn.disabled = editorFiles.length < 2;
}

function renderEditorSelected() {
    const list = document.getElementById('editor-selected-list');
    const count = document.getElementById('editor-file-count');
    count.textContent = editorFiles.length;
    if (editorFiles.length === 0) {
        list.innerHTML = '<p class="placeholder">No files added yet. Search and add above.</p>';
        return;
    }
    let html = '<div class="chapters-items">';
    editorFiles.forEach((item, idx) => {
        html += `
            <div class="chapter-item" draggable="true" ondragstart="editorDragStart(event, ${idx})" ondragover="editorDragOver(event, ${idx})" ondrop="editorDrop(event, ${idx})">
                <div class="chapter-number"><span class="chapter-index">${idx+1}</span></div>
                <div class="chapter-details">
                    <div class="chapter-filename">${escapeHtml(item.filename)}</div>
                    <div class="chapter-title-input">
                        <label>Delay after file (seconds):</label>
                        <input type="number" min="0.1" max="10.0" step="0.1" value="${item.delaySeconds}" onchange="updateEditorDelay(${idx}, parseFloat(this.value))">
                    </div>
                </div>
                <div class="chapter-actions">
                    <button class="btn-remove" onclick="removeEditorFile(${idx})">🗑️ Remove</button>
                </div>
            </div>`;
    });
    html += '</div>';
    list.innerHTML = html;
}

function updateEditorDelay(index, value) {
    if (isNaN(value) || value < 0.1 || value > 10.0) {
        alert('Delay must be between 0.1 and 10.0 seconds');
        return;
    }
    editorFiles[index].delaySeconds = value;
}

function removeEditorFile(index) {
    editorFiles.splice(index, 1);
    renderEditorSelected();
    const createBtn = document.getElementById('editor-create-btn');
    if (createBtn) createBtn.disabled = editorFiles.length < 2;
}

let dragIndex = null;
function editorDragStart(e, idx) { dragIndex = idx; e.dataTransfer.effectAllowed = 'move'; }
function editorDragOver(e, idx) { e.preventDefault(); }
function editorDrop(e, idx) {
    e.preventDefault();
    if (dragIndex === null || dragIndex === idx) return;
    const [moved] = editorFiles.splice(dragIndex, 1);
    editorFiles.splice(idx, 0, moved);
    dragIndex = null;
    renderEditorSelected();
}

async function generatePreview() {
    if (editorFiles.length === 0) return;
    const previewSeconds = parseInt(document.getElementById('preview-duration').value, 10) || 5;
    const files = editorFiles.map(f => f.filename);
    const delays = editorFiles.map(f => f.delaySeconds);
    try {
        const response = await fetch(`${API_BASE}/audio/preview-stitch`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files, delays, preview_duration_seconds: previewSeconds })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to generate preview');
        const audioEl = document.getElementById('editor-preview-audio');
        const container = document.getElementById('editor-preview-player');
        audioEl.src = data.url;
        audioEl.dataset.previewId = data.preview_id;
        container.style.display = 'block';
        audioEl.play().catch(() => {});
    } catch (error) {
        console.error('Preview error:', error);
        alert(error.message);
    }
}

async function submitStitch() {
    const outputName = document.getElementById('editor-output-filename').value.trim();
    if (!outputName) { alert('Please enter an output filename'); return; }
    if (editorFiles.length < 2) { alert('Add at least two files'); return; }
    const payload = {
        files: editorFiles.map(f => f.filename),
        delays: editorFiles.map(f => f.delaySeconds),
        output_filename: outputName
    };
    try {
        const response = await fetch(`${API_BASE}/audio/stitch`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to start stitching');
        activeStitchTaskId = data.task_id;
        connectStitchWS();
        const progress = document.getElementById('editor-progress');
        const cancelBtn = document.getElementById('editor-cancel-task-btn');
        if (progress) progress.style.display = 'block';
        if (cancelBtn) cancelBtn.style.display = 'inline-block';
        document.getElementById('editor-status').textContent = 'Processing';
    } catch (error) {
        console.error('Stitch start error:', error);
        alert(error.message);
    }
}

function connectStitchWS() {
    if (!activeStitchTaskId) return;
    const wsUrl = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/stitch/${activeStitchTaskId}`;
    stitchWS = new WebSocket(wsUrl);
    const fill = document.getElementById('editor-progress-fill');
    const statusEl = document.getElementById('editor-status');
    const currentFileEl = document.getElementById('editor-current-file');
    stitchWS.onmessage = (evt) => {
        try {
            const msg = JSON.parse(evt.data);
            console.debug('Stitch WS:', msg);
            if (msg.event === 'snapshot' || msg.event === 'heartbeat' || msg.event === 'progress') {
                if (typeof msg.progress === 'number' && fill) fill.style.width = `${msg.progress}%`;
                if (msg.current_file && currentFileEl) currentFileEl.textContent = msg.current_file;
            } else if (msg.event === 'loading' && msg.file && currentFileEl) {
                currentFileEl.textContent = `Loading ${msg.file}`;
            } else if (msg.event === 'finalizing') {
                statusEl.textContent = 'Finalizing';
            } else if (msg.event === 'completed') {
                statusEl.textContent = 'Completed';
                fill.style.width = '100%';
                // Refresh list and close editor after brief delay
                setTimeout(() => { loadAudioFiles(); }, 1000);
            } else if (msg.event === 'error') {
                statusEl.textContent = `Error: ${msg.message || ''}`;
            } else if (msg.event === 'cancelled') {
                statusEl.textContent = 'Cancelled';
            }
        } catch (e) { console.warn('WS parse error', e); }
    };
    stitchWS.onclose = () => { stitchWS = null; };
}

async function cancelStitchTask() {
    if (!activeStitchTaskId) return;
    try {
        const response = await fetch(`${API_BASE}/audio/stitch/${encodeURIComponent(activeStitchTaskId)}/cancel`, { method: 'POST' });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Failed to cancel');
        document.getElementById('editor-status').textContent = 'Cancelling';
    } catch (error) {
        console.error('Cancel error:', error);
        alert(error.message);
    }
}

async function checkActiveStitchTask() {
    try {
        const response = await fetch(`${API_BASE}/audio/stitch/status`);
        const data = await response.json();
        if (data.active && data.task_id) {
            activeStitchTaskId = data.task_id;
            connectStitchWS();
            const progress = document.getElementById('editor-progress');
            const cancelBtn = document.getElementById('editor-cancel-task-btn');
            if (progress) progress.style.display = 'block';
            if (cancelBtn) cancelBtn.style.display = 'inline-block';
            document.getElementById('editor-status').textContent = data.status || 'Processing';
            document.getElementById('editor-progress-fill').style.width = `${data.progress || 0}%`;
            if (data.current_file) document.getElementById('editor-current-file').textContent = data.current_file;
        }
    } catch (e) { console.debug('No active stitch task'); }
}
