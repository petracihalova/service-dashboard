/**
 * BackOffice Proxy Token Management and Release Scope
 *
 * Handles token updates for OpenShift API access and release scope viewing
 */

document.addEventListener('DOMContentLoaded', function() {
    loadTokenStatus();

    const saveTokensBtn = document.getElementById('saveTokensBtn');
    if (saveTokensBtn) {
        saveTokensBtn.addEventListener('click', updateTokens);
    }

    const updateDataBtn = document.getElementById('updateDataBtn');
    if (updateDataBtn) {
        updateDataBtn.addEventListener('click', () => loadDeploymentData(false));
    }

    // Try to load cached data on page load
    loadCachedDeploymentData();
});

/**
 * Load cached deployment data on page load
 */
async function loadCachedDeploymentData() {
    try {
        const response = await fetch('/backoffice-proxy/deployment-info/cached');

        if (response.status === 404) {
            // No cached data, show initial state
            console.log('No cached data available');
            return;
        }

        const data = await response.json();

        if (data && !data.error) {
            // Hide initial state and show cached data
            document.getElementById('initialState').classList.add('d-none');
            document.getElementById('deploymentData').classList.remove('d-none');

            // Render deployment data
            renderDeploymentData(data);

            // Show last updated info if available
            if (data.last_updated) {
                const lastUpdated = new Date(data.last_updated);
                const formattedDate = lastUpdated.toLocaleString();
                showDataInfo(`Data loaded from cache (last updated: ${formattedDate})`);
            }
        }
    } catch (error) {
        console.error('Error loading cached data:', error);
        // Silently fail, user can click "Update Data"
    }
}

/**
 * Load fresh deployment data from the API
 */
async function loadDeploymentData(isAutoRefresh = false) {
    const btn = document.getElementById('updateDataBtn');
    const initialState = document.getElementById('initialState');
    const loadingState = document.getElementById('loadingState');
    const errorState = document.getElementById('errorState');
    const deploymentData = document.getElementById('deploymentData');

    // Show loading
    initialState.classList.add('d-none');
    errorState.classList.add('d-none');
    deploymentData.classList.add('d-none');
    loadingState.classList.remove('d-none');
    btn.disabled = true;

    try {
        const response = await fetch('/backoffice-proxy/deployment-info');
        const data = await response.json();

        loadingState.classList.add('d-none');
        btn.disabled = false;

        // If status is 206, we have cached data but update failed
        if (response.status === 206 || data.update_error) {
            // Render cached data
            renderDeploymentData(data);
            deploymentData.classList.remove('d-none');

            // Show VPN/Token warning
            document.getElementById('vpnTokenWarning').classList.remove('d-none');

            // Show warning message about failed update
            const lastUpdated = data.last_updated ? new Date(data.last_updated).toLocaleString() : 'unknown';
            showDataInfo(
                `⚠️ Could not fetch new data (VPN required?). Showing cached data from ${lastUpdated}`,
                'warning'
            );
            return;
        }

        if (data.error && !data.repo) {
            // No cached data available
            // Show VPN/Token warning
            document.getElementById('vpnTokenWarning').classList.remove('d-none');

            errorState.querySelector('#errorMessage').textContent = data.error;
            errorState.classList.remove('d-none');
            return;
        }

        // Render deployment data
        renderDeploymentData(data);
        deploymentData.classList.remove('d-none');

        // Hide VPN/Token warning on successful update
        document.getElementById('vpnTokenWarning').classList.add('d-none');

        // Show success message with timestamp
        if (data.last_updated) {
            const lastUpdated = new Date(data.last_updated);
            const formattedDate = lastUpdated.toLocaleString();
            showDataInfo(`Data updated successfully (${formattedDate})`, 'success');
        }

    } catch (error) {
        console.error('Error loading deployment data:', error);
        loadingState.classList.add('d-none');
        btn.disabled = false;

        // Show VPN/Token warning on network error
        document.getElementById('vpnTokenWarning').classList.remove('d-none');

        errorState.querySelector('#errorMessage').textContent = 'Failed to load deployment data. Please try again.';
        errorState.classList.remove('d-none');
    }
}

/**
 * Show data info message
 */
