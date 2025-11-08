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

// Delete all backups button
document.getElementById('deleteAllBackupsBtn').addEventListener('click', function() {
    showDeleteAllConfirmation();
});

// Confirm delete all button
document.getElementById('confirmDeleteAllBtn').addEventListener('click', async function() {
    const modal = bootstrap.Modal.getInstance(document.getElementById('deleteAllBackupsConfirmModal'));
    modal.hide();
    await deleteAllBackups();
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
    const deleteAllBtn = document.getElementById('deleteAllBackupsBtn');

    container.innerHTML = '';

    // Show/hide delete all button
    if (currentBackups.length > 0 && !isBackupMode) {
        deleteAllBtn.style.display = 'inline-block';
    } else {
        deleteAllBtn.style.display = 'none';
    }

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

        const envBadge = backup.env_backed_up
            ? '<span class="badge bg-success ms-2" title="Environment file included"><i class="bi bi-file-earmark-text me-1"></i>including .env file</span>'
            : '<span class="badge bg-secondary ms-2" title="Environment file not included">No .env</span>';

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
                            ${envBadge}
                        </small>
                    </div>
                    <div class="btn-group" role="group">
                        ${!isCurrent && !isBackupMode ? `
                            <button type="button" class="btn btn-sm btn-outline-success"
                                onclick="restoreBackupToLive('${backup.id}')" title="Restore this backup to live mode">
                                <i class="bi bi-arrow-clockwise me-1"></i>Restore to Live
                            </button>
                        ` : ''}
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
    const backupCounter = document.getElementById('backupCounter');

    // Update counter
    const maxBackups = 10;
    const remaining = maxBackups - currentBackups.length;
    const used = currentBackups.length;

    if (remaining > 0) {
        backupCounter.className = 'badge bg-info ms-2';
        backupCounter.textContent = `${remaining} of ${maxBackups} slots remaining`;
    } else {
        backupCounter.className = 'badge bg-danger ms-2';
        backupCounter.textContent = 'Maximum backups reached';
    }

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
 * Restore a backup to live mode (replaces current data)
 */
async function restoreBackupToLive(backupId) {
    // Get backup info for the confirmation message
    const backup = currentBackups.find(b => b.id === backupId);
    const backupDesc = backup ? backup.description : backupId;

    // Show Bootstrap confirmation modal
    const restoreBackupName = document.getElementById('restoreBackupName');
    restoreBackupName.textContent = backupDesc;

    const confirmModal = new bootstrap.Modal(document.getElementById('restoreBackupConfirmModal'));
    confirmModal.show();

    // Store backup ID for the confirmation button
    document.getElementById('confirmRestoreBtn').onclick = async function() {
        confirmModal.hide();
        await executeRestoreBackup(backupId);
    };
}

/**
 * Execute the backup restore (called after confirmation)
 */
async function executeRestoreBackup(backupId) {
    // Show loading indicator
    const alertDiv = document.getElementById('backupAlert');
    alertDiv.className = 'alert alert-info';
    alertDiv.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Restoring backup to live mode... This may take a moment.';
    alertDiv.style.display = 'block';

    try {
        const response = await fetch(`/backups/restore/${backupId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            showBackupAlert(
                `✓ Backup restored successfully!<br>` +
                `<small>Automatic backup created: ${result.auto_backup.description}</small>`,
                'success'
            );

            // Reload after a short delay to show the success message
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } else {
            showBackupAlert('Error restoring backup: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error restoring backup to live:', error);
        showBackupAlert('Error restoring backup: ' + error.message, 'danger');
    }
}

/**
 * Show delete all confirmation modal
 */
function showDeleteAllConfirmation() {
    const deleteAllCount = document.getElementById('deleteAllCount');
    deleteAllCount.textContent = `${currentBackups.length}`;

    const confirmModal = new bootstrap.Modal(document.getElementById('deleteAllBackupsConfirmModal'));
    confirmModal.show();
}

/**
 * Delete all backups
 */
async function deleteAllBackups() {
    const alertDiv = document.getElementById('backupAlert');
    alertDiv.className = 'alert alert-info';
    alertDiv.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Deleting all backups... This may take a moment.';
    alertDiv.style.display = 'block';

    try {
        // Delete each backup one by one
        const deletePromises = currentBackups
            .filter(backup => backup.id !== currentBackupId) // Don't delete current backup
            .map(backup =>
                fetch(`/backups/${backup.id}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
            );

        await Promise.all(deletePromises);

        showBackupAlert('All backups deleted successfully!', 'success');
        await loadBackups();
    } catch (error) {
        console.error('Error deleting all backups:', error);
        showBackupAlert('Error deleting backups: ' + error.message, 'danger');
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
