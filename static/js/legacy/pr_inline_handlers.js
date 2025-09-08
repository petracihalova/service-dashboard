/**
 * PR/MR Templates Inline Handlers
 * Contains functionality specific to PR/MR templates that was previously inline
 */

document.addEventListener('DOMContentLoaded', function() {
    // Source filter functionality
    const sourceItems = document.querySelectorAll('#sourceDropdown + .dropdown-menu .dropdown-item');
    sourceItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();

            // Remove active class from all items
            sourceItems.forEach(i => i.classList.remove('active'));

            // Add active class to clicked item
            this.classList.add('active');

            // Get selected source
            const selectedSource = this.dataset.source;

            // Get current URL parameters
            const urlParams = new URLSearchParams(window.location.search);

            // Update source parameter
            if (selectedSource === 'both') {
                urlParams.delete('source');
            } else {
                urlParams.set('source', selectedSource);
            }

            // Navigate to updated URL
            const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
            window.location.href = newUrl;
        });
    });

    // Organization filter functionality
    const organizationItems = document.querySelectorAll('#organizationDropdown + .dropdown-menu .dropdown-item');
    organizationItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();

            // Remove active class from all items
            organizationItems.forEach(i => i.classList.remove('active'));

            // Add active class to clicked item
            this.classList.add('active');

            // Get selected organization
            const selectedOrganization = this.dataset.organization;

            // Get current URL parameters
            const urlParams = new URLSearchParams(window.location.search);

            // Update organization parameter
            if (selectedOrganization === '' || selectedOrganization === null) {
                urlParams.delete('organization');
            } else {
                urlParams.set('organization', selectedOrganization);
            }

            // Navigate to updated URL
            const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
            window.location.href = newUrl;
        });
    });

    // Clear filters button override (for pages that need custom clear functionality)
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function(e) {
            e.preventDefault();

            // Clear username input
            const usernameInput = document.getElementById('username-input');
            if (usernameInput) usernameInput.value = '';

            // Navigate to base URL without parameters
            window.location.href = window.location.pathname;
        });
    }

    // View Toggle Switch functionality (additional to pull_requests.js for templates that use switches instead of buttons)
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
