/**
 * Download All Data From Scratch functionality
 * Similar to Update All Data but deletes incremental files first
 */

class DownloadFromScratchManager {
    constructor() {
        this.modal = null;
        this.modalInstance = null;
        this.downloadButton = null;
        this.isRunning = false;
        this.currentStep = 0;
        this.totalSteps = 10; // 10 data sources total

        // Files that will be deleted for "from scratch" download
        this.filesToDelete = {
            'merged-prs': ['data/github_merged_pr_list.json', 'data/gitlab_merged_pr_list.json'],
            'closed-prs': ['data/github_closed_pr_list.json', 'data/gitlab_closed_pr_list.json'],
            'jira-closed': ['data/jira_closed_tickets.json']
        };

        // Data sources configuration (same as update all, but uses scope=all for incremental ones)
        this.dataSources = [
            { id: 'open-prs', name: 'Open PRs (GitHub + GitLab)', endpoint: '/pull-requests/open?reload_data=1', deletesFiles: false },
            { id: 'merged-prs', name: 'Merged PRs (GitHub + GitLab)', endpoint: '/pull-requests/merged?reload_data=1&scope=all', deletesFiles: true },
            { id: 'closed-prs', name: 'Closed PRs (GitHub + GitLab)', endpoint: '/pull-requests/closed?reload_data=1&scope=all', deletesFiles: true },
            { id: 'app-interface-open', name: 'App-interface Open MRs', endpoint: '/pull-requests/app-interface?reload_data=1', deletesFiles: false },
            { id: 'app-interface-merged', name: 'App-interface Merged MRs', endpoint: '/pull-requests/app-interface-merged?reload_data=1', deletesFiles: false },
            { id: 'app-interface-closed', name: 'App-interface Closed MRs', endpoint: '/pull-requests/app-interface-closed?reload_data=1', deletesFiles: false },
            { id: 'jira-open', name: 'JIRA Open Tickets', endpoint: '/jira-tickets/jira-tickets?reload_data=1', deletesFiles: false },
            { id: 'jira-reported', name: 'JIRA Reported Tickets', endpoint: '/jira-tickets/jira-reported-tickets?reload_data=1', deletesFiles: false },
            { id: 'jira-closed', name: 'JIRA Closed Tickets', endpoint: '/jira-tickets/jira-closed-tickets?reload_data=1&scope=all', deletesFiles: true },
            { id: 'deployments', name: 'Deployments', endpoint: '/deployments/?reload_data=1', deletesFiles: false }
        ];

        this.init();
    }

    init() {
        // Get DOM elements
        this.downloadButton = document.getElementById('downloadFromScratchBtn');
        this.modal = document.getElementById('downloadFromScratchModal');

        if (this.downloadButton && this.modal) {
            this.downloadButton.addEventListener('click', () => this.openModal());

            // Modal event listeners
            const startButton = document.getElementById('startDownloadButtonScr');
            if (startButton) {
                startButton.addEventListener('click', () => this.startDownload());
            }

            // Setup retry prerequisites button
            const retryButton = document.getElementById('retryPrerequisitesButtonScr');
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
            return;
        }

        this.resetModal();

        // Check if enhancement is running before showing modal
        await this.checkEnhancementStatus();

        // Show selection section, hide prerequisites
        this.showSelectionStep();

        // Update files to delete summary
        this.updateFilesToDeleteSummary();

        // Create and store modal instance
        this.modalInstance = new bootstrap.Modal(this.modal, {
            backdrop: true,
            keyboard: true
        });
        this.modalInstance.show();
    }

    resetModal() {
        if (this.isRunning) {
            return;
        }

        // Reset to selection step
        this.showSelectionStep();

        // Reset all hidden sections
        document.getElementById('progressSectionScr').classList.add('d-none');
        document.getElementById('completionSectionScr').classList.add('d-none');
        document.getElementById('errorSectionScr').classList.add('d-none');
        document.getElementById('prerequisiteErrorScr').classList.add('d-none');

        // Clean up any completion/error messages
        const progressSection = document.getElementById('progressSectionScr');
        const completionMessages = progressSection.querySelectorAll('.alert');
        completionMessages.forEach(msg => msg.remove());

        // Reset start button
        const startButton = document.getElementById('startDownloadButtonScr');
        if (startButton) {
            startButton.classList.remove('d-none');
            startButton.disabled = true;
            startButton.innerHTML = `
                <i class="bi bi-trash me-1"></i>
                Delete & Download
            `;
        }

        // Re-enable modal dismissal
        this.enableModalDismissal();

        // Reset progress
        this.currentStep = 0;
        this.updateOverallProgress();

        // Reset all status indicators
        this.resetStatusIndicators();

        // Reset any visual styling on progress items
        this.dataSources.forEach(source => {
            const progressItem = document.getElementById(`${source.id}-progress-scr`);
            if (progressItem) {
                progressItem.classList.remove('opacity-50');
                progressItem.style.fontStyle = '';
            }
        });

        this.isRunning = false;
    }

