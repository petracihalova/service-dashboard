/**
 * App-Interface Templates Inline Handlers
 * Contains functionality specific to app-interface templates that was previously inline
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-apply date range filter functionality
    const dateFromInput = document.getElementById('date-from-input');
    const dateToInput = document.getElementById('date-to-input');

    function applyDateFilter() {
        const dateFrom = dateFromInput ? dateFromInput.value : '';
        const dateTo = dateToInput ? dateToInput.value : '';

        // Only apply if we have a from date
        if (dateFrom) {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.delete('reload_data');

            // Set date range parameters
            urlParams.set('date_from', dateFrom);
            if (dateTo) {
                urlParams.set('date_to', dateTo);
            } else {
                urlParams.delete('date_to');
            }

            // Navigate to filtered URL
            const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
            window.location.href = newUrl;
        }
    }

    if (dateFromInput) {
        dateFromInput.addEventListener('change', applyDateFilter);
    }
    if (dateToInput) {
        dateToInput.addEventListener('change', applyDateFilter);
    }

    // View Toggle Switch functionality (specific to app-interface pages)
    const viewToggleSwitch = document.getElementById('viewToggleSwitch');
    const tableView = document.getElementById('table_view');
    const listView = document.getElementById('list_view');
    const switchLabel = document.querySelector('label[for="viewToggleSwitch"]');

    if (viewToggleSwitch) {
        // Handle switch toggle
        viewToggleSwitch.addEventListener('change', function() {
            if (this.checked) {
                // Switch ON = Table View
                if (tableView) tableView.style.display = 'block';
                if (listView) listView.style.display = 'none';
                if (switchLabel) switchLabel.textContent = 'Table View';
            } else {
                // Switch OFF = List View
                if (tableView) tableView.style.display = 'none';
                if (listView) listView.style.display = 'block';
                if (switchLabel) switchLabel.textContent = 'List View';
            }
        });
    }
});
