/**
 * Days filter functionality for merged pull requests page
 */

document.addEventListener('DOMContentLoaded', function() {
    const daysInput = document.getElementById('days-input');
    const applyButton = document.getElementById('apply-days');

    function applyDaysFilter() {
        const days = parseInt(daysInput.value);

        // Validate input
        if (isNaN(days) || days < 1 || days > 365) {
            alert('Please enter a number between 1 and 365');
            daysInput.focus();
            return;
        }

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.set('days', days);

        // Preserve reload_data parameter if it exists
        const newUrl = window.location.pathname + '?' + urlParams.toString();

        // Show loading state
        applyButton.disabled = true;
        applyButton.textContent = 'Loading...';

        // Navigate to new URL
        window.location.href = newUrl;
    }

    // Apply button click
    if (applyButton) {
        applyButton.addEventListener('click', applyDaysFilter);
    }

    // Enter key in input field
    if (daysInput) {
        daysInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                applyDaysFilter();
            }
        });

        // Auto-select input text when focused
        daysInput.addEventListener('focus', function() {
            this.select();
        });
    }
});
