/**
 * Release Process Management
 * Handles creation of release processes and navigation
 */

/**
 * Gather release notes data from the current page
 */
function gatherReleaseNotesData(deploymentName, toCommit) {
    // Check if we're on the release notes page
    const releaseNotesContainer = document.getElementById('releaseNotes');
    if (!releaseNotesContainer) {
        return null; // Not on release notes page
    }

    // Count PRs in scope
    const scopeSection = releaseNotesContainer.querySelector('div h2:nth-of-type(4)');
    let prCount = 0;
    if (scopeSection && scopeSection.nextElementSibling) {
        const prList = scopeSection.nextElementSibling.nextElementSibling;
        if (prList && prList.tagName === 'UL') {
            prCount = prList.querySelectorAll('li').length;
        }
    }

    // Build release notes URL
    const url = window.location.origin + window.location.pathname +
                (toCommit ? `?up_to_pr=${toCommit}` : '');

    return {
        pr_count: prCount,
        url: url
    };
}

// Start Release Process button handler
document.addEventListener('DOMContentLoaded', function() {
    const startProcessBtn = document.getElementById('start_release_process');

    if (startProcessBtn) {
        const deploymentName = startProcessBtn.getAttribute('data-deployment-name');
        const fromCommit = startProcessBtn.getAttribute('data-from-commit');
        const toCommit = startProcessBtn.getAttribute('data-to-commit');

        // Check if an active process exists for this commit range
        checkForExistingProcess(deploymentName, fromCommit, toCommit, startProcessBtn);

        // Original click handler for starting new process
        startProcessBtn.addEventListener('click', function() {
            // Show confirmation dialog with option to include JIRA
            showStartProcessModal(deploymentName, fromCommit, toCommit);
        });
    }
});

/**
 * Check if an active process exists and replace button if needed
 */
function checkForExistingProcess(deploymentName, fromCommit, toCommit, button) {
    fetch(`/release_processes/check_existing?deployment=${deploymentName}&from_commit=${fromCommit}&to_commit=${toCommit}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.exists) {
                // Replace button with "View Active Process"
                button.className = 'btn btn-info btn-sm';
                button.innerHTML = '<i class="bi bi-arrow-right-circle me-1"></i>View Active Process';

                // Remove old event listeners by cloning
                const newButton = button.cloneNode(true);
                button.parentNode.replaceChild(newButton, button);

                // Add new click handler to navigate to process
                newButton.addEventListener('click', function(e) {
                    e.preventDefault();
                    window.location.href = data.process_url;
                });

                // Update tooltip
                newButton.title = `Go to active release process for ${fromCommit.substring(0, 7)}...${toCommit.substring(0, 7)}`;
            }
            // If no process exists, keep the original "Start Process" button
        })
        .catch(error => {
            console.error('Error checking for existing process:', error);
            // On error, keep the original button behavior
        });
}

function showStartProcessModal(deploymentName, fromCommit, toCommit) {
    // Create a Bootstrap modal
    const modalHtml = `
        <div class="modal fade" id="startProcessModal" tabindex="-1">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">
                            <i class="bi bi-play-circle me-2"></i>Start Release Process
                        </h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body">
                        <p><strong>Deployment:</strong> ${deploymentName.toUpperCase()}</p>
                        <p><strong>Commit Range:</strong> <code>${fromCommit.substring(0, 7)}</code> → <code>${toCommit.substring(0, 7)}</code></p>

                        <div class="alert alert-info">
                            <i class="bi bi-info-circle me-2"></i>
                            This will create a guided release process that tracks all steps.
                        </div>

                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" id="includeJira" checked>
                            <label class="form-check-label" for="includeJira">
                                Include JIRA ticket step (optional)
                            </label>
                        </div>

                        <div id="process-error" class="alert alert-danger mt-3" style="display: none;"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-success" id="confirmStartProcess">
                            <i class="bi bi-play-circle me-1"></i>Start Process
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Remove existing modal if any
    const existingModal = document.getElementById('startProcessModal');
    if (existingModal) {
        existingModal.remove();
    }

    // Add modal to body
    document.body.insertAdjacentHTML('beforeend', modalHtml);

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('startProcessModal'));
    modal.show();

    // Handle confirm button
    document.getElementById('confirmStartProcess').addEventListener('click', function() {
        const includeJira = document.getElementById('includeJira').checked;
        const errorDiv = document.getElementById('process-error');
        const btn = this;

        // Disable button and show loading
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Creating...';
        errorDiv.style.display = 'none';

        // Gather release notes data if on release notes page
        const releaseNotesData = gatherReleaseNotesData(deploymentName, toCommit);

        // Create process
        fetch('/release_processes/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                deployment_name: deploymentName,
                from_commit: fromCommit,
                to_commit: toCommit,
                enable_jira: includeJira,
                release_notes_data: releaseNotesData
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Redirect to process page
                window.location.href = data.redirect_url;
            } else {
                errorDiv.textContent = data.error || 'Failed to create process';
                errorDiv.style.display = 'block';
                btn.disabled = false;
                btn.innerHTML = '<i class="bi bi-play-circle me-1"></i>Start Process';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            errorDiv.textContent = 'An error occurred while creating the process';
            errorDiv.style.display = 'block';
            btn.disabled = false;
            btn.innerHTML = '<i class="bi bi-play-circle me-1"></i>Start Process';
        });
    });
}
