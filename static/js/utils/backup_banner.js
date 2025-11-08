/**
 * Backup Banner Management
 * Shows a banner when viewing a backup (read-only mode)
 */

// Check backup status on page load
document.addEventListener('DOMContentLoaded', async function () {
    await checkBackupStatus();
});

/**
 * Check if we're in backup mode and show banner if needed
 */
async function checkBackupStatus() {
    try {
        const response = await fetch('/backups/status', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success && result.is_backup_mode && result.current_backup) {
            showBackupBanner(result.current_backup);
            disableWriteOperations();
        }
    } catch (error) {
        console.error('Error checking backup status:', error);
    }
}

/**
 * Show the backup mode banner
 */
function showBackupBanner(backup) {
    const banner = document.getElementById('backupModeBanner');
    const timestamp = new Date(backup.timestamp).toLocaleString();

    banner.innerHTML = `
        <div class="alert alert-warning border-warning mb-0 rounded-0 d-flex justify-content-between align-items-center" role="alert">
            <div>
                <i class="bi bi-exclamation-triangle-fill me-2"></i>
                <strong>READ-ONLY MODE:</strong> Viewing Backup: <strong>${escapeHtml(backup.description)}</strong>
                (${timestamp})
                <span class="ms-2 small">
                    - Data download, edits, JIRA tickets, MRs, and release processes are disabled
                </span>
            </div>
            <button class="btn btn-sm btn-warning" onclick="openBackupManager()">
                <i class="bi bi-archive me-1"></i>Backup Manager
            </button>
        </div>
    `;
    banner.style.display = 'block';
}

/**
 * Open the backup manager modal
 */
function openBackupManager() {
    const modal = new bootstrap.Modal(document.getElementById('backupModal'));
    modal.show();
}

/**
 * Disable all write operations when in backup mode
 */
function disableWriteOperations() {
    // Disable data download buttons
    const updateAllBtn = document.getElementById('updateAllDataBtn');
    const downloadFromScratchBtn = document.getElementById('downloadFromScratchBtn');

    if (updateAllBtn) {
        updateAllBtn.disabled = true;
        updateAllBtn.title = 'Disabled in backup mode';
        updateAllBtn.classList.add('disabled');
    }

    if (downloadFromScratchBtn) {
        downloadFromScratchBtn.disabled = true;
        downloadFromScratchBtn.title = 'Disabled in backup mode';
        downloadFromScratchBtn.classList.add('disabled');
    }

    // Disable any "Create" buttons (JIRA, MR, Google Doc, Release Process, etc.)
    const createButtons = [
        'create_jira_ticket',
        'create_google_doc',
        'createMrBtn',
        'start_release_process',
        'createBackupBtn', // Can't create backup from backup mode
        'addIgnoreItemBtn', // Can't modify ignore list in backup mode
        'saveIgnoreListBtn',
        'check-mr-status-btn', // Can't check MR status in backup mode
        'updateDataBtn', // Can't update data on Back Office Proxy page in backup mode
        'saveTokensBtn', // Can't update OpenShift tokens in backup mode
        'createGoogleDocBtn' // Can't create Google Doc from Back Office Proxy in backup mode
    ];

    createButtons.forEach(btnId => {
        const btn = document.getElementById(btnId);
        if (btn) {
            btn.disabled = true;
            btn.title = 'Disabled in backup mode';
            btn.classList.add('disabled');
        }
    });

    // Disable buttons with specific classes (for Release Process page)
    const buttonClassesToDisable = [
        'mark-step-complete',
        'mark-step-incomplete',
        'btn-jira-create',
        'btn-google-doc-create',
        'btn-mr-create'
    ];

    buttonClassesToDisable.forEach(className => {
        const buttons = document.querySelectorAll(`.${className}`);
        buttons.forEach(btn => {
            btn.disabled = true;
            btn.title = 'Disabled in backup mode';
            btn.classList.add('disabled');
        });
    });

    // Disable all buttons that contain certain text patterns
    const allButtons = document.querySelectorAll('button');
    allButtons.forEach(btn => {
        const btnText = btn.textContent.toLowerCase();

        // Exceptions: Read-only operations that should stay enabled in backup mode
        if (btnText.includes('generate release notes') ||
            btnText.includes('view release notes') ||
            btnText.includes('preview')) {
            return; // Skip these buttons, keep them enabled
        }

        if (btnText.includes('create') ||
            btnText.includes('mark as complete') ||
            btnText.includes('unmark') ||
            btnText.includes('generate') ||
            btnText.includes('update') ||
            btnText.includes('check mr status') ||
            btnText.includes('delete process')) {
            btn.disabled = true;
            btn.title = 'Disabled in backup mode';
            btn.classList.add('disabled');
        }
    });

    // Disable "Download new data" button on deployments page
    const updateButton = document.getElementById('update_button');
    if (updateButton) {
        updateButton.disabled = true;
        updateButton.title = 'Disabled in backup mode';
        updateButton.classList.add('disabled');
    }

    // Disable edit mode on overview page
    const editModeToggle = document.getElementById('editModeToggle');
    if (editModeToggle) {
        editModeToggle.disabled = true;
        editModeToggle.checked = false; // Ensure it's unchecked
        const label = document.querySelector('label[for="editModeToggle"]');
        if (label) {
            label.title = 'Editing disabled in backup mode';
            label.classList.add('text-muted');
        }
    }

    // Add a global flag for other scripts to check
    window.IS_BACKUP_MODE = true;
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
