/**
 * Deployment MR Creation functionality for Release Notes page
 */

document.addEventListener('DOMContentLoaded', function() {
    const createMrBtn = document.getElementById('createMrBtn');
    const deploymentMrModal = new bootstrap.Modal(document.getElementById('deploymentMrModal'));

    if (createMrBtn) {
        createMrBtn.addEventListener('click', function() {
            const deploymentName = this.dataset.deploymentName;
            const currentCommit = this.dataset.currentCommit;
            const newCommit = this.dataset.newCommit;

            // Show modal and loading state
            deploymentMrModal.show();
            showModalState('loading');

            // Make API call to preview MR
            const previewUrl = `/release_notes/${deploymentName}/preview_mr?current_commit=${currentCommit}&new_commit=${newCommit}`;

            fetch(previewUrl)
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // First restore the original modal content structure (in case it was in VPN error state)
                        restoreOriginalModalContent();
                        // Then populate it with data
                        populateModalContent(data.data);
                        showModalState('content');
                    } else {
                        // Check if this is a VPN connectivity issue
                        if (data.error_type === 'vpn_required') {
                            showVpnError(data.error);
                        } else {
                            showModalError(data.error);
                        }
                    }
                })
                .catch(error => {
                    console.error('Error fetching MR preview:', error);

                    // Check if this looks like a VPN/network connectivity issue
                    const errorStr = error.toString().toLowerCase();
                    if (errorStr.includes('failed to fetch') ||
                        errorStr.includes('network error') ||
                        errorStr.includes('connection') ||
                        error.name === 'TypeError' ||
                        !navigator.onLine) {
                        showVpnError('Network connection failed. Please ensure you are connected to the company VPN.');
                    } else {
                        showModalError('Failed to fetch deployment information. Please try again.');
                    }
                });
        });
    }

    function showModalState(state) {
        const loadingDiv = document.getElementById('mrModalLoading');
        const contentDiv = document.getElementById('mrModalContent');
        const errorDiv = document.getElementById('mrModalError');
        const confirmBtn = document.getElementById('confirmCreateMr');

        // Hide all states
        loadingDiv.style.display = 'none';
        contentDiv.style.display = 'none';
        errorDiv.style.display = 'none';
        confirmBtn.style.display = 'none';

        // Show selected state
        if (state === 'loading') {
            loadingDiv.style.display = 'block';
        } else if (state === 'content') {
            contentDiv.style.display = 'block';
            confirmBtn.style.display = 'inline-block';
        } else if (state === 'error') {
            errorDiv.style.display = 'block';
        }
    }

    function populateModalContent(data) {
        document.getElementById('branchName').textContent = data.branch_name;
        document.getElementById('mrTitle').textContent = data.mr_title;
        // Extract just the filename from the full path
        const fileName = data.deploy_file_path.split('/').pop();
        document.getElementById('deployFileName').textContent = fileName;

        // Construct the full GitLab URL to the deployment file
        const deployFileUrl = `https://gitlab.cee.redhat.com/service/app-interface/-/blob/master/${data.deploy_file_path}`;
        document.getElementById('deployFileLink').href = deployFileUrl;
        document.getElementById('currentCommit').textContent = data.current_commit;
        document.getElementById('newCommit').textContent = data.new_commit;

        // Update validation status
        const validationStatus = document.getElementById('validationStatus');
        const validationMessage = document.getElementById('validationMessage');

        if (data.validation_success) {
            validationStatus.className = 'alert alert-success';
            validationStatus.style.setProperty('border', 'none', 'important');
            validationStatus.innerHTML = '<i class="bi bi-check-circle me-2"></i><strong>Validation Status:</strong> <span id="validationMessage"></span>';
        } else {
            validationStatus.className = 'alert alert-warning';
            validationStatus.style.setProperty('border', 'none', 'important');
            validationStatus.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i><strong>Validation Status:</strong> <span id="validationMessage"></span>';
        }

        document.getElementById('validationMessage').textContent = data.validation_message;

        // Update GitLab connectivity status
        updateGitlabStatus(data);

        // Update button state based on all checks
        updateCreateMrButtonState(data);
    }

    function updateGitlabStatus(data) {
        const gitlabStatus = document.getElementById('gitlabStatus');
        const gitlabError = document.getElementById('gitlabError');

        if (data.gitlab_connected) {
            gitlabStatus.innerHTML = `
                <i class="bi bi-check-circle text-success me-2"></i>
                <span class="text-success">VPN connected, GitLab API ready</span>
            `;
            gitlabError.style.display = 'none';
        } else {
            gitlabStatus.innerHTML = `
                <i class="bi bi-exclamation-triangle text-warning me-2"></i>
                <span class="text-warning">GitLab connection issue</span>
            `;
            gitlabError.style.display = 'block';
            gitlabError.innerHTML = '<small class="text-danger">' + data.gitlab_error + '</small>';
        }
    }

    function updateCreateMrButtonState(data) {
        const confirmBtn = document.getElementById('confirmCreateMr');

        if (data.validation_success && data.can_create_mr) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '<i class="bi bi-git-merge me-2"></i>Create MR';
            confirmBtn.className = 'btn btn-success';
        } else {
            confirmBtn.disabled = true;
            if (!data.gitlab_connected) {
                confirmBtn.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>VPN Required';
                confirmBtn.className = 'btn btn-warning';
            } else {
                confirmBtn.innerHTML = '<i class="bi bi-exclamation-triangle me-2"></i>Issues Found';
                confirmBtn.className = 'btn btn-secondary';
            }
        }
    }

    function showModalError(errorMessage) {
        document.getElementById('errorMessage').textContent = errorMessage;
        showModalState('error');
    }

    function showVpnError(errorMessage) {
        const contentDiv = document.getElementById('mrModalContent');
        contentDiv.innerHTML = `
            <div class="text-center py-4">
                <i class="bi bi-wifi-off text-warning" style="font-size: 3rem;"></i>
                <h4 class="mt-3 text-warning">VPN Connection Required</h4>
                <p class="text-muted mb-4">You need to be connected to the company VPN to access GitLab and create deployment MRs.</p>
                <div class="card border-0 bg-light mb-3">
                    <div class="card-body">
                        <h6 class="card-title text-dark">
                            <i class="bi bi-info-circle me-2"></i>
                            Next steps:
                        </h6>
                        <ol class="mb-0" style="list-style-position: inside; padding-left: 0; margin-left: 0;">
                            <li style="padding-left: 0; margin-bottom: 0.25rem;">Connect to the company VPN</li>
                            <li style="padding-left: 0; margin-bottom: 0;">Click "Retry" below to try again</li>
                        </ol>
                    </div>
                </div>
                <button type="button" class="btn btn-primary" id="retryConnectionBtn">
                    <i class="bi bi-arrow-clockwise me-2"></i>
                    Retry Connection
                </button>
            </div>
        `;
        showModalState('content');

        // Hide the Create MR button for VPN errors
        const confirmBtn = document.getElementById('confirmCreateMr');
        confirmBtn.style.display = 'none';

        // Add event listener for retry button
        document.getElementById('retryConnectionBtn').addEventListener('click', function() {
            retryMrPreview();
        });
    }

    function restoreOriginalModalContent() {
        const contentDiv = document.getElementById('mrModalContent');
        contentDiv.innerHTML = `
            <h6 class="mb-3">
                <i class="bi bi-info-circle me-2"></i>
                Deployment MR Preview
            </h6>

            <div class="card border-0 bg-light mb-3">
                <div class="card-body">
                    <div class="row">
                        <div class="col-md-6">
                            <p class="mb-1"><strong>Branch name:</strong></p>
                            <code id="branchName" class="small"></code>
                            <p class="mb-1 mt-2"><strong>File:</strong></p>
                            <a id="deployFileLink" href="#" target="_blank" rel="noopener noreferrer" style="text-decoration: underline;">
                                <code id="deployFileName" class="small"></code>
                            </a>
                        </div>
                        <div class="col-md-6">
                            <p class="mb-1"><strong>Current PROD commit:</strong></p>
                            <code id="currentCommit" class="small"></code>
                            <p class="mb-1 mt-2"><strong>New PROD commit:</strong></p>
                            <code id="newCommit" class="small"></code>
                        </div>
                    </div>
                    <div class="row mt-2">
                        <div class="col-12">
                            <p class="mb-1"><strong>MR title:</strong></p>
                            <code id="mrTitle" class="small"></code>
                        </div>
                    </div>
                </div>
            </div>

            <div id="validationStatus" class="alert alert-success" role="alert" style="border: none !important;">
                <i class="bi bi-check-circle me-2"></i>
                <strong>Validation Status:</strong> <span id="validationMessage">All checks passed!</span>
            </div>

            <!-- GitLab Connectivity Status -->
            <div class="card border-0 bg-light mb-3">
                <div class="card-body">
                    <h6 class="card-title">GitLab Connectivity</h6>
                    <div id="gitlabStatus" class="d-flex align-items-center">
                        <div class="spinner-border spinner-border-sm text-muted me-2" role="status">
                            <span class="visually-hidden">Checking...</span>
                        </div>
                        <span class="text-muted">Checking VPN connection...</span>
                    </div>
                    <div id="gitlabError" style="display: none;" class="mt-2">
                        <small class="text-danger"></small>
                    </div>
                </div>
            </div>
        `;
    }

    function retryMrPreview() {
        // Show loading state
        showModalState('loading');

        // Get the same data as the original request
        const deploymentName = createMrBtn.dataset.deploymentName;
        const currentCommit = createMrBtn.dataset.currentCommit;
        const newCommit = createMrBtn.dataset.newCommit;

        // Retry the same API call
        const previewUrl = `/release_notes/${deploymentName}/preview_mr?current_commit=${currentCommit}&new_commit=${newCommit}`;

        fetch(previewUrl)
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // First restore the original modal content structure
                    restoreOriginalModalContent();
                    // Then populate it with data
                    populateModalContent(data.data);
                    showModalState('content');
                } else {
                    // Check if this is still a VPN connectivity issue
                    if (data.error_type === 'vpn_required') {
                        showVpnError(data.error);
                    } else {
                        showModalError(data.error);
                    }
                }
            })
            .catch(error => {
                console.error('Error retrying MR preview:', error);

                // Check if this looks like a VPN/network connectivity issue
                const errorStr = error.toString().toLowerCase();
                if (errorStr.includes('failed to fetch') ||
                    errorStr.includes('network error') ||
                    errorStr.includes('connection') ||
                    error.name === 'TypeError' ||
                    !navigator.onLine) {
                    showVpnError('Network connection failed. Please ensure you are connected to the company VPN.');
                } else {
                    showModalError('Failed to fetch deployment information. Please try again.');
                }
            });
    }

    // Add MR creation functionality
    document.getElementById('confirmCreateMr').addEventListener('click', function() {
        const deploymentName = createMrBtn.dataset.deploymentName;
        const currentCommit = createMrBtn.dataset.currentCommit;
        const newCommit = createMrBtn.dataset.newCommit;

        // Show creating state
        this.disabled = true;
        this.innerHTML = '<div class="spinner-border spinner-border-sm me-2" role="status"><span class="visually-hidden">Creating...</span></div>Creating MR...';

        // Create the MR
        fetch(`/release_notes/${deploymentName}/create_mr`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                current_commit: currentCommit,
                new_commit: newCommit
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showMrCreatedSuccess(data.data);
            } else {
                showMrCreationError(data.error);
            }
        })
        .catch(error => {
            console.error('Error creating MR:', error);
            showMrCreationError('Failed to create MR. Please try again.');
        });
    });

    function showMrCreatedSuccess(data) {
        const contentDiv = document.getElementById('mrModalContent');

        // Check if this is a direct MR URL or a creation URL
        const isCreationUrl = data.mr_url && data.mr_url.includes('/merge_requests/new');

        if (isCreationUrl) {
            // Manual MR creation workflow
            contentDiv.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-check-circle text-success" style="font-size: 3rem;"></i>
                    <h4 class="mt-3 text-success">Merge request data prepared successfully!</h4>
                    <p class="text-muted mb-4">File updated with new commit reference.</p>
                    <div class="d-grid gap-2">
                        <a href="${data.mr_url}" target="_blank" class="btn btn-primary">
                            <i class="bi bi-git-merge me-2"></i>
                            Click here to create the MR
                        </a>
                    </div>
                    <small class="text-muted mt-3 d-block">
                        GitLab will open with all fields pre-filled. Just review and create!
                    </small>
                </div>
            `;
        } else {
            // Automatic MR creation (if we ever get this working)
            contentDiv.innerHTML = `
                <div class="text-center py-4">
                    <i class="bi bi-check-circle text-success" style="font-size: 3rem;"></i>
                    <h4 class="mt-3 text-success">MR Created Successfully!</h4>
                    <p class="text-muted mb-4">${data.message}</p>
                    <div class="d-grid gap-2">
                        <a href="${data.mr_url}" target="_blank" class="btn btn-primary">
                            <i class="bi bi-box-arrow-up-right me-2"></i>
                            View MR in GitLab
                        </a>
                    </div>
                </div>
            `;
        }

        // Update button in footer
        const confirmBtn = document.getElementById('confirmCreateMr');
        confirmBtn.style.display = 'none';
    }

    function showMrCreationError(errorMessage) {
        const validationStatus = document.getElementById('validationStatus');
        validationStatus.className = 'alert alert-danger';
        validationStatus.style.setProperty('border', 'none', 'important');
        validationStatus.innerHTML = `
            <i class="bi bi-exclamation-triangle me-2"></i>
            <strong>MR Creation Failed:</strong> ${errorMessage}
        `;

        // Reset button
        const confirmBtn = document.getElementById('confirmCreateMr');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = '<i class="bi bi-git-merge me-2"></i>Retry Create MR';
        confirmBtn.className = 'btn btn-danger';
    }

    // Fix modal backdrop issue - clean up when modal is hidden
    document.getElementById('deploymentMrModal').addEventListener('hidden.bs.modal', function (event) {
        // Remove any leftover backdrops
        const backdrops = document.querySelectorAll('.modal-backdrop');
        backdrops.forEach(backdrop => backdrop.remove());

        // Reset body classes that might be stuck
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';

        // Fix aria-hidden issue
        const modal = event.target;
        modal.removeAttribute('aria-hidden');
        modal.style.display = 'none';

        // Reset modal state to loading for next time
        showModalState('loading');
    });
});
