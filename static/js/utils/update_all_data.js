/**
 * Update All Data functionality
 */

class UpdateAllDataManager {
    constructor() {
        this.modal = null;
        this.modalInstance = null;
        this.updateButton = null;
        this.isRunning = false;
        this.currentStep = 0;
        this.totalSteps = 10; // 10 data sources total

        // Data sources configuration (deployments last - most time consuming)
        this.dataSources = [
            { id: 'open-prs', name: 'Open PRs (GitHub + GitLab)', endpoint: '/pull-requests/open?reload_data=1' },
            { id: 'merged-prs', name: 'Merged PRs (GitHub + GitLab)', endpoint: '/pull-requests/merged?reload_data=1' },
            { id: 'closed-prs', name: 'Closed PRs (GitHub + GitLab)', endpoint: '/pull-requests/closed?reload_data=1' },
            { id: 'app-interface-open', name: 'App-interface Open MRs', endpoint: '/pull-requests/app-interface?reload_data=1' },
            { id: 'app-interface-merged', name: 'App-interface Merged MRs', endpoint: '/pull-requests/app-interface-merged?reload_data=1' },
            { id: 'app-interface-closed', name: 'App-interface Closed MRs', endpoint: '/pull-requests/app-interface-closed?reload_data=1' },
            { id: 'jira-open', name: 'JIRA Open Tickets', endpoint: '/jira-tickets/jira-tickets?reload_data=1' },
            { id: 'jira-reported', name: 'JIRA Reported Tickets', endpoint: '/jira-tickets/jira-reported-tickets?reload_data=1' },
            { id: 'jira-closed', name: 'JIRA Closed Tickets', endpoint: '/jira-tickets/jira-closed-tickets?reload_data=1' },
            { id: 'deployments', name: 'Deployments', endpoint: '/deployments/?reload_data=1' }
        ];

        this.init();
    }

    init() {
        // Get DOM elements
        this.updateButton = document.getElementById('updateAllDataBtn');
        this.modal = document.getElementById('updateAllDataModal');

        if (this.updateButton && this.modal) {
            this.updateButton.addEventListener('click', () => this.openModal());

            // Modal event listeners
            const startButton = document.getElementById('startUpdateButton');
            if (startButton) {
                startButton.addEventListener('click', () => this.startUpdate());
            }

            // Setup retry prerequisites button
            const retryButton = document.getElementById('retryPrerequisitesButton');
            if (retryButton) {
                retryButton.addEventListener('click', () => this.retryPrerequisites());
            }

            // Reset modal when hidden
            this.modal.addEventListener('hidden.bs.modal', () => this.resetModal());

            // Setup checkbox event listeners for selection
            this.setupCheckboxListeners();

            // Setup Continue button event listener
            this.setupContinueButton();

            // Initialize button state
            this.updateMainButtonState();
        }
    }

    async openModal() {
        if (this.isRunning) {
            // Don't allow opening modal if update is in progress
            // Button should already be disabled and showing "Updating..." state
            return;
        }

        this.resetModal();

        // Check if enhancement is running before showing modal
        await this.checkEnhancementStatus();

        // Show selection section, hide prerequisites (they'll show after Continue)
        this.showSelectionStep();

        // Create and store modal instance (allow dismissal initially)
        this.modalInstance = new bootstrap.Modal(this.modal, {
            backdrop: true,  // Allow closing by clicking backdrop initially
            keyboard: true   // Allow closing with Escape key initially
        });
        this.modalInstance.show();
    }

    resetModal() {
        // Don't reset modal if update is still running
        if (this.isRunning) {
            return;
        }

        // Reset to selection step (first step)
        this.showSelectionStep();

        // Reset all hidden sections
        document.getElementById('progressSection').classList.add('d-none');
        document.getElementById('completionSection').classList.add('d-none');
        document.getElementById('errorSection').classList.add('d-none');
        document.getElementById('prerequisiteError').classList.add('d-none');

        // Clean up any completion/error messages that were added to progress section
        const progressSection = document.getElementById('progressSection');
        const completionMessages = progressSection.querySelectorAll('.alert');
        completionMessages.forEach(msg => msg.remove());

        // Reset start button for when user gets to prerequisites step
        const startButton = document.getElementById('startUpdateButton');
        if (startButton) {
            startButton.classList.remove('d-none'); // Make sure it's visible again
            startButton.disabled = true;
            startButton.innerHTML = `
                <i class="bi bi-play-fill me-1"></i>
                Start Update
            `;
        }

        // Re-enable modal dismissal
        this.enableModalDismissal();

        // Reset progress
        this.currentStep = 0;
        this.updateOverallProgress();

        // Reset all status indicators
        this.resetStatusIndicators();

        // Reset any visual styling on progress items (remove skipped styling)
        this.dataSources.forEach(source => {
            const progressItem = document.getElementById(`${source.id}-progress`);
            if (progressItem) {
                progressItem.classList.remove('opacity-50');
                progressItem.style.fontStyle = '';
            }
        });

        this.isRunning = false;
    }

