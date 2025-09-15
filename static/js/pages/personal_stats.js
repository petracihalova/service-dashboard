// Personal Statistics page JavaScript functionality

// Use IIFE to prevent variable conflicts and global scope pollution
(function() {
    'use strict';

    // Check if script already loaded to prevent duplicate execution
    if (typeof window.personalStatsScriptLoaded !== 'undefined') {
        return;
    }
    window.personalStatsScriptLoaded = true;

    document.addEventListener('DOMContentLoaded', function() {
        // Get DOM elements
        const dateInputs = document.querySelectorAll('#date-from-input, #date-to-input');
        const quarterSelect = document.getElementById('quarter-select');
        const yearSelect = document.getElementById('year-select');
        const fromInput = document.getElementById('date-from-input');
        const toInput = document.getElementById('date-to-input');
        const clearFiltersButton = document.getElementById('clear-filters');

        // Set max date to today for date inputs
        const today = new Date().toISOString().split('T')[0];
        if (fromInput) fromInput.max = today;
        if (toInput) toInput.max = today;

        // LocalStorage key for saving date range
        const STORAGE_KEY = 'personalStatsDateRange';

        // Save date range to localStorage
        function saveDateRange(fromDate, toDate) {
            const dateRange = {
                from: fromDate,
                to: toDate,
                timestamp: Date.now()
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(dateRange));
        }

        // Load date range from localStorage
        function loadSavedDateRange() {
            try {
                const saved = localStorage.getItem(STORAGE_KEY);
                if (saved) {
                    const dateRange = JSON.parse(saved);
                    // Check if saved date is not too old (expire after 30 days)
                    const thirtyDaysAgo = Date.now() - (30 * 24 * 60 * 60 * 1000);
                    if (dateRange.timestamp > thirtyDaysAgo) {
                        return dateRange;
                    }
                }
            } catch (e) {
                // Invalid JSON, ignore
            }
            return null;
        }

        // Save dates when inputs change (but don't auto-submit - let date_range_filter.js handle that)
        dateInputs.forEach(input => {
            input.addEventListener('change', function() {
                if (fromInput && toInput && fromInput.value && toInput.value) {
                    saveDateRange(fromInput.value, toInput.value);
                }
            });
        });

        // Populate year dropdown dynamically
        function populateYearDropdown() {
            if (!yearSelect) return;

            const currentDate = new Date();
            const currentYear = currentDate.getFullYear();
            const currentMonth = currentDate.getMonth() + 1; // JavaScript months are 0-indexed

            // Start from 2024, go to current year + 1 if we're in January
            const startYear = 2024;
            const endYear = currentMonth === 1 ? currentYear + 1 : currentYear;

            // Clear existing options except the first "Select..." option
            const selectOption = yearSelect.querySelector('option[value=""]');
            yearSelect.innerHTML = '';
            if (selectOption) {
                yearSelect.appendChild(selectOption);
            }

            // Add year options
            for (let year = startYear; year <= endYear; year++) {
                const option = document.createElement('option');
                option.value = year.toString();
                option.textContent = year.toString();
                yearSelect.appendChild(option);
            }
        }

        // Calculate date range based on quarter and year selection
        function calculateDateRange(quarter, year) {
            if (!quarter || !year) return null;

            const yearNum = parseInt(year);
            let fromDate, toDate;

            switch (quarter) {
                case 'q1':
                    fromDate = `${yearNum}-01-01`;
                    toDate = `${yearNum}-03-31`;
                    break;
                case 'q2':
                    fromDate = `${yearNum}-04-01`;
                    toDate = `${yearNum}-06-30`;
                    break;
                case 'q3':
                    fromDate = `${yearNum}-07-01`;
                    toDate = `${yearNum}-09-30`;
                    break;
                case 'q4':
                    fromDate = `${yearNum}-10-01`;
                    toDate = `${yearNum}-12-31`;
                    break;
                case 'all':
                    fromDate = `${yearNum}-01-01`;
                    toDate = `${yearNum}-12-31`;
                    break;
                default:
                    return null;
            }

            return { fromDate, toDate };
        }

        // Handle dropdown changes
        function handleDropdownChange() {
            const quarterValue = quarterSelect ? quarterSelect.value : '';
            const yearValue = yearSelect ? yearSelect.value : '';

            // Only proceed if both values are selected
            if (quarterValue && yearValue) {
                const dateRange = calculateDateRange(quarterValue, yearValue);

                if (dateRange && fromInput && toInput) {
                    fromInput.value = dateRange.fromDate;
                    toInput.value = dateRange.toDate;
                    // Save the selected date range
                    saveDateRange(dateRange.fromDate, dateRange.toDate);

                    // Trigger change events to let date_range_filter.js handle the filtering
                    const changeEvent = new Event('change', { bubbles: true });
                    fromInput.dispatchEvent(changeEvent);
                    toInput.dispatchEvent(changeEvent);
                }
            }
        }

        // Add event listeners to dropdowns
        if (quarterSelect) {
            quarterSelect.addEventListener('change', handleDropdownChange);
        }
        if (yearSelect) {
            yearSelect.addEventListener('change', handleDropdownChange);
        }

        // Clear filters functionality - handle everything for statistics pages
        if (clearFiltersButton) {
            clearFiltersButton.addEventListener('click', function(e) {
                // Prevent other event listeners from firing
                e.stopImmediatePropagation();

                // Calculate default 7-day range (6 days ago to today)
                const today = new Date();
                const defaultFrom = new Date();
                defaultFrom.setDate(today.getDate() - 6);

                // Format dates as YYYY-MM-DD
                const formatDate = (date) => {
                    return date.toISOString().split('T')[0];
                };

                // Reset dropdown selections
                if (quarterSelect) quarterSelect.value = '';
                if (yearSelect) yearSelect.value = '';

                // Clear localStorage
                try {
                    localStorage.removeItem(STORAGE_KEY);
                    // Also clear the date_range_filter.js storage keys
                    const path = window.location.pathname;
                    if (path.includes('personal-stats')) {
                        localStorage.removeItem('personalStats_dateRange');
                    } else if (path.includes('all-data-stats')) {
                        localStorage.removeItem('allDataStats_dateRange');
                    }
                } catch (e) {
                    // Silent fail
                }

                // Navigate to apply default filters using URL parameters
                const urlParams = new URLSearchParams();
                urlParams.set('date_from', formatDate(defaultFrom));
                urlParams.set('date_to', formatDate(today));

                const newUrl = window.location.pathname + '?' + urlParams.toString();
                window.location.href = newUrl;
            });
        }

        // Highlight current selection if dates match
        function highlightCurrentSelection() {
            if (!fromInput || !toInput || !quarterSelect || !yearSelect) return;

            const currentFrom = fromInput.value;
            const currentTo = toInput.value;

            // Try to match current date range with dropdown combinations
            const fromParts = currentFrom.split('-');
            const toParts = currentTo.split('-');

            if (fromParts.length === 3 && toParts.length === 3) {
                const year = fromParts[0];

                // Check if it's a full year (all quarters)
                if (currentFrom === `${year}-01-01` && currentTo === `${year}-12-31`) {
                    quarterSelect.value = 'all';
                    yearSelect.value = year;
                } else {
                    // Check individual quarters
                    const quarterRanges = {
                        'q1': { from: `${year}-01-01`, to: `${year}-03-31` },
                        'q2': { from: `${year}-04-01`, to: `${year}-06-30` },
                        'q3': { from: `${year}-07-01`, to: `${year}-09-30` },
                        'q4': { from: `${year}-10-01`, to: `${year}-12-31` }
                    };

                    for (const [quarter, range] of Object.entries(quarterRanges)) {
                        if (currentFrom === range.from && currentTo === range.to) {
                            quarterSelect.value = quarter;
                            yearSelect.value = year;
                            break;
                        }
                    }
                }
            }
        }

        // Load saved date range on page load if no URL parameters
        function loadSavedDateRangeOnPageLoad() {
            // Check if we have URL parameters for date range
            const urlParams = new URLSearchParams(window.location.search);
            const hasDateParams = urlParams.has('date_from') || urlParams.has('date_to');

            // Only load saved range if no URL parameters are present
            if (!hasDateParams) {
                const savedRange = loadSavedDateRange();
                if (savedRange && fromInput && toInput) {
                    // Check if current dates are different from saved dates
                    if (fromInput.value !== savedRange.from || toInput.value !== savedRange.to) {
                        // Update form inputs
                        fromInput.value = savedRange.from;
                        toInput.value = savedRange.to;

                        // Navigate to apply saved dates using URL parameters
                        const urlParams = new URLSearchParams();
                        urlParams.set('date_from', savedRange.from);
                        urlParams.set('date_to', savedRange.to);

                        const newUrl = window.location.pathname + '?' + urlParams.toString();
                        window.location.href = newUrl;
                    }
                }
            }
        }

        // Save current date range if it was loaded from URL parameters
        function saveCurrentDateRangeFromURL() {
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('date_from') || urlParams.has('date_to')) {
                // Page loaded with URL parameters, save current dates
                if (fromInput && toInput && fromInput.value && toInput.value) {
                    saveDateRange(fromInput.value, toInput.value);
                }
            }
        }

        // Initialize page
        populateYearDropdown();

        // Call on page load to highlight any matching selection
        highlightCurrentSelection();

        // Save current URL-based date range for future use
        saveCurrentDateRangeFromURL();

        // Load saved date range if applicable (only if no URL params)
        loadSavedDateRangeOnPageLoad();

        // === Code Stats Filters Functionality (previously inline in template) ===
        // Personal Statistics JavaScript - v3.0 (Updated: Removed Konflux filters for Personal Stats)
        // Cache Buster: If you see Konflux toggle errors, hard refresh (Ctrl+F5/Cmd+Shift+R)

        // Handle collapse chevron rotation
        // Handle Overall Activity panel
        const activityCollapse = document.getElementById('activityStatsCollapse');
        const activityChevron = activityCollapse?.parentElement.querySelector('.collapse-indicator');

        if (activityCollapse && activityChevron) {
            // Set initial state - activity panel starts expanded
            if (activityCollapse.classList.contains('show')) {
                activityChevron.style.transform = 'rotate(180deg)';
            }

            activityCollapse.addEventListener('show.bs.collapse', function() {
                activityChevron.style.transform = 'rotate(180deg)';
            });

            activityCollapse.addEventListener('hide.bs.collapse', function() {
                activityChevron.style.transform = 'rotate(0deg)';
            });
        }

        // Handle Code Impact panel
        const codeStatsCollapse = document.getElementById('codeStatsCollapse');
        const codeStatsChevron = codeStatsCollapse?.parentElement.querySelector('.collapse-indicator');

        if (codeStatsCollapse && codeStatsChevron) {
            // Set initial state - code stats panel starts expanded
            if (codeStatsCollapse.classList.contains('show')) {
                codeStatsChevron.style.transform = 'rotate(180deg)';
            }

            codeStatsCollapse.addEventListener('show.bs.collapse', function() {
                codeStatsChevron.style.transform = 'rotate(180deg)';
            });

            codeStatsCollapse.addEventListener('hide.bs.collapse', function() {
                codeStatsChevron.style.transform = 'rotate(0deg)';
            });
        }

        // Handle Code Stats Filters
        const githubOnlyToggle = document.getElementById('githubOnlyToggle');
        const gitlabOnlyToggle = document.getElementById('gitlabOnlyToggle');
        const appInterfaceOnlyToggle = document.getElementById('appInterfaceOnlyToggle');
        const withoutPersonalToggle = document.getElementById('withoutPersonalToggle');
        const clearCodeStatsFilters = document.getElementById('clearCodeStatsFilters');

        // Defensive: Define old toggles as null to prevent ReferenceError if cached code references them
        const mergedOnlyToggle = null;
        const closedOnlyToggle = null;
        const konfluxOnlyToggle = null;
        const nonKonfluxOnlyToggle = null;

        // Initialize toggle states from URL parameters
        function initializeCodeStatsFilters() {
            const urlParams = new URLSearchParams(window.location.search);
            const codeStatsSource = urlParams.get('code_stats_source');
            const codeStatsExcludePersonal = urlParams.get('code_stats_exclude_personal');

            // Clear all source toggles first
            if (githubOnlyToggle) githubOnlyToggle.checked = false;
            if (gitlabOnlyToggle) gitlabOnlyToggle.checked = false;
            if (appInterfaceOnlyToggle) appInterfaceOnlyToggle.checked = false;

            // Clear personal repo filter
            if (withoutPersonalToggle) withoutPersonalToggle.checked = false;

            // Set the active source toggle based on URL parameter
            if (codeStatsSource === 'github' && githubOnlyToggle) {
                githubOnlyToggle.checked = true;
            } else if (codeStatsSource === 'gitlab' && gitlabOnlyToggle) {
                gitlabOnlyToggle.checked = true;
            } else if (codeStatsSource === 'app-interface' && appInterfaceOnlyToggle) {
                appInterfaceOnlyToggle.checked = true;
            }

            // Set the personal repo filter based on URL parameter
            if (codeStatsExcludePersonal === 'true' && withoutPersonalToggle) {
                withoutPersonalToggle.checked = true;
            }

            // Force visual update by triggering a reflow, then complete initialization
            setTimeout(() => {
                refreshToggleVisuals();
                completeCodeStatsInitialization();
            }, 50);
        }

        // Helper function to refresh toggle visuals
        function refreshToggleVisuals() {
            // Only process existing toggles (defensive coding for browser cache issues)
            const toggles = [githubOnlyToggle, gitlabOnlyToggle, appInterfaceOnlyToggle, withoutPersonalToggle].filter(toggle => toggle);

            toggles.forEach(toggle => {
                // Force a visual refresh
                const wasChecked = toggle.checked;
                toggle.style.display = 'none';
                toggle.offsetHeight; // Force reflow
                toggle.style.display = '';

                // Ensure the checked state is maintained
                if (wasChecked) {
                    toggle.checked = true;
                }
            });
        }

        // Continue with the initialization after refreshing visuals
        function completeCodeStatsInitialization() {
            const urlParams = new URLSearchParams(window.location.search);
            const codeStatsSource = urlParams.get('code_stats_source');
            const codeStatsExcludePersonal = urlParams.get('code_stats_exclude_personal');

            // Auto-scroll to Code Impact filters if any filter is applied
            if (codeStatsSource || codeStatsExcludePersonal) {
                setTimeout(() => {
                    const filtersElement = document.getElementById('codeStatsFilters');
                    if (filtersElement) {
                        filtersElement.scrollIntoView({
                            behavior: 'smooth',
                            block: 'center',
                            inline: 'nearest'
                        });
                    }
                }, 150); // Small delay to ensure page is fully loaded
            }
        }

        // Handle source filter changes (mutually exclusive within source filters)
        function handleCodeStatsSourceFilterChange(activeToggle, sourceValue) {
            const urlParams = new URLSearchParams(window.location.search);

            // Clear other source toggles
            [githubOnlyToggle, gitlabOnlyToggle, appInterfaceOnlyToggle].forEach(toggle => {
                if (toggle && toggle !== activeToggle) {
                    toggle.checked = false;
                }
            });

            if (activeToggle.checked) {
                urlParams.set('code_stats_source', sourceValue);
            } else {
                urlParams.delete('code_stats_source');
            }

            // Navigate to new URL
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.location.href = newUrl;
        }

        // Handle personal repository filter (independent toggle)
        function handleCodeStatsPersonalRepoFilterChange(activeToggle) {
            const urlParams = new URLSearchParams(window.location.search);

            if (activeToggle.checked) {
                urlParams.set('code_stats_exclude_personal', 'true');
            } else {
                urlParams.delete('code_stats_exclude_personal');
            }

            // Navigate to new URL
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.location.href = newUrl;
        }

        // Add event listeners for source filters
        if (githubOnlyToggle) {
            githubOnlyToggle.addEventListener('change', function() {
                handleCodeStatsSourceFilterChange(this, 'github');
            });
        }

        if (gitlabOnlyToggle) {
            gitlabOnlyToggle.addEventListener('change', function() {
                handleCodeStatsSourceFilterChange(this, 'gitlab');
            });
        }

        if (appInterfaceOnlyToggle) {
            appInterfaceOnlyToggle.addEventListener('change', function() {
                handleCodeStatsSourceFilterChange(this, 'app-interface');
            });
        }

        // Add event listeners for status filters (legacy - kept for defensive compatibility)
        if (mergedOnlyToggle) {
            mergedOnlyToggle.addEventListener('change', function() {
                handleCodeStatsStatusFilterChange(this, 'merged');
            });
        }

        if (closedOnlyToggle) {
            closedOnlyToggle.addEventListener('change', function() {
                handleCodeStatsStatusFilterChange(this, 'closed');
            });
        }

        // Add event listener for personal repository filter
        if (withoutPersonalToggle) {
            withoutPersonalToggle.addEventListener('change', function() {
                handleCodeStatsPersonalRepoFilterChange(this);
            });
        }

        // Clear all filters
        if (clearCodeStatsFilters) {
            clearCodeStatsFilters.addEventListener('click', function() {
                const urlParams = new URLSearchParams(window.location.search);
                urlParams.delete('code_stats_source');
                urlParams.delete('code_stats_exclude_personal');

                const newUrl = window.location.pathname + '?' + urlParams.toString();
                window.location.href = newUrl;
            });
        }

        // Handler function for status filter changes (legacy - kept for compatibility)
        function handleCodeStatsStatusFilterChange(activeToggle, statusValue) {
            const urlParams = new URLSearchParams(window.location.search);

            // Clear other status toggles
            [mergedOnlyToggle, closedOnlyToggle].forEach(toggle => {
                if (toggle && toggle !== activeToggle) {
                    toggle.checked = false;
                }
            });

            if (activeToggle.checked) {
                urlParams.set('code_stats_status', statusValue);
            } else {
                urlParams.delete('code_stats_status');
            }

            // Navigate to new URL
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.location.href = newUrl;
        }

        // Initialize code stats filters on page load
        if (githubOnlyToggle || gitlabOnlyToggle || appInterfaceOnlyToggle || withoutPersonalToggle) {
            initializeCodeStatsFilters();
        }
    });

})();
