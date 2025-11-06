/**
 * Deployments Ignore List Management
 * Handles UI interactions for managing the DEPLOY_TEMPLATE_IGNORE_LIST
 */

// Store current ignore list
let currentIgnoreList = [];

// Load ignore list when modal is opened
document.getElementById('ignoreListModal').addEventListener('show.bs.modal', async function () {
    await loadIgnoreList();
});

// Add item button click handler
document.getElementById('addIgnoreItemBtn').addEventListener('click', function () {
    addIgnoreItem();
});

// Allow Enter key to add item
document.getElementById('newIgnoreItem').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        addIgnoreItem();
    }
});

// Save changes button click handler
document.getElementById('saveIgnoreListBtn').addEventListener('click', async function () {
    await saveIgnoreList();
});

/**
 * Load the current ignore list from the server
 */
async function loadIgnoreList() {
    try {
        const response = await fetch('/deployments/ignore_list', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const result = await response.json();

        if (result.success) {
            currentIgnoreList = result.ignore_list || [];
            renderIgnoreList();
        } else {
            showAlert('Error loading ignore list: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error loading ignore list:', error);
        showAlert('Error loading ignore list: ' + error.message, 'danger');
    }
}

/**
 * Render the ignore list in the UI
 */
function renderIgnoreList() {
    const container = document.getElementById('ignoreListItems');
    const emptyMessage = document.getElementById('emptyIgnoreListMessage');

    // Clear current content
    container.innerHTML = '';

    if (currentIgnoreList.length === 0) {
        emptyMessage.style.display = 'block';
        return;
    }

    emptyMessage.style.display = 'none';

    // Sort the list alphabetically for better UX
    const sortedList = [...currentIgnoreList].sort();

    sortedList.forEach((item, index) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'border border-primary rounded d-inline-flex align-items-center py-2 px-3 me-2 mb-2';
        itemDiv.style.width = 'auto';
        itemDiv.style.backgroundColor = '#cfe2ff';
        itemDiv.innerHTML = `
            <span><code class="text-dark">${escapeHtml(item)}</code></span>
            <button type="button" class="btn btn-sm btn-link text-danger ms-2 p-0" onclick="removeIgnoreItem('${escapeHtml(item)}')" title="Remove this item">
                <i class="bi bi-x-circle-fill"></i>
            </button>
        `;
        container.appendChild(itemDiv);
    });
}

/**
 * Add a new item to the ignore list
 */
function addIgnoreItem() {
    const input = document.getElementById('newIgnoreItem');
    const newItem = input.value.trim();

    if (!newItem) {
        showAlert('Please enter a value', 'warning');
        return;
    }

    if (currentIgnoreList.includes(newItem)) {
        showAlert('This item is already in the ignore list', 'warning');
        return;
    }

    currentIgnoreList.push(newItem);
    input.value = '';
    renderIgnoreList();
    showAlert('Item added. Click "Save Changes" to apply.', 'info');
}

/**
 * Remove an item from the ignore list
 */
function removeIgnoreItem(item) {
    currentIgnoreList = currentIgnoreList.filter(i => i !== item);
    renderIgnoreList();
    showAlert('Item removed. Click "Save Changes" to apply.', 'info');
}

/**
 * Save the ignore list to the server
 */
async function saveIgnoreList() {
    const updateEnvFile = document.getElementById('updateEnvFileCheckbox').checked;
    const saveBtn = document.getElementById('saveIgnoreListBtn');

    // Disable button while saving
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>Saving...';

    try {
        const response = await fetch('/deployments/ignore_list', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                ignore_list: currentIgnoreList,
                update_env_file: updateEnvFile
            })
        });

        const result = await response.json();

        if (result.success) {
            // Reload the list to verify the update
            await loadIgnoreList();

            let message = 'Ignore list updated successfully!';
            if (result.env_file_updated) {
                message += ' .env file has been updated.';
            } else if (updateEnvFile && result.env_file_error) {
                message += ' However, there was an error updating the .env file: ' + result.env_file_error;
            }
            message += ' Please download new data to see the changes.';
            showAlert(message, 'success');
        } else {
            showAlert('Error saving ignore list: ' + (result.error || 'Unknown error'), 'danger');
        }
    } catch (error) {
        console.error('Error saving ignore list:', error);
        showAlert('Error saving ignore list: ' + error.message, 'danger');
    } finally {
        // Re-enable button
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<i class="bi bi-save me-1"></i>Save Changes';
    }
}

/**
 * Show an alert message in the modal
 */
function showAlert(message, type) {
    const alertDiv = document.getElementById('ignoreListAlert');

    // Use blue for info/warning, green for success, red for danger
    if (type === 'success') {
        alertDiv.className = 'alert alert-success';
    } else if (type === 'danger') {
        alertDiv.className = 'alert alert-danger';
    } else {
        // info and warning both get blue
        alertDiv.className = 'alert alert-info';
    }

    alertDiv.innerHTML = message;
    alertDiv.style.display = 'block';

    // Auto-hide after 5 seconds for non-error messages
    if (type !== 'danger') {
        setTimeout(() => {
            alertDiv.style.display = 'none';
        }, 5000);
    }
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
