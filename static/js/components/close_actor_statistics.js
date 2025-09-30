(function() {
    'use strict';

    // Prevent redeclaration errors
    if (window.closeActorStatisticsInitialized) {
        return;
    }

    class CloseActorStatistics {
        constructor() {
            this.isPersonalPage = window.location.pathname.includes('personal-stats');
            this.init();
        }

        init() {
            // Load statistics when the perfect coverage section becomes visible
            this.observePerfectCoverageSection();

            // Listen for date range changes to refresh statistics
            this.setupDateRangeListener();
        }

        observePerfectCoverageSection() {
            const perfectCoverageSection = document.getElementById('perfect-coverage-section');

            if (!perfectCoverageSection) {
                console.log('❌ perfect-coverage-section not found');
                return;
            }

            // Flag to prevent multiple loads
            this.statisticsLoaded = false;

            // Use MutationObserver to watch for class changes
            const observer = new MutationObserver((mutations) => {
                // Check if already loaded to prevent duplicates
                if (this.statisticsLoaded) {
                    return;
                }

                // Check if section became visible in any of the mutations
                const becameVisible = !perfectCoverageSection.classList.contains('d-none');

            if (becameVisible) {
                observer.disconnect(); // Disconnect immediately to prevent multiple triggers
                this.statisticsLoaded = true;

                // Add small delay to ensure URL parameters are ready
                setTimeout(() => {
                    this.loadStatistics();
                }, 500);
            }
            });

            observer.observe(perfectCoverageSection, {
                attributes: true,
                attributeFilter: ['class']
            });

            // Also check if it's already visible
            const isVisible = !perfectCoverageSection.classList.contains('d-none');

            if (isVisible) {
                this.statisticsLoaded = true;
                observer.disconnect(); // No need to observe if already visible

                // Add small delay to ensure page and URL parameters are fully loaded
                setTimeout(() => {
                    this.loadStatistics();
                }, 500);
            }
        }

        async loadStatistics() {
            if (this.isPersonalPage) {
                await this.loadPersonalStatistics();
            } else {
                await this.loadOrganizationStatistics();
            }
        }

        async loadPersonalStatistics() {
            try {

                // Get current date range from URL parameters
                const urlParams = new URLSearchParams(window.location.search);
                let dateFrom = urlParams.get('date_from');
                let dateTo = urlParams.get('date_to');

                // Apply same default logic as backend: last 7 days if no parameters
                if (!dateFrom) {
                    const fromDateObj = new Date();
                    fromDateObj.setDate(fromDateObj.getDate() - 6); // 6 days ago + today = 7 days
                    dateFrom = fromDateObj.toISOString().split('T')[0]; // Format as YYYY-MM-DD
                }

                if (!dateTo) {
                    dateTo = new Date().toISOString().split('T')[0]; // Today
                }

                // Build API URL with date parameters
                let apiUrl = '/api/enhance/close-actor/personal-stats';
                const apiParams = new URLSearchParams();
                if (dateFrom) apiParams.set('date_from', dateFrom);
                if (dateTo) apiParams.set('date_to', dateTo);

                if (apiParams.toString()) {
                    apiUrl += '?' + apiParams.toString();
                }

                const response = await fetch(apiUrl);
                const data = await response.json();

                if (data.error) {
                    this.showError('personal-close-stats', data.error);
                    this.showError('team-comparison', 'Failed to load statistics');
                    this.showError('monthly-activity', 'Failed to load statistics');
                    return;
                }

                this.renderPersonalCloseStats(data);
                this.renderKonfluxActivity(data.username);
                this.renderMonthlyActivity(data.monthly_activity);

            } catch (error) {
                console.error('❌ Error loading personal statistics:', error);
                this.showError('personal-close-stats', 'Failed to load statistics');
                this.showError('team-comparison', 'Failed to load statistics');
                this.showError('monthly-activity', 'Failed to load statistics');
            }
        }

        async loadOrganizationStatistics() {
            try {

                // Get current date range from URL parameters
                const urlParams = new URLSearchParams(window.location.search);
                let dateFrom = urlParams.get('date_from');
                let dateTo = urlParams.get('date_to');

                // Apply same default logic as backend: last 7 days if no parameters
                if (!dateFrom) {
                    const fromDateObj = new Date();
                    fromDateObj.setDate(fromDateObj.getDate() - 6); // 6 days ago + today = 7 days
                    dateFrom = fromDateObj.toISOString().split('T')[0]; // Format as YYYY-MM-DD
                }

                if (!dateTo) {
                    dateTo = new Date().toISOString().split('T')[0]; // Today
                }

                // Load team statistics first (new panels)
                await this.loadTeamStatistics(dateFrom, dateTo);

                // Build API URL with date parameters for organization stats
                let apiUrl = '/api/enhance/close-actor/organization-stats';
                const apiParams = new URLSearchParams();
                if (dateFrom) apiParams.set('date_from', dateFrom);
                if (dateTo) apiParams.set('date_to', dateTo);

                if (apiParams.toString()) {
                    apiUrl += '?' + apiParams.toString();
                }

                // Load regular repository breakdown
                const response = await fetch(apiUrl);
                const data = await response.json();

                if (data.error) {
                    this.showError('repository-breakdown', 'Failed to load statistics');
                } else {
                    this.renderRepositoryBreakdown(data.top_repositories);
                }

                // Load Konflux repository breakdown
                let konfluxApiUrl = '/api/enhance/close-actor/konflux-repository-stats';
                if (apiParams.toString()) {
                    konfluxApiUrl += '?' + apiParams.toString();
                }

                const konfluxResponse = await fetch(konfluxApiUrl);
                const konfluxData = await konfluxResponse.json();

                if (konfluxData.error) {
                    this.showError('konflux-repository-breakdown', 'Failed to load Konflux statistics');
                } else {
                    this.renderKonfluxRepositoryBreakdown(konfluxData.top_repositories);
                }

            } catch (error) {
                console.error('❌ Error loading organization statistics:', error);
                this.showError('repository-breakdown', 'Failed to load statistics');
                this.showError('konflux-repository-breakdown', 'Failed to load statistics');
            }
        }

        renderPersonalCloseStats(data) {
            const container = document.getElementById('personal-close-stats-content');
            const loadingDiv = document.getElementById('personal-close-stats-loading');

            if (!container) return;

            const stats = data.stats;
            const username = data.username;

            const html = `
                <div class="row text-center">
                    <div class="col-6">
                        <div class="p-3 bg-success bg-opacity-10 rounded">
                            <h3 class="text-success mb-1">${stats.merged_prs_closed.toLocaleString()}</h3>
                            <small class="text-muted">Merged PRs Closed</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="p-3 bg-danger bg-opacity-10 rounded">
                            <h3 class="text-danger mb-1">${stats.closed_prs_closed.toLocaleString()}</h3>
                            <small class="text-muted">Closed PRs Closed</small>
                        </div>
                    </div>
                </div>
                <hr>
                <div class="text-center">
                    <h4 class="text-primary mb-2">${stats.total_closed.toLocaleString()}</h4>
                    <p class="mb-2">Total GitHub PRs Closed by <strong>${username}</strong> (excluding Konflux PRs)</p>
                    <small class="text-muted">Out of ${data.total_prs_in_system.toLocaleString()} total GitHub PRs in system</small>
                </div>
                ${stats.total_closed > 0 ? `
                <hr>
                <div class="mt-3">
                    <h6 class="text-muted mb-2">Your Top Repositories:</h6>
                    <div class="row">
                        ${Object.entries(data.top_repositories)
                            .sort(([,a], [,b]) => b - a)  // Sort by count, highest to lowest
                            .slice(0, 5)  // Take top 5 repositories
                            .map(([repo, count]) => `
                        <div class="col-12 mb-1">
                            <div class="d-flex justify-content-between align-items-center small">
                                <span class="text-truncate" title="${repo}">${repo}</span>
                                <span class="badge bg-secondary">${count}</span>
                            </div>
                        </div>
                        `).join('')}
                    </div>
                </div>
                ` : ''}
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        async renderKonfluxActivity(username) {
            const container = document.getElementById('team-comparison-content');
            const loadingDiv = document.getElementById('team-comparison-loading');

            if (!container) return;

            try {
                // Get current date range from URL parameters
                const urlParams = new URLSearchParams(window.location.search);
                let dateFrom = urlParams.get('date_from');
                let dateTo = urlParams.get('date_to');

                // Apply same default logic as backend: last 7 days if no parameters
                if (!dateFrom) {
                    const fromDateObj = new Date();
                    fromDateObj.setDate(fromDateObj.getDate() - 6); // 6 days ago + today = 7 days
                    dateFrom = fromDateObj.toISOString().split('T')[0]; // Format as YYYY-MM-DD
                }

                if (!dateTo) {
                    dateTo = new Date().toISOString().split('T')[0]; // Today
                }

                // Build API URL with date parameters
                let apiUrl = '/api/enhance/close-actor/personal-konflux-stats';
                const apiParams = new URLSearchParams();
                if (dateFrom) apiParams.set('date_from', dateFrom);
                if (dateTo) apiParams.set('date_to', dateTo);

                if (apiParams.toString()) {
                    apiUrl += '?' + apiParams.toString();
                }

                const response = await fetch(apiUrl);
                const data = await response.json();

                if (data.error) {
                    this.showError('team-comparison', data.error);
                    return;
                }

                const stats = data.stats;

                const html = `
                    <div class="row text-center">
                        <div class="col-6">
                            <div class="p-3 bg-success bg-opacity-10 rounded">
                                <h3 class="text-success mb-1">${stats.merged_prs_closed.toLocaleString()}</h3>
                                <small class="text-muted">Konflux Merged PRs Closed</small>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="p-3 bg-danger bg-opacity-10 rounded">
                                <h3 class="text-danger mb-1">${stats.closed_prs_closed.toLocaleString()}</h3>
                                <small class="text-muted">Konflux Closed PRs Closed</small>
                            </div>
                        </div>
                    </div>
                    <hr>
                    <div class="text-center">
                        <h4 class="text-primary mb-2">${stats.total_closed.toLocaleString()}</h4>
                        <p class="mb-2">Total Konflux GitHub PRs Closed by <strong>${username}</strong></p>
                        <small class="text-muted">Out of ${data.total_konflux_prs_in_system.toLocaleString()} total Konflux GitHub PRs in system</small>
                    </div>
                    ${stats.total_closed > 0 ? `
                    <hr>
                    <div class="mt-3">
                        <h6 class="text-muted mb-2">Your Top Konflux Repositories:</h6>
                        <div class="row">
                            ${Object.entries(data.top_repositories)
                                .sort(([,a], [,b]) => b - a)  // Sort by count, highest to lowest
                                .slice(0, 5)  // Take top 5 repositories
                                .map(([repo, count]) => `
                            <div class="col-12 mb-1">
                                <div class="d-flex justify-content-between align-items-center small">
                                    <span class="text-truncate" title="${repo}">${repo}</span>
                                    <span class="badge bg-secondary">${count}</span>
                                </div>
                            </div>
                            `).join('')}
                        </div>
                    </div>
                    ` : `
                    <div class="text-center mt-3">
                        <div class="text-muted">
                            <i class="bi bi-info-circle me-1"></i>
                            No Konflux PRs closed yet in this date range.
                        </div>
                    </div>
                    `}
                `;

                container.innerHTML = html;
                loadingDiv.classList.add('d-none');
                container.classList.remove('d-none');

            } catch (error) {
                console.error('❌ Error loading Konflux statistics:', error);
                this.showError('team-comparison', 'Failed to load Konflux statistics');
            }
        }

        formatMonthLabel(monthStr) {
            // Convert "Sep 2025" to "9/25"
            const parts = monthStr.split(' ');
            if (parts.length !== 2) return monthStr; // fallback

            const monthName = parts[0];
            const year = parts[1];

            // Map month names to numbers
            const monthMap = {
                'Jan': '1', 'Feb': '2', 'Mar': '3', 'Apr': '4', 'May': '5', 'Jun': '6',
                'Jul': '7', 'Aug': '8', 'Sep': '9', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            };

            const monthNum = monthMap[monthName];
            if (!monthNum) return monthStr; // fallback

            // Return format like "9/25"
            return `${monthNum}/${year.slice(-2)}`;
        }

        renderMonthlyActivity(monthlyData) {
            const container = document.getElementById('monthly-activity-content');
            const loadingDiv = document.getElementById('monthly-activity-loading');

            if (!container || !monthlyData) return;

            // Create a stacked bar chart using CSS
            const maxCount = Math.max(...monthlyData.map(d => d.count), 1);

            const html = `
                <div class="monthly-chart">
                    ${monthlyData.map(data => {
                        const totalHeight = (data.count / maxCount) * 100;
                        const konfluxHeight = data.konflux > 0 ? (data.konflux / data.count) * totalHeight : 0;
                        const regularHeight = data.regular > 0 ? (data.regular / data.count) * totalHeight : 0;

                        return `
                        <div class="month-bar d-flex flex-column align-items-center" style="flex: 1;">
                            <div class="bar-container d-flex align-items-end justify-content-center" style="height: 120px; position: relative;">
                                <div class="stacked-bar" style="width: 38px; height: ${totalHeight}%; display: flex; flex-direction: column; justify-content: flex-end;">
                                    ${data.regular > 0 ? `
                                    <div class="bar regular-bar bg-primary"
                                         style="height: ${regularHeight}%; min-height: ${data.regular > 0 ? '2px' : '0'}; border-radius: ${data.konflux > 0 ? '0' : '2px 2px 0 0'};"
                                         title="${data.month}: ${data.regular} regular PRs closed">
                                    </div>
                                    ` : ''}
                                    ${data.konflux > 0 ? `
                                    <div class="bar konflux-bar"
                                         style="background-color: #28a745; height: ${konfluxHeight}%; min-height: ${data.konflux > 0 ? '2px' : '0'}; border-radius: 2px 2px 0 0;"
                                         title="${data.month}: ${data.konflux} Konflux PRs closed">
                                    </div>
                                    ` : ''}
                                </div>
                                ${data.count > 0 ? `
                                <span class="count-label position-absolute small text-dark"
                                      style="top: -20px; font-weight: bold;">${data.count}</span>
                                ` : ''}
                            </div>
                            <small class="month-label text-muted mt-1" style="font-size: 0.9rem; text-align: center; font-weight: 500;">
                                ${this.formatMonthLabel(data.month)}
                            </small>
                        </div>
                        `;
                    }).join('')}
                </div>
                <style>
                    .monthly-chart {
                        display: flex;
                        gap: 4px;
                        padding: 0 10px;
                    }
                    .bar {
                        transition: all 0.3s ease;
                    }
                    .bar:hover {
                        opacity: 0.8;
                        transform: scaleY(1.05);
                    }
                    .stacked-bar {
                        transition: all 0.3s ease;
                    }
                    .regular-bar {
                        border-radius: 0 0 0 0;
                    }
                    .konflux-bar {
                        border-radius: 2px 2px 0 0;
                    }
                </style>
                <div class="legend mt-3 d-flex justify-content-center">
                    <div class="legend-item d-flex align-items-center me-3">
                        <div style="width: 16px; height: 12px; background-color: #0d6efd; border-radius: 2px;" class="me-2"></div>
                        <small class="text-muted">Regular PRs</small>
                    </div>
                    <div class="legend-item d-flex align-items-center">
                        <div style="width: 16px; height: 12px; background-color: #28a745; border-radius: 2px;" class="me-2"></div>
                        <small class="text-muted">Konflux PRs</small>
                    </div>
                </div>
                <div class="text-center mt-3">
                    <small class="text-muted">
                        Total activity over the last 12 months: <strong>${monthlyData.reduce((sum, d) => sum + d.count, 0).toLocaleString()}</strong> PRs closed
                    </small>
                </div>
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        renderTopClosers(topClosers) {
            const container = document.getElementById('top-closers-content');
            const loadingDiv = document.getElementById('top-closers-loading');

            if (!container || !topClosers) return;

            const html = `
                <div class="leaderboard">
                    ${topClosers.slice(0, 8).map((closer, index) => {
                        let badgeClass, iconClass;
                        if (index === 0) {
                            badgeClass = 'bg-warning text-dark';
                            iconClass = 'bi-trophy-fill';
                        } else if (index === 1) {
                            badgeClass = 'bg-secondary';
                            iconClass = 'bi-award-fill';
                        } else if (index === 2) {
                            badgeClass = 'bg-danger';
                            iconClass = 'bi-award';
                        } else {
                            badgeClass = 'bg-light text-dark';
                            iconClass = 'bi-person-fill';
                        }

                        return `
                        <div class="d-flex justify-content-between align-items-center py-2 ${index < 3 ? 'border-bottom' : ''}">
                            <div class="d-flex align-items-center">
                                <span class="badge ${badgeClass} me-2">
                                    <i class="bi ${iconClass} me-1"></i>${index + 1}
                                </span>
                                <strong>${closer.username}</strong>
                            </div>
                            <div class="text-end">
                                <div class="fw-bold">${closer.count.toLocaleString()}</div>
                                <small class="text-muted">${closer.percentage}%</small>
                            </div>
                        </div>
                        `;
                    }).join('')}
                </div>
                ${topClosers.length > 8 ? `
                <div class="text-center mt-2">
                    <small class="text-muted">... and ${topClosers.length - 8} more contributors</small>
                </div>
                ` : ''}
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        renderClosurePatterns(stats) {
            const container = document.getElementById('closure-patterns-content');
            const loadingDiv = document.getElementById('closure-patterns-loading');

            if (!container || !stats) return;

            const html = `
                <div class="text-center">
                    <div class="row mb-3">
                        <div class="col-6">
                            <div class="p-3 bg-success bg-opacity-10 rounded">
                                <h4 class="text-success mb-1">${stats.self_close_percentage}%</h4>
                                <small class="text-muted">Self-Closed</small>
                                <div class="small text-muted">${stats.self_closes.toLocaleString()} PRs</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="p-3 bg-primary bg-opacity-10 rounded">
                                <h4 class="text-primary mb-1">${stats.cross_close_percentage}%</h4>
                                <small class="text-muted">Team-Closed</small>
                                <div class="small text-muted">${stats.cross_closes.toLocaleString()} PRs</div>
                            </div>
                        </div>
                    </div>

                    <div class="progress mb-3" style="height: 30px;">
                        <div class="progress-bar bg-success" role="progressbar"
                             style="width: ${stats.self_close_percentage}%"
                             aria-valuenow="${stats.self_close_percentage}"
                             title="Self-closed: ${stats.self_close_percentage}%">
                            ${stats.self_close_percentage}%
                        </div>
                        <div class="progress-bar bg-primary" role="progressbar"
                             style="width: ${stats.cross_close_percentage}%"
                             aria-valuenow="${stats.cross_close_percentage}"
                             title="Team-closed: ${stats.cross_close_percentage}%">
                            ${stats.cross_close_percentage}%
                        </div>
                    </div>

                    <p class="small text-muted mb-0">
                        ${stats.cross_close_percentage > stats.self_close_percentage
                            ? `<i class="bi bi-people-fill text-primary me-1"></i>Great collaboration! Most PRs are closed by teammates.`
                            : `<i class="bi bi-person-fill text-success me-1"></i>High autonomy! Most PRs are self-closed.`
                        }
                    </p>
                </div>
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        renderTeamInsights(insights, stats) {
            const container = document.getElementById('team-insights-content');
            const loadingDiv = document.getElementById('team-insights-loading');

            if (!container || !insights) return;

            const html = `
                <div class="row">
                    <div class="col-md-6 mb-3">
                        <div class="insight-card p-3 bg-light rounded">
                            <h6 class="text-primary mb-2">
                                <i class="bi bi-star-fill me-1"></i>Most Active Closer
                            </h6>
                            <p class="mb-1"><strong>${insights.most_active_closer}</strong></p>
                            <small class="text-muted">Leading the team in PR closures</small>
                        </div>
                    </div>
                    <div class="col-md-6 mb-3">
                        <div class="insight-card p-3 bg-light rounded">
                            <h6 class="text-primary mb-2">
                                <i class="bi bi-people-fill me-1"></i>Most Collaborative Repo
                            </h6>
                            <p class="mb-1"><strong>${insights.most_collaborative_repo}</strong></p>
                            <small class="text-muted">Highest number of different closers</small>
                        </div>
                    </div>
                </div>

                <div class="row">
                    <div class="col-md-6 mb-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="small text-muted">Total Repositories:</span>
                            <span class="badge bg-secondary">${insights.total_repositories}</span>
                        </div>
                    </div>
                    <div class="col-md-6 mb-2">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="small text-muted">Avg PRs per Closer:</span>
                            <span class="badge bg-info">${stats.avg_prs_per_closer}</span>
                        </div>
                    </div>
                </div>

                <div class="mt-3 p-2 bg-success bg-opacity-10 rounded">
                    <small class="text-success">
                        <i class="bi bi-lightbulb-fill me-1"></i>
                        <strong>Team Health:</strong>
                        ${stats.cross_close_percentage > 30
                            ? 'Excellent collaboration with good peer review practices!'
                            : stats.self_close_percentage > 70
                            ? 'High autonomy - consider more peer reviews for knowledge sharing.'
                            : 'Balanced approach between self-management and collaboration.'
                        }
                    </small>
                </div>
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        renderQuickStats(stats) {
            const container = document.getElementById('quick-stats-content');
            const loadingDiv = document.getElementById('quick-stats-loading');

            if (!container || !stats) return;

            const html = `
                <div class="quick-stats-grid">
                    <div class="stat-item text-center p-2 mb-3 bg-primary bg-opacity-10 rounded">
                        <h4 class="text-primary mb-1">${stats.total_prs.toLocaleString()}</h4>
                        <small class="text-muted">Total PRs</small>
                    </div>

                    <div class="stat-item text-center p-2 mb-3 bg-info bg-opacity-10 rounded">
                        <h4 class="text-info mb-1">${stats.total_closers.toLocaleString()}</h4>
                        <small class="text-muted">Active Closers</small>
                    </div>

                    <div class="stat-item text-center p-2 mb-3 bg-success bg-opacity-10 rounded">
                        <h4 class="text-success mb-1">${stats.avg_prs_per_closer}</h4>
                        <small class="text-muted">Avg per Closer</small>
                    </div>

                    <div class="stat-item text-center p-2 mb-3 bg-warning bg-opacity-10 rounded">
                        <h4 class="text-warning text-dark mb-1">${Math.round((stats.total_closers / (stats.total_prs / 100)) * 100)}%</h4>
                        <small class="text-muted">Participation Rate</small>
                    </div>
                </div>

                <div class="text-center">
                    <small class="text-muted">
                        📊 Organization-wide closure activity insights
                    </small>
                </div>
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        renderRepositoryBreakdown(topRepos) {
            const container = document.getElementById('repository-breakdown-content');
            const loadingDiv = document.getElementById('repository-breakdown-loading');

            if (!container || !topRepos) return;

            const maxPrs = Math.max(...topRepos.map(repo => repo.total_prs), 1);

            const html = `
                <div class="repository-chart">
                    ${topRepos.map(repo => {
                        const width = (repo.total_prs / maxPrs) * 100;
                        return `
                        <div class="repo-row mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <strong class="text-truncate" title="${repo.repository}">${repo.repository}</strong>
                                <div class="text-end">
                                    <span class="badge bg-primary">${repo.total_prs.toLocaleString()}</span>
                                    <small class="text-muted ms-2">${repo.unique_closers} closers</small>
                                </div>
                            </div>
                            <div class="progress mb-1" style="height: 20px;">
                                <div class="progress-bar repo-progress-bar" role="progressbar"
                                     style="width: ${width}%;"
                                     aria-valuenow="${width}">
                                </div>
                            </div>
                            <div class="d-flex justify-content-between">
                                <small class="text-muted">
                                    Top closer: <strong>${repo.top_closer}</strong> (${repo.top_closer_count})
                                </small>
                                <small class="text-muted">
                                    ${Math.round((repo.top_closer_count / repo.total_prs) * 100)}% dominance
                                </small>
                            </div>
                        </div>
                        `;
                    }).join('')}
                </div>

                <div class="text-center mt-3">
                    <small class="text-muted">
                        📊 Showing top ${topRepos.length} most active repositories by PR/MR closure volume
                    </small>
                </div>

                <style>
                    .progress-bar.repo-progress-bar {
                        background: linear-gradient(45deg, #007bff, #0056b3) !important;
                    }
                </style>
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        renderKonfluxRepositoryBreakdown(topRepos) {
            const container = document.getElementById('konflux-repository-breakdown-content');
            const loadingDiv = document.getElementById('konflux-repository-breakdown-loading');

            if (!container) return;

            if (!topRepos || topRepos.length === 0) {
                const html = `
                    <div class="text-center py-4">
                        <div class="text-muted">
                            <i class="bi bi-info-circle me-1"></i>
                            No Konflux PRs found in this date range.
                        </div>
                    </div>
                `;
                container.innerHTML = html;
                loadingDiv.classList.add('d-none');
                container.classList.remove('d-none');
                return;
            }

            const maxPrs = Math.max(...topRepos.map(repo => repo.total_prs), 1);

            const html = `
                <div class="repository-chart">
                    ${topRepos.map(repo => {
                        const width = (repo.total_prs / maxPrs) * 100;
                        return `
                        <div class="repo-row mb-3">
                            <div class="d-flex justify-content-between align-items-center mb-1">
                                <strong class="text-truncate" title="${repo.repository}">${repo.repository}</strong>
                                <div class="text-end">
                                    <span class="badge bg-success">${repo.total_prs.toLocaleString()}</span>
                                    <small class="text-muted ms-2">${repo.unique_closers} closers</small>
                                </div>
                            </div>
                            <div class="progress mb-1" style="height: 20px;">
                                <div class="progress-bar konflux-progress-bar" role="progressbar"
                                     style="width: ${width}%;"
                                     aria-valuenow="${width}">
                                </div>
                            </div>
                            <div class="d-flex justify-content-between">
                                <small class="text-muted">
                                    Top closer: <strong>${repo.top_closer}</strong> (${repo.top_closer_count})
                                </small>
                                <small class="text-muted">
                                    ${Math.round((repo.top_closer_count / repo.total_prs) * 100)}% dominance
                                </small>
                            </div>
                        </div>
                        `;
                    }).join('')}
                </div>

                <div class="text-center mt-3">
                    <small class="text-muted">
                        🤖 Showing top ${topRepos.length} most active repositories by Konflux PR closure volume
                    </small>
                </div>

                <style>
                    .progress-bar.konflux-progress-bar {
                        background: linear-gradient(45deg, #28a745, #1e7e34) !important;
                    }
                </style>
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        showError(containerId, errorMessage) {
            const container = document.getElementById(`${containerId}-content`);
            const loadingDiv = document.getElementById(`${containerId}-loading`);

            if (container) {
                container.innerHTML = `
                    <div class="text-center py-4">
                        <i class="bi bi-exclamation-triangle text-warning mb-2" style="font-size: 2rem;"></i>
                        <p class="text-muted mb-0">${errorMessage}</p>
                    </div>
                `;
                container.classList.remove('d-none');
            }

            if (loadingDiv) {
                loadingDiv.classList.add('d-none');
            }
        }

        setupDateRangeListener() {
            // Listen for changes to date range inputs
            const dateInputs = document.querySelectorAll('input[type="date"]');
            dateInputs.forEach(input => {
                input.addEventListener('change', () => {
                    console.log('📅 Date range changed, refreshing close actor statistics...');
                    // Add small delay to allow URL to update
                    setTimeout(() => {
                        this.refreshStatistics();
                    }, 100);
                });
            });

            // Listen for URL parameter changes (for programmatic updates)
            let currentUrl = window.location.href;
            const urlObserver = setInterval(() => {
                if (window.location.href !== currentUrl) {
                    currentUrl = window.location.href;
                    console.log('🔄 URL changed, refreshing close actor statistics...');
                    setTimeout(() => {
                        this.refreshStatistics();
                    }, 100);
                }
            }, 1000);

            // Store observer for cleanup if needed
            this.urlObserver = urlObserver;
        }

        async loadTeamStatistics(dateFrom, dateTo) {
            try {

                // Build API URLs with date parameters
                const apiParams = new URLSearchParams();
                if (dateFrom) apiParams.set('date_from', dateFrom);
                if (dateTo) apiParams.set('date_to', dateTo);
                const queryString = apiParams.toString() ? '?' + apiParams.toString() : '';

                // Load team stats in parallel
                const [teamResponse, teamKonfluxResponse] = await Promise.all([
                    fetch('/api/enhance/close-actor/team-stats' + queryString),
                    fetch('/api/enhance/close-actor/team-konflux-stats' + queryString)
                ]);

                const teamData = await teamResponse.json();
                const teamKonfluxData = await teamKonfluxResponse.json();

                if (teamData.error) {
                    this.showError('team-close-stats', teamData.error);
                    return;
                }

                if (teamKonfluxData.error) {
                    this.showError('team-konflux-stats', teamKonfluxData.error);
                    return;
                }

                // Render team statistics
                this.renderTeamCloseStats(teamData);
                this.renderTeamKonfluxActivity(teamKonfluxData);
                this.renderTeamMonthlyActivity(teamData.monthly_activity);

            } catch (error) {
                console.error('❌ Error loading team statistics:', error);
                this.showError('team-close-stats', 'Failed to load team statistics');
                this.showError('team-konflux-stats', 'Failed to load team Konflux statistics');
                this.showError('team-monthly-activity', 'Failed to load team monthly activity');
            }
        }

        renderTeamCloseStats(data) {
            const container = document.getElementById('team-close-stats-content');
            const loadingDiv = document.getElementById('team-close-stats-loading');

            if (!container) return;

            const stats = data.stats;

            const html = `
                <div class="row text-center">
                    <div class="col-6">
                        <div class="p-3 bg-success bg-opacity-10 rounded">
                            <h3 class="text-success mb-1">${stats.merged_prs_closed.toLocaleString()}</h3>
                            <small class="text-muted">Merged PRs Closed</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="p-3 bg-danger bg-opacity-10 rounded">
                            <h3 class="text-danger mb-1">${stats.closed_prs_closed.toLocaleString()}</h3>
                            <small class="text-muted">Closed PRs Closed</small>
                        </div>
                    </div>
                </div>
                <hr>
                <div class="text-center">
                    <h4 class="text-primary mb-2">${stats.total_closed.toLocaleString()}</h4>
                    <p class="mb-2">Total GitHub PRs Closed by <strong>Team</strong></p>
                </div>
                ${stats.total_closed > 0 ? `
                <hr>
                <div class="row">
                    <div class="col-6">
                        <h6 class="text-muted mb-2">Top Repositories:</h6>
                        <div class="row">
                            ${Object.entries(data.top_repositories)
                                .sort(([,a], [,b]) => b - a)
                                .slice(0, 5)
                                .map(([repo, count]) => `
                            <div class="col-12 mb-1">
                                <div class="d-flex justify-content-between align-items-center small">
                                    <span class="text-truncate" title="${repo}">${repo}</span>
                                    <span class="badge bg-secondary">${count}</span>
                                </div>
                            </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="col-6">
                        <h6 class="text-muted mb-2">Top Close Actors:</h6>
                        <div class="row">
                            ${Object.entries(data.top_closers)
                                .sort(([,a], [,b]) => b - a)
                                .slice(0, 5)
                                .map(([user, count]) => `
                            <div class="col-12 mb-1">
                                <div class="d-flex justify-content-between align-items-center small">
                                    <span class="text-truncate" title="${user}">${user}</span>
                                    <span class="badge bg-primary">${count}</span>
                                </div>
                            </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                ` : ''}
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        renderTeamKonfluxActivity(data) {
            const container = document.getElementById('team-konflux-stats-content');
            const loadingDiv = document.getElementById('team-konflux-stats-loading');

            if (!container) return;

            const stats = data.stats;

            const html = `
                <div class="row text-center">
                    <div class="col-6">
                        <div class="p-3 bg-success bg-opacity-10 rounded">
                            <h3 class="text-success mb-1">${stats.merged_prs_closed.toLocaleString()}</h3>
                            <small class="text-muted">Konflux Merged PRs Closed</small>
                        </div>
                    </div>
                    <div class="col-6">
                        <div class="p-3 bg-danger bg-opacity-10 rounded">
                            <h3 class="text-danger mb-1">${stats.closed_prs_closed.toLocaleString()}</h3>
                            <small class="text-muted">Konflux Closed PRs Closed</small>
                        </div>
                    </div>
                </div>
                <hr>
                <div class="text-center">
                    <h4 class="text-primary mb-2">${stats.total_closed.toLocaleString()}</h4>
                    <p class="mb-2">Total Konflux GitHub PRs Closed by <strong>Team</strong></p>
                </div>
                ${stats.total_closed > 0 ? `
                <hr>
                <div class="row">
                    <div class="col-6">
                        <h6 class="text-muted mb-2">Top Konflux Repositories:</h6>
                        <div class="row">
                            ${Object.entries(data.top_repositories)
                                .sort(([,a], [,b]) => b - a)
                                .slice(0, 5)
                                .map(([repo, count]) => `
                            <div class="col-12 mb-1">
                                <div class="d-flex justify-content-between align-items-center small">
                                    <span class="text-truncate" title="${repo}">${repo}</span>
                                    <span class="badge bg-secondary">${count}</span>
                                </div>
                            </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="col-6">
                        <h6 class="text-muted mb-2">Top Close Actors:</h6>
                        <div class="row">
                            ${Object.entries(data.top_closers || {})
                                .sort(([,a], [,b]) => b - a)
                                .slice(0, 5)
                                .map(([user, count]) => `
                            <div class="col-12 mb-1">
                                <div class="d-flex justify-content-between align-items-center small">
                                    <span class="text-truncate" title="${user}">${user}</span>
                                    <span class="badge bg-primary">${count}</span>
                                </div>
                            </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
                ` : `
                <div class="text-center mt-3">
                    <div class="text-muted">
                        <i class="bi bi-info-circle me-1"></i>
                        No Konflux PRs closed yet in this date range.
                    </div>
                </div>
                `}
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        renderTeamMonthlyActivity(monthlyData) {
            const container = document.getElementById('team-monthly-activity-content');
            const loadingDiv = document.getElementById('team-monthly-activity-loading');

            if (!container || !monthlyData) return;

            // Use stacked bar chart logic to show both Konflux and regular PRs
            const maxCount = Math.max(...monthlyData.map(d => d.count), 1);

            const html = `
                <div class="monthly-chart">
                    ${monthlyData.map(data => {
                        const totalHeight = (data.count / maxCount) * 100;
                        const konfluxHeight = data.konflux > 0 ? (data.konflux / data.count) * totalHeight : 0;
                        const regularHeight = data.regular > 0 ? (data.regular / data.count) * totalHeight : 0;

                        return `
                        <div class="month-bar d-flex flex-column align-items-center" style="flex: 1;">
                            <div class="bar-container d-flex align-items-end justify-content-center" style="height: 120px; position: relative;">
                                <div class="stacked-bar" style="width: 38px; height: ${totalHeight}%; display: flex; flex-direction: column; justify-content: flex-end;">
                                    ${data.regular > 0 ? `
                                    <div class="bar regular-bar bg-primary"
                                         style="height: ${regularHeight}%; min-height: ${data.regular > 0 ? '2px' : '0'}; border-radius: ${data.konflux > 0 ? '0' : '2px 2px 0 0'};"
                                         title="${data.month}: ${data.regular} regular PRs closed by team">
                                    </div>
                                    ` : ''}
                                    ${data.konflux > 0 ? `
                                    <div class="bar konflux-bar"
                                         style="background-color: #28a745; height: ${konfluxHeight}%; min-height: ${data.konflux > 0 ? '2px' : '0'}; border-radius: 2px 2px 0 0;"
                                         title="${data.month}: ${data.konflux} Konflux PRs closed by team">
                                    </div>
                                    ` : ''}
                                </div>
                                ${data.count > 0 ? `
                                <span class="count-label position-absolute small text-dark"
                                      style="top: -20px; font-weight: bold;">${data.count}</span>
                                ` : ''}
                            </div>
                            <small class="month-label text-muted mt-1" style="font-size: 0.9rem; text-align: center; font-weight: 500;">
                                ${this.formatMonthLabel(data.month)}
                            </small>
                        </div>
                        `;
                    }).join('')}
                </div>
                <div class="legend mt-3 d-flex justify-content-center">
                    <div class="legend-item d-flex align-items-center me-3">
                        <div style="width: 16px; height: 12px; background-color: #0d6efd; border-radius: 2px;" class="me-2"></div>
                        <small class="text-muted">Regular PRs</small>
                    </div>
                    <div class="legend-item d-flex align-items-center">
                        <div style="width: 16px; height: 12px; background-color: #28a745; border-radius: 2px;" class="me-2"></div>
                        <small class="text-muted">Konflux PRs</small>
                    </div>
                </div>
                <style>
                    .monthly-chart {
                        display: flex;
                        align-items: end;
                        gap: 4px;
                        min-height: 140px;
                        padding: 0 10px;
                    }
                    .bar {
                        transition: all 0.3s ease;
                    }
                    .bar:hover {
                        opacity: 0.8;
                        transform: scaleY(1.05);
                    }
                    .stacked-bar {
                        transition: all 0.3s ease;
                    }
                    .regular-bar {
                        border-radius: 0 0 0 0;
                    }
                    .konflux-bar {
                        border-radius: 2px 2px 0 0;
                    }
                </style>
                <div class="text-center mt-3">
                    <small class="text-muted">
                        Team activity over the last 12 months: <strong>${monthlyData.reduce((sum, d) => sum + d.count, 0).toLocaleString()}</strong> PRs closed
                    </small>
                </div>
            `;

            container.innerHTML = html;
            loadingDiv.classList.add('d-none');
            container.classList.remove('d-none');
        }

        showError(containerId, message) {
            const container = document.getElementById(`${containerId}-content`);
            const loadingDiv = document.getElementById(`${containerId}-loading`);

            if (container && loadingDiv) {
                container.innerHTML = `
                    <div class="alert alert-danger" role="alert">
                        <i class="bi bi-exclamation-triangle me-2"></i>${message}
                    </div>
                `;

                loadingDiv.classList.add('d-none');
                container.classList.remove('d-none');
            }
        }

        refreshStatistics() {
            const perfectCoverageSection = document.getElementById('perfect-coverage-section');

            // Only refresh if the section is visible (statistics are active)
            if (perfectCoverageSection && !perfectCoverageSection.classList.contains('d-none')) {
                console.log('🔄 Refreshing close actor statistics with current URL parameters...');
                // Allow refresh even if previously loaded (for date range changes)
                this.loadStatistics();
            }
        }
    }

    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        window.closeActorStatistics = new CloseActorStatistics();
        window.closeActorStatisticsInitialized = true;
    });

})();
