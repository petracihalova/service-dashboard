/**
 * Backup Manager
 * Handles UI interactions for creating, viewing, switching, and deleting backups
 */

let currentBackups = [];
let currentBackupId = null;
let isBackupMode = false;

// Load backups when modal is opened
document.getElementById('backupModal').addEventListener('show.bs.modal', async function () {
    await loadBackups();
});

// Create backup button
document.getElementById('createBackupBtn').addEventListener('click', async function () {
    await createBackup();
});

// Restore to live mode button
document.getElementById('restoreToLiveBtn').addEventListener('click', async function () {
    await restoreToLive();
});

/**
 * Load all backups and current status
 */
async function loadBackups() {
    try {
        const response = await fetch('/backups/', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            currentBackups = result.backups || [];
            currentBackupId = result.current_backup;
            isBackupMode = result.is_backup_mode;

            renderBackupsList();
            updateModeIndicator();
        } else {
            showBackupAlert('Error loading backups: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error loading backups:', error);
        showBackupAlert('Error loading backups: ' + error.message, 'danger');
    }
}

/**
 * Render the list of backups
 */
function renderBackupsList() {
    const container = document.getElementById('backupsList');
    const emptyMessage = document.getElementById('emptyBackupsMessage');

    container.innerHTML = '';

    if (currentBackups.length === 0) {
        emptyMessage.style.display = 'block';
        return;
    }

    emptyMessage.style.display = 'none';

    currentBackups.forEach((backup) => {
        const isCurrent = backup.id === currentBackupId;
        const backupDiv = document.createElement('div');
        backupDiv.className = `card mb-2 ${isCurrent ? 'border-primary' : ''}`;

        const timestamp = new Date(backup.timestamp).toLocaleString();

        backupDiv.innerHTML = `
            <div class="card-body py-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${escapeHtml(backup.description)}</strong>
                        <br>
                        <small class="text-muted">
                            <i class="bi bi-clock me-1"></i>${timestamp}
                            <i class="bi bi-hdd ms-2 me-1"></i>${backup.size_mb} MB
                            ${isCurrent ? '<span class="badge bg-primary ms-2">Currently Viewing</span>' : ''}
                        </small>
                    </div>
                    <div class="btn-group" role="group">
                        ${!isCurrent ? `
                            <button type="button" class="btn btn-sm btn-outline-primary"
                                onclick="switchToBackup('${backup.id}')" title="View this backup">
                                <i class="bi bi-eye me-1"></i>View
                            </button>
                        ` : ''}
                        <button type="button" class="btn btn-sm btn-outline-danger"
                            onclick="deleteBackup('${backup.id}')" title="Delete this backup"
                            ${isCurrent ? 'disabled' : ''}>
                            <i class="bi bi-trash me-1"></i>Delete
                        </button>
                    </div>
                </div>
            </div>
        `;

        container.appendChild(backupDiv);
    });
}

/**
 * Update the mode indicator in the modal
 */
function updateModeIndicator() {
    const liveIndicator = document.getElementById('liveModeIndicator');
    const backupIndicator = document.getElementById('backupModeIndicator');
    const createBackupBtn = document.getElementById('createBackupBtn');
    const restoreToLiveBtn = document.getElementById('restoreToLiveBtn');
    const backupDescInput = document.getElementById('backupDescription');

    if (isBackupMode) {
        liveIndicator.style.display = 'none';
        backupIndicator.style.display = 'block';
        createBackupBtn.disabled = true;
        backupDescInput.disabled = true;
        restoreToLiveBtn.disabled = false;
    } else {
        liveIndicator.style.display = 'block';
        backupIndicator.style.display = 'none';
        createBackupBtn.disabled = currentBackups.length >= 10;
        backupDescInput.disabled = false;
        restoreToLiveBtn.disabled = true;
    }
}

/**
 * Create a new backup
 */
async function createBackup() {
    const descriptionInput = document.getElementById('backupDescription');
    const description = descriptionInput.value.trim();
    const createBtn = document.getElementById('createBackupBtn');

    // Disable button while creating
    createBtn.disabled = true;
    createBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Creating...';

    try {
        const response = await fetch('/backups/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                description: description || null
            })
        });

        const result = await response.json();

        if (result.success) {
            showBackupAlert('Backup created successfully!', 'success');
            descriptionInput.value = '';
            await loadBackups();
        } else {
            showBackupAlert('Error creating backup: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error creating backup:', error);
        showBackupAlert('Error creating backup: ' + error.message, 'danger');
    } finally {
        createBtn.disabled = false;
        createBtn.innerHTML = '<i class="bi bi-plus-circle me-1"></i>Create Backup';
    }
}

/**
 * Switch to viewing a backup
 */
async function switchToBackup(backupId) {
    try {
        const response = await fetch(`/backups/switch/${backupId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            // Reload the page to apply changes
            window.location.reload();
        } else {
            showBackupAlert('Error switching to backup: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error switching to backup:', error);
        showBackupAlert('Error switching to backup: ' + error.message, 'danger');
    }
}

/**
 * Delete a backup
 */
async function deleteBackup(backupId) {
    if (!confirm('Are you sure you want to delete this backup? This action cannot be undone.')) {
        return;
    }

    try {
        const response = await fetch(`/backups/${backupId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            showBackupAlert('Backup deleted successfully!', 'success');
            await loadBackups();
        } else {
            showBackupAlert('Error deleting backup: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error deleting backup:', error);
        showBackupAlert('Error deleting backup: ' + error.message, 'danger');
    }
}

/**
 * Restore to live data mode
 */
async function restoreToLive() {
    try {
        const response = await fetch('/backups/restore', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            // Reload the page to apply changes
            window.location.reload();
        } else {
            showBackupAlert('Error restoring to live mode: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error restoring to live mode:', error);
        showBackupAlert('Error restoring to live mode: ' + error.message, 'danger');
    }
}

/**
 * Show an alert message in the modal
 */
function showBackupAlert(message, type) {
    const alertDiv = document.getElementById('backupAlert');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.innerHTML = message;
    alertDiv.style.display = 'block';

    // Auto-hide after 5 seconds
    setTimeout(() => {
        alertDiv.style.display = 'none';
    }, 5000);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}