function showDataInfo(message, type = 'info') {
    // Remove any existing info messages first
    const existingAlerts = document.querySelectorAll('.alert.data-info-alert');
    existingAlerts.forEach(alert => alert.remove());

    // Choose icon based on type
    let icon = 'info-circle';
    if (type === 'success') icon = 'check-circle';
    if (type === 'warning') icon = 'exclamation-triangle';
    if (type === 'danger') icon = 'x-circle';

    const infoDiv = document.createElement('div');
    infoDiv.className = `alert alert-${type} alert-dismissible fade show mt-3 data-info-alert`;
    infoDiv.innerHTML = `
        <i class="bi bi-${icon} me-2"></i>
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;

    // Insert at the top, right after the VPN warning
    const vpnWarning = document.getElementById('vpnTokenWarning');
    if (vpnWarning && vpnWarning.parentNode) {
        vpnWarning.insertAdjacentElement('afterend', infoDiv);
    } else {
        // Fallback: insert at the beginning of container-fluid
        const container = document.querySelector('.container-fluid');
        if (container) {
            const firstChild = container.firstElementChild;
            if (firstChild) {
                firstChild.insertAdjacentElement('afterend', infoDiv);
            }
        }
    }

    // Auto-remove after 8 seconds for warnings, 5 for others
    const timeout = type === 'warning' ? 8000 : 5000;
    setTimeout(() => {
        if (infoDiv.parentNode) {
            infoDiv.remove();
        }
    }, timeout);
}

// Store deployment data globally for access by other functions
let cachedDeploymentData = null;

/**
 * Render deployment data into the page
 */
function renderDeploymentData(deployment) {
    // Store for later use
    cachedDeploymentData = deployment;

    // Update related links
    renderRelatedLinks(deployment.links);

    // Update default branch commit
    renderDefaultBranchCommit(deployment);

    // Update stage and prod environments
    renderEnvironment('stage', deployment.stage, deployment);
    renderEnvironment('prod', deployment.prod, deployment);

    // Auto-display MR scopes if they exist in cached data (only prod, stage is always in sync)
    if (deployment.prod_scope) {
        displayCachedScope('prod', deployment.prod_scope);
    }

    // Load and display open MRs
    loadOpenMRs();
}

/**
 * Render default branch commit section
 */
function renderDefaultBranchCommit(deployment) {
    const container = document.querySelector('[data-section="default-branch"]');
    if (!container) return;

    if (deployment.default_branch_commit) {
        const commitShort = deployment.default_branch_commit.substring(0, 7);
        container.innerHTML = `
            <p class="mb-0">
                <strong>Latest Commit:</strong>
                <code>${commitShort}</code>
                <a href="${deployment.repo}/commit/${deployment.default_branch_commit}"
                   target="_blank" rel="noopener noreferrer" class="ms-2">
                    <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </p>
        `;
    } else {
        container.innerHTML = `
            <p class="text-muted mb-0">
                <i class="bi bi-exclamation-circle me-1"></i>
                Unable to fetch commit info (VPN required)
            </p>
        `;
    }
}

/**
 * Render environment (stage or prod) section
 */
function renderEnvironment(envType, envData, deployment) {
    const container = document.querySelector(`[data-section="${envType}-env"]`);
    if (!container) return;

    if (envData.commit) {
        let html = `
            <p class="mb-2">
                <strong>Commit:</strong>
                <code>${envData.commit}</code>
                <a href="${deployment.repo}/commit/${envData.commit}"
                   target="_blank" rel="noopener noreferrer" class="ms-2">
                    <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </p>
        `;

        if (envData.image) {
            // Extract commit ref from image tag (format: image:062df42-hash)
            const imageTag = envData.image.split(':')[1] || '';
            const commitRef = imageTag.split('-')[0];
            const commitUrl = commitRef ? `${deployment.repo}/commit/${commitRef}` : '';

            html += `
                <p class="mb-2">
                    <strong>Image:</strong>
                    <code class="text-break">${envData.image}</code>
                    ${commitRef ? `<a href="${commitUrl}" target="_blank" rel="noopener noreferrer" class="ms-2">
                        <i class="bi bi-box-arrow-up-right"></i>
                    </a>` : ''}
                </p>
            `;
        }

        // Only show diff for production (stage auto-deploys from master)
        if (deployment.default_branch_commit && envType === 'prod') {
            html += `
                <p class="mb-2">
                    <strong>Master/Prod Diff:</strong>
                    <a href="${deployment.repo}/compare/${envData.commit}...${deployment.default_branch_commit}"
                       target="_blank" rel="noopener noreferrer">
                        View Diff
                    </a>
                </p>
            `;
        }

        html += `
            <p class="mb-0">
                <strong>OpenShift:</strong>
                <a href="${envData.console_url}" target="_blank" rel="noopener noreferrer">
                    Link
                </a>
            </p>
        `;

        container.innerHTML = html;
    } else {
        container.innerHTML = `
            <p class="text-muted mb-2">
                <i class="bi bi-exclamation-circle me-1"></i>
                Unable to fetch deployment info (VPN/Token required)
            </p>
            <p class="mb-0">
                <strong>OpenShift:</strong>
                <a href="${envData.console_url}" target="_blank" rel="noopener noreferrer">
                    Link
                </a>
            </p>
        `;
    }
}

/**
 * Display cached MR scope data
 */
function displayCachedScope(envType, scopeData) {
    const section = document.getElementById(`${envType}MrsSection`);
    const content = document.getElementById(`${envType}MrsContent`);

    if (!section || !content) return;

    // Update summary
    document.getElementById(`${envType}ScopeFromCommit`).textContent = scopeData.from_commit_short;
    document.getElementById(`${envType}ScopeToCommit`).textContent = scopeData.to_commit_short;
    document.getElementById(`${envType}ScopeTotalCommits`).textContent = scopeData.total_commits;
    document.getElementById(`${envType}ScopeTotalMrs`).textContent = scopeData.total_mrs;

    // Display document link if it exists
    if (scopeData.document_url) {
        const linkContainer = document.getElementById(`${envType}ScopeDocumentLink`);
        const linkElement = document.getElementById(`${envType}ScopeDocumentUrl`);
        if (linkContainer && linkElement) {
            linkElement.href = scopeData.document_url;
            linkContainer.classList.remove('d-none');
        }
    } else {
        const linkContainer = document.getElementById(`${envType}ScopeDocumentLink`);
        if (linkContainer) {
            linkContainer.classList.add('d-none');
        }
    }

    // Display MRs
    displayMergeRequests(scopeData.merge_requests, `${envType}MergeRequestsList`);

    // Show the section
    section.classList.remove('d-none');
    content.classList.remove('d-none');
}

/**
 * Render related links section
 */
function renderRelatedLinks(links) {
    const container = document.querySelector('[data-section="related-links"]');
    if (!container) return;

    if (!links || links.length === 0) {
        container.parentElement.classList.add('d-none');
        return;
    }

    container.parentElement.classList.remove('d-none');

    // Create inline list with bullet separators
    const linkElements = links.map(link =>
        `<a href="${link.url}" target="_blank" rel="noopener noreferrer">${link.name}</a>`
    );

    container.innerHTML = linkElements.join(' <span class="text-muted">•</span> ');
}

/**
 * Show release scope (MRs) between two commits (prod only, stage is automatic)
 */
async function showReleaseScope(environment, fromCommit, toCommit) {
    // Only prod environment is supported (stage auto-deploys from master)
    const section = document.getElementById('prodMrsSection');
    const loading = document.getElementById('prodMrsLoading');
    const error = document.getElementById('prodMrsError');
    const content = document.getElementById('prodMrsContent');

    // Show section and loading
    section.classList.remove('d-none');
    error.classList.add('d-none');
    content.classList.add('d-none');

    // Scroll to section
    section.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    // Check if we have cached scope data
    if (cachedDeploymentData && cachedDeploymentData.prod_scope) {
        const data = cachedDeploymentData.prod_scope;

        // Update summary
        document.getElementById('prodScopeFromCommit').textContent = data.from_commit_short;
        document.getElementById('prodScopeToCommit').textContent = data.to_commit_short;
        document.getElementById('prodScopeTotalCommits').textContent = data.total_commits;
        document.getElementById('prodScopeTotalMrs').textContent = data.total_mrs;

        // Display MRs
        displayMergeRequests(data.merge_requests, 'prodMergeRequestsList');

        content.classList.remove('d-none');
        return;
    }

    // No cached data, fetch from API
    loading.classList.remove('d-none');

    try {
        const response = await fetch(
            `/backoffice-proxy/release-scope?from_commit=${fromCommit}&to_commit=${toCommit}`
        );
        const data = await response.json();

        loading.classList.add('d-none');

        if (data.error) {
            error.textContent = data.error;
            error.classList.remove('d-none');
            return;
        }

        // Update summary
        document.getElementById('prodScopeFromCommit').textContent = data.from_commit_short;
        document.getElementById('prodScopeToCommit').textContent = data.to_commit_short;
        document.getElementById('prodScopeTotalCommits').textContent = data.total_commits;
        document.getElementById('prodScopeTotalMrs').textContent = data.total_mrs;

        // Display MRs
        displayMergeRequests(data.merge_requests, 'prodMergeRequestsList');

        content.classList.remove('d-none');

    } catch (err) {
        console.error('Error fetching release scope:', err);
        loading.classList.add('d-none');
        error.textContent = 'Failed to fetch release scope. Please try again.';
        error.classList.remove('d-none');
    }
}

/**
 * Display merge requests in the list
 */
function displayMergeRequests(mergeRequests, targetContainerId = 'mergeRequestsList') {
    const listContainer = document.getElementById(targetContainerId);

    if (!mergeRequests || mergeRequests.length === 0) {
        listContainer.innerHTML = '<p class="text-muted">No merge requests found in this scope.</p>';
        return;
    }

    let html = '<div class="list-group">';

    mergeRequests.forEach(mr => {
        const mrUrl = mr.web_url;
        const mrTitle = mr.title;
        const mrIid = mr.iid;
        const mrState = mr.state;
        const mrAuthor = mr.author ? mr.author.name : 'Unknown';
        const mrCreatedAt = new Date(mr.created_at).toLocaleDateString();
        const mrMergedAt = mr.merged_at ? new Date(mr.merged_at).toLocaleDateString() : null;

        // Determine badge color based on state
        let stateBadge = '';
        if (mrState === 'merged') {
            stateBadge = '<span class="badge bg-success">Merged</span>';
        } else if (mrState === 'opened') {
            stateBadge = '<span class="badge bg-warning">Open</span>';
        } else if (mrState === 'closed') {
            stateBadge = '<span class="badge bg-secondary">Closed</span>';
        }

        html += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <a href="${mrUrl}" target="_blank" rel="noopener noreferrer" class="text-decoration-none">
                                !${mrIid}: ${mrTitle}
                                <i class="bi bi-box-arrow-up-right ms-1 small"></i>
                            </a>
                        </h6>
                        <p class="mb-1 small text-muted">
                            <i class="bi bi-person me-1"></i>${mrAuthor}
                            <span class="ms-2"><i class="bi bi-calendar me-1"></i>Created: ${mrCreatedAt}</span>
                            ${mrMergedAt ? `<span class="ms-2"><i class="bi bi-check-circle me-1"></i>Merged: ${mrMergedAt}</span>` : ''}
                        </p>
                    </div>
                    <div class="ms-3">
                        ${stateBadge}
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    listContainer.innerHTML = html;
}

/**
 * Load and display open MRs
 */
async function loadOpenMRs() {
    const section = document.getElementById('openMrsSection');
    const loading = document.getElementById('openMrsLoading');
    const error = document.getElementById('openMrsError');
    const content = document.getElementById('openMrsContent');
    const totalSpan = document.getElementById('openMrsTotal');
    const listContainer = document.getElementById('openMergeRequestsList');

    if (!section) return;

    // Show section and loading
    section.classList.remove('d-none');
    loading.classList.remove('d-none');
    error.classList.add('d-none');
    content.classList.add('d-none');

    try {
        const response = await fetch('/backoffice-proxy/open-mrs');
        const data = await response.json();

        loading.classList.add('d-none');

        if (data.error) {
            error.textContent = data.error;
            error.classList.remove('d-none');
            return;
        }

        // Update total count
        totalSpan.textContent = data.total;

        // Display open MRs
        if (!data.open_mrs || data.open_mrs.length === 0) {
            listContainer.innerHTML = '<p class="text-muted mb-0">No open merge requests.</p>';
        } else {
            displayOpenMRs(data.open_mrs);
        }

        content.classList.remove('d-none');

    } catch (err) {
        console.error('Error loading open MRs:', err);
        loading.classList.add('d-none');
        error.textContent = 'Failed to load open MRs. Please try again.';
        error.classList.remove('d-none');
    }
}

/**
 * Display open MRs in the list
 */
function displayOpenMRs(openMrs) {
    const listContainer = document.getElementById('openMergeRequestsList');

    let html = '<div class="list-group">';

    openMrs.forEach(mr => {
        const mrUrl = mr.html_url;
        const mrTitle = mr.title;
        const mrNumber = mr.number;
        const mrAuthor = mr.user_login || 'Unknown';
        const mrCreatedAt = new Date(mr.created_at).toLocaleDateString();
        const isDraft = mr.draft;

        const draftBadge = isDraft ? '<span class="badge bg-secondary ms-2">Draft</span>' : '';

        html += `
            <div class="list-group-item">
                <div class="d-flex w-100 justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <h6 class="mb-1">
                            <a href="${mrUrl}" target="_blank" rel="noopener noreferrer" class="text-decoration-none">
                                !${mrNumber}: ${mrTitle}
                                <i class="bi bi-box-arrow-up-right ms-1 small"></i>
                            </a>
                            ${draftBadge}
                        </h6>
                        <p class="mb-1 small text-muted">
                            <i class="bi bi-person me-1"></i>${mrAuthor}
                            <span class="ms-2"><i class="bi bi-calendar me-1"></i>Created: ${mrCreatedAt}</span>
                        </p>
                    </div>
                    <div class="ms-3">
                        <span class="badge bg-warning">Open</span>
                    </div>
                </div>
            </div>
        `;
    });

    html += '</div>';
    listContainer.innerHTML = html;
}

/**
 * Load current token status
 */
async function loadTokenStatus() {
    try {
        const response = await fetch('/backoffice-proxy/tokens');
        const data = await response.json();

        // Update status indicators
        const prodStatus = document.getElementById('prodTokenStatus');
        const stageStatus = document.getElementById('stageTokenStatus');

        if (data.prod_configured) {
            prodStatus.innerHTML = '<span class="badge bg-success">✓ Configured</span>';
            prodStatus.title = `Current: ${data.prod_preview}`;
        } else {
            prodStatus.innerHTML = '<span class="badge bg-warning text-dark">⚠ Not Set</span>';
        }

        if (data.stage_configured) {
            stageStatus.innerHTML = '<span class="badge bg-success">✓ Configured</span>';
            stageStatus.title = `Current: ${data.stage_preview}`;
        } else {
            stageStatus.innerHTML = '<span class="badge bg-warning text-dark">⚠ Not Set</span>';
        }

    } catch (error) {
        console.error('Error loading token status:', error);
    }
}

/**
 * Update tokens via API
 */
async function updateTokens() {
    const prodToken = document.getElementById('prodToken').value.trim();
    const stageToken = document.getElementById('stageToken').value.trim();
    const updateEnvFile = document.getElementById('updateEnvFile').checked;

    // Validate that at least one token is provided
    if (!prodToken && !stageToken) {
        showAlert('Please enter at least one token to update.', 'warning');
        return;
    }

    const saveBtn = document.getElementById('saveTokensBtn');
    const originalBtnText = saveBtn.innerHTML;
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Updating...';

    try {
        const response = await fetch('/backoffice-proxy/tokens', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prod_token: prodToken,
                stage_token: stageToken,
                update_env_file: updateEnvFile
            })
        });

        const data = await response.json();

        if (data.success) {
            showAlert(data.message, 'success');

            // Clear input fields after successful update
            document.getElementById('prodToken').value = '';
            document.getElementById('stageToken').value = '';

            // Reload token status
            await loadTokenStatus();

            // Show reload hint if .env was not updated
            if (!updateEnvFile) {
                setTimeout(() => {
                    showAlert('Tokens updated in memory only. They will be lost on application restart unless you update the .env file.', 'warning');
                }, 2000);
            }
        } else {
            showAlert('Error: ' + data.message, 'danger');
        }

    } catch (error) {
        console.error('Error updating tokens:', error);
        showAlert('Failed to update tokens. Please try again.', 'danger');
    } finally {
        saveBtn.disabled = false;
        saveBtn.innerHTML = originalBtnText;
    }
}

/**
 * Show alert message
 */
function showAlert(message, type) {
    const alertDiv = document.getElementById('tokenAlert');
    alertDiv.className = `alert alert-${type}`;
    alertDiv.textContent = message;
    alertDiv.classList.remove('d-none');

    // Auto-hide after 5 seconds for success messages
    if (type === 'success') {
        setTimeout(() => {
            alertDiv.classList.add('d-none');
        }, 5000);
    }
}

/**
 * Show release notes modal with preview
 */
function showReleaseNotesModal() {
    if (!cachedDeploymentData || !cachedDeploymentData.prod_scope) {
        alert('No release scope data available. Please update data first.');
        return;
    }

    const scope = cachedDeploymentData.prod_scope;
    const deployment = cachedDeploymentData;

    // Generate preview HTML
    const previewHtml = `
        <div class="mb-3">
            <h6>Deployment Information</h6>
            <ul>
                <li><strong>Repository:</strong> <a href="${deployment.repo}" target="_blank">${deployment.repo}</a></li>
                <li><strong>From Commit:</strong> <code>${scope.from_commit_short}</code></li>
                <li><strong>To Commit:</strong> <code>${scope.to_commit_short}</code></li>
                <li><strong>Total Commits:</strong> ${scope.total_commits}</li>
                <li><strong>Total MRs:</strong> ${scope.total_mrs}</li>
            </ul>
        </div>

        <div class="mb-3">
            <h6>Merge Requests (${scope.merge_requests.length})</h6>
            ${scope.merge_requests && scope.merge_requests.length > 0
                ? generateMRPreviewList(scope.merge_requests)
                : '<p class="text-muted">No merge requests in this scope.</p>'
            }
        </div>
    `;

    document.getElementById('releaseNotesPreview').innerHTML = previewHtml;

    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('releaseNotesModal'));
    modal.show();
}

/**
 * Generate MR preview list HTML
 */
function generateMRPreviewList(mergeRequests) {
    let html = '<ul class="list-group">';

    mergeRequests.forEach(mr => {
        const mrTitle = mr.title || 'Untitled';
        const mrUrl = mr.web_url || '#';
        const mrIid = mr.iid || mr.number || 'N/A';
        const mrAuthor = mr.author ? mr.author.name : 'Unknown';

        html += `
            <li class="list-group-item">
                <strong>!${mrIid}:</strong> ${mrTitle}
                <br>
                <small class="text-muted">Author: ${mrAuthor}</small>
                <a href="${mrUrl}" target="_blank" class="ms-2 small">
                    <i class="bi bi-box-arrow-up-right"></i>
                </a>
            </li>
        `;
    });

    html += '</ul>';
    return html;
}

/**
 * Create Google Doc for BackOffice Proxy release notes
 */
document.getElementById('createGoogleDocBtn').addEventListener('click', async function() {
    if (!cachedDeploymentData || !cachedDeploymentData.prod_scope) {
        alert('No release scope data available.');
        return;
    }

    const btn = this;
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Creating...';

    try {
        const response = await fetch('/backoffice-proxy/create-release-notes', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                deployment_data: cachedDeploymentData,
                scope_data: cachedDeploymentData.prod_scope
            })
        });

        const data = await response.json();

        if (data.error) {
            alert('Error creating Google Doc: ' + data.error);
            btn.disabled = false;
            btn.innerHTML = originalText;
            return;
        }

        if (data.document_url) {
            // Close modal
            bootstrap.Modal.getInstance(document.getElementById('releaseNotesModal')).hide();

            // Reload cached data to get the updated document URL
            await loadCachedDeploymentData();

            // Show success message and open doc
            const message = `Release notes document created successfully!`;
            showDataInfo(message, 'success');

            // Open document in new tab
            window.open(data.document_url, '_blank');
        }

        btn.disabled = false;
        btn.innerHTML = originalText;

    } catch (error) {
        console.error('Error creating Google Doc:', error);
        alert('Failed to create Google Doc: ' + error.message);
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
});

/**
 * Remove document reference from the current scope
 */
async function removeDocumentReference() {
    if (!confirm('Remove the document reference? (The document will not be deleted from Google Drive)')) {
        return;
    }

    try {
        const response = await fetch('/backoffice-proxy/remove-document-reference', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        const data = await response.json();

        if (data.success) {
            // Reload cached data to reflect the removal
            await loadCachedDeploymentData();

            // Show success message
            showDataInfo('Document reference removed successfully', 'success');
        } else {
            alert('Failed to remove document reference: ' + (data.error || 'Unknown error'));
        }

    } catch (error) {
        console.error('Error removing document reference:', error);
        alert('Failed to remove document reference: ' + error.message);
    }
}
