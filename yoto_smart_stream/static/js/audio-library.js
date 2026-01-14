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
        
        container.innerHTML = files.map(file => `
            <div class="list-item">
                <div class="list-item-header">
                    <span class="list-item-title">
                        🎵 ${escapeHtml(file.filename)}
                        ${file.is_static ? '<span class="badge" style="background: #805ad5; color: white; margin-left: 0.5rem;">Static</span>' : ''}
                    </span>
                </div>
                <div class="list-item-details">
                    <span>Duration: ${file.duration}s | Size: ${file.size} bytes (${formatFileSize(file.size)})</span>
                    <button class="control-btn" onclick="copyAudioUrl('${escapeHtml(file.url)}', event)" title="Copy Full URL">
                        📋
                    </button>
                    <audio controls preload="none" style="width: 100%; max-width: 300px; margin-top: 8px;">
                        <source src="${escapeHtml(file.url)}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading audio files:', error);
        container.innerHTML = '<p class="error-message">Failed to load audio files.</p>';
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
        
        // Reset recorder after delay
        setTimeout(() => {
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
        
        // Generate default filename with timestamp
        const timestamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-');
        filenameInput.value = `recording-${timestamp}`;
        
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
