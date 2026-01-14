// Cover Art Management JavaScript

const API_BASE = '/api';

// Modal management
function openCoverArtManager() {
    const modal = document.getElementById('cover-art-modal');
    modal.style.display = 'block';
    loadCoverArt();
    
    // Add escape key listener
    document.addEventListener('keydown', handleCoverArtEscape);
}

function closeCoverArtManager() {
    const modal = document.getElementById('cover-art-modal');
    modal.style.display = 'none';
    
    // Remove escape key listener
    document.removeEventListener('keydown', handleCoverArtEscape);
    
    // Clear form
    document.getElementById('cover-art-file').value = '';
    document.getElementById('remote-image-url').value = '';
    document.getElementById('remote-filename').value = '';
    
    // Clear result message
    const resultDiv = document.getElementById('cover-art-result');
    resultDiv.style.display = 'none';
}

function handleCoverArtEscape(event) {
    if (event.key === 'Escape') {
        // Check if preview modal is open, close it first
        const previewModal = document.getElementById('image-preview-modal');
        if (previewModal.style.display === 'block') {
            closeImagePreview();
        } else {
            closeCoverArtManager();
        }
    }
}

// Tab management
function switchTab(tabName) {
    // Hide all tabs
    document.getElementById('upload-tab').style.display = 'none';
    document.getElementById('remote-tab').style.display = 'none';
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab
    if (tabName === 'upload') {
        document.getElementById('upload-tab').style.display = 'block';
        document.querySelectorAll('.tab-btn')[0].classList.add('active');
    } else {
        document.getElementById('remote-tab').style.display = 'block';
        document.querySelectorAll('.tab-btn')[1].classList.add('active');
    }
}

// Load cover art
async function loadCoverArt() {
    const container = document.getElementById('cover-art-grid');
    
    try {
        const response = await fetch(`${API_BASE}/cover-images`);
        if (!response.ok) throw new Error('Failed to fetch cover art');
        
        const data = await response.json();
        const images = data.images || [];
        
        if (images.length === 0) {
            container.innerHTML = '<p style="color: #999; text-align: center; padding: 2rem;">No cover art found.</p>';
            return;
        }
        
        container.innerHTML = images.map(img => `
            <div class="cover-art-card">
                <div class="cover-art-image" onclick="previewImage('${escapeHtml(img.filename, true)}')">
                    <img src="${API_BASE}/cover-images/${escapeHtml(img.filename, true)}" 
                         alt="${escapeHtml(img.filename)}"
                         loading="lazy" />
                </div>
                <div class="cover-art-info">
                    <div class="cover-art-filename">${escapeHtml(img.filename)}</div>
                    <div class="cover-art-dimensions">
                        ${img.dimensions.width}×${img.dimensions.height}
                        ${img.is_recommended_size ? '<span class="badge-success">✓</span>' : ''}
                        ${img.is_permanent ? '<span class="badge-permanent">Permanent</span>' : ''}
                    </div>
                    <div class="cover-art-size">${formatFileSize(img.size)}</div>
                    ${!img.is_permanent ? `
                        <button class="btn-danger btn-small" onclick="deleteCoverArt('${escapeHtml(img.filename, true)}')">
                            Delete
                        </button>
                    ` : ''}
                </div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('Error loading cover art:', error);
        container.innerHTML = '<p class="error-message">Failed to load cover art.</p>';
    }
}

// Upload cover art
async function uploadCoverArt() {
    const fileInput = document.getElementById('cover-art-file');
    const resultDiv = document.getElementById('cover-art-result');
    
    if (!fileInput.files || fileInput.files.length === 0) {
        showResult(resultDiv, 'Please select an image file.', 'error');
        return;
    }
    
    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        resultDiv.style.display = 'none';
        
        const response = await fetch(`${API_BASE}/cover-images/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Upload failed');
        }
        
        const message = `✓ Uploaded: ${data.filename} (${data.dimensions[0]}×${data.dimensions[1]})`;
        showResult(resultDiv, message, 'success');
        
        // Clear file input
        fileInput.value = '';
        
        // Reload cover art
        await loadCoverArt();
        
    } catch (error) {
        console.error('Error uploading cover art:', error);
        showResult(resultDiv, `Upload failed: ${error.message}`, 'error');
    }
}

