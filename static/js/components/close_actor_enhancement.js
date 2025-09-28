/**
 * Close Actor Enhancement Component
 * Handles UI for enhancing PR data with close_actor information
 */

// Prevent redeclaration errors by using IIFE pattern
(function() {
    'use strict';

    // Check if already initialized
    if (window.closeActorEnhancementInitialized) {
        return;
    }

    class CloseActorEnhancer {
    constructor() {
        this.isRunning = false;
        this.progressTimer = null;
        this.init();
    }

    init() {
        this.checkStatus();
        this.bindEvents();
    }

    bindEvents() {
        const enhanceBtn = document.getElementById('enhance-close-actor-btn');
        if (enhanceBtn) {
            // Remove any existing listeners to prevent duplicates
            enhanceBtn.removeEventListener('click', this.handleStartEnhancement);
            // Bind the handler to 'this' for proper removal
            this.handleStartEnhancement = () => this.startEnhancement();
            enhanceBtn.addEventListener('click', this.handleStartEnhancement);
        }

        const stopBtn = document.getElementById('stop-enhancement-btn');
        if (stopBtn) {
            // Remove any existing listeners to prevent duplicates
            stopBtn.removeEventListener('click', this.handleStopEnhancement);
            // Bind the handler to 'this' for proper removal
            this.handleStopEnhancement = () => this.stopEnhancement();
            stopBtn.addEventListener('click', this.handleStopEnhancement);
        }
    }

    async checkStatus() {
        try {
            const response = await fetch('/api/enhance/close-actor/status');
            const status = await response.json();

            // Sync client-side state with server status on page load
            this.isRunning = status.is_running || status.is_stopping || false;

            this.updateUI(status);

            // If running or stopping, start polling
            if (status.is_running || status.is_stopping) {
                this.startProgressPolling();
            }
        } catch (error) {
            console.error('Error checking enhancement status:', error);

            // Fallback: Show missing files warning when API is unavailable
            // This handles cases where server is not running but user needs guidance
            const fallbackStatus = {
                is_available: false,
                is_running: false,
                existing_data: {
                    files_missing: true,
                    missing_files: ['merged PRs', 'closed PRs'],
                    reason: 'Unable to check data status - please ensure merged and closed PRs are downloaded'
                }
            };

            this.updateUI(fallbackStatus);
        }
    }

    async startEnhancement() {
        // Debounce rapid clicks
        const enhanceBtn = document.getElementById('enhance-close-actor-btn');
        if (enhanceBtn && enhanceBtn.disabled) {
            return;
        }

        // Check current state first to avoid race conditions
        try {
            const statusCheck = await fetch('/api/enhance/close-actor/progress');
            const currentStatus = await statusCheck.json();

            if (['running', 'stopping'].includes(currentStatus.status)) {
                console.log('Enhancement already running on server');
                // Update UI to reflect current state instead of showing error
                this.isRunning = true;
                this.startProgressPolling();
                this.updateUI({
                    is_running: currentStatus.status === 'running',
                    is_stopping: currentStatus.status === 'stopping',
                    progress: currentStatus
                });
                return;
            }

            // Optimistic UI update - show starting state immediately
            if (enhanceBtn) {
                enhanceBtn.disabled = true;
                enhanceBtn.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Starting...';
            }

            const response = await fetch('/api/enhance/close-actor/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.error) {
                this.showError(result.error);
                // Reset button state on error
                if (enhanceBtn) {
                    enhanceBtn.disabled = false;
                }
                return;
            }

            this.isRunning = true;
            // Brief delay before starting polling to let server settle
            setTimeout(() => {
                this.startProgressPolling();
            }, 500);
            this.updateUI({ is_running: true, progress: result.progress });

        } catch (error) {
            console.error('Error starting enhancement:', error);
            this.showError('Failed to start enhancement process');
            // Reset button state on error
            if (enhanceBtn) {
                enhanceBtn.disabled = false;
            }
        }
    }

    async stopEnhancement() {
        // Debounce rapid clicks
        const stopBtn = document.getElementById('stop-enhancement-btn');
        if (stopBtn && stopBtn.disabled) {
            return;
        }

        try {
            // First check if anything is actually running on server
            const statusResponse = await fetch('/api/enhance/close-actor/progress');
            const currentStatus = await statusResponse.json();

            if (!['running', 'stopping'].includes(currentStatus.status)) {
                console.log('Enhancement not running on server, updating UI to reflect current state');
                // Instead of showing error, just sync UI with current state
                this.isRunning = false;
                this.updateUI({
                    is_running: false,
                    is_stopping: false,
                    is_stopped: currentStatus.status === 'stopped',
                    is_available: currentStatus.status === 'completed',
                    progress: currentStatus
                });
                return;
            }

            // Optimistic UI update - show stopping state immediately
            if (stopBtn) {
                stopBtn.disabled = true;
                stopBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><i class="bi bi-stop-circle"></i> Stopping...';
            }

            // Update main button to show stopping state
            const enhanceBtn = document.getElementById('enhance-close-actor-btn');
            if (enhanceBtn) {
                enhanceBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><i class="bi bi-stop-circle me-1"></i> Stopping...';
                enhanceBtn.disabled = true;
                enhanceBtn.classList.remove('btn-warning', 'btn-success', 'btn-info');
                enhanceBtn.classList.add('btn-secondary');
            }

            // Send stop request
            const response = await fetch('/api/enhance/close-actor/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });

            const result = await response.json();

            if (result.error) {
                this.showError(result.error);
                // Reset button states on error
                if (stopBtn) {
                    stopBtn.disabled = false;
                }
                return;
            }

            // Update UI to show stopping state
            this.updateUI({
                is_running: false,
                is_stopping: true,
                progress: result.progress
            });

            console.log('Enhancement stop requested successfully');

            // Schedule additional status refresh to ensure fresh coverage data (backup)
            setTimeout(() => {
                this.checkStatus();
            }, 600);

        } catch (error) {
            console.error('Error stopping enhancement:', error);
            this.showError('Failed to stop enhancement process');
            // Reset button state on error
            if (stopBtn) {
                stopBtn.disabled = false;
            }
        }
    }

    startProgressPolling() {
        if (this.progressTimer) {
            clearInterval(this.progressTimer);
        }

        this.progressTimer = setInterval(async () => {
            try {
                const response = await fetch('/api/enhance/close-actor/progress');
                const progress = await response.json();

                // Sync client-side state with server status
                this.isRunning = ['running', 'stopping'].includes(progress.status);

                this.updateUI({
                    is_running: progress.status === 'running',
                    is_available: progress.status === 'completed',
                    is_stopping: progress.status === 'stopping',
                    is_stopped: progress.status === 'stopped',
                    has_error: progress.status === 'error',
                    progress: progress
                });

                // Stop polling if completed, stopped, or error
                if (['completed', 'stopped', 'error'].includes(progress.status)) {
                    this.stopProgressPolling();
                    this.isRunning = false;

                    // For stopped/completed processes, fetch full status to get fresh coverage data
                    if (['completed', 'stopped'].includes(progress.status)) {
                        setTimeout(() => {
                            this.checkStatus(); // This fetches /api/enhance/close-actor/status with existing_data
                        }, 200);
                    }

                    // Refresh the page to show new statistics if completed
                    if (progress.status === 'completed') {
                        setTimeout(() => {
                            window.location.reload();
                        }, 2000);
                    }
                }
            } catch (error) {
                console.error('Error fetching progress:', error);
                this.stopProgressPolling();
                this.isRunning = false;
            }
        }, 2000); // Poll every 2 seconds
    }

    stopProgressPolling() {
        if (this.progressTimer) {
            clearInterval(this.progressTimer);
            this.progressTimer = null;
        }
    }

    updateUI(status) {
        this.updateButton(status);
        this.updateProgressInfo(status);
        this.updateStatsVisibility(status);
    }

    updateButton(status) {
        const enhanceBtn = document.getElementById('enhance-close-actor-btn');
        const stopBtn = document.getElementById('stop-enhancement-btn');

        if (!enhanceBtn) return;

        if (status.is_available) {
            const coverage = status.existing_data ? status.existing_data.coverage_percentage : 100;
            const needsEnhancement = status.existing_data ? status.existing_data.needs_enhancement : 0;
            // Only show 100% if it's truly 100%, otherwise show actual percentage
            const displayCoverage = coverage >= 100 ? 100 : Math.floor(coverage * 10) / 10; // Round to 1 decimal

            if (needsEnhancement > 0) {
                // Still have PRs that need enhancement - keep button active
                enhanceBtn.innerHTML = `<i class="bi bi-arrow-repeat me-1"></i> Re-enhance (${needsEnhancement} PRs missing, ${displayCoverage}% coverage)`;
                enhanceBtn.disabled = false;
                enhanceBtn.classList.remove('btn-success', 'btn-info');
                enhanceBtn.classList.add('btn-warning');
            } else {
                // True 100% coverage - but keep button available for new data
                enhanceBtn.innerHTML = `<i class="bi bi-check-circle-fill text-success me-1"></i> Enhancement Complete (${displayCoverage}% coverage) - Re-run Available`;
                enhanceBtn.disabled = false;
                enhanceBtn.classList.remove('btn-warning', 'btn-info');
                enhanceBtn.classList.add('btn-success');
            }
            this.hideStopButton(stopBtn);
        } else if (status.is_running) {
            enhanceBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><i class="bi bi-gear-fill spin me-1"></i> Enhancing...';
            enhanceBtn.disabled = true;
            enhanceBtn.classList.remove('btn-warning', 'btn-success');
            enhanceBtn.classList.add('btn-info');
            this.showStopButton(stopBtn);
        } else if (status.is_stopping) {
            enhanceBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><i class="bi bi-stop-circle me-1"></i> Stopping...';
            enhanceBtn.disabled = true;
            enhanceBtn.classList.remove('btn-warning', 'btn-success');
            enhanceBtn.classList.add('btn-secondary');
            this.hideStopButton(stopBtn);
        } else if (status.is_stopped) {
            enhanceBtn.innerHTML = '<i class="bi bi-play-fill"></i> Continue Enhancement';
            enhanceBtn.disabled = false;
            enhanceBtn.classList.remove('btn-secondary', 'btn-success', 'btn-info');
            enhanceBtn.classList.add('btn-warning');
            this.hideStopButton(stopBtn);
        } else if (status.has_error) {
            enhanceBtn.innerHTML = '<i class="bi bi-exclamation-triangle"></i> Enhancement Failed - Retry';
            enhanceBtn.disabled = false;
            enhanceBtn.classList.remove('btn-warning', 'btn-success', 'btn-info');
            enhanceBtn.classList.add('btn-danger');
            this.hideStopButton(stopBtn);
        } else {
            // Show information about what needs to be enhanced
            const needsEnhancement = status.existing_data ? status.existing_data.needs_enhancement : 0;
            if (needsEnhancement > 0) {
                enhanceBtn.innerHTML = `<i class="bi bi-download"></i> Enhance ${needsEnhancement.toLocaleString()} PRs`;
            } else {
                enhanceBtn.innerHTML = '<i class="bi bi-download"></i> Enhance PR Close Data';
            }
            enhanceBtn.disabled = false;
            enhanceBtn.classList.remove('btn-success', 'btn-info', 'btn-danger');
            enhanceBtn.classList.add('btn-warning');
            this.hideStopButton(stopBtn);
        }
    }

    showStopButton(stopBtn) {
        if (stopBtn) {
            stopBtn.classList.remove('d-none');
        }
    }

    hideStopButton(stopBtn) {
        if (stopBtn) {
            stopBtn.classList.add('d-none');
        }
    }

    updateProgressInfo(status) {
        const progressDiv = document.getElementById('enhancement-progress');
        if (!progressDiv) return;

        if ((status.is_running || status.is_stopping) && status.progress) {
            const p = status.progress;
            const batchPercentage = p.total > 0 ? Math.round((p.processed / p.total) * 100) : 0;

            // Coverage calculation for running state

            // Use overall system coverage for the main progress bar for consistency
            const systemCoverage = status.existing_data && status.existing_data.coverage_percentage
                ? Math.round(status.existing_data.coverage_percentage)
                : 0;

            let stoppingAlert = '';
            if (status.is_stopping) {
                stoppingAlert = `
                    <div class="alert alert-warning mb-3">
                        <i class="bi bi-stop-circle me-2"></i>
                        <strong>Stopping after current repository...</strong>
                        <br><small>Current repository "${p.current_repo}" will complete, then process will stop. Progress will be saved.</small>
                    </div>
                `;
            }

            progressDiv.innerHTML = `
                ${stoppingAlert}
                <div class="mb-2">
                    <strong>${status.is_stopping ? 'Finishing' : 'Enhancing'} ${p.current_file}</strong> - ${p.current_repo}
                </div>
                <div class="progress mb-2">
                    <div class="progress-bar ${status.is_stopping ? 'bg-warning' : ''}" role="progressbar"
                         style="width: ${systemCoverage}%"
                         aria-valuenow="${systemCoverage}"
                         aria-valuemin="0"
                         aria-valuemax="100">
                        ${systemCoverage}%
                    </div>
                </div>
                <small class="text-muted">
                    Current batch: ${p.processed.toLocaleString()}/${p.total.toLocaleString()} PRs (${batchPercentage}%) |
                    Enhanced: ${p.enhanced.toLocaleString()} |
                    Failed: ${p.failed.toLocaleString()}
                    ${status.is_stopping ? ' | <strong>Will stop after current repository</strong>' : ''}
                </small>
            `;
            progressDiv.classList.remove('d-none');
        } else if (status.has_error && status.progress) {
            progressDiv.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Enhancement Failed:</strong> ${status.progress.error_message || 'Unknown error'}
                </div>
            `;
            progressDiv.classList.remove('d-none');
        } else if (status.is_stopped && status.progress) {
            const p = status.progress;
            // Status calculation for stopped state

            // Coverage calculation for stopped state
            const systemCoverage = status.existing_data && status.existing_data.coverage_percentage
                ? Math.round(status.existing_data.coverage_percentage)
                : 0;

            progressDiv.innerHTML = `
                <div class="alert alert-info">
                    <strong>Enhancement Stopped</strong>
                    <br>Progress saved: ${p.enhanced.toLocaleString()} PRs enhanced (${systemCoverage}% total coverage)
                    <br><small>Click "Continue Enhancement" to resume from where you left off</small>
                </div>
            `;
            progressDiv.classList.remove('d-none');
        } else if (status.is_available && status.existing_data) {
            const data = status.existing_data;
            // Only show 100% if it's truly 100%, otherwise show actual percentage
            const displayCoverage = data.coverage_percentage >= 100 ? 100 : Math.floor(data.coverage_percentage * 10) / 10;
            progressDiv.innerHTML = `
                <div class="alert alert-success">
                    <strong>Enhancement Complete!</strong>
                    Coverage: ${data.enhanced_prs.toLocaleString()}/${data.total_prs.toLocaleString()} PRs (${displayCoverage}%)
                </div>
            `;
            progressDiv.classList.remove('d-none');
        } else if (status.existing_data && status.existing_data.needs_enhancement > 0) {
            const data = status.existing_data;
            progressDiv.innerHTML = `
                <div class="alert alert-info">
                    <strong>Enhancement Available:</strong>
                    ${data.needs_enhancement.toLocaleString()} PRs need close_actor data
                    (Current coverage: ${Math.round(data.coverage_percentage)}%)
                </div>
            `;
            progressDiv.classList.remove('d-none');
        } else {
            progressDiv.classList.add('d-none');
        }
    }

    updateStatsVisibility(status) {
        // Show enhanced statistics only when data is available
        const enhancedStats = document.querySelectorAll('.enhanced-stats');
        const basicStats = document.querySelectorAll('.basic-stats');
        const manualUpdateBtn = document.getElementById('manual-update-close-actor-btn');
        const manualUpdateSection = document.getElementById('manual-update-section');
        const missingFilesSection = document.getElementById('missing-files-section');
        const enhancementSection = document.getElementById('enhancement-section');
        const githubPRDependentSections = document.getElementById('github-pr-dependent-sections');

        // Check if files are missing OR enhancement is not complete
        const filesAreMissing = status.existing_data && status.existing_data.files_missing;
        const enhancementIncomplete = !status.is_available || (status.existing_data && status.existing_data.needs_enhancement > 0);

        // Visibility Logic: Files exist, enhancement incomplete - show enhancement section

        if (filesAreMissing) {
            // Show missing files section, hide everything else
            if (missingFilesSection) {
                missingFilesSection.classList.remove('d-none');

                // Update the missing files details
                const missingFilesDetails = document.getElementById('missing-files-details');
                if (missingFilesDetails && status.existing_data.missing_files) {
                    const filesList = status.existing_data.missing_files.join(' and ');
                    missingFilesDetails.textContent = `Missing: ${filesList} data files.`;
                }
            }

            if (enhancementSection) {
                enhancementSection.classList.add('d-none');
            }

            // Hide GitHub PR dependent sections when files are missing
            if (githubPRDependentSections) {
                githubPRDependentSections.classList.add('d-none');
            }

            // Hide enhanced stats when files are missing
            enhancedStats.forEach(el => {
                el.classList.add('d-none');
            });
            return;
        }

        if (enhancementIncomplete) {
            // Files exist but enhancement is not complete - hide dependent sections but show enhancement options
            if (missingFilesSection) {
                missingFilesSection.classList.add('d-none');
            }

            // Show enhancement section for users to run the enhancement
            if (enhancementSection) {
                enhancementSection.classList.remove('d-none');
            }

            // Hide GitHub PR dependent sections until enhancement is complete
            if (githubPRDependentSections) {
                githubPRDependentSections.classList.add('d-none');
            }

            // Hide enhanced stats until enhancement is complete (but continue to check manual update)
            enhancedStats.forEach(el => {
                el.classList.add('d-none');
            });

            // Don't return early - continue to check if manual update should be shown
        } else {
            // Files exist AND enhancement is complete - show everything
            if (missingFilesSection) {
                missingFilesSection.classList.add('d-none');
            }

            // Show GitHub PR dependent sections when enhancement is complete
            if (githubPRDependentSections) {
                githubPRDependentSections.classList.remove('d-none');
            }

            // For complete state, always show enhancement section for potential re-runs
            if (enhancementSection) {
                enhancementSection.classList.remove('d-none');
            }
        }

        // Manual update logic (runs for both incomplete and complete states)
        const needsEnhancement = status.existing_data ? status.existing_data.needs_enhancement : 0;
        const coverage = status.existing_data ? status.existing_data.coverage_percentage : 0;

        // Enhanced stats visibility (for non-incomplete states or high coverage cases)
        if (!enhancementIncomplete || (coverage >= 99)) {
            enhancedStats.forEach(el => {
                el.classList.remove('d-none');
            });
        }

        // Show appropriate section based on coverage
        const perfectCoverageSection = document.getElementById('perfect-coverage-section');

        // Manual update section visibility logic

        if (status.is_available && needsEnhancement === 0 && coverage >= 100) {
            // TRUE 100% COVERAGE - Show congratulatory section
            if (manualUpdateBtn) {
                manualUpdateBtn.classList.add('d-none');
            }
            if (manualUpdateSection) {
                manualUpdateSection.classList.add('d-none');
            }
            if (perfectCoverageSection) {
                perfectCoverageSection.classList.remove('d-none');
            }

            // Hide enhancement section since no enhancement needed
            if (enhancementSection) {
                enhancementSection.classList.add('d-none');
            }
        } else if (status.is_available && coverage >= 99 && needsEnhancement > 0) {
            // NEAR 100% (99%+) - Show manual update option
            if (manualUpdateBtn) {
                manualUpdateBtn.classList.remove('d-none');
            }
            if (manualUpdateSection) {
                manualUpdateSection.classList.remove('d-none');
            }
            if (perfectCoverageSection) {
                perfectCoverageSection.classList.add('d-none');
            }
        } else {
            // LESS THAN 99% - Hide both sections
            if (manualUpdateBtn) {
                manualUpdateBtn.classList.add('d-none');
            }
            if (manualUpdateSection) {
                manualUpdateSection.classList.add('d-none');
            }
            if (perfectCoverageSection) {
                perfectCoverageSection.classList.add('d-none');
            }
        }
    }

    showError(message) {
        // Filter out race condition errors that resolve quickly
        const isRaceConditionError =
            message.includes('Enhancement already running') ||
            message.includes('Enhancement not running') ||
            message.includes('already running') ||
            message.includes('not running');

        if (isRaceConditionError) {
            console.log('Ignoring temporary race condition error:', message);
            return;
        }

        const progressDiv = document.getElementById('enhancement-progress');
        if (progressDiv) {
            progressDiv.innerHTML = `
                <div class="alert alert-danger">
                    <strong>Error:</strong> ${message}
                </div>
            `;
            progressDiv.classList.remove('d-none');
        }
    }
    }

    // Initialize when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        new CloseActorEnhancer();
        window.closeActorEnhancementInitialized = true;
    });

})(); // End IIFE