    async checkEnhancementStatus() {
        try {
            const response = await fetch('/api/enhance/is-running');
            const status = await response.json();

            const warningDiv = document.getElementById('enhancementWarning');
            const mergedCheckbox = document.getElementById('merged-prs-checkbox');
            const closedCheckbox = document.getElementById('closed-prs-checkbox');
            const selectAllCheckbox = document.getElementById('selectAllDataSources');

            if (status.is_running) {
                // Show warning
                if (warningDiv) {
                    warningDiv.classList.remove('d-none');
                }

                // Disable conflicting checkboxes
                if (mergedCheckbox) {
                    mergedCheckbox.disabled = true;
                    mergedCheckbox.checked = false;
                    const label = mergedCheckbox.closest('.list-group-item');
                    if (label) {
                        label.classList.add('text-muted');
                        label.style.opacity = '0.6';
                    }
                }

                if (closedCheckbox) {
                    closedCheckbox.disabled = true;
                    closedCheckbox.checked = false;
                    const label = closedCheckbox.closest('.list-group-item');
                    if (label) {
                        label.classList.add('text-muted');
                        label.style.opacity = '0.6';
                    }
                }

                // Update "Select All" to reflect that some items are unavailable
                this.updateSelectAllState();
            } else {
                // Hide warning
                if (warningDiv) {
                    warningDiv.classList.add('d-none');
                }

                // Re-enable checkboxes
                if (mergedCheckbox) {
                    mergedCheckbox.disabled = false;
                    const label = mergedCheckbox.closest('.list-group-item');
                    if (label) {
                        label.classList.remove('text-muted');
                        label.style.opacity = '';
                    }
                }

                if (closedCheckbox) {
                    closedCheckbox.disabled = false;
                    const label = closedCheckbox.closest('.list-group-item');
                    if (label) {
                        label.classList.remove('text-muted');
                        label.style.opacity = '';
                    }
                }
            }
        } catch (error) {
            console.error('Error checking enhancement status:', error);
            // If we can't check, assume it's safe and hide warning
            const warningDiv = document.getElementById('enhancementWarning');
            if (warningDiv) {
                warningDiv.classList.add('d-none');
            }
        }
    }

    disableModalDismissal() {
        // Disable close buttons
        const headerCloseButton = this.modal.querySelector('.btn-close');
        const footerCloseButton = document.getElementById('closeButton');

        if (headerCloseButton) {
            headerCloseButton.disabled = true;
            headerCloseButton.style.opacity = '0.3';
            headerCloseButton.style.cursor = 'not-allowed';
        }

        if (footerCloseButton) {
            footerCloseButton.disabled = true;
            footerCloseButton.classList.add('opacity-50'); // Visual indication it's disabled
        }

        // Prevent backdrop and keyboard dismissal
        if (this.modalInstance) {
            this.modalInstance._config.backdrop = 'static';
            this.modalInstance._config.keyboard = false;
        }
    }

    enableModalDismissal() {
        // Re-enable close buttons
        const headerCloseButton = this.modal.querySelector('.btn-close');
        const footerCloseButton = document.getElementById('closeButton');

        if (headerCloseButton) {
            headerCloseButton.disabled = false;
            headerCloseButton.style.opacity = '';
            headerCloseButton.style.cursor = '';
        }

        if (footerCloseButton) {
            footerCloseButton.disabled = false;
            footerCloseButton.classList.remove('opacity-50'); // Remove visual disabled styling
        }

        // Allow backdrop and keyboard dismissal
        if (this.modalInstance) {
            this.modalInstance._config.backdrop = true;
            this.modalInstance._config.keyboard = true;
        }
    }

