/**
 * Shared PR/MR filtering functionality for both open and merged pull requests pages
 */

(function() {
    // Prevent duplicate declarations when script loads multiple times
    if (typeof window.PRFilterUtils !== 'undefined') {
        return;
    }

class PRFilterUtils {
    constructor() {
        this.usernameInput = document.getElementById('username-input');
        this.applyUsernameButton = document.getElementById('apply-username');
        this.myPrsToggle = document.getElementById('my-prs-toggle') || document.getElementById('my-mrs-toggle');
        this.clearFiltersButton = document.getElementById('clear-filters');
        this.filterKonfluxButton = document.getElementById('filter-konflux');
        this.filterNonKonfluxButton = document.getElementById('filter-non-konflux');

        // Size filter elements (may not exist on all pages)
        this.sizeDropdown = document.getElementById('sizeDropdown');
        this.sizeDropdownItems = document.querySelectorAll('[data-size]');
        this.currentSizeFilter = 'all';

        // New toggle switches for boolean filters
        this.konfluxToggle = document.getElementById('konfluxToggle');
        this.nonKonfluxToggle = document.getElementById('nonKonfluxToggle');
        this.myPrsToggleSwitch = document.getElementById('myPrsToggle');

        // Determine if this is app-interface page (uses my_mrs parameter)
        this.isAppInterface = window.location.pathname.includes('app-interface');

        // Initialize size filter from URL parameter on page load
        this.initializeSizeFilterFromURL();
    }

    initializeSizeFilterFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const sizeParam = urlParams.get('size');

        if (sizeParam && ['unknown', 'small', 'medium', 'large', 'huge'].includes(sizeParam)) {
            // Set the current size filter from URL parameter
            this.currentSizeFilter = sizeParam;

            // Update dropdown UI to match URL parameter (when DOM is ready)
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => {
                    this.updateSizeDropdownButton(sizeParam);
                    this.updateSizeDropdownActive(sizeParam);
                });
            } else {
                this.updateSizeDropdownButton(sizeParam);
                this.updateSizeDropdownActive(sizeParam);
            }
        } else {
            // Default to 'all' if no valid size parameter
            this.currentSizeFilter = 'all';
        }
    }

    applyUsernameFilter() {
        const username = this.usernameInput.value.trim();

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        if (username) {
            urlParams.set('username', username);
            // Clear my_prs/my_mrs parameter when using custom username
            urlParams.delete('my_prs');
            urlParams.delete('my_mrs');

            // Visually deactivate "My PRs/MRs" toggle if it's active
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
        const paramName = this.isAppInterface ? 'my_mrs' : 'my_prs';

        if (isActive) {
            // Turn off "My PRs/MRs" filter
            urlParams.delete(paramName);
            urlParams.delete('username');
        } else {
            // Turn on "My PRs/MRs" filter - clear custom username filter
            urlParams.set(paramName, 'true');
            urlParams.delete('username');

            // Clear username input field visually
            if (this.usernameInput) {
                this.usernameInput.value = '';
            }
        }

        // Navigate to new URL
        this.navigateWithLoadingState(this.myPrsToggle, 'Loading...', urlParams);
    }

    // Toggle filter methods with mutual exclusivity
    toggleKonfluxFilter(isChecked) {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        if (isChecked) {
            // Turn ON Konflux filter, turn OFF Non-Konflux and My PRs/MRs
            if (this.isAppInterface) {
                urlParams.set('my_mrs', 'true');
                urlParams.delete('my_mrs_non_konflux');
            } else {
                urlParams.set('username', 'konflux');
                urlParams.delete('my_prs');
            }

            // Update toggle states
            if (this.nonKonfluxToggle) {
                this.nonKonfluxToggle.checked = false;
            }
            if (this.myPrsToggleSwitch) {
                this.myPrsToggleSwitch.checked = false;
            }
        } else {
            // Turn OFF Konflux filter
            if (this.isAppInterface) {
                urlParams.delete('my_mrs');
            } else {
                urlParams.delete('username');
            }

            // Clear saved column filter state when turning off filter to show all data
            try {
                localStorage.removeItem('openPR_columnFilters');
                localStorage.removeItem('closedPR_columnFilters');
                localStorage.removeItem('mergedPR_columnFilters');
            } catch (e) {
                // Silent fail
            }
        }

        // Navigate to new URL (preserves other filters like Size)
        this.navigateWithLoadingState(null, 'Loading...', urlParams);
    }

    toggleNonKonfluxFilter(isChecked) {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        if (isChecked) {
            // Turn ON Non-Konflux filter, turn OFF Konflux and My PRs/MRs
            if (this.isAppInterface) {
                urlParams.set('my_mrs_non_konflux', 'true');
                urlParams.delete('my_mrs');
            } else {
                urlParams.set('username', 'non-konflux');
                urlParams.delete('my_prs');
            }

            // Update toggle states
            if (this.konfluxToggle) {
                this.konfluxToggle.checked = false;
            }
            if (this.myPrsToggleSwitch) {
                this.myPrsToggleSwitch.checked = false;
            }
        } else {
            // Turn OFF Non-Konflux filter
            if (this.isAppInterface) {
                urlParams.delete('my_mrs_non_konflux');
            } else {
                urlParams.delete('username');
            }

            // Clear saved column filter state when turning off filter to show all data
            try {
                localStorage.removeItem('openPR_columnFilters');
                localStorage.removeItem('closedPR_columnFilters');
                localStorage.removeItem('mergedPR_columnFilters');
            } catch (e) {
                // Silent fail
            }
        }

        // Navigate to new URL (preserves other filters like Size)
        this.navigateWithLoadingState(null, 'Loading...', urlParams);
    }

    toggleMyPrsFilter(isChecked) {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        if (isChecked) {
            // Turn ON My PRs/MRs filter, turn OFF Konflux and Non-Konflux
            if (this.isAppInterface) {
                urlParams.set('my_mrs', 'true');
                // Clear Konflux/Non-Konflux filters for app-interface
                urlParams.delete('my_mrs_non_konflux');
            } else {
                urlParams.set('my_prs', 'true');
                // Clear Konflux/Non-Konflux filters for regular pages
                urlParams.delete('username');
            }

            // Update toggle states
            if (this.konfluxToggle) {
                this.konfluxToggle.checked = false;
            }
            if (this.nonKonfluxToggle) {
                this.nonKonfluxToggle.checked = false;
            }
        } else {
            // Turn OFF My PRs/MRs filter
            if (this.isAppInterface) {
                urlParams.delete('my_mrs');
            } else {
                urlParams.delete('my_prs');
            }

            // Clear saved column filter state when turning off filter to show all data
            try {
                localStorage.removeItem('openPR_columnFilters');
                localStorage.removeItem('closedPR_columnFilters');
                localStorage.removeItem('mergedPR_columnFilters');
            } catch (e) {
                // Silent fail
            }
        }

        // Navigate to new URL (preserves other filters like Size)
        this.navigateWithLoadingState(null, 'Loading...', urlParams);
    }

    clearAllFilters() {
        const urlParams = new URLSearchParams(window.location.search);

        // IMPORTANT: Remove reload_data parameter to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        // Remove filter parameters (but keep days for merged PR page)
        urlParams.delete('username');
        urlParams.delete('my_prs');
        urlParams.delete('my_mrs');
        urlParams.delete('my_mrs_non_konflux');
        urlParams.delete('size');
        urlParams.delete('source');
        urlParams.delete('organization');

        // Remove date range parameters and clear input fields
        urlParams.delete('date_from');
        urlParams.delete('date_to');

        // Clear date range input fields if they exist
        const dateFromInput = document.getElementById('date-from-input');
        const dateToInput = document.getElementById('date-to-input');
        if (dateFromInput) dateFromInput.value = '';
        if (dateToInput) dateToInput.value = '';

        // Clear date range from localStorage if available (but don't clear input values - let backend control them)
        try {
            // Determine which storage key to clear based on current page
            const path = window.location.pathname;
            let storageKey = 'mergedPR_dateRange'; // default
            if (path.includes('app-interface-merged')) {
                storageKey = 'appInterfaceMerged_dateRange';
            } else if (path.includes('jira-closed-tickets')) {
                storageKey = 'jiraClosedTickets_dateRange';
            }
            localStorage.removeItem(storageKey);
        } catch (e) {
            // Silent fail
        }

        // Reset size filter using DataTables API (only if size dropdown exists)
        if (this.sizeDropdown && this.currentSizeFilter !== 'all') {
            this.applySizeFilter('all');
        }

        // Reset toggle switches
        if (this.konfluxToggle) {
            this.konfluxToggle.checked = false;
        }
        if (this.nonKonfluxToggle) {
            this.nonKonfluxToggle.checked = false;
        }
        if (this.myPrsToggleSwitch) {
            this.myPrsToggleSwitch.checked = false;
        }

        // Clear column-specific filters (if DataTable is present)
        if (typeof window.clearColumnFilters === 'function') {
            window.clearColumnFilters();
        }

        // For clear filters, we don't want to preserve column state
        // Clear any saved column filter state
        try {
            localStorage.removeItem('openPR_columnFilters');
        } catch (e) {
            // Silent fail
        }

        // Navigate to new URL (this will also try to save state, but we just cleared it)
        this.navigateWithLoadingState(this.clearFiltersButton, 'Loading...', urlParams);
    }


    // Size filtering functionality using DataTables API (much faster!)
    applySizeFilter(sizeCategory) {
        this.currentSizeFilter = sizeCategory;

        // Update URL to preserve size filter across page reloads
        const urlParams = new URLSearchParams(window.location.search);
        if (sizeCategory === 'all') {
            urlParams.delete('size');
        } else {
            urlParams.set('size', sizeCategory);
        }

        // Update URL without page reload
        const newUrl = window.location.pathname + (urlParams.toString() ? '?' + urlParams.toString() : '');
        window.history.replaceState(null, '', newUrl);

        // Check which view is currently visible
        const tableView = document.getElementById('table_view');
        const listView = document.getElementById('list_view');
        const isTableViewVisible = tableView && tableView.style.display !== 'none';
        const isListViewVisible = listView && listView.style.display !== 'none';

        // Get DataTables instance if available and table view is visible
        const table = $('#datatable');
        if (isTableViewVisible && table.length && $.fn.DataTable.isDataTable(table)) {
            const dataTable = table.DataTable();

            // Get the Size Category column index (should be column 5, after hidden Size column)
            const sizeColumnIndex = 5; // Size Category column

            if (sizeCategory === 'all') {
                // Clear the search filter on Size Category column
                dataTable.column(sizeColumnIndex).search('').draw();
            } else {
                // Apply filter based on size category (search by title attribute)
                const sizeLabels = {
                    'unknown': 'No Changes',
                    'small': 'Small',
                    'medium': 'Medium',
                    'large': 'Large',
                    'huge': 'Huge'
                };
                const searchTerm = sizeLabels[sizeCategory] || sizeCategory;
                // Search for exact match of the size category (now hidden in span)
                dataTable.column(sizeColumnIndex).search('^' + searchTerm + '$', true, false).draw();
            }
        } else if (isListViewVisible) {
            // Use list view filtering when list view is visible
            const listItems = document.querySelectorAll('#list_view li');
            let visibleCount = 0;

            listItems.forEach(item => {
                const shouldShow = this.shouldShowPR(item, sizeCategory);
                item.style.display = shouldShow ? '' : 'none';
                if (shouldShow) visibleCount++;
            });

            // Update count for list view
            this.updateVisibleCount(visibleCount, listItems.length);
        }

        // Update dropdown button text and styling
        this.updateSizeDropdownButton(sizeCategory);

        // Update active state in dropdown
        this.updateSizeDropdownActive(sizeCategory);
    }

    shouldShowPR(element, sizeCategory) {
        if (sizeCategory === 'all') return true;

        let totalChanges = 0;

        // Check if this is a table row or list item
        if (element.tagName === 'TR') {
            // Table row - look for hidden size column with data-size attribute
            const sizeCell = element.querySelector('td[data-size]');
            if (sizeCell) {
                totalChanges = parseInt(sizeCell.getAttribute('data-size')) || 0;
            }
        } else if (element.tagName === 'LI') {
            // List item - check data-size attribute directly on the li element
            totalChanges = parseInt(element.getAttribute('data-size')) || 0;
        } else {
            // Fallback to old method for backward compatibility
            let additions = 0, deletions = 0;
            const additionsElement = element.querySelector('.text-success');
            const deletionsElement = element.querySelector('.text-danger');

            if (additionsElement && deletionsElement) {
                const additionsText = additionsElement.textContent || '';
                const deletionsText = deletionsElement.textContent || '';

                const additionsMatch = additionsText.match(/\+?(\d+)/);
                const deletionsMatch = deletionsText.match(/-?(\d+)/);

                if (additionsMatch) additions = parseInt(additionsMatch[1]) || 0;
                if (deletionsMatch) deletions = parseInt(deletionsMatch[1]) || 0;
            }
            totalChanges = additions + deletions;
        }

        // Apply size category logic
        switch (sizeCategory) {
            case 'small': return totalChanges >= 1 && totalChanges <= 50;
            case 'medium': return totalChanges >= 51 && totalChanges <= 300;
            case 'large': return totalChanges >= 301 && totalChanges <= 1000;
            case 'huge': return totalChanges >= 1001;
            default: return true;
        }
    }

    updateSizeDropdownButton(sizeCategory) {
        if (!this.sizeDropdown) return;

        const sizeLabels = {
            'all': 'All',
            'unknown': 'No Changes',
            'small': 'Small',
            'medium': 'Medium',
            'large': 'Large',
            'huge': 'Huge'
        };

        const isFiltered = sizeCategory !== 'all';

        // Update button content to match organization dropdown pattern
        if (isFiltered) {
            this.sizeDropdown.innerHTML = `✓ <strong>${sizeLabels[sizeCategory] || 'All'}</strong>`;
        } else {
            this.sizeDropdown.innerHTML = `<i class="bi bi-bar-chart me-1"></i>Size: All`;
        }

        // Ensure dropdown toggle classes are preserved
        if (!this.sizeDropdown.classList.contains('dropdown-toggle')) {
            this.sizeDropdown.classList.add('dropdown-toggle');
        }

        // Update button styling to match organization dropdown
        if (isFiltered) {
            this.sizeDropdown.classList.remove('btn-outline-primary');
            this.sizeDropdown.classList.add('btn-primary', 'fw-bold');
            this.sizeDropdown.style.border = '2px solid #0d6efd';
        } else {
            this.sizeDropdown.classList.remove('btn-primary', 'fw-bold');
            this.sizeDropdown.classList.add('btn-outline-primary');
            this.sizeDropdown.style.border = '';
        }
    }

    updateSizeDropdownActive(sizeCategory) {
        // Remove active state from all items
        this.sizeDropdownItems.forEach(item => {
            item.classList.remove('active');
        });

        // Add active state to selected item (CSS will handle styling)
        const selectedItem = document.querySelector(`[data-size="${sizeCategory}"]`);
        if (selectedItem) {
            selectedItem.classList.add('active');
        }
    }

    updateVisibleCount(visibleCount, totalCount) {
        // For DataTables, the count is automatically updated in the table footer
        // This method is now mainly for list view or non-DataTables pages
        const titleElement = document.querySelector('h1');
        if (titleElement && totalCount > 0) {
            const titleText = titleElement.textContent;
            const baseTitle = titleText.replace(/\s*\(\d+.*?\)$/, '');

            if (visibleCount === totalCount) {
                titleElement.textContent = `${baseTitle} (${totalCount})`;
            } else {
                titleElement.textContent = `${baseTitle} (${visibleCount} of ${totalCount})`;
            }
        }
    }

    // Universal view state management
    getViewStorageKey() {
        const path = window.location.pathname;
        if (path.includes('open-pr')) {
            return 'openPR_viewMode';
        } else if (path.includes('merged-pr')) {
            return 'mergedPR_viewMode';
        } else if (path.includes('closed-pr')) {
            return 'closedPR_viewMode';
        } else if (path.includes('app-interface-open')) {
            return 'appInterfaceOpen_viewMode';
        } else if (path.includes('app-interface-merged')) {
            return 'appInterfaceMerged_viewMode';
        } else if (path.includes('app-interface-closed')) {
            return 'appInterfaceClosed_viewMode';
        } else {
            return 'pullRequests_viewMode'; // fallback
        }
    }

    getCurrentViewState() {
        const tableView = document.getElementById('table_view');
        const listView = document.getElementById('list_view');

        // Use more robust visibility detection (offsetParent is null when element is hidden)
        const isListViewVisible = listView && listView.offsetParent !== null && listView.style.display !== 'none';
        const isTableViewVisible = tableView && tableView.offsetParent !== null && tableView.style.display !== 'none';

        // Check visible view - list view takes priority if both are visible
        if (isListViewVisible) {
            return 'list';
        } else if (isTableViewVisible) {
            return 'table';
        }

        // Fallback to localStorage
        const storageKey = this.getViewStorageKey();
        return localStorage.getItem(storageKey) || 'table';
    }

    saveViewState(viewMode) {
        const storageKey = this.getViewStorageKey();
        localStorage.setItem(storageKey, viewMode);
    }

    restoreViewState() {
        // Check URL parameters first (for preservation across page loads)
        const urlParams = new URLSearchParams(window.location.search);
        let viewMode = urlParams.get('view');

        // If not in URL, check localStorage
        if (!viewMode) {
            const storageKey = this.getViewStorageKey();
            viewMode = localStorage.getItem(storageKey) || 'table';
        }

        // Apply the view state
        const tableView = document.getElementById('table_view');
        const listView = document.getElementById('list_view');

        if (viewMode === 'list' && listView) {
            // Switch to list view
            if (tableView) tableView.style.display = 'none';
            listView.style.display = 'block';
            this.updateViewToggleUI('list');
        } else {
            // Default to table view
            if (tableView) tableView.style.display = 'block';
            if (listView) listView.style.display = 'none';
            this.updateViewToggleUI('table');
        }

        // Save the state to localStorage for future use
        this.saveViewState(viewMode);
    }

    updateViewToggleUI(viewMode) {
        // Update button states for pull_requests.js style toggles
        const tableButton = document.querySelector('.view-toggle[onclick*="table"], .view-toggle.table-view');
        const listButton = document.querySelector('.view-toggle[onclick*="list"], .view-toggle.list-view');

        if (tableButton && listButton) {
            if (viewMode === 'list') {
                tableButton.classList.remove('active');
                listButton.classList.add('active');
            } else {
                tableButton.classList.add('active');
                listButton.classList.remove('active');
            }
        }

        // Update switch states for app-interface style toggles
        const viewToggleSwitch = document.getElementById('viewToggleSwitch');
        const switchLabel = document.querySelector('label[for="viewToggleSwitch"]');

        if (viewToggleSwitch && switchLabel) {
            if (viewMode === 'list') {
                viewToggleSwitch.checked = false;
                switchLabel.textContent = 'List View';
            } else {
                viewToggleSwitch.checked = true;
                switchLabel.textContent = 'Table View';
            }
        }
    }

    initializeViewToggle() {
        // Set up event listeners for pull_requests.js style buttons
        const tableButton = document.querySelector('.view-toggle[onclick*="table"], .view-toggle.table-view');
        const listButton = document.querySelector('.view-toggle[onclick*="list"], .view-toggle.list-view');

        if (tableButton) {
            // Remove existing onclick handlers
            tableButton.removeAttribute('onclick');
            tableButton.addEventListener('click', () => {
                const tableView = document.getElementById('table_view');
                const listView = document.getElementById('list_view');

                if (tableView) tableView.style.display = 'block';
                if (listView) listView.style.display = 'none';

                this.saveViewState('table');
                this.updateViewToggleUI('table');
            });
        }

        if (listButton) {
            // Remove existing onclick handlers
            listButton.removeAttribute('onclick');
            listButton.addEventListener('click', () => {
                const tableView = document.getElementById('table_view');
                const listView = document.getElementById('list_view');

                if (tableView) tableView.style.display = 'none';
                if (listView) listView.style.display = 'block';

                this.saveViewState('list');
                this.updateViewToggleUI('list');
            });
        }

        // Set up event listeners for app-interface style switches
        const viewToggleSwitch = document.getElementById('viewToggleSwitch');
        if (viewToggleSwitch) {
            // Remove existing listeners by replacing the element
            const newSwitch = viewToggleSwitch.cloneNode(true);
            viewToggleSwitch.parentNode.replaceChild(newSwitch, viewToggleSwitch);

            newSwitch.addEventListener('change', () => {
                const tableView = document.getElementById('table_view');
                const listView = document.getElementById('list_view');
                const switchLabel = document.querySelector('label[for="viewToggleSwitch"]');

                if (newSwitch.checked) {
                    // Switch ON = Table View
                    if (tableView) tableView.style.display = 'block';
                    if (listView) listView.style.display = 'none';
                    if (switchLabel) switchLabel.textContent = 'Table View';
                    this.saveViewState('table');
                } else {
                    // Switch OFF = List View
                    if (tableView) tableView.style.display = 'none';
                    if (listView) listView.style.display = 'block';
                    if (switchLabel) switchLabel.textContent = 'List View';
                    this.saveViewState('list');
                }
            });
        }
    }

    navigateWithLoadingState(button, loadingText, urlParams) {
        // Save current column filter state before navigation (if DataTable exists)
        if (typeof window.saveColumnFilterState === 'function') {
            window.saveColumnFilterState();
        }

        // Preserve current view state in URL parameters
        const currentView = this.getCurrentViewState();
        if (currentView) {
            urlParams.set('view', currentView);
        }

        // Navigate to new URL
        const newUrl = window.location.pathname + '?' + urlParams.toString();

        // Show loading state if button exists
        if (button) {
            const originalText = button.textContent;
            button.disabled = true;
            button.textContent = loadingText;

            // Reset button state after a delay in case navigation fails
            setTimeout(() => {
                button.disabled = false;
                button.textContent = originalText;
            }, 5000);
        }

        window.location.href = newUrl;
    }

    // Apply initial size filter after DataTables is loaded
    applyInitialSizeFilter() {
        if (this.sizeDropdown && this.currentSizeFilter && this.currentSizeFilter !== 'all') {
            // Apply the size filter that was loaded from URL
            this.applySizeFilter(this.currentSizeFilter);
        }
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

        // My PRs toggle event listener (only if toggle switch is not present)
        if (this.myPrsToggle && !this.myPrsToggleSwitch) {
            this.myPrsToggle.addEventListener('click', () => this.toggleMyPrs());
        }

        // Clear filters event listener
        if (this.clearFiltersButton) {
            this.clearFiltersButton.addEventListener('click', () => this.clearAllFilters());
        }

        // Konflux filter event listener (only if toggles are not present)
        if (this.filterKonfluxButton && !this.konfluxToggle) {
            this.filterKonfluxButton.addEventListener('click', () => this.toggleKonfluxFilter());
        }

        // Non-Konflux filter event listener (only if toggles are not present)
        if (this.filterNonKonfluxButton && !this.nonKonfluxToggle) {
            this.filterNonKonfluxButton.addEventListener('click', () => this.toggleNonKonfluxFilter());
        }

        // Size filter event listeners (only if size dropdown exists)
        if (this.sizeDropdown && this.sizeDropdownItems.length > 0) {
            this.sizeDropdownItems.forEach(item => {
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    const sizeCategory = item.getAttribute('data-size');
                    this.applySizeFilter(sizeCategory);
                });
            });
        }

        // Toggle switch event listeners
        if (this.konfluxToggle) {
            this.konfluxToggle.addEventListener('change', (e) => {
                this.toggleKonfluxFilter(e.target.checked);
            });
        }

        if (this.nonKonfluxToggle) {
            this.nonKonfluxToggle.addEventListener('change', (e) => {
                this.toggleNonKonfluxFilter(e.target.checked);
            });
        }

        if (this.myPrsToggleSwitch) {
            this.myPrsToggleSwitch.addEventListener('change', (e) => {
                this.toggleMyPrsFilter(e.target.checked);
            });
        }
    }
}

