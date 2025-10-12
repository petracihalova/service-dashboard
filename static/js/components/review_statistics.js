/**
 * PR Review Statistics Component
 *
 * Handles fetching and displaying PR review statistics for personal and team views.
 */

/**
 * Detect which page we're on
 */
function isAllDataStatsPage() {
    const url = window.location.pathname;
    const pageTitle = document.querySelector('h1')?.textContent.trim() || '';
    return url.includes('all-data-stats') || pageTitle.includes('All Data Statistics');
}

/**
 * Load and display review statistics
 */
async function loadReviewStatistics() {
    const reviewStatsSection = document.getElementById('review-stats-section');
    if (!reviewStatsSection) return;

    try {
        // Check if review data is available
        const statusResponse = await fetch('/api/enhance/reviews/status');
        const status = await statusResponse.json();

        if (!status.is_available) {
            // Hide the review stats section if data is not available
            reviewStatsSection.classList.add('d-none');
            return;
        }

        // Show the review stats section
        reviewStatsSection.classList.remove('d-none');

        // Determine which page we're on and load appropriate stats
        const isAllDataPage = isAllDataStatsPage();

        if (isAllDataPage) {
            // All Data Statistics page - load team stats only
            await loadTeamReviewStatsAllData();
        } else {
            // Personal Statistics page - load personal statistics only (team stats are on All Data page)
            await loadPersonalReviewStats();
        }

    } catch (error) {
        console.error('Error loading review statistics:', error);
        reviewStatsSection.classList.add('d-none');
    }
}

/**
 * Load personal review statistics (both non-Konflux and Konflux)
 */
async function loadPersonalReviewStats() {
    const loadingEl = document.getElementById('personal-review-stats-loading');
    const contentEl = document.getElementById('personal-review-stats-content');

    if (!loadingEl || !contentEl) return;

    try {
        // Get date range from URL or inputs
        const urlParams = new URLSearchParams(window.location.search);
        const dateFrom = urlParams.get('from') || document.getElementById('date-from-input')?.value;
        const dateTo = urlParams.get('to') || document.getElementById('date-to-input')?.value;

        // Fetch both non-Konflux and Konflux stats
        const [nonKonfluxData, konfluxData] = await Promise.all([
            fetchPersonalStats(dateFrom, dateTo, 'non-konflux'),
            fetchPersonalStats(dateFrom, dateTo, 'konflux')
        ]);

        if (nonKonfluxData.error && konfluxData.error) {
            contentEl.innerHTML = `
                <div class="alert alert-warning mb-0">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    ${nonKonfluxData.error}
                </div>
            `;
        } else {
            contentEl.innerHTML = generateCombinedPersonalReviewStatsHTML(nonKonfluxData, konfluxData);
        }

        // Show content, hide loading
        loadingEl.classList.add('d-none');
        contentEl.classList.remove('d-none');

    } catch (error) {
        console.error('Error loading personal review stats:', error);
        contentEl.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="bi bi-exclamation-circle me-2"></i>
                Error loading review statistics
            </div>
        `;
        loadingEl.classList.add('d-none');
        contentEl.classList.remove('d-none');
    }
}

/**
 * Load team review statistics for All Data Statistics page (both non-Konflux and Konflux)
 */
async function loadTeamReviewStatsAllData() {
    const loadingEl = document.getElementById('team-review-stats-loading-all');
    const contentEl = document.getElementById('team-review-stats-content-all');

    if (!loadingEl || !contentEl) return;

    try {
        // Get date range from URL or inputs
        const urlParams = new URLSearchParams(window.location.search);
        const dateFrom = urlParams.get('from') || document.getElementById('date-from-input')?.value;
        const dateTo = urlParams.get('to') || document.getElementById('date-to-input')?.value;

        // Fetch both non-Konflux and Konflux stats
        const [nonKonfluxData, konfluxData] = await Promise.all([
            fetchTeamStats(dateFrom, dateTo, 'non-konflux'),
            fetchTeamStats(dateFrom, dateTo, 'konflux')
        ]);

        if (nonKonfluxData.error && konfluxData.error) {
            contentEl.innerHTML = `
                <div class="alert alert-warning mb-0">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    ${nonKonfluxData.error}
                </div>
            `;
        } else {
            contentEl.innerHTML = generateCombinedTeamReviewStatsHTML(nonKonfluxData, konfluxData);
        }

        // Show content, hide loading
        loadingEl.classList.add('d-none');
        contentEl.classList.remove('d-none');

    } catch (error) {
        console.error('Error loading team review stats (all data):', error);
        contentEl.innerHTML = `
            <div class="alert alert-danger mb-0">
                <i class="bi bi-exclamation-circle me-2"></i>
                Error loading team statistics
            </div>
        `;
        loadingEl.classList.add('d-none');
        contentEl.classList.remove('d-none');
    }
}

/**
 * Helper function to fetch personal stats with Konflux filter
 */
async function fetchPersonalStats(dateFrom, dateTo, konfluxFilter) {
    try {
        let url = '/api/enhance/reviews/personal-stats';
        const params = new URLSearchParams();
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        if (konfluxFilter) params.append('konflux_filter', konfluxFilter);
        if (params.toString()) url += '?' + params.toString();

        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${konfluxFilter} personal stats:`, error);
        return { error: error.message };
    }
}

