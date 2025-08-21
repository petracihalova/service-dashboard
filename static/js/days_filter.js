/**
 * Days filter and username filter functionality for merged pull requests page
 */

document.addEventListener('DOMContentLoaded', function() {
    const daysInput = document.getElementById('days-input');
    const applyDaysButton = document.getElementById('apply-days');
    const usernameInput = document.getElementById('username-input');
    const applyUsernameButton = document.getElementById('apply-username');
    const myPrsToggle = document.getElementById('my-prs-toggle');
    const clearFiltersButton = document.getElementById('clear-filters');

    // Load saved days value from localStorage
    loadSavedDaysValue();

    function loadSavedDaysValue() {
        // Check if URL already has days parameter
        const urlParams = new URLSearchParams(window.location.search);
        const urlDays = urlParams.get('days');

        if (urlDays) {
            // URL has days parameter - save it for future visits
            const days = parseInt(urlDays);
            if (days >= 1 && days <= 365) {
                localStorage.setItem('mergedPR_days', days);
            }
        } else {
            // No days in URL, try to load from localStorage
            const savedDays = localStorage.getItem('mergedPR_days');
            if (savedDays && daysInput) {
                const days = parseInt(savedDays);
                if (days >= 1 && days <= 365) {
                    // Silently redirect to page with saved days value
                    urlParams.set('days', days);
                    const newUrl = window.location.pathname + '?' + urlParams.toString();
                    window.location.href = newUrl;
                }
            }
        }
    }

    function applyDaysFilter() {
        const days = parseInt(daysInput.value);

        // Validate input
        if (isNaN(days) || days < 1 || days > 365) {
            alert('Please enter a number between 1 and 365');
            daysInput.focus();
            return;
        }

        // Save to localStorage for future visits
        localStorage.setItem('mergedPR_days', days);

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.set('days', days);

        // Navigate to new URL
        navigateWithLoadingState(applyDaysButton, 'Loading...', urlParams);
    }

    function applyUsernameFilter() {
        const username = usernameInput.value.trim();

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);

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

        // Remove filter parameters but keep days
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

    // Days filter event listeners
    if (applyDaysButton) {
        applyDaysButton.addEventListener('click', applyDaysFilter);
    }

    if (daysInput) {
        daysInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applyDaysFilter();
            }
        });

        daysInput.addEventListener('focus', function() {
            this.select();
        });
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
