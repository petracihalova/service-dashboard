// All Data Statistics page JavaScript functionality

document.addEventListener('DOMContentLoaded', function() {
    // User configuration modal functionality
    const userConfigInfo = document.getElementById('user-config-info');
    const userConfigInfoOverview = document.getElementById('user-config-info-overview');

    function showConfigModal() {
        const configModal = document.getElementById('configModal');
        if (configModal) {
            const modal = new bootstrap.Modal(configModal);
            modal.show();

            // Handle modal cleanup when hidden
            configModal.addEventListener('hidden.bs.modal', function () {
                // Remove any remaining backdrop
                const backdrop = document.querySelector('.modal-backdrop');
                if (backdrop) {
                    backdrop.remove();
                }

                // Remove modal-open class from body
                document.body.classList.remove('modal-open');
                document.body.style.removeProperty('overflow');
                document.body.style.removeProperty('padding-right');
            });
        }
    }

    if (userConfigInfo) {
        userConfigInfo.addEventListener('click', showConfigModal);
    }

    if (userConfigInfoOverview) {
        userConfigInfoOverview.addEventListener('click', showConfigModal);
    }

        // User stats toggle functionality
    function setupUserStatsToggle(toggleId, fullId) {
        const toggle = document.getElementById(toggleId);
        const full = document.getElementById(fullId);

        if (toggle && full) {
            // Check if already has event listener to prevent duplicates
            if (toggle.hasAttribute('data-listener-attached')) {
                return;
            }

            // Mark as having listener attached
            toggle.setAttribute('data-listener-attached', 'true');

            // Store original text for toggling
            const originalText = toggle.innerHTML;

            toggle.addEventListener('click', function(e) {
                e.preventDefault(); // Prevent any default button behavior
                e.stopPropagation(); // Prevent event bubbling

                // Add small delay to prevent rapid double-clicks
                if (this.disabled) {
                    return;
                }

                // Temporarily disable button
                this.disabled = true;
                setTimeout(() => {
                    this.disabled = false;
                }, 300); // Re-enable after 300ms

                // Check current state using computed style
                const computedStyle = window.getComputedStyle(full);
                const currentDisplay = computedStyle.display;
                const isExpanded = currentDisplay !== 'none';

                if (isExpanded) {
                    // Collapse - hide additional users
                    full.style.display = 'none';
                    toggle.innerHTML = originalText;
                } else {
                    // Expand - show all users
                    full.style.display = 'block';
                    toggle.innerHTML = '<i class="bi bi-chevron-up me-1"></i>Show less';
                }
            });
        }
    }

    // Setup toggle functionality for all panels
    setupUserStatsToggle('github-user-stats-toggle', 'github-user-stats-full');
    setupUserStatsToggle('gitlab-user-stats-toggle', 'gitlab-user-stats-full');
    setupUserStatsToggle('app-interface-user-stats-toggle', 'app-interface-user-stats-full');

    // Handle collapse chevron rotation and Code Stats filters
    // Handle Overall Activity panel
    const overallActivityCollapse = document.getElementById('overallActivityCollapse');
    const overallActivityChevron = overallActivityCollapse?.parentElement.querySelector('.collapse-indicator');

    if (overallActivityCollapse && overallActivityChevron) {
        overallActivityCollapse.addEventListener('show.bs.collapse', function() {
            overallActivityChevron.style.transform = 'rotate(180deg)';
        });

        overallActivityCollapse.addEventListener('hide.bs.collapse', function() {
            overallActivityChevron.style.transform = 'rotate(0deg)';
        });
    }

    // Handle Code Stats panel
    const codeStatsCollapse = document.getElementById('allDataCodeStatsCollapse');
    const codeStatsChevron = codeStatsCollapse?.parentElement.querySelector('.collapse-indicator');

    if (codeStatsCollapse && codeStatsChevron) {
        codeStatsCollapse.addEventListener('show.bs.collapse', function() {
            codeStatsChevron.style.transform = 'rotate(180deg)';
        });

        codeStatsCollapse.addEventListener('hide.bs.collapse', function() {
            codeStatsChevron.style.transform = 'rotate(0deg)';
        });
    }

    // Handle Code Stats Filters
    const githubOnlyToggle = document.getElementById('allDataGithubOnlyToggle');
    const gitlabOnlyToggle = document.getElementById('allDataGitlabOnlyToggle');
    const appInterfaceOnlyToggle = document.getElementById('allDataAppInterfaceOnlyToggle');
    const konfluxOnlyToggle = document.getElementById('allDataKonfluxOnlyToggle');
    const nonKonfluxOnlyToggle = document.getElementById('allDataNonKonfluxOnlyToggle');
    const clearCodeStatsFilters = document.getElementById('allDataClearCodeStatsFilters');

    // Initialize toggle states from URL parameters
    function initializeCodeStatsFilters() {
        const urlParams = new URLSearchParams(window.location.search);
        const codeStatsSource = urlParams.get('code_stats_source');
        const konfluxFilter = urlParams.get('code_stats_konflux_filter');

        // Clear all source toggles first
        if (githubOnlyToggle) githubOnlyToggle.checked = false;
        if (gitlabOnlyToggle) gitlabOnlyToggle.checked = false;
        if (appInterfaceOnlyToggle) appInterfaceOnlyToggle.checked = false;

        // Set the active source toggle based on URL parameter
        if (codeStatsSource === 'github' && githubOnlyToggle) {
            githubOnlyToggle.checked = true;
        } else if (codeStatsSource === 'gitlab' && gitlabOnlyToggle) {
            gitlabOnlyToggle.checked = true;
        } else if (codeStatsSource === 'app-interface' && appInterfaceOnlyToggle) {
            appInterfaceOnlyToggle.checked = true;
        }

        // Set the Konflux filter toggles
        if (konfluxOnlyToggle) konfluxOnlyToggle.checked = false;
        if (nonKonfluxOnlyToggle) nonKonfluxOnlyToggle.checked = false;

        if (konfluxFilter === 'konflux' && konfluxOnlyToggle) {
            konfluxOnlyToggle.checked = true;
        } else if (konfluxFilter === 'non-konflux' && nonKonfluxOnlyToggle) {
            nonKonfluxOnlyToggle.checked = true;
        }
    }

    // Handle source filter changes (mutually exclusive within source filters)
    function handleSourceFilterChange(activeToggle, sourceValue) {
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

    // Add event listeners for source filters
    if (githubOnlyToggle) {
        githubOnlyToggle.addEventListener('change', function() {
            handleSourceFilterChange(this, 'github');
        });
    }

    if (gitlabOnlyToggle) {
        gitlabOnlyToggle.addEventListener('change', function() {
            handleSourceFilterChange(this, 'gitlab');
        });
    }

    if (appInterfaceOnlyToggle) {
        appInterfaceOnlyToggle.addEventListener('change', function() {
            handleSourceFilterChange(this, 'app-interface');
        });
    }

    // Handle Konflux filter toggles (mutually exclusive)
    if (konfluxOnlyToggle) {
        konfluxOnlyToggle.addEventListener('change', function() {
            handleKonfluxFilterChange(this, 'konflux');
        });
    }

    if (nonKonfluxOnlyToggle) {
        nonKonfluxOnlyToggle.addEventListener('change', function() {
            handleKonfluxFilterChange(this, 'non-konflux');
        });
    }

    // Handler function for Konflux filter changes
    function handleKonfluxFilterChange(activeToggle, filterValue) {
        const urlParams = new URLSearchParams(window.location.search);

        // Clear other Konflux toggles (mutually exclusive)
        [konfluxOnlyToggle, nonKonfluxOnlyToggle].forEach(toggle => {
            if (toggle && toggle !== activeToggle) {
                toggle.checked = false;
            }
        });

        if (activeToggle.checked) {
            urlParams.set('code_stats_konflux_filter', filterValue);
        } else {
            urlParams.delete('code_stats_konflux_filter');
        }

        // Navigate to new URL
        const newUrl = window.location.pathname + '?' + urlParams.toString();
        window.location.href = newUrl;
    }

    // Clear all filters
    if (clearCodeStatsFilters) {
        clearCodeStatsFilters.addEventListener('click', function() {
            const urlParams = new URLSearchParams(window.location.search);
            urlParams.delete('code_stats_source');
            urlParams.delete('code_stats_konflux_filter');

            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.location.href = newUrl;
        });
    }

    // Initialize filters on page load
    initializeCodeStatsFilters();

    // === Date Range Management (All Data Statistics specific) ===

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

    // LocalStorage key for All Data Statistics - matches date_range_filter.js
    const STORAGE_KEY = 'allDataStats_dateRange';

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

    // Clear filters functionality - handle everything for all data statistics pages
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

            // Clear localStorage - only for All Data Statistics
            try {
                localStorage.removeItem(STORAGE_KEY);
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
});
