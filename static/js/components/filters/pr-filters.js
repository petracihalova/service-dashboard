/**
 * Consolidated PR/MR Filter Functionality
 * Replaces: pr_inline_handlers.js, pr_advanced_inline_handlers.js (partially)
 * Provides reusable filter components for PR/MR pages
 */

document.addEventListener('DOMContentLoaded', function() {
    // Source filter (GitHub/GitLab)
    function initSourceFilter() {
        const sourceItems = document.querySelectorAll('#sourceDropdown + .dropdown-menu .dropdown-item');
        sourceItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                handleSourceFilter(item, sourceItems);
            });
        });
    }

    function handleSourceFilter(clickedItem, allItems) {
        // Remove active class from all items
        allItems.forEach(i => i.classList.remove('active'));

        // Add active class to clicked item
        clickedItem.classList.add('active');

        // Get selected source
        const selectedSource = clickedItem.dataset.source;

        // Update dropdown appearance (for advanced mode)
        updateSourceDropdown(selectedSource);

        // Navigate to filtered URL
        updateURL({ source: selectedSource === 'both' ? null : selectedSource });
    }

    function updateSourceDropdown(source) {
        const dropdown = document.getElementById('sourceDropdown');
        if (!dropdown) return; // Not all pages have visual dropdown updates

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
    }

    // Organization filter
    function initOrganizationFilter() {
        const organizationItems = document.querySelectorAll('#organizationDropdown + .dropdown-menu .dropdown-item');
        organizationItems.forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                handleOrganizationFilter(item, organizationItems);
            });
        });
    }

    function handleOrganizationFilter(clickedItem, allItems) {
        // Remove active class from all items
        allItems.forEach(i => i.classList.remove('active'));

        // Add active class to clicked item
        clickedItem.classList.add('active');

        // Get selected organization
        const selectedOrganization = clickedItem.dataset.organization;

        // Navigate to filtered URL
        updateURL({
            organization: selectedOrganization === '' || selectedOrganization === null ? null : selectedOrganization
        });
    }

    // Clear filters functionality
    function initClearFilters() {
        const clearFiltersBtn = document.getElementById('clear-filters');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', (e) => {
                e.preventDefault();
                handleClearFilters();
            });
        }
    }

    function handleClearFilters() {
        // Reset dropdowns to default state
        resetSourceDropdown();
        resetOrganizationDropdown();

        // Clear username input
        const usernameInput = document.getElementById('username-input');
        if (usernameInput) usernameInput.value = '';

        // Preserve view state when clearing filters
        let viewParam = '';
        if (window.prFilterUtils) {
            const currentView = window.prFilterUtils.getCurrentViewState();
            if (currentView && currentView !== 'table') {
                viewParam = '?view=' + currentView;
            }
        }

        // Navigate to base URL preserving only view parameter
        window.location.href = window.location.pathname + viewParam;
    }

    function resetSourceDropdown() {
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
    }

    function resetOrganizationDropdown() {
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
    }

    // View toggle functionality
    function initViewToggle() {
        const viewToggleSwitch = document.getElementById('viewToggleSwitch');
        const tableView = document.getElementById('table_view');
        const listView = document.getElementById('list_view');
        const switchLabel = document.querySelector('label[for="viewToggleSwitch"]');

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

    // Utility method to update URL with parameters
    function updateURL(params) {
        const urlParams = new URLSearchParams(window.location.search);
        urlParams.delete('reload_data');

        // Preserve current view state if filter utils are available
        if (window.prFilterUtils) {
            const currentView = window.prFilterUtils.getCurrentViewState();
            if (currentView) {
                urlParams.set('view', currentView);
            }
        }

        // Update parameters
        Object.keys(params).forEach(key => {
            if (params[key] === null || params[key] === undefined) {
                urlParams.delete(key);
            } else {
                urlParams.set(key, params[key]);
            }
        });

        // Navigate to updated URL
        const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
        window.location.href = newUrl;
    }

    // Initialize all filter functionality
    initSourceFilter();
    initOrganizationFilter();
    initClearFilters();
    initViewToggle();
});
