/**
 * Date range filter functionality for merged PR pages
 * Works alongside the existing days filter
 */

document.addEventListener('DOMContentLoaded', function() {
    const dateFromInput = document.getElementById('date-from-input');
    const dateToInput = document.getElementById('date-to-input');
    const applyDateRangeButton = document.getElementById('apply-date-range');
    const dateRangeInfo = document.getElementById('date-range-info');

    // LocalStorage key for this page - determined by URL
    const STORAGE_KEY = getStorageKey();

    function getStorageKey() {
        const path = window.location.pathname;
        if (path.includes('app-interface-merged')) {
            return 'appInterfaceMerged_dateRange';
        } else if (path.includes('jira-closed-tickets')) {
            return 'jiraClosedTickets_dateRange';
        } else if (path.includes('personal-stats')) {
            return 'personalStats_dateRange';
        } else if (path.includes('all-data-stats')) {
            return 'allDataStats_dateRange';
        } else {
            return 'mergedPR_dateRange';
        }
    }

    // DISABLED: Initialize date inputs - priority: URL > localStorage > defaults
    // initializeDateInputs(); // DISABLED - was overriding backend-provided date values

    function initializeDateInputs() {
        const urlParams = new URLSearchParams(window.location.search);
        const fromDateUrl = urlParams.get('date_from');
        const toDateUrl = urlParams.get('date_to');

        let fromDate = '';
        let toDate = '';
        let shouldAutoApply = false;

        // Priority 1: URL parameters (highest)
        if (fromDateUrl) {
            fromDate = fromDateUrl;
            toDate = toDateUrl || ''; // Can be empty (means "until today")
        } else {
            // Priority 2: LocalStorage
            const savedRange = loadDateRangeFromStorage();
            if (savedRange.fromDate) {
                fromDate = savedRange.fromDate;
                toDate = savedRange.toDate || '';
                shouldAutoApply = true; // Auto-apply saved dates
            } else {
                // Priority 3: Default (7 days including today)
                const sevenDaysAgo = new Date();
                sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 6); // -6 days to get 7 days total (including today)
                fromDate = sevenDaysAgo.toISOString().split('T')[0];
                toDate = ''; // Empty means "until today"
                shouldAutoApply = true; // Auto-apply defaults
            }
        }

        // Set input values
        if (dateFromInput) dateFromInput.value = fromDate;
        if (dateToInput) dateToInput.value = toDate;

        updateDateRangeInfo();

        // Auto-apply filter if we loaded from storage or using defaults
        if (shouldAutoApply && !fromDateUrl) {
            setTimeout(() => applyDateRangeFilter(), 100); // Small delay to ensure DOM is ready
        }
    }

    function loadDateRangeFromStorage() {
        try {
            const saved = localStorage.getItem(STORAGE_KEY);
            return saved ? JSON.parse(saved) : {};
        } catch (e) {
            return {};
        }
    }

    function saveDateRangeToStorage(fromDate, toDate) {
        try {
            const rangeData = {
                fromDate: fromDate,
                toDate: toDate,
                lastUsed: new Date().toISOString()
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(rangeData));
        } catch (e) {
            // Silent fail
        }
    }

    function updateDateRangeInfo() {
        if (!dateRangeInfo) return;

        const fromDate = dateFromInput ? dateFromInput.value : '';
        const toDate = dateToInput ? dateToInput.value : '';

        if (fromDate && toDate) {
            // Format dates for display
            const fromFormatted = formatDateForDisplay(fromDate);
            const toFormatted = formatDateForDisplay(toDate);
            const dayCount = calculateDaysBetween(fromDate, toDate);
            dateRangeInfo.textContent = `${fromFormatted} - ${toFormatted} (${dayCount} day${dayCount === 1 ? '' : 's'})`;
        } else if (fromDate && !toDate) {
            // Only from date - will default to "until today"
            const fromFormatted = formatDateForDisplay(fromDate);
            const today = new Date().toISOString().split('T')[0];
            const dayCount = calculateDaysBetween(fromDate, today);
            dateRangeInfo.textContent = `From ${fromFormatted} until today (${dayCount} day${dayCount === 1 ? '' : 's'})`;
        } else if (!fromDate && toDate) {
            dateRangeInfo.textContent = 'Please select a start date (From)';
        } else {
            dateRangeInfo.textContent = 'Select date range (defaults to last 7 days including today)';
        }
    }

    function formatDateForDisplay(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric'
        });
    }

    function calculateDaysBetween(fromDate, toDate) {
        if (!fromDate || !toDate) return 0;

        const startDate = new Date(fromDate);
        const endDate = new Date(toDate);

        // Calculate the difference in time (milliseconds)
        const timeDiff = endDate.getTime() - startDate.getTime();

        // Convert milliseconds to days and add 1 to include both start and end dates
        const daysDiff = Math.ceil(timeDiff / (1000 * 60 * 60 * 24)) + 1;

        // Ensure we return at least 1 day (same day = 1 day)
        return Math.max(1, daysDiff);
    }

        function applyDateRangeFilter() {
        let fromDate = dateFromInput ? dateFromInput.value : '';
        let toDate = dateToInput ? dateToInput.value : '';

        // Validate inputs
        if (!fromDate) {
            alert('Please select a start date (From)');
            return;
        }

        // If no "to" date is provided, default to today
        if (!toDate) {
            const today = new Date();
            toDate = today.toISOString().split('T')[0]; // Format as YYYY-MM-DD
        }

        const fromDateObj = new Date(fromDate);
        const toDateObj = new Date(toDate);

        if (fromDateObj > toDateObj) {
            alert('From date must be earlier than To date');
            return;
        }

        // Check if date range is not too large (reasonable limit)
        const diffTime = toDateObj - fromDateObj;
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

        if (diffDays > 365) {
            const confirmLarge = confirm(`You've selected a ${diffDays}-day range. This might take a while to process. Continue?`);
            if (!confirmLarge) return;
        }

        // Get current URL parameters
        const urlParams = new URLSearchParams(window.location.search);

        // Remove days parameter (date range takes precedence over days filter)
        urlParams.delete('days');

        // Remove reload_data to avoid downloading new data when filtering
        urlParams.delete('reload_data');

        // Save user's choice to localStorage before navigating
        saveDateRangeToStorage(fromDate, toDate);

        // Add date range parameters
        urlParams.set('date_from', fromDate);
        urlParams.set('date_to', toDate);

        // Navigate to new URL using shared utility
        if (window.prFilterUtils) {
            window.prFilterUtils.navigateWithLoadingState(applyDateRangeButton, 'Loading...', urlParams);
        } else {
            // Fallback if shared utilities not available
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.location.href = newUrl;
        }
    }

    function clearDateRangeFilter() {
        // Don't clear input values - let backend control them based on default date range
        // Backend will now provide actual calculated dates for the default "last X days" period
        updateDateRangeInfo();

        // Clear saved date range from localStorage
        try {
            localStorage.removeItem(STORAGE_KEY);
        } catch (e) {
            // Silent fail
        }

        const urlParams = new URLSearchParams(window.location.search);
        urlParams.delete('date_from');
        urlParams.delete('date_to');
        urlParams.delete('reload_data');

        const newUrl = window.location.pathname + '?' + urlParams.toString();
        window.location.href = newUrl;
    }

    // Auto-apply functionality for pages without a button
    function autoApplyDateFilter() {
        const fromDate = dateFromInput ? dateFromInput.value : '';
        const toDate = dateToInput ? dateToInput.value : '';

        // Only auto-apply if we have a from date (required)
        if (fromDate) {
            updateDateRangeInfo();

            // Small delay to allow user to finish selecting both dates
            setTimeout(() => {
                applyDateRangeFilter();
            }, 500);
        }
    }

    // Event listeners
    if (applyDateRangeButton) {
        // Button-based filtering (JIRA closed tickets)
        applyDateRangeButton.addEventListener('click', applyDateRangeFilter);

        // For pages with button, only update info on change
        if (dateFromInput) {
            dateFromInput.addEventListener('change', updateDateRangeInfo);
        }

        if (dateToInput) {
            dateToInput.addEventListener('change', updateDateRangeInfo);
            dateToInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    applyDateRangeFilter();
                }
            });
        }
    } else {
        // Auto-apply filtering (PR pages without button)
        if (dateFromInput) {
            dateFromInput.addEventListener('change', autoApplyDateFilter);
        }

        if (dateToInput) {
            dateToInput.addEventListener('change', autoApplyDateFilter);
        }
    }

    // Handle clear filters button (skip for statistics pages - they have their own handler)
    const clearFiltersButton = document.getElementById('clear-filters');
    const path = window.location.pathname;
    const isStatsPage = path.includes('personal-stats') || path.includes('all-data-stats');

    if (clearFiltersButton && !isStatsPage) {
        clearFiltersButton.addEventListener('click', clearDateRangeFilter);
    }

    // Export function for use by clear filters button
    window.clearDateRangeFilter = clearDateRangeFilter;
});