    updateFilesToDeleteSummary() {
        const selectedSources = this.getSelectedDataSources();
        const listElement = document.getElementById('filesToDeleteListScr');
        const summaryDiv = document.getElementById('filesToDeleteSummaryScr');

        if (!listElement || !summaryDiv) return;

        const filesToDelete = [];

        selectedSources.forEach(source => {
            if (this.filesToDelete[source.id]) {
                filesToDelete.push(...this.filesToDelete[source.id]);
            }
        });

        if (filesToDelete.length > 0) {
            listElement.innerHTML = filesToDelete.map(file => `<li><code>${file}</code></li>`).join('');
            summaryDiv.classList.remove('d-none');
        } else {
            summaryDiv.classList.add('d-none');
        }
    }

    async checkEnhancementStatus() {
        try {
            const response = await fetch('/api/enhance/is-running');
            const status = await response.json();

            const warningDiv = document.getElementById('enhancementWarningScr');
            const mergedCheckbox = document.getElementById('merged-prs-checkbox-scr');
            const closedCheckbox = document.getElementById('closed-prs-checkbox-scr');

            if (status.is_running) {
                if (warningDiv) {
                    warningDiv.classList.remove('d-none');
                }

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

                this.updateSelectAllState();
            } else {
                if (warningDiv) {
                    warningDiv.classList.add('d-none');
                }

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
            const warningDiv = document.getElementById('enhancementWarningScr');
            if (warningDiv) {
                warningDiv.classList.add('d-none');
            }
        }
    }

    disableModalDismissal() {
        const headerCloseButton = this.modal.querySelector('.btn-close');
        const footerCloseButton = document.getElementById('closeButtonScr');

        if (headerCloseButton) {
            headerCloseButton.disabled = true;
            headerCloseButton.style.opacity = '0.3';
            headerCloseButton.style.cursor = 'not-allowed';
        }

        if (footerCloseButton) {
            footerCloseButton.disabled = true;
            footerCloseButton.classList.add('opacity-50');
        }

        if (this.modalInstance) {
            this.modalInstance._config.backdrop = 'static';
            this.modalInstance._config.keyboard = false;
        }
    }

    enableModalDismissal() {
        const headerCloseButton = this.modal.querySelector('.btn-close');
        const footerCloseButton = document.getElementById('closeButtonScr');

        if (headerCloseButton) {
            headerCloseButton.disabled = false;
            headerCloseButton.style.opacity = '';
            headerCloseButton.style.cursor = '';
        }

        if (footerCloseButton) {
            footerCloseButton.disabled = false;
            footerCloseButton.classList.remove('opacity-50');
        }

        if (this.modalInstance) {
            this.modalInstance._config.backdrop = true;
            this.modalInstance._config.keyboard = true;
        }
    }

    updateMainButtonState() {
        if (!this.downloadButton) return;

        if (this.isRunning) {
            this.downloadButton.disabled = true;
            this.downloadButton.innerHTML = `
                <div class="spinner-border spinner-border-sm me-1" role="status"></div>
                <span class="d-none d-md-inline">Downloading...</span>
            `;
            this.downloadButton.title = 'Download in progress';
        } else {
            this.downloadButton.disabled = false;
            this.downloadButton.innerHTML = `
                <i class="bi bi-arrow-repeat me-1"></i>
                <span class="d-none d-md-inline">Download new data</span>
            `;
            this.downloadButton.title = 'Download all data from scratch';
        }
    }

    resetStatusIndicators() {
        // Reset prerequisite status
        document.getElementById('githubTokenStatusScr').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';
        document.getElementById('gitlabTokenStatusScr').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';
        document.getElementById('jiraTokenStatusScr').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';

        // Reset greying out of prerequisite rows
        ['githubTokenStatusScr', 'gitlabTokenStatusScr', 'jiraTokenStatusScr'].forEach(elementId => {
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
            const statusElement = document.getElementById(`${source.id}-status-scr`);
            if (statusElement) {
                statusElement.innerHTML = '<i class="bi bi-clock text-muted"></i>';
            }
        });
    }

    async checkPrerequisites() {
        const selectedSources = this.getSelectedDataSources().map(source => source.id);

        // Reset status indicators to loading state
        document.getElementById('githubTokenStatusScr').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';
        document.getElementById('gitlabTokenStatusScr').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';
        document.getElementById('jiraTokenStatusScr').innerHTML = '<div class="spinner-border spinner-border-sm text-muted" role="status"></div>';

        // Update start button to checking state
        const startButton = document.getElementById('startDownloadButtonScr');
        if (startButton) {
            startButton.disabled = true;
            startButton.innerHTML = `
                <div class="spinner-border spinner-border-sm me-1" role="status"></div>
                Checking Prerequisites...
            `;
        }

        // Hide any existing error
        document.getElementById('prerequisiteErrorScr').classList.add('d-none');

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

            // Update status indicators
            this.updatePrerequisiteStatus('githubTokenStatusScr', result.github_token, result.github_needed);
            this.updatePrerequisiteStatus('gitlabTokenStatusScr', result.gitlab_token, result.gitlab_needed);
            this.updatePrerequisiteStatus('jiraTokenStatusScr', result.jira_token, result.jira_needed);

            // Update button based on prerequisite check result
            if (result.all_valid) {
                if (startButton) {
                    startButton.disabled = false;
                    startButton.innerHTML = `
                        <i class="bi bi-trash me-1"></i>
                        Delete & Download
                    `;
                }
                document.getElementById('prerequisiteErrorScr').classList.add('d-none');
            } else {
                if (startButton) {
                    startButton.disabled = true;
                    startButton.innerHTML = `
                        <i class="bi bi-x-circle me-1"></i>
                        Prerequisites Failed
                    `;
                }
                document.getElementById('prerequisiteErrorScr').classList.remove('d-none');
                document.getElementById('prerequisiteErrorTextScr').textContent = result.error_message;
            }

        } catch (error) {
            if (startButton) {
                startButton.disabled = true;
                startButton.innerHTML = `
                    <i class="bi bi-exclamation-triangle me-1"></i>
                    Check Failed
                `;
            }
            document.getElementById('prerequisiteErrorScr').classList.remove('d-none');
            document.getElementById('prerequisiteErrorTextScr').textContent = 'Failed to check prerequisites. Please try again.';
        }
    }