/**
 * Helper function to fetch team stats with Konflux filter
 */
async function fetchTeamStats(dateFrom, dateTo, konfluxFilter) {
    try {
        let url = '/api/enhance/reviews/team-stats';
        const params = new URLSearchParams();
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        if (konfluxFilter) params.append('konflux_filter', konfluxFilter);
        if (params.toString()) url += '?' + params.toString();

        const response = await fetch(url);
        return await response.json();
    } catch (error) {
        console.error(`Error fetching ${konfluxFilter} team stats:`, error);
        return { error: error.message };
    }
}

/**
 * Generate combined HTML for both non-Konflux and Konflux personal review statistics
 */
function generateCombinedPersonalReviewStatsHTML(nonKonfluxData, konfluxData) {
    let html = '<div class="row">';

    // Non-Konflux PRs Section
    if (!nonKonfluxData.error) {
        html += `
            <div class="col-lg-6 mb-3">
                <h6 class="text-primary mb-3">
                    <i class="bi bi-people me-2"></i>Your Reviews (without Konflux PRs)
                </h6>
                ${generatePersonalReviewStatsHTML(nonKonfluxData)}
            </div>
        `;
    }

    // Konflux PRs Section
    if (!konfluxData.error) {
        html += `
            <div class="col-lg-6 mb-3">
                <h6 class="text-primary mb-3">
                    <i class="bi bi-robot me-2"></i>Your Reviews (Konflux PRs only)
                </h6>
                ${generatePersonalReviewStatsHTML(konfluxData)}
            </div>
        `;
    }

    html += '</div>';

    if (nonKonfluxData.error && konfluxData.error) {
        html = `
            <div class="alert alert-warning mb-0">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Unable to load review statistics
            </div>
        `;
    }

    return html;
}

/**
 * Generate combined HTML for both non-Konflux and Konflux team review statistics
 */
function generateCombinedTeamReviewStatsHTML(nonKonfluxData, konfluxData) {
    let html = '';

    if (nonKonfluxData.error && konfluxData.error) {
        return `
            <div class="alert alert-warning mb-0">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Unable to load review statistics
            </div>
        `;
    }

    // Two-column layout
    html += '<div class="row">';

    // Non-Konflux PRs Section (Left Column)
    if (!nonKonfluxData.error) {
        html += `
            <div class="col-md-6">
                <h6 class="text-primary mb-3">
                    <i class="bi bi-people me-2"></i>Team Reviews (without Konflux PRs)
                </h6>
                ${generateTeamReviewStatsHTML(nonKonfluxData, 'non-konflux')}
            </div>
        `;
    }

    // Konflux PRs Section (Right Column)
    if (!konfluxData.error) {
        html += `
            <div class="col-md-6">
                <h6 class="text-primary mb-3">
                    <i class="bi bi-robot me-2"></i>Team Reviews (Konflux PRs only)
                </h6>
                ${generateTeamReviewStatsHTML(konfluxData, 'konflux')}
            </div>
        `;
    }

    html += '</div>'; // Close row

    return html;
}

/**
 * Generate HTML for personal review statistics
 */
