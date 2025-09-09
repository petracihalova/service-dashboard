/**
 * PR/MR Templates Advanced Inline Handlers
 * Contains complex functionality for merged/closed PR templates that was previously inline
 * Includes visual state management for dropdowns and filters
 */

document.addEventListener('DOMContentLoaded', function() {
    // Source filter functionality with button state management
    const sourceItems = document.querySelectorAll('#sourceDropdown + .dropdown-menu .dropdown-item');
    sourceItems.forEach(item => {
        item.addEventListener('click', function(e) {
            e.preventDefault();

            // Remove active class from all items
            sourceItems.forEach(i => i.classList.remove('active'));

            // Add active class to clicked item
            this.classList.add('active');

            // Update button appearance and text
            const dropdown = document.getElementById('sourceDropdown');
            const source = this.getAttribute('data-source');

            if (source === 'both') {
                dropdown.className = 'btn btn-outline-primary btn-sm dropdown-toggle';
                dropdown.style.border = '';
                dropdown.innerHTML = 'Source: Both';
            } else {
                dropdown.className = 'btn btn-primary fw-bold btn-sm dropdown-toggle';
                dropdown.style.border = '2px solid #0d6efd';
                if (source === 'github') {
                    dropdown.innerHTML = '✓ <strong>GitHub Only</strong>';
                } else if (source === 'gitlab') {
                    dropdown.innerHTML = '✓ <strong>GitLab Only</strong>';
                }
            }

            // Build URL with source filter
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.delete('reload_data');

            if (source && source !== 'both') {
                urlParams.set('source', source);
            } else {
                urlParams.delete('source');
            }

            // Navigate to filtered URL
            const newUrl = urlParams.toString() ? `${window.location.pathname}?${urlParams.toString()}` : window.location.pathname;
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
            urlParams.delete('reload_data');

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

    // Override clear filters to reset source and organization filters with visual state
    const clearFiltersBtn = document.getElementById('clear-filters');
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', function() {
            // Reset source dropdown to default state
            const sourceDropdown = document.getElementById('sourceDropdown');
            const sourceItems = document.querySelectorAll('#sourceDropdown + .dropdown-menu .dropdown-item');

            if (sourceDropdown && sourceItems.length > 0) {
                // Remove active class from all items
                sourceItems.forEach(item => item.classList.remove('active'));

                // Set "both" as active
                const bothItem = document.querySelector('#sourceDropdown + .dropdown-menu .dropdown-item[data-source="both"]');
                if (bothItem) {
                    bothItem.classList.add('active');
                }

                // Reset dropdown button appearance
                sourceDropdown.className = 'btn btn-outline-primary btn-sm dropdown-toggle';
                sourceDropdown.style.border = '';
                sourceDropdown.innerHTML = 'Source: Both';
            }

            // Reset organization dropdown to default state
            const orgDropdown = document.getElementById('organizationDropdown');
            const orgItems = document.querySelectorAll('#organizationDropdown + .dropdown-menu .dropdown-item');

            if (orgDropdown && orgItems.length > 0) {
                // Remove active class from all items
                orgItems.forEach(item => item.classList.remove('active'));

                // Set "all organizations" as active
                const allOrgItem = document.querySelector('#organizationDropdown + .dropdown-menu .dropdown-item[data-organization=""]');
                if (allOrgItem) {
                    allOrgItem.classList.add('active');
                }

                // Reset dropdown button appearance
                orgDropdown.className = 'btn btn-outline-primary btn-sm dropdown-toggle';
                orgDropdown.style.border = '';
                orgDropdown.innerHTML = 'Organization: All';
            }

            // Clear username input
            const usernameInput = document.getElementById('username-input');
            if (usernameInput) usernameInput.value = '';

            // Navigate to base URL without parameters
            window.location.href = window.location.pathname;
        });
    }

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

    // View Toggle Switch functionality
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
