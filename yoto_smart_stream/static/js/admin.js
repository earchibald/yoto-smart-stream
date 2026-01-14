// Admin JavaScript

// API base URL
const API_BASE = '/api';

// Current user state
let currentUser = null;

// Check user authentication and admin status
async function checkUserAuth() {
    try {
        const response = await fetch('/api/user/session', { credentials: 'include' });
        const data = await response.json();
        
        if (!data.authenticated) {
            // Redirect to login page
            window.location.href = '/login';
            return false;
        }
        
        currentUser = data;
        return true;
    } catch (error) {
        console.error('Error checking authentication:', error);
        window.location.href = '/login';
        return false;
    }
}

// Check if user is admin
async function checkAdminStatus() {
    try {
        const response = await fetch('/api/admin/users', { credentials: 'include' });
        
        if (response.status === 403) {
            // User is not admin
            document.getElementById('access-denied').style.display = 'block';
            document.getElementById('admin-content').style.display = 'none';
            return false;
        }
        
        if (!response.ok) {
            throw new Error('Failed to verify admin status');
        }
        
        // User is admin
        document.getElementById('access-denied').style.display = 'none';
        document.getElementById('admin-content').style.display = 'block';
        return true;
    } catch (error) {
        console.error('Error checking admin status:', error);
        document.getElementById('access-denied').style.display = 'block';
        document.getElementById('admin-content').style.display = 'none';
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
    
    // Check admin status
    const isAdmin = await checkAdminStatus();
    if (!isAdmin) {
        return; // Stop loading if not admin
    }
    
    loadSystemStatus();
    loadUsers();
    
    // Setup create user form
    const createUserForm = document.getElementById('create-user-form');
    if (createUserForm) {
        createUserForm.addEventListener('submit', handleCreateUser);
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

// Load users list
async function loadUsers() {
    const container = document.getElementById('users-list');
    
    try {
        const response = await fetch(`${API_BASE}/admin/users`, { credentials: 'include' });
        if (!response.ok) throw new Error('Failed to fetch users');
        
        const users = await response.json();
        
        if (users.length === 0) {
            container.innerHTML = '<p class="loading">No users found.</p>';
            return;
        }
        
        container.innerHTML = users.map(user => `
            <div class="list-item" data-user-id="${user.id}" data-username="${escapeHtml(user.username)}" data-email="${escapeHtml(user.email || '')}" data-is-admin="${user.is_admin}">
                <div class="list-item-header">
                    <span class="list-item-title">
                        ${user.is_admin ? '👑 ' : '👤 '}${escapeHtml(user.username)}
                    </span>
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <span class="badge ${user.is_active ? 'online' : 'offline'}">
                            ${user.is_active ? 'Active' : 'Inactive'}
                        </span>
                        <button class="control-btn edit-user-btn" title="Edit user">
                            ✏️
                        </button>
                    </div>
                </div>
                <div class="list-item-details">
                    ${user.email ? `<span>📧 ${escapeHtml(user.email)}</span>` : '<span>📧 No email</span>'}
                    <span>${user.is_admin ? '⚙️ Admin' : '📖 User'}</span>
                    <span>📅 Created: ${formatDate(user.created_at)}</span>
                </div>
            </div>
        `).join('');
        
        // Add event listeners for edit buttons
        container.querySelectorAll('.edit-user-btn').forEach((btn, index) => {
            btn.addEventListener('click', function() {
                const listItem = this.closest('.list-item');
                const userId = parseInt(listItem.dataset.userId);
                const username = listItem.dataset.username;
                const email = listItem.dataset.email;
                const isAdmin = listItem.dataset.isAdmin === 'true';
                openEditUserModal(userId, username, email, isAdmin);
            });
        });
        
    } catch (error) {
        console.error('Error loading users:', error);
        container.innerHTML = '<p class="error-message">Failed to load users.</p>';
    }
}

// Handle create user form submission
async function handleCreateUser(event) {
    event.preventDefault();
    
    const form = event.target;
    const submitBtn = document.getElementById('create-user-btn');
    const submitText = document.getElementById('create-user-text');
    const submitSpinner = document.getElementById('create-user-spinner');
    const result = document.getElementById('create-user-result');
    const successDiv = document.getElementById('create-user-success');
    const errorDiv = document.getElementById('create-user-error');
    const successMessage = document.getElementById('create-user-success-message');
    const errorMessage = document.getElementById('create-user-error-message');
    
    // Get form data
    const username = document.getElementById('username').value.trim();
    const password = document.getElementById('password').value;
    const email = document.getElementById('email').value.trim() || null;
    
    if (!username || !password) {
        showCreateUserError('Please fill in username and password');
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
        const response = await fetch(`${API_BASE}/admin/users`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
                username: username,
                password: password,
                email: email
            }),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to create user');
        }
        
        // Show success message
        successMessage.textContent = data.message || `User '${username}' created successfully`;
        successDiv.style.display = 'block';
        result.style.display = 'block';
        
        // Reset form
        form.reset();
        
        // Refresh users list
        setTimeout(() => {
            loadUsers();
            // Clear success message after a delay
            result.style.display = 'none';
        }, 2000);
        
    } catch (error) {
        console.error('Error creating user:', error);
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

// Helper function to show create user error
function showCreateUserError(message) {
    const result = document.getElementById('create-user-result');
    const errorDiv = document.getElementById('create-user-error');
    const errorMessage = document.getElementById('create-user-error-message');
    
    errorMessage.textContent = message;
    errorDiv.style.display = 'block';
    result.style.display = 'block';
}

// Refresh data function (from dashboard)
async function refreshData(event) {
    try {
        const button = event ? event.target : document.querySelector("button[onclick*='refreshData']");
        if (button) {
            button.disabled = true;
            button.textContent = '🔄 Refreshing...';
        }
        
        // Call the players endpoint to refresh
        const response = await fetch(`${API_BASE}/players`);
        if (!response.ok) throw new Error('Failed to refresh data');
        
        // Success feedback
        if (button) {
            button.textContent = '✓ Data Refreshed';
            setTimeout(() => {
                button.disabled = false;
                button.textContent = '🔄 Refresh Data';
            }, 2000);
        }
        
    } catch (error) {
        console.error('Error refreshing data:', error);
        const button = event ? event.target : document.querySelector("button[onclick*='refreshData']");
        if (button) {
            button.textContent = '✗ Refresh Failed';
            setTimeout(() => {
                button.disabled = false;
                button.textContent = '🔄 Refresh Data';
            }, 2000);
        }
    }
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
}

// Open edit user modal
function openEditUserModal(userId, username, email, isAdmin) {
    const modal = document.getElementById('edit-user-modal');
    if (!modal) return;
    
    // Store user ID
    modal.dataset.userId = userId;
    
    // Populate form
    document.getElementById('edit-username').textContent = username;
    document.getElementById('edit-email').value = email;
    document.getElementById('edit-password').value = '';
    
    // Show modal
    modal.style.display = 'flex';
}

// Close edit user modal
function closeEditUserModal() {
    const modal = document.getElementById('edit-user-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

// Handle edit user form submission
async function handleEditUser(event) {
    event.preventDefault();
    
    const modal = document.getElementById('edit-user-modal');
    const userId = modal.dataset.userId;
    const email = document.getElementById('edit-email').value.trim() || null;
    const password = document.getElementById('edit-password').value;
    
    const submitBtn = document.getElementById('edit-user-btn');
    const submitText = document.getElementById('edit-user-text');
    const submitSpinner = document.getElementById('edit-user-spinner');
    const result = document.getElementById('edit-user-result');
    const successDiv = document.getElementById('edit-user-success');
    const errorDiv = document.getElementById('edit-user-error');
    const successMessage = document.getElementById('edit-user-success-message');
    const errorMessage = document.getElementById('edit-user-error-message');
    
    // At least one field must be changed
    if (!email && !password) {
        showEditUserError('Please change at least one field');
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
        const updateData = {};
        if (email) updateData.email = email;
        if (password) updateData.password = password;
        
        const response = await fetch(`${API_BASE}/admin/users/${userId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify(updateData),
        });
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.detail || 'Failed to update user');
        }
        
        // Show success message
        successMessage.textContent = data.message || 'User updated successfully';
        successDiv.style.display = 'block';
        result.style.display = 'block';
        
        // Reset password field
        document.getElementById('edit-password').value = '';
        
        // Refresh users list
        setTimeout(() => {
            loadUsers();
            closeEditUserModal();
        }, 1500);
        
    } catch (error) {
        console.error('Error updating user:', error);
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

// Helper function to show edit user error
function showEditUserError(message) {
    const result = document.getElementById('edit-user-result');
    const errorDiv = document.getElementById('edit-user-error');
    const errorMessage = document.getElementById('edit-user-error-message');
    
    errorMessage.textContent = message;
    errorDiv.style.display = 'block';
    result.style.display = 'block';
}
