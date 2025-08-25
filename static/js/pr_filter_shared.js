/**
 * Shared PR/MR filtering functionality for both open and merged pull requests pages
 */

class PRFilterUtils {
    constructor() {
        this.usernameInput = document.getElementById('username-input');
        this.applyUsernameButton = document.getElementById('apply-username');
        this.myPrsToggle = document.getElementById('my-prs-toggle');
        this.clearFiltersButton = document.getElementById('clear-filters');
        this.filterKonfluxButton = document.getElementById('filter-konflux');
    }

    applyUsernameFilter() {
        const username = this.usernameInput.value.trim();

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        if (username) {
            urlParams.set('username', username);
            // Clear my_prs parameter when using custom username
            urlParams.delete('my_prs');

            // Visually deactivate "My PRs" toggle if it's active
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

        if (isActive) {
            // Turn off "My PRs" filter
            urlParams.delete('my_prs');
            urlParams.delete('username');
        } else {
            // Turn on "My PRs" filter - clear custom username filter
            urlParams.set('my_prs', 'true');
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

            // Update username input field visually
            if (this.usernameInput) {
                this.usernameInput.value = 'konflux';
            }

            // Visually deactivate "My PRs" toggle if it's active
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
    const hasFilterButtons = document.getElementById('filter-konflux') || document.getElementById('my-prs-toggle');

    if (hasUsernameFilter || hasFilterButtons) {
        // Initialize shared filter utilities automatically
        const prFilterUtils = new PRFilterUtils();
        prFilterUtils.initializeEventListeners();

        // Make instance available globally for pages that need direct access
        window.prFilterUtils = prFilterUtils;
    }
});
