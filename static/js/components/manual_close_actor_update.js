/**
 * Manual Close Actor Update Component
 * Handles manual updates for PRs with missing close_actor data
 */

(function() {
    'use strict';

    // Check if already initialized
    if (window.manualCloseActorUpdateInitialized) {
        return;
    }

    class ManualCloseActorUpdate {
        constructor() {
            this.missingPrs = [];
            this.init();
        }

        init() {
            this.bindEvents();
        }

        bindEvents() {
            // Modal show event
            const modal = document.getElementById('manualCloseActorModal');
            if (modal) {
                modal.addEventListener('show.bs.modal', () => this.loadMissingPrs());
            }

            // Update button
            const updateBtn = document.getElementById('manual-update-btn');
            if (updateBtn) {
                updateBtn.removeEventListener('click', this.handleUpdateAll);
                this.handleUpdateAll = () => this.updateAll();
                updateBtn.addEventListener('click', this.handleUpdateAll);
            }

            // Refresh button
            const refreshBtn = document.getElementById('manual-refresh-btn');
            if (refreshBtn) {
                refreshBtn.removeEventListener('click', this.handleRefresh);
                this.handleRefresh = () => this.loadMissingPrs();
                refreshBtn.addEventListener('click', this.handleRefresh);
            }
        }

        async loadMissingPrs() {
            this.showLoading(true);
            this.showError(false);
            this.showPrList(false);
            this.showNoMissing(false);

            try {
                const response = await fetch('/api/enhance/close-actor/missing-prs');
                const data = await response.json();

                if (data.error) {
                    this.showError(true, data.error);
                    return;
                }

                this.missingPrs = data.missing_prs || [];

                if (this.missingPrs.length === 0) {
                    this.showNoMissing(true);
                    this.showHelpText(false);
                } else {
                    this.renderPrList();
                    this.showPrList(true);
                    this.showHelpText(true);
                    document.getElementById('manual-update-btn').classList.remove('d-none');
                    document.getElementById('manual-refresh-btn').classList.remove('d-none');
                }

                document.getElementById('missing-count').textContent = this.missingPrs.length;

            } catch (error) {
                console.error('Error loading missing PRs:', error);
                this.showError(true, 'Failed to load missing PRs: ' + error.message);
            } finally {
                this.showLoading(false);
            }
        }

        renderPrList() {
            const tbody = document.getElementById('missing-prs-table');
            if (!tbody) return;

            tbody.innerHTML = '';

            this.missingPrs.forEach((pr, index) => {
                const row = document.createElement('tr');

                // Truncate long titles
                const title = pr.title.length > 50 ? pr.title.substring(0, 50) + '...' : pr.title;

                row.innerHTML = `
                    <td>
                        <span class="badge bg-secondary">${pr.repository}</span>
                    </td>
                    <td>
                        <strong>#${pr.pr_number}</strong>
                    </td>
                    <td>
                        <span title="${pr.title}">${title}</span>
                    </td>
                    <td>
                        <span class="badge ${pr.state === 'merged' ? 'bg-success' : 'bg-danger'}">${pr.state}</span>
                    </td>
                    <td>
                        <a href="${pr.url}" target="_blank" class="btn btn-sm btn-outline-primary">
                            <i class="bi bi-box-arrow-up-right"></i> View PR
                        </a>
                    </td>
                    <td>
                        <div class="input-group input-group-sm">
                            <input
                                type="text"
                                class="form-control close-actor-input"
                                data-repo="${pr.repository}"
                                data-pr-number="${pr.pr_number}"
                                data-file="${pr.file}"
                                placeholder="GitHub username"
                                maxlength="39"
                            >
                            <button class="btn btn-outline-secondary" type="button" onclick="this.previousElementSibling.value = 'unknown'">
                                <i class="bi bi-question-lg" title="Set as 'unknown' if can't determine"></i>
                            </button>
                        </div>
                    </td>
                `;

                tbody.appendChild(row);
            });
        }

        async updateAll() {
            const inputs = document.querySelectorAll('.close-actor-input');
            const updates = [];

            // Collect all updates
            inputs.forEach(input => {
                const closeActor = input.value.trim();
                if (closeActor) {
                    updates.push({
                        repository: input.dataset.repo,
                        pr_number: parseInt(input.dataset.prNumber),
                        close_actor: closeActor,
                        file: input.dataset.file
                    });
                }
            });

            if (updates.length === 0) {
                this.showError(true, 'Please enter close_actor values for at least one PR');
                return;
            }

            // Validate usernames (basic GitHub username rules)
            const invalidUsernames = updates.filter(update => {
                const username = update.close_actor;
                return !/^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$/.test(username) && username !== 'unknown';
            });

            if (invalidUsernames.length > 0) {
                this.showError(true,
                    `Invalid usernames found: ${invalidUsernames.map(u => u.close_actor).join(', ')}. ` +
                    'GitHub usernames can only contain letters, numbers, and hyphens, and cannot start or end with a hyphen.'
                );
                return;
            }

            // Show updating state
            const updateBtn = document.getElementById('manual-update-btn');
            const originalText = updateBtn.innerHTML;
            updateBtn.innerHTML = '<i class="bi bi-arrow-repeat spin me-1"></i>Updating...';
            updateBtn.disabled = true;

            try {
                const response = await fetch('/api/enhance/close-actor/manual-update', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ updates })
                });

                const data = await response.json();

                if (data.error) {
                    this.showError(true, data.error);
                    return;
                }

                // Show success message
                const results = data.results;
                let message = `✅ Successfully updated ${results.updated} PRs`;
                if (results.failed > 0) {
                    message += `, ${results.failed} failed`;
                }

                this.showError(false);
                this.showSuccess(message);

                // Reload the missing PRs list
                setTimeout(() => {
                    this.loadMissingPrs();
                }, 1500);

            } catch (error) {
                console.error('Error updating PRs:', error);
                this.showError(true, 'Failed to update PRs: ' + error.message);
            } finally {
                updateBtn.innerHTML = originalText;
                updateBtn.disabled = false;
            }
        }

        showLoading(show) {
            const loading = document.getElementById('manual-loading');
            if (loading) {
                loading.classList.toggle('d-none', !show);
            }
        }

        showError(show, message = '') {
            const error = document.getElementById('manual-error');
            const errorMessage = document.getElementById('manual-error-message');

            if (error) {
                error.classList.toggle('d-none', !show);
                if (errorMessage && message) {
                    errorMessage.textContent = message;
                }
            }
        }

        showPrList(show) {
            const prList = document.getElementById('manual-pr-list');
            if (prList) {
                prList.classList.toggle('d-none', !show);
            }
        }

        showNoMissing(show) {
            const noMissing = document.getElementById('manual-no-missing');
            if (noMissing) {
                noMissing.classList.toggle('d-none', !show);
            }
        }

        showHelpText(show) {
            const help = document.getElementById('manual-help');
            if (help) {
                help.classList.toggle('d-none', !show);
            }
        }

        showSuccess(message) {
            // Create temporary success alert
            const errorDiv = document.getElementById('manual-error');
            if (errorDiv) {
                errorDiv.className = 'alert alert-success';
                errorDiv.querySelector('#manual-error-message').textContent = message;
                errorDiv.classList.remove('d-none');

                // Revert to error style after 3 seconds
                setTimeout(() => {
                    errorDiv.className = 'alert alert-danger d-none';
                }, 3000);
            }
        }
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        new ManualCloseActorUpdate();
        window.manualCloseActorUpdateInitialized = true;
    });

})(); // End IIFE