    updateMainButtonState() {
        if (!this.updateButton) return;

        if (this.isRunning) {
            // Disable button and show running state
            this.updateButton.disabled = true;
            this.updateButton.innerHTML = `
                <div class="spinner-border spinner-border-sm me-1" role="status"></div>
                <span class="d-none d-md-inline">Updating...</span>
            `;
            this.updateButton.title = 'Data update in progress';
        } else {
            // Re-enable button and restore original state
            this.updateButton.disabled = false;
            this.updateButton.innerHTML = `
                <i class="bi bi-arrow-clockwise me-1"></i>
                <span class="d-none d-md-inline">Update All</span>
            `;
            this.updateButton.title = 'Update all data';
        }
    }

    resetStatusIndicators() {
        // Reset prerequisite status
        document.getElementById('githubTokenStatus').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';
        document.getElementById('gitlabTokenStatus').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';
        document.getElementById('jiraTokenStatus').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';

        // Reset greying out of prerequisite rows
        ['githubTokenStatus', 'gitlabTokenStatus', 'jiraTokenStatus'].forEach(elementId => {
            const element = document.getElementById(elementId);
            if (element) {
                const listItem = element.closest('.list-group-item');
                if (listItem) {
                    listItem.classList.remove('opacity-50');
                }
            }
        });

        // Reset data source status
        this.dataSources.forEach(source => {
            const statusElement = document.getElementById(`${source.id}-status`);
            if (statusElement) {
                statusElement.innerHTML = '<i class="bi bi-clock text-muted"></i>';
            }
        });
    }

