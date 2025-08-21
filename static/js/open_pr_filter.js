/**
 * Username filter functionality for open pull requests page
 */

document.addEventListener('DOMContentLoaded', function() {
    const usernameInput = document.getElementById('username-input');
    const applyUsernameButton = document.getElementById('apply-username');
    const myPrsToggle = document.getElementById('my-prs-toggle');
    const clearFiltersButton = document.getElementById('clear-filters');

    function applyUsernameFilter() {
        const username = usernameInput.value.trim();

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        if (username) {
            urlParams.set('username', username);
            // Clear my_prs parameter when using custom username
            urlParams.delete('my_prs');

            // Visually deactivate "My PRs" toggle if it's active
            if (myPrsToggle && myPrsToggle.dataset.active === 'true') {
                myPrsToggle.dataset.active = 'false';
                // Remove checkmark and update button appearance
                myPrsToggle.innerHTML = myPrsToggle.innerHTML.replace('✓', '').trim();
                myPrsToggle.classList.remove('active');
            }
        } else {
            // If username is empty, just remove the username parameter
            urlParams.delete('username');
        }

        // Navigate to new URL
        navigateWithLoadingState(applyUsernameButton, 'Loading...', urlParams);
    }

    function toggleMyPrs() {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        const isActive = myPrsToggle.dataset.active === 'true';

        if (isActive) {
            // Turn off "My PRs" filter
            urlParams.delete('my_prs');
            urlParams.delete('username');
        } else {
            // Turn on "My PRs" filter - clear custom username filter
            urlParams.set('my_prs', 'true');
            urlParams.delete('username');

            // Clear username input field visually
            if (usernameInput) {
                usernameInput.value = '';
            }
        }

        // Navigate to new URL
        navigateWithLoadingState(myPrsToggle, 'Loading...', urlParams);
    }

    function clearAllFilters() {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        // Remove filter parameters
        urlParams.delete('username');
        urlParams.delete('my_prs');

        // Navigate to new URL
        navigateWithLoadingState(clearFiltersButton, 'Loading...', urlParams);
    }

    function navigateWithLoadingState(button, loadingText, urlParams) {
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

    // Username filter event listeners
    if (applyUsernameButton) {
        applyUsernameButton.addEventListener('click', applyUsernameFilter);
    }

    if (usernameInput) {
        usernameInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applyUsernameFilter();
            }
        });

        usernameInput.addEventListener('focus', function() {
            this.select();
        });
    }

    // My PRs toggle event listener
    if (myPrsToggle) {
        myPrsToggle.addEventListener('click', toggleMyPrs);
    }

    // Clear filters event listener
    if (clearFiltersButton) {
        clearFiltersButton.addEventListener('click', clearAllFilters);
    }
});