function generatePersonalReviewStatsHTML(data) {
    const { total_reviews, merged_reviews, closed_reviews, by_repository } = data;

    if (total_reviews === 0) {
        return `
            <div class="alert alert-info mb-0">
                <i class="bi bi-info-circle me-2"></i>
                No review activity found in this date range.
            </div>
        `;
    }

    // Sort repositories by total reviews
    const sortedRepos = Object.entries(by_repository)
        .sort((a, b) => b[1].total - a[1].total)
        .slice(0, 10); // Show top 10

    let html = `
        <div class="mb-4">
            <h6 class="text-primary mb-3">Review Summary</h6>
            <div class="row g-3">
                <div class="col-4">
                    <div class="text-center p-3 bg-light rounded">
                        <div class="h3 mb-1 text-primary">${total_reviews}</div>
                        <div class="small text-muted">Total Reviews</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="text-center p-3 bg-light rounded">
                        <div class="h3 mb-1 text-success">${merged_reviews}</div>
                        <div class="small text-muted">Merged PRs</div>
                    </div>
                </div>
                <div class="col-4">
                    <div class="text-center p-3 bg-light rounded">
                        <div class="h3 mb-1 text-danger">${closed_reviews}</div>
                        <div class="small text-muted">Closed PRs</div>
                    </div>
                </div>
            </div>
        </div>
    `;

    if (sortedRepos.length > 0) {
        html += `
            <div>
                <h6 class="text-primary mb-3">Top Repositories</h6>
                <div class="table-responsive">
                    <table class="table table-sm table-hover">
                        <thead>
                            <tr>
                                <th>Repository</th>
                                <th class="text-center">Merged</th>
                                <th class="text-center">Closed</th>
                                <th class="text-center">Total</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        for (const [repo, stats] of sortedRepos) {
            const repoShortName = repo.split('/').pop();
            html += `
                <tr>
                    <td>
                        <code class="small">${repoShortName}</code>
                    </td>
                    <td class="text-center">
                        <span class="badge bg-success">${stats.merged}</span>
                    </td>
                    <td class="text-center">
                        <span class="badge bg-danger">${stats.closed}</span>
                    </td>
                    <td class="text-center">
                        <strong>${stats.total}</strong>
                    </td>
                </tr>
            `;
        }

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    return html;
}

/**
 * Generate modal HTML for PRs without reviews
 * @param {Array} prsList - List of PRs without reviews
 * @param {string} modalId - Unique modal ID
 * @param {string} filterType - Optional filter type ('non-konflux' or 'konflux')
 */
function generatePRsWithoutReviewsModal(prsList, modalId, filterType) {
    const filterLabel = filterType === 'non-konflux' ? ' (without Konflux PRs)' :
                        filterType === 'konflux' ? ' (Konflux PRs only)' : '';

    // Count merged vs closed
    const mergedCount = prsList.filter(pr => pr.state === 'merged').length;
    const closedCount = prsList.filter(pr => pr.state === 'closed').length;

    let html = `
        <div class="modal fade" id="${modalId}" tabindex="-1" aria-labelledby="${modalId}Label" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-scrollable">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title" id="${modalId}Label">PRs Without Reviews${filterLabel}</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <p><strong>${prsList.length} PRs</strong> have no reviews in this date range (<strong>${mergedCount} merged</strong>, <strong>${closedCount} closed</strong>).</p>
                        <div class="table-responsive">
                            <table class="table table-sm table-hover">
                                <thead>
                                    <tr>
                                        <th style="width: 10%">State</th>
                                        <th style="width: 15%">Repository</th>
                                        <th>PR Title</th>
                                        <th style="width: 13%">Author</th>
                                        <th style="width: 13%">Closed By</th>
                                        <th style="width: 12%">Date</th>
                                    </tr>
                                </thead>
                                <tbody>
    `;

    // Sort by date (most recent first)
    const sortedPRs = [...prsList].sort((a, b) => {
        return new Date(b.date) - new Date(a.date);
    });

    sortedPRs.forEach(pr => {
        const stateBadge = pr.state === 'merged' ?
            '<span class="badge bg-success">Merged</span>' :
            '<span class="badge bg-danger">Closed</span>';
        const repoName = pr.repo.split('/').pop();
        const date = new Date(pr.date).toLocaleDateString();
        const closeActor = pr.close_actor ?
            `<code class="small">${pr.close_actor}</code>` :
            '<span class="text-muted small">N/A</span>';

        html += `
            <tr>
                <td>${stateBadge}</td>
                <td><code class="small">${repoName}</code></td>
                <td>
                    <a href="${pr.url}" target="_blank" class="text-decoration-none">
                        #${pr.number}: ${pr.title}
                        <i class="bi bi-box-arrow-up-right small ms-1"></i>
                    </a>
                </td>
                <td><code class="small">${pr.author}</code></td>
                <td>${closeActor}</td>
                <td class="small text-muted">${date}</td>
            </tr>
        `;
    });

    html += `
                                </tbody>
                            </table>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    return html;
}

/**
 * Generate HTML for team review statistics
 * @param {Object} data - The review statistics data
 * @param {string} filterType - Optional filter type ('non-konflux' or 'konflux')
 */
function generateTeamReviewStatsHTML(data, filterType = null) {
    const { by_user, total_prs, prs_with_reviews, prs_without_reviews, prs_with_one_review = 0, prs_with_multiple_reviews = 0, prs_without_reviews_list = [] } = data;

    if (!by_user || Object.keys(by_user).length === 0) {
        // Check if we have PR counts even with no reviewers
        if (total_prs && total_prs > 0) {
            return `
                <div class="alert alert-info mb-0">
                    <i class="bi bi-info-circle me-2"></i>
                    <strong>${total_prs} PRs analyzed</strong> - No reviews found in this date range.
                </div>
            `;
        }
        return `
            <div class="alert alert-info mb-0">
                <i class="bi bi-info-circle me-2"></i>
                No team review activity found in this date range.
            </div>
        `;
    }

    // Sort users by total reviews
    const sortedUsers = Object.entries(by_user)
        .sort((a, b) => b[1].total - a[1].total)
        .slice(0, 15); // Show top 15 reviewers

    let html = '';

    // Add PR summary at the top if available
    if (total_prs) {
        const reviewPercentage = total_prs > 0 ? ((prs_with_reviews / total_prs) * 100).toFixed(1) : 0;
        const oneReviewPercentage = total_prs > 0 ? ((prs_with_one_review / total_prs) * 100).toFixed(1) : 0;
        const multipleReviewsPercentage = total_prs > 0 ? ((prs_with_multiple_reviews / total_prs) * 100).toFixed(1) : 0;
        const noReviewPercentage = total_prs > 0 ? ((prs_without_reviews / total_prs) * 100).toFixed(1) : 0;

        // Generate unique modal ID based on filter type
        const modalId = `prsWithoutReviewsModal${filterType ? '-' + filterType : ''}`;

        html += `
            <div class="alert alert-info mb-3">
                <div class="row g-2 text-center">
                    <div class="col-md-3">
                        <div class="h4 mb-1">${total_prs}</div>
                        <div class="small text-muted">Total PRs</div>
                    </div>
                    <div class="col-md-3">
                        <div class="h4 mb-1 text-warning">${prs_without_reviews}</div>
                        <div class="small text-muted">
                            0 Reviews (${noReviewPercentage}%)
                            ${prs_without_reviews > 0 ? `
                                <button type="button" class="btn btn-sm btn-link p-0 ms-1"
                                        data-bs-toggle="modal"
                                        data-bs-target="#${modalId}">
                                    <i class="bi bi-info-circle"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="h4 mb-1 text-info">${prs_with_one_review}</div>
                        <div class="small text-muted">1 Review (${oneReviewPercentage}%)</div>
                    </div>
                    <div class="col-md-3">
                        <div class="h4 mb-1 text-success">${prs_with_multiple_reviews}</div>
                        <div class="small text-muted">2+ Reviews (${multipleReviewsPercentage}%)</div>
                    </div>
                </div>
            </div>
        `;

        // Generate modal for PRs without reviews if there are any
        if (prs_without_reviews > 0 && prs_without_reviews_list.length > 0) {
            html += generatePRsWithoutReviewsModal(prs_without_reviews_list, modalId, filterType);
        }
    }

    html += `
        <div class="mb-3">
            <h6 class="text-primary mb-3">Top Reviewers</h6>
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead>
                        <tr>
                            <th>#</th>
                            <th>Reviewer</th>
                            <th class="text-center">Merged</th>
                            <th class="text-center">Closed</th>
                            <th class="text-center">Total Reviews</th>
                        </tr>
                    </thead>
                    <tbody>
    `;

    sortedUsers.forEach(([username, stats], index) => {
        const rankClass = index === 0 ? 'text-warning' : index === 1 ? 'text-secondary' : index === 2 ? 'text-warning-emphasis' : '';
        const rankIcon = index === 0 ? '🥇' : index === 1 ? '🥈' : index === 2 ? '🥉' : '';

        html += `
            <tr>
                <td class="${rankClass}"><strong>${rankIcon || (index + 1)}</strong></td>
                <td>
                    <code>${username}</code>
                </td>
                <td class="text-center">
                    <span class="badge bg-success">${stats.merged}</span>
                </td>
                <td class="text-center">
                    <span class="badge bg-danger">${stats.closed}</span>
                </td>
                <td class="text-center">
                    <strong>${stats.total}</strong>
                </td>
            </tr>
        `;
    });

    html += `
                    </tbody>
                </table>
            </div>
        </div>
    `;

    // Add total summary
    const totalReviews = Object.values(by_user).reduce((sum, stats) => sum + stats.total, 0);
    const totalMerged = Object.values(by_user).reduce((sum, stats) => sum + stats.merged, 0);
    const totalClosed = Object.values(by_user).reduce((sum, stats) => sum + stats.closed, 0);

    html += `
        <div class="border-top pt-3 mt-3">
            <div class="row g-2">
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="text-muted">Total Reviews Given:</span>
                        <span>
                            <span class="badge bg-success me-1">${totalMerged} merged</span>
                            <span class="badge bg-danger me-1">${totalClosed} closed</span>
                            <span class="badge bg-primary">${totalReviews} total</span>
                        </span>
                    </div>
                </div>
                <div class="col-12">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="text-muted">Active Reviewers:</span>
                        <strong>${Object.keys(by_user).length}</strong>
                    </div>
                </div>
            </div>
        </div>
    `;

    return html;
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        // Check if we're on the personal stats page
        if (document.getElementById('review-stats-section')) {
            loadReviewStatistics();
        }
    });
} else {
    if (document.getElementById('review-stats-section')) {
        loadReviewStatistics();
    }
}
