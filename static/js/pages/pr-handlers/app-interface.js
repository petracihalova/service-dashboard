/**
 * App-Interface PR/MR Page Handlers
 * Replaces: app_interface_inline_handlers.js
 * Specific functionality for app-interface PR/MR pages
 */

document.addEventListener('DOMContentLoaded', function() {
    // Auto-apply date range filter functionality
    function initDateRangeFilter() {
        const dateFromInput = document.getElementById('date-from-input');
        const dateToInput = document.getElementById('date-to-input');

        if (dateFromInput) {
            dateFromInput.addEventListener('change', () => applyDateFilter());
        }
        if (dateToInput) {
            dateToInput.addEventListener('change', () => applyDateFilter());
        }
    }

    function applyDateFilter() {
        const dateFromInput = document.getElementById('date-from-input');
        const dateToInput = document.getElementById('date-to-input');

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

    // View Toggle Switch functionality (specific to app-interface pages)
    function initViewToggle() {
        const viewToggleSwitch = document.getElementById('viewToggleSwitch');
        const tableView = document.getElementById('table_view');
        const listView = document.getElementById('list_view');
        const switchLabel = document.querySelector('label[for="viewToggleSwitch"]');

        // Restore view state on page load
        if (viewToggleSwitch && tableView && listView && switchLabel) {
            // Check URL parameters first (for view state preservation across page loads)
            const urlParams = new URLSearchParams(window.location.search);
            let viewMode = urlParams.get('view');

            // If not in URL, check localStorage (basic fallback)
            if (!viewMode && window.prFilterUtils) {
                const storageKey = window.prFilterUtils.getViewStorageKey();
                viewMode = localStorage.getItem(storageKey);
            }

            // Apply the view state
            if (viewMode === 'list') {
                // Switch to list view
                viewToggleSwitch.checked = false;
                tableView.style.display = 'none';
                listView.style.display = 'block';
                switchLabel.textContent = 'List View';
            } else {
                // Default to table view
                viewToggleSwitch.checked = true;
                tableView.style.display = 'block';
                listView.style.display = 'none';
                switchLabel.textContent = 'Table View';
            }
        }

        if (viewToggleSwitch) {
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
    }

    // Initialize app-interface handlers
    initDateRangeFilter();
    initViewToggle();
});