    retryPrerequisites() {
        this.checkPrerequisites();
    }

    updatePrerequisiteStatus(elementId, isValid, isNeeded) {
        const element = document.getElementById(elementId);

        if (isNeeded === false) {
            element.innerHTML = '<i class="bi bi-dash-circle text-muted" title="Not needed for selected sources"></i>';
            const listItem = element.closest('.list-group-item');
            if (listItem) {
                listItem.classList.add('opacity-50');
            }
        } else if (isValid) {
            element.innerHTML = '<i class="bi bi-check-circle text-success"></i>';
            const listItem = element.closest('.list-group-item');
            if (listItem) {
                listItem.classList.remove('opacity-50');
            }
        } else {
            element.innerHTML = '<i class="bi bi-x-circle text-danger"></i>';
            const listItem = element.closest('.list-group-item');
            if (listItem) {
                listItem.classList.remove('opacity-50');
            }
        }
    }

    async deleteFiles(selectedSources) {
        // Get list of files to delete based on selected sources
        const filesToDelete = [];
        selectedSources.forEach(source => {
            if (this.filesToDelete[source.id]) {
                filesToDelete.push(...this.filesToDelete[source.id]);
            }
        });

        if (filesToDelete.length === 0) {
            return { success: true, deleted: [] };
        }

        try {
            const response = await fetch('/api/delete-data-files', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    files: filesToDelete
                })
            });

            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Error deleting files:', error);
            throw new Error(`Failed to delete files: ${error.message}`);
        }
    }

    async startDownload() {
        if (this.isRunning) return;

        this.isRunning = true;
        this.updateMainButtonState();

        // Disable modal dismissal during download
        this.disableModalDismissal();

        // Hide prerequisites section and show progress
        document.getElementById('prerequisitesSectionScr').classList.add('d-none');
        document.getElementById('progressSectionScr').classList.remove('d-none');
        document.getElementById('startDownloadButtonScr').classList.add('d-none');

        try {
            // First, delete the files
            const selectedSources = this.getSelectedDataSources();
            const deleteResult = await this.deleteFiles(selectedSources);

            if (!deleteResult.success) {
                throw new Error('Failed to delete some files');
            }

            // Then start the download process
            await this.runDataDownloads();
            this.showCompletion();
        } catch (error) {
            this.showError(error.message);
        } finally {
            this.isRunning = false;
            this.updateMainButtonState();

            // Re-enable modal dismissal after download completes
            this.enableModalDismissal();
        }
    }

    async runDataDownloads() {
        const results = [];
        const selectedSources = this.getSelectedDataSources();

        // Mark all non-selected sources as skipped
        this.dataSources.forEach(source => {
            const isSelected = selectedSources.find(s => s.id === source.id);
            if (!isSelected) {
                this.updateDataSourceStatus(source.id, 'skipped');
                results.push({ source: source.name, status: 'skipped' });
            }
        });

        // Process only the selected sources
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
        this.downloadResults = results;
    }

    updateDataSourceStatus(sourceId, status) {
        const statusElement = document.getElementById(`${sourceId}-status-scr`);
        const progressItem = document.getElementById(`${sourceId}-progress-scr`);

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
                    statusElement.innerHTML = '<i class="bi bi-dash-circle text-muted" title="Not selected for download"></i>';
                    if (progressItem) {
                        progressItem.classList.add('opacity-50');
                        progressItem.style.fontStyle = 'italic';
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
        const progressBar = document.getElementById('overallProgressBarScr');
        const progressText = document.getElementById('overallProgressTextScr');

        if (progressBar) {
            progressBar.style.width = `${percentage}%`;
            progressBar.setAttribute('aria-valuenow', percentage);
        }

        if (progressText) {
            progressText.textContent = `${this.currentStep} / ${totalSelected}`;
        }
    }

    showCompletion() {
        const progressSection = document.getElementById('progressSectionScr');

        // Generate completion summary
        const successCount = this.downloadResults.filter(r => r.status === 'success').length;
        const errorCount = this.downloadResults.filter(r => r.status === 'error').length;
        const skippedCount = this.downloadResults.filter(r => r.status === 'skipped').length;

        let summaryHtml = '';
        if (errorCount === 0) {
            summaryHtml = `
                <div class="alert alert-success mt-4">
                    <i class="bi bi-check-circle me-2"></i>
                    <strong>All selected downloads completed successfully!</strong>
                    <p class="mb-1 mt-2">✅ Downloaded (${successCount}): ${this.downloadResults.filter(r => r.status === 'success').map(r => r.source).join(', ')}</p>
                    ${skippedCount > 0 ? `<p class="mb-0 text-muted"><i class="bi bi-dash-circle me-1"></i>Skipped (${skippedCount}): ${this.downloadResults.filter(r => r.status === 'skipped').map(r => r.source).join(', ')}</p>` : ''}
                    <p class="mb-0 mt-2 small text-muted">
                        <i class="bi bi-info-circle me-1"></i>
                        Close this modal to refresh the page and view downloaded data.
                    </p>
                </div>
            `;
        } else {
            summaryHtml = `
                <div class="alert alert-warning mt-4">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    <strong>Downloads completed with some issues</strong>
                    <p class="mb-1 mt-2">✅ Success (${successCount}): ${this.downloadResults.filter(r => r.status === 'success').map(r => r.source).join(', ')}</p>
                    <p class="mb-1">❌ Errors (${errorCount}): ${this.downloadResults.filter(r => r.status === 'error').map(r => `${r.source} (${r.error})`).join(', ')}</p>
                    ${skippedCount > 0 ? `<p class="mb-0 text-muted"><i class="bi bi-dash-circle me-1"></i>Skipped (${skippedCount}): ${this.downloadResults.filter(r => r.status === 'skipped').map(r => r.source).join(', ')}</p>` : ''}
                    <p class="mb-0 mt-2 small text-muted">
                        <i class="bi bi-info-circle me-1"></i>
                        Close this modal to refresh the page and view downloaded data.
                    </p>
                </div>
            `;
        }

        progressSection.insertAdjacentHTML('beforeend', summaryHtml);

        const startButton = document.getElementById('startDownloadButtonScr');
        if (startButton) {
            startButton.classList.add('d-none');
        }

        const closeButton = document.getElementById('closeButtonScr');
        if (closeButton) {
            closeButton.disabled = false;
            closeButton.classList.remove('opacity-50');
        }

        // Set up page reload on modal close
        if (successCount > 0) {
            this.setupReloadOnModalClose();
        }
    }

    setupReloadOnModalClose() {
        const closeButton = document.getElementById('closeButtonScr');
        const modal = document.getElementById('downloadFromScratchModal');

        if (!modal) return;

        const reloadPage = () => {
            window.location.reload();
        };

        if (closeButton) {
            closeButton.addEventListener('click', reloadPage, { once: true });
        }

        modal.addEventListener('hidden.bs.modal', reloadPage, { once: true });
    }

    showError(errorMessage) {
        const progressSection = document.getElementById('progressSectionScr');

        const errorHtml = `
            <div class="alert alert-danger mt-4">
                <i class="bi bi-exclamation-triangle me-2"></i>
                <strong>Download process failed</strong>
                <p class="mb-0 mt-2">${errorMessage}</p>
            </div>
        `;

        progressSection.insertAdjacentHTML('beforeend', errorHtml);

        const startButton = document.getElementById('startDownloadButtonScr');
        if (startButton) {
            startButton.classList.add('d-none');
        }

        const closeButton = document.getElementById('closeButtonScr');
        if (closeButton) {
            closeButton.disabled = false;
            closeButton.classList.remove('opacity-50');
        }
    }

    // ========== SELECTION LOGIC ==========

    setupCheckboxListeners() {
        // Handle "Select All" checkbox
        const selectAllCheckbox = document.getElementById('selectAllDataSourcesScr');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', () => {
                const isChecked = selectAllCheckbox.checked;
                const dataSourceCheckboxes = document.querySelectorAll('.data-source-checkbox-scr');
                dataSourceCheckboxes.forEach(checkbox => {
                    if (!checkbox.disabled) {
                        checkbox.checked = isChecked;
                    }
                });
                this.updateFilesToDeleteSummary();
            });
        }

        // Handle individual data source checkboxes
        const dataSourceCheckboxes = document.querySelectorAll('.data-source-checkbox-scr');
        dataSourceCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateSelectAllState();
                this.updateFilesToDeleteSummary();
            });
        });
    }

    setupContinueButton() {
        const continueButton = document.getElementById('continueButtonScr');
        if (continueButton) {
            continueButton.addEventListener('click', () => {
                const selectedSources = this.getSelectedDataSources();
                if (selectedSources.length === 0) {
                    alert('Please select at least one data source to download.');
                    return;
                }
                this.showPrerequisitesStep();
            });
        }
    }

    showSelectionStep() {
        // Show selection section, hide others
        document.getElementById('selectionSectionScr').classList.remove('d-none');
        document.getElementById('prerequisitesSectionScr').classList.add('d-none');
        document.getElementById('progressSectionScr').classList.add('d-none');
        document.getElementById('completionSectionScr').classList.add('d-none');
        document.getElementById('errorSectionScr').classList.add('d-none');

        // Show selection footer, hide update footer
        document.getElementById('selectionFooterScr').classList.remove('d-none');
        document.getElementById('updateFooterScr').classList.add('d-none');
    }

    showPrerequisitesStep() {
        // Hide selection section, show prerequisites
        document.getElementById('selectionSectionScr').classList.add('d-none');
        document.getElementById('prerequisitesSectionScr').classList.remove('d-none');
        document.getElementById('progressSectionScr').classList.add('d-none');
        document.getElementById('completionSectionScr').classList.add('d-none');
        document.getElementById('errorSectionScr').classList.add('d-none');

        // Hide selection footer, show update footer
        document.getElementById('selectionFooterScr').classList.add('d-none');
        document.getElementById('updateFooterScr').classList.remove('d-none');

        // Prepare start button for prerequisites check
        const startButton = document.getElementById('startDownloadButtonScr');
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
        const selectAllCheckbox = document.getElementById('selectAllDataSourcesScr');
        const dataSourceCheckboxes = document.querySelectorAll('.data-source-checkbox-scr');

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
            const checkbox = document.getElementById(`${source.id}-checkbox-scr`);
            if (checkbox && checkbox.checked) {
                selectedSources.push(source);
            }
        });
        return selectedSources;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    new DownloadFromScratchManager();
});
