/**
 * Merged pull requests page specific functionality (days filter)
 * Uses shared PR filter utilities from pr_filter_shared.js
 */

document.addEventListener('DOMContentLoaded', function() {
    // Days-specific elements
    const daysInput = document.getElementById('days-input');
    const applyDaysButton = document.getElementById('apply-days');

    // Use the globally initialized prFilterUtils instance
    // (initialized automatically by pr_filter_shared.js)

    // Load saved days value from localStorage
    loadSavedDaysValue();

    function loadSavedDaysValue() {
        // Check if URL already has days parameter
        const urlParams = new URLSearchParams(window.location.search);
        const urlDays = urlParams.get('days');

        if (urlDays) {
            // URL has days parameter - save it for future visits
            const days = parseInt(urlDays);
            if (days >= 1 && days <= 10000) {
                localStorage.setItem('mergedPR_days', days);
            }
        } else {
            // No days in URL, try to load from localStorage
            const savedDays = localStorage.getItem('mergedPR_days');
            if (savedDays && daysInput) {
                const days = parseInt(savedDays);
                if (days >= 1 && days <= 10000) {
                    // Remove reload_data when silently redirecting with saved days
                    urlParams.delete('reload_data');
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
        if (isNaN(days) || days < 1 || days > 10000) {
            alert('Please enter a number between 1 and 10000');
            daysInput.focus();
            return;
        }

        // Save to localStorage for future visits
        localStorage.setItem('mergedPR_days', days);

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        urlParams.set('days', days);

        // Navigate to new URL using shared utility
        window.prFilterUtils.navigateWithLoadingState(applyDaysButton, 'Loading...', urlParams);
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
});