    async checkPrerequisites() {
        // Get selected sources
        const selectedSources = this.getSelectedDataSources().map(source => source.id);

        // Reset status indicators to loading state
        document.getElementById('githubTokenStatus').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';
        document.getElementById('gitlabTokenStatus').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';
        document.getElementById('jiraTokenStatus').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';

        // Update start button to checking state
        const startButton = document.getElementById('startUpdateButton');
        if (startButton) {
            startButton.disabled = true;
            startButton.innerHTML = `
                <div class="spinner-border spinner-border-sm me-1" role="status"></div>
                Checking Prerequisites...
            `;
        }

        // Hide any existing error
        document.getElementById('prerequisiteError').classList.add('d-none');

        try {
            const response = await fetch('/api/check-prerequisites', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    selected_sources: selectedSources
                })
            });

            const result = await response.json();

            // Update status indicators based on whether check was needed and result
            this.updatePrerequisiteStatus('githubTokenStatus', result.github_token, result.github_needed);
            this.updatePrerequisiteStatus('gitlabTokenStatus', result.gitlab_token, result.gitlab_needed);
            this.updatePrerequisiteStatus('jiraTokenStatus', result.jira_token, result.jira_needed);

            // Update button based on prerequisite check result
            if (result.all_valid) {
                if (startButton) {
                    startButton.disabled = false;
                    startButton.innerHTML = `
                        <i class="bi bi-play-fill me-1"></i>
                        Start Update
                    `;
                }
                document.getElementById('prerequisiteError').classList.add('d-none');
            } else {
                if (startButton) {
                    startButton.disabled = true;
                    startButton.innerHTML = `
                        <i class="bi bi-x-circle me-1"></i>
                        Prerequisites Failed
                    `;
                }
                document.getElementById('prerequisiteError').classList.remove('d-none');
                document.getElementById('prerequisiteErrorText').textContent = result.error_message;
            }

        } catch (error) {
            if (startButton) {
                startButton.disabled = true;
                startButton.innerHTML = `
                    <i class="bi bi-exclamation-triangle me-1"></i>
                    Check Failed
                `;
            }
            document.getElementById('prerequisiteError').classList.remove('d-none');
            document.getElementById('prerequisiteErrorText').textContent = 'Failed to check prerequisites. Please try again.';
        }
    }

    retryPrerequisites() {
        // Re-run the prerequisites check
        this.checkPrerequisites();
    }

    updatePrerequisiteStatus(elementId, isValid, isNeeded) {
        const element = document.getElementById(elementId);

        if (isNeeded === false) {
            // Check was not needed - show skipped
            element.innerHTML = '<i class="bi bi-dash-circle text-muted" title="Not needed for selected sources"></i>';
            // Also grey out the entire row
            const listItem = element.closest('.list-group-item');
            if (listItem) {
                listItem.classList.add('opacity-50');
            }
        } else if (isValid) {
            // Check passed
            element.innerHTML = '<i class="bi bi-check-circle text-success"></i>';
            // Remove any greying
            const listItem = element.closest('.list-group-item');
            if (listItem) {
                listItem.classList.remove('opacity-50');
            }
        } else {
            // Check failed
            element.innerHTML = '<i class="bi bi-x-circle text-danger"></i>';
            // Remove any greying
            const listItem = element.closest('.list-group-item');
            if (listItem) {
                listItem.classList.remove('opacity-50');
            }
        }
    }

    async startUpdate() {
        if (this.isRunning) return;

        this.isRunning = true;
        this.updateMainButtonState();

        // Disable modal dismissal during update
        this.disableModalDismissal();

        // Hide prerequisites section and show progress
        document.getElementById('prerequisitesSection').classList.add('d-none');
        document.getElementById('progressSection').classList.remove('d-none');
        document.getElementById('startUpdateButton').classList.add('d-none');

        // Start the update process
        try {
            await this.runDataUpdates();
            this.showCompletion();
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.isRunning = false;
            this.updateMainButtonState();

            // Re-enable modal dismissal after update completes
            this.enableModalDismissal();
        }
    }

    async runDataUpdates() {
        const results = [];
        const selectedSources = this.getSelectedDataSources();

        // First, mark all non-selected sources as skipped
        this.dataSources.forEach(source => {
            const isSelected = selectedSources.find(s => s.id === source.id);
            if (!isSelected) {
                this.updateDataSourceStatus(source.id, 'skipped');
                results.push({ source: source.name, status: 'skipped' });
            }
        });

        // Now process only the selected sources
        for (let i = 0; i < selectedSources.length; i++) {
            const source = selectedSources[i];

            try {
                // Update status to running
                this.updateDataSourceStatus(source.id, 'running');

                // Make the API call
                const response = await fetch(source.endpoint, {
                    method: 'GET',
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest'
                    }
                });

                if (response.ok) {
                    this.updateDataSourceStatus(source.id, 'success');
                    results.push({ source: source.name, status: 'success' });
                } else {
                    throw new Error(`HTTP ${response.status}`);
                }

            } catch (error) {
                this.updateDataSourceStatus(source.id, 'error');
                results.push({ source: source.name, status: 'error', error: error.message });
            }

            // Update overall progress
            this.currentStep++;
            this.updateOverallProgress();

            // Small delay to show progress visually
            await new Promise(resolve => setTimeout(resolve, 500));
        }

        // Store results for completion summary
        this.updateResults = results;
    }

    updateDataSourceStatus(sourceId, status) {
        const statusElement = document.getElementById(`${sourceId}-status`);
        const progressItem = document.getElementById(`${sourceId}-progress`);

        if (statusElement) {
            switch (status) {
                case 'running':
                    statusElement.innerHTML = '<div class="spinner-border spinner-border-sm text-primary" role="status"></div>';
                    if (progressItem) {
                        progressItem.classList.remove('opacity-50');
                        progressItem.style.fontStyle = '';
                    }
                    break;
                case 'success':
                    statusElement.innerHTML = '<i class="bi bi-check-circle text-success"></i>';
                    if (progressItem) {
                        progressItem.classList.remove('opacity-50');
                        progressItem.style.fontStyle = '';
                    }
                    break;
                case 'error':
                    statusElement.innerHTML = '<i class="bi bi-x-circle text-danger"></i>';
                    if (progressItem) {
                        progressItem.classList.remove('opacity-50');
                        progressItem.style.fontStyle = '';
                    }
                    break;
                case 'skipped':
                    statusElement.innerHTML = '<i class="bi bi-dash-circle text-muted" title="Not selected for update"></i>';
                    if (progressItem) {
                        progressItem.classList.add('opacity-50'); // Make the whole row appear muted
                        progressItem.style.fontStyle = 'italic'; // Italicize to show it's inactive
                    }
                    break;
                default:
                    statusElement.innerHTML = '<i class="bi bi-clock text-muted"></i>';
                    if (progressItem) {
                        progressItem.classList.remove('opacity-50');
                        progressItem.style.fontStyle = '';
                    }
                    break;
            }
        }
    }

    updateOverallProgress() {
        const selectedSources = this.getSelectedDataSources();
        const totalSelected = selectedSources.length;
        const percentage = totalSelected > 0 ? Math.round((this.currentStep / totalSelected) * 100) : 0;
        const progressBar = document.getElementById('overallProgressBar');
        const progressText = document.getElementById('overallProgressText');

        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }

        if (progressText) {
            progressText.textContent = `${this.currentStep} / ${totalSelected}`;
        }
    }

    showCompletion() {
        // Keep progress section visible, just add completion message
        const progressSection = document.getElementById('progressSection');

        // Generate completion summary
        const successCount = this.updateResults.filter(r => r.status === 'success').length;
        const errorCount = this.updateResults.filter(r => r.status === 'error').length;
        const skippedCount = this.updateResults.filter(r => r.status === 'skipped').length;

        // Create success message to show in progress section
        let summaryHtml = '';
        if (errorCount === 0) {
            summaryHtml = `
                <div class="alert alert-success mt-4">
                    <i class="bi bi-check-circle me-2"></i>
                    <strong>All selected updates completed successfully!</strong>
                    <p class="mb-1 mt-2">✅ Updated (${successCount}): ${this.updateResults.filter(r => r.status === 'success').map(r => r.source).join(', ')}</p>
                    ${skippedCount > 0 ? `<p class="mb-0 text-muted"><i class="bi bi-dash-circle me-1"></i>Skipped (${skippedCount}): ${this.updateResults.filter(r => r.status === 'skipped').map(r => r.source).join(', ')}</p>` : ''}
                    <p class="mb-0 mt-2 small text-muted">
                        <i class="bi bi-info-circle me-1"></i>
                        Close this modal to refresh the page and view updated data.
                    </p>
                </div>
            `;
        } else {
            summaryHtml = `
                <div class="alert alert-warning mt-4">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>Updates completed with some issues</strong>
                    <p class="mb-1 mt-2">✅ Success (${successCount}): ${this.updateResults.filter(r => r.status === 'success').map(r => r.source).join(', ')}</p>
                    <p class="mb-1">❌ Errors (${errorCount}): ${this.updateResults.filter(r => r.status === 'error').map(r => `${r.source} (${r.error})`).join(', ')}</p>
                    ${skippedCount > 0 ? `<p class="mb-0 text-muted"><i class="bi bi-dash-circle me-1"></i>Skipped (${skippedCount}): ${this.updateResults.filter(r => r.status === 'skipped').map(r => r.source).join(', ')}</p>` : ''}
                    <p class="mb-0 mt-2 small text-muted">
                        <i class="bi bi-info-circle me-1"></i>
                        Close this modal to refresh the page and view updated data.
                    </p>
                </div>
            `;
        }

        // Add completion message to progress section
        progressSection.insertAdjacentHTML('beforeend', summaryHtml);

        // Hide the Start Update button (no longer needed after completion)
        const startButton = document.getElementById('startUpdateButton');
        if (startButton) {
            startButton.classList.add('d-none');
        }

        // Enable the Close button (it was disabled during update)
        const closeButton = document.getElementById('closeButton');
        if (closeButton) {
            closeButton.disabled = false;
            closeButton.classList.remove('opacity-50'); // Remove any visual disabled styling
        }

        // Set up page reload on modal close (only if there were successful updates)
        if (successCount > 0) {
            this.setupReloadOnModalClose();
        }
    }

    setupReloadOnModalClose() {
        const closeButton = document.getElementById('closeButton');
        const modal = document.getElementById('updateAllDataModal');

        if (!modal) return;

        const reloadPage = () => {
            window.location.reload();
        };

        // Reload on close button click
        if (closeButton) {
            closeButton.addEventListener('click', reloadPage, { once: true });
        }

        // Reload when modal is dismissed (X button, ESC key, backdrop click)
        modal.addEventListener('hidden.bs.modal', reloadPage, { once: true });
    }

    showError(errorMessage) {
        // Keep progress section visible, just add error message
        const progressSection = document.getElementById('progressSection');

        const errorHtml = `
            <div class="alert alert-danger mt-4">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Update process failed</strong>
                <p class="mb-0 mt-2">${errorMessage}</p>
            </div>
        `;

        // Add error message to progress section
        progressSection.insertAdjacentHTML('beforeend', errorHtml);

        // Hide the Start Update button (no longer needed after error)
        const startButton = document.getElementById('startUpdateButton');
        if (startButton) {
            startButton.classList.add('d-none');
        }

        // Enable the Close button
        const closeButton = document.getElementById('closeButton');
        if (closeButton) {
            closeButton.disabled = false;
            closeButton.classList.remove('opacity-50');
        }
    }

    // ========== NEW SELECTION LOGIC ==========

    setupCheckboxListeners() {
        // Handle "Select All" checkbox
        const selectAllCheckbox = document.getElementById('selectAllDataSources');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', () => {
                const isChecked = selectAllCheckbox.checked;
                const dataSourceCheckboxes = document.querySelectorAll('.data-source-checkbox');
                dataSourceCheckboxes.forEach(checkbox => {
                    // Only change enabled checkboxes
                    if (!checkbox.disabled) {
                        checkbox.checked = isChecked;
                    }
                });
            });
        }

        // Handle individual data source checkboxes
        const dataSourceCheckboxes = document.querySelectorAll('.data-source-checkbox');
        dataSourceCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateSelectAllState();
            });
        });
    }

    setupContinueButton() {
        const continueButton = document.getElementById('continueButton');
        if (continueButton) {
            continueButton.addEventListener('click', () => {
                const selectedSources = this.getSelectedDataSources();
                if (selectedSources.length === 0) {
                    alert('Please select at least one data source to update.');
                    return;
                }
                this.showPrerequisitesStep();
            });
        }
    }

    showSelectionStep() {
        // Show selection section, hide others
        document.getElementById('selectionSection').classList.remove('d-none');
        document.getElementById('prerequisitesSection').classList.add('d-none');
        document.getElementById('progressSection').classList.add('d-none');
        document.getElementById('completionSection').classList.add('d-none');
        document.getElementById('errorSection').classList.add('d-none');

        // Show selection footer, hide update footer
        document.getElementById('selectionFooter').classList.remove('d-none');
        document.getElementById('updateFooter').classList.add('d-none');
    }

    showPrerequisitesStep() {
        // Hide selection section, show prerequisites
        document.getElementById('selectionSection').classList.add('d-none');
        document.getElementById('prerequisitesSection').classList.remove('d-none');
        document.getElementById('progressSection').classList.add('d-none');
        document.getElementById('completionSection').classList.add('d-none');
        document.getElementById('errorSection').classList.add('d-none');

        // Hide selection footer, show update footer
        document.getElementById('selectionFooter').classList.add('d-none');
        document.getElementById('updateFooter').classList.remove('d-none');

        // Prepare start button for prerequisites check
        const startButton = document.getElementById('startUpdateButton');
        if (startButton) {
            startButton.disabled = true;
            startButton.innerHTML = `
                <div class="spinner-border spinner-border-sm me-1" role="status"></div>
                Checking Prerequisites...
            `;
        }

        // Start prerequisites check
        this.checkPrerequisites();
    }

    updateSelectAllState() {
        const selectAllCheckbox = document.getElementById('selectAllDataSources');
        const dataSourceCheckboxes = document.querySelectorAll('.data-source-checkbox');

        // Only consider enabled checkboxes for "Select All" logic
        const enabledCheckboxes = Array.from(dataSourceCheckboxes).filter(cb => !cb.disabled);
        const checkedEnabledCount = enabledCheckboxes.filter(cb => cb.checked).length;
        const totalEnabledCount = enabledCheckboxes.length;

        if (checkedEnabledCount === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedEnabledCount === totalEnabledCount) {
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }

    getSelectedDataSources() {
        const selectedSources = [];
        this.dataSources.forEach(source => {
            const checkbox = document.getElementById(`${source.id}-checkbox`);
            if (checkbox && checkbox.checked) {
                selectedSources.push(source);
            }
        });
        return selectedSources;
    }
}

// Add CSS for spinning animation
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }

    .spin {
        animation: spin 1s linear infinite;
    }
`;
document.head.appendChild(style);

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new UpdateAllDataManager();
});
