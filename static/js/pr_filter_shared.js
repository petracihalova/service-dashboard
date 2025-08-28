/**
 * Shared PR/MR filtering functionality for both open and merged pull requests pages
 */

class PRFilterUtils {
    constructor() {
        this.usernameInput = document.getElementById('username-input');
        this.applyUsernameButton = document.getElementById('apply-username');
        this.myPrsToggle = document.getElementById('my-prs-toggle') || document.getElementById('my-mrs-toggle');
        this.clearFiltersButton = document.getElementById('clear-filters');
        this.filterKonfluxButton = document.getElementById('filter-konflux');

        // Determine if this is app-interface page (uses my_mrs parameter)
        this.isAppInterface = !!document.getElementById('my-mrs-toggle');

        console.log('PRFilterUtils initialized with elements:', {
            usernameInput: !!this.usernameInput,
            applyUsernameButton: !!this.applyUsernameButton,
            myPrsToggle: !!this.myPrsToggle,
            clearFiltersButton: !!this.clearFiltersButton,
            filterKonfluxButton: !!this.filterKonfluxButton,
            isAppInterface: this.isAppInterface
        });
    }

    applyUsernameFilter() {
        const username = this.usernameInput.value.trim();

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        if (username) {
            urlParams.set('username', username);
            // Clear my_prs/my_mrs parameter when using custom username
            urlParams.delete('my_prs');
            urlParams.delete('my_mrs');

            // Visually deactivate "My PRs/MRs" toggle if it's active
            if (this.myPrsToggle && this.myPrsToggle.dataset.active === 'true') {
                this.myPrsToggle.dataset.active = 'false';
                // Remove checkmark and update button appearance
                this.myPrsToggle.innerHTML = this.myPrsToggle.innerHTML.replace('✓', '').trim();
                this.myPrsToggle.classList.remove('active');
            }
        } else {
            // If username is empty, just remove the username parameter
            urlParams.delete('username');
        }

        // Navigate to new URL
        this.navigateWithLoadingState(this.applyUsernameButton, 'Loading...', urlParams);
    }

    toggleMyPrs() {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        const isActive = this.myPrsToggle.dataset.active === 'true';
        const paramName = this.isAppInterface ? 'my_mrs' : 'my_prs';

        if (isActive) {
            // Turn off "My PRs/MRs" filter
            urlParams.delete(paramName);
            urlParams.delete('username');
        } else {
            // Turn on "My PRs/MRs" filter - clear custom username filter
            urlParams.set(paramName, 'true');
            urlParams.delete('username');

            // Clear username input field visually
            if (this.usernameInput) {
                this.usernameInput.value = '';
            }
        }

        // Navigate to new URL
        this.navigateWithLoadingState(this.myPrsToggle, 'Loading...', urlParams);
    }

    clearAllFilters() {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        // Remove filter parameters (but keep days for merged PR page)
        urlParams.delete('username');
        urlParams.delete('my_prs');
        urlParams.delete('my_mrs');

        // Remove date range parameters
        urlParams.delete('date_from');
        urlParams.delete('date_to');

        // Clear date range inputs and localStorage if available
        if (window.clearDateRangeFilter) {
            // Clear the date inputs visually (but don't navigate - we'll do that below)
            const dateFromInput = document.getElementById('date-from-input');
            const dateToInput = document.getElementById('date-to-input');
            if (dateFromInput) dateFromInput.value = '';
            if (dateToInput) dateToInput.value = '';

            // Clear date range from localStorage
            try {
                // Determine which storage key to clear based on current page
                const path = window.location.pathname;
                let storageKey = 'mergedPR_dateRange'; // default
                if (path.includes('app-interface-merged')) {
                    storageKey = 'appInterfaceMerged_dateRange';
                } else if (path.includes('jira-closed-tickets')) {
                    storageKey = 'jiraClosedTickets_dateRange';
                }
                localStorage.removeItem(storageKey);
            } catch (e) {
                console.warn('Error clearing date range from localStorage:', e);
            }
        }

        // Navigate to new URL
        this.navigateWithLoadingState(this.clearFiltersButton, 'Loading...', urlParams);
    }

    toggleKonfluxFilter() {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        const isActive = this.filterKonfluxButton.dataset.active === 'true';

        if (isActive) {
            // Turn off Konflux filter
            urlParams.delete('username');
        } else {
            // Turn on Konflux filter - set username to 'konflux' and clear other filters
            urlParams.set('username', 'konflux');
            urlParams.delete('my_prs');
            urlParams.delete('my_mrs');

            // Update username input field visually
            if (this.usernameInput) {
                this.usernameInput.value = 'konflux';
            }

            // Visually deactivate "My PRs/MRs" toggle if it's active
            if (this.myPrsToggle && this.myPrsToggle.dataset.active === 'true') {
                this.myPrsToggle.dataset.active = 'false';
                this.myPrsToggle.innerHTML = this.myPrsToggle.innerHTML.replace('✓', '').trim();
                this.myPrsToggle.classList.remove('active');
            }
        }

        // Navigate to new URL
        this.navigateWithLoadingState(this.filterKonfluxButton, 'Loading...', urlParams);
    }

    navigateWithLoadingState(button, loadingText, urlParams) {
        // Show loading state
        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = loadingText;

        // Navigate to new URL
        const newUrl = window.location.pathname + '?' + urlParams.toString();
        window.location.href = newUrl;

        // Reset button state after a delay in case navigation fails
        setTimeout(() => {
            button.disabled = false;
            button.textContent = originalText;
        }, 5000);
    }

    // Initialize common event listeners
    initializeEventListeners() {
        // Username filter event listeners
        if (this.applyUsernameButton) {
            this.applyUsernameButton.addEventListener('click', () => this.applyUsernameFilter());
        }

        if (this.usernameInput) {
            this.usernameInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.applyUsernameFilter();
                }
            });

            this.usernameInput.addEventListener('focus', function() {
                this.select();
            });
        }

        // My PRs toggle event listener
        if (this.myPrsToggle) {
            this.myPrsToggle.addEventListener('click', () => this.toggleMyPrs());
        }

        // Clear filters event listener
        if (this.clearFiltersButton) {
            this.clearFiltersButton.addEventListener('click', () => this.clearAllFilters());
        }

        // Konflux filter event listener
        if (this.filterKonfluxButton) {
            this.filterKonfluxButton.addEventListener('click', () => this.toggleKonfluxFilter());
        }
    }
}

// Make PRFilterUtils available globally
window.PRFilterUtils = PRFilterUtils;

// Auto-initialize when DOM is loaded if filter elements are present
document.addEventListener('DOMContentLoaded', function() {
    // Check if this is a PR page by looking for common filter elements
    const hasUsernameFilter = document.getElementById('username-input');
    const hasFilterButtons = document.getElementById('filter-konflux') || document.getElementById('my-prs-toggle') || document.getElementById('my-mrs-toggle');
    const hasDaysFilter = document.getElementById('days-input');
    const hasDateRangeFilter = document.getElementById('date-from-input') || document.getElementById('date-to-input');
    const hasClearFilters = document.getElementById('clear-filters');

    if (hasUsernameFilter || hasFilterButtons || hasDaysFilter || hasDateRangeFilter || hasClearFilters) {
        // Initialize shared filter utilities automatically
        const prFilterUtils = new PRFilterUtils();
        prFilterUtils.initializeEventListeners();

        // Make instance available globally for pages that need direct access
        window.prFilterUtils = prFilterUtils;
    }
});