// Fetch remote cover art
async function fetchRemoteCoverArt() {
    const urlInput = document.getElementById('remote-image-url');
    const filenameInput = document.getElementById('remote-filename');
    const resultDiv = document.getElementById('cover-art-result');
    
    const imageUrl = urlInput.value.trim();
    if (!imageUrl) {
        showResult(resultDiv, 'Please enter an image URL.', 'error');
        return;
    }
    
    const requestData = {
        image_url: imageUrl
    };
    
    const filename = filenameInput.value.trim();
    if (filename) {
        requestData.filename = filename;
    }
    
    try {
        resultDiv.style.display = 'none';
        
        const response = await fetch(`${API_BASE}/cover-images/fetch`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Fetch failed');
        }
        
        const message = `✓ Fetched: ${data.filename} (${data.dimensions[0]}×${data.dimensions[1]})`;
        showResult(resultDiv, message, 'success');
        
        // Clear inputs
        urlInput.value = '';
        filenameInput.value = '';
        
        // Reload cover art
        await loadCoverArt();
        
    } catch (error) {
        console.error('Error fetching remote cover art:', error);
        showResult(resultDiv, `Fetch failed: ${error.message}`, 'error');
    }
}

// Delete cover art
async function deleteCoverArt(filename) {
    if (!confirm(`Delete "${filename}"?`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/cover-images/${encodeURIComponent(filename)}`, {
            method: 'DELETE'
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Delete failed');
        }
        
        // Reload cover art
        await loadCoverArt();
        
    } catch (error) {
        console.error('Error deleting cover art:', error);
        alert(`Failed to delete: ${error.message}`);
    }
}

// Preview image
function previewImage(filename) {
    const modal = document.getElementById('image-preview-modal');
    const img = document.getElementById('preview-image');
    const title = document.getElementById('preview-title');
    const info = document.getElementById('preview-info');
    
    title.textContent = filename;
    img.src = `${API_BASE}/cover-images/${encodeURIComponent(filename)}`;
    
    // Load image info
    fetch(`${API_BASE}/cover-images`)
        .then(r => r.json())
        .then(data => {
            const imgData = data.images.find(i => i.filename === filename);
            if (imgData) {
                info.innerHTML = `
                    <p><strong>Dimensions:</strong> ${imgData.dimensions.width}×${imgData.dimensions.height} 
                       ${imgData.is_recommended_size ? '<span class="badge-success">✓ Recommended size</span>' : ''}</p>
                    <p><strong>File size:</strong> ${formatFileSize(imgData.size)}</p>
                    ${imgData.is_permanent ? '<p><strong>Status:</strong> <span class="badge-permanent">Permanent (cannot be deleted)</span></p>' : ''}
                `;
            }
        })
        .catch(err => console.error('Error loading image info:', err));
    
    modal.style.display = 'block';
    
    // Add escape key listener
    document.addEventListener('keydown', handleImagePreviewEscape);
}

function closeImagePreview() {
    const modal = document.getElementById('image-preview-modal');
    modal.style.display = 'none';
    
    // Remove escape key listener
    document.removeEventListener('keydown', handleImagePreviewEscape);
}

function handleImagePreviewEscape(event) {
    if (event.key === 'Escape') {
        closeImagePreview();
    }
}

// Close modals when clicking outside
window.addEventListener('click', function(event) {
    const coverArtModal = document.getElementById('cover-art-modal');
    const previewModal = document.getElementById('image-preview-modal');
    
    if (event.target === coverArtModal) {
        closeCoverArtManager();
    } else if (event.target === previewModal) {
        closeImagePreview();
    }
});

// Helper functions
function showResult(element, message, type) {
    element.textContent = message;
    element.className = `result-message ${type === 'error' ? 'error-message' : 'success-message'}`;
    element.style.display = 'block';
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function escapeHtml(text, forAttribute = false) {
    const div = document.createElement('div');
    div.textContent = text;
    const escaped = div.innerHTML;
    return forAttribute ? escaped.replace(/"/g, '&quot;') : escaped;
}