// Make PRFilterUtils available globally
window.PRFilterUtils = PRFilterUtils;

// Auto-initialize when DOM is loaded if filter elements are present
document.addEventListener('DOMContentLoaded', function() {
    // Check if this is a PR page by looking for common filter elements
    const hasUsernameFilter = document.getElementById('username-input');
    const hasFilterButtons = document.getElementById('filter-konflux') || document.getElementById('my-prs-toggle') || document.getElementById('my-mrs-toggle');
    const hasDaysFilter = document.getElementById('days-input');
    const hasDateRangeFilter = document.getElementById('date-from-input') || document.getElementById('date-to-input');
    const hasClearFilters = document.getElementById('clear-filters');

    if (hasUsernameFilter || hasFilterButtons || hasDaysFilter || hasDateRangeFilter || hasClearFilters) {
        // Initialize shared filter utilities automatically
        const prFilterUtils = new PRFilterUtils();
        prFilterUtils.initializeEventListeners();

        // Check if page has its own view toggle system (pull_requests.js or app-interface.js)
        const hasPageSpecificToggle = document.querySelector('.view-toggle') || document.getElementById('viewToggleSwitch');

        // Only initialize universal view toggle if no page-specific system exists
        if (!hasPageSpecificToggle) {
            prFilterUtils.initializeViewToggle();
            prFilterUtils.restoreViewState();
        }

        // Make instance available globally for pages that need direct access
        window.prFilterUtils = prFilterUtils;
    }
});

})(); // End of IIFE
