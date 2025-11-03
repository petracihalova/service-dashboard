/**
 * Google Doc creation functionality for release notes
 */

document.addEventListener('DOMContentLoaded', function() {
    const createGoogleDocBtn = document.getElementById('create_google_doc');

    if (createGoogleDocBtn) {
        // Check Google Drive availability on page load
        checkGoogleDriveAvailability(createGoogleDocBtn);

        createGoogleDocBtn.addEventListener('click', function() {
            const deploymentName = this.getAttribute('data-deployment-name');
            const upToPr = this.getAttribute('data-up-to-pr');

            createGoogleDoc(deploymentName, upToPr);
        });
    }
});

/**
 * Check if Google Drive integration is available
 */
function checkGoogleDriveAvailability(button) {
    const deploymentName = button.getAttribute('data-deployment-name');
    const infoIcon = document.getElementById('google_doc_info');

    fetch(`/release_notes/${deploymentName}/check_google_drive`)
        .then(response => response.json())
        .then(data => {
            if (!data.google_drive_available || !data.folder_configured) {
                // Disable button and show tooltip
                button.disabled = true;
                button.title = data.error || 'Google Drive not configured';
                button.classList.add('disabled');

                // Add visual indicator
                const icon = button.querySelector('i');
                if (icon) {
                    icon.classList.remove('bi-file-earmark-text');
                    icon.classList.add('bi-exclamation-triangle');
                }

                // Show info icon with setup instructions
                if (infoIcon) {
                    infoIcon.style.display = 'inline';
                    // Initialize Bootstrap tooltip
                    new bootstrap.Tooltip(infoIcon);
                }
            } else {
                // Enable button
                button.disabled = false;

                // Build informative tooltip
                let tooltip = `Create release notes in: ${data.folder_name}`;
                if (data.folder_source) {
                    tooltip += `\n(${data.folder_source})`;
                }
                button.title = tooltip;

                // Hide info icon when configured
                if (infoIcon) {
                    infoIcon.style.display = 'none';
                }

                // Log folder info for debugging
                console.log(`Google Drive folder configured for ${deploymentName}:`, {
                    name: data.folder_name,
                    source: data.folder_source,
                    url: data.folder_url
                });
            }
        })
        .catch(error => {
            console.error('Error checking Google Drive availability:', error);
            button.disabled = true;
            button.title = 'Could not check Google Drive status';

            // Show info icon on error
            if (infoIcon) {
                infoIcon.style.display = 'inline';
                new bootstrap.Tooltip(infoIcon);
            }
        });
}

/**
 * Create Google Doc with release notes
 */
function createGoogleDoc(deploymentName, upToPr) {
    const button = document.getElementById('create_google_doc');

    // Disable button and show loading state
    button.disabled = true;
    const originalContent = button.innerHTML;
    button.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Creating...';

    // Prepare request data
    const requestData = {};
    if (upToPr) {
        requestData.up_to_pr = parseInt(upToPr);
    }

    // Make API call
    fetch(`/release_notes/${deploymentName}/create_google_doc`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
    .then(response => response.json())
    .then(data => {
        // Re-enable button
        button.disabled = false;
        button.innerHTML = originalContent;

        if (data.success) {
            // Show success modal
            showGoogleDocSuccessModal(data.data.document_url, data.data.document_title);

            // Show success flash message
            showFlashMessage('success', data.data.message);
        } else {
            // Show error message
            showFlashMessage('danger', data.error || 'Failed to create Google Doc');
        }
    })
    .catch(error => {
        console.error('Error creating Google Doc:', error);
        button.disabled = false;
        button.innerHTML = originalContent;
        showFlashMessage('danger', 'An error occurred while creating the Google Doc');
    });
}

/**
 * Show Google Doc success modal
 */
function showGoogleDocSuccessModal(docUrl, docTitle) {
    const modal = new bootstrap.Modal(document.getElementById('googleDocSuccessModal'));
    const linkElement = document.getElementById('googleDocLink');
    const textElement = document.getElementById('googleDocText');

    // Set the document URL and title
    linkElement.href = docUrl;
    textElement.textContent = docTitle;

    // Show the modal
    modal.show();
}

/**
 * Show flash message
 */
function showFlashMessage(type, message) {
    const flashContainer = document.getElementById('flash-messages');

    if (!flashContainer) {
        console.warn('Flash messages container not found');
        return;
    }

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.role = 'alert';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    flashContainer.appendChild(alertDiv);

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
        alertDiv.classList.remove('show');
        setTimeout(() => alertDiv.remove(), 150);
    }, 5000);
}
