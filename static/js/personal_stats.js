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
        const quarterButtons = document.querySelectorAll('.quarter-btn');
        const yearButtons = document.querySelectorAll('.year-btn');
        const fromInput = document.getElementById('date-from-input');
        const toInput = document.getElementById('date-to-input');
        const form = document.querySelector('form');
        const resetButton = document.getElementById('reset-filters');

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

        // Save dates when inputs change
        dateInputs.forEach(input => {
            input.addEventListener('change', function() {
                if (fromInput && toInput && fromInput.value && toInput.value) {
                    saveDateRange(fromInput.value, toInput.value);
                }
            });
        });

        // Save dates when form is submitted
        if (form) {
            form.addEventListener('submit', function() {
                if (fromInput && toInput && fromInput.value && toInput.value) {
                    saveDateRange(fromInput.value, toInput.value);
                }
            });
        }

        // Year selection functionality
        yearButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Remove active state from all buttons
                quarterButtons.forEach(btn => btn.classList.remove('active'));
                yearButtons.forEach(btn => btn.classList.remove('active'));

                // Add active state to clicked button
                this.classList.add('active');

                // Set the date inputs
                const fromDate = this.getAttribute('data-from');
                const toDate = this.getAttribute('data-to');

                if (fromInput && toInput) {
                    fromInput.value = fromDate;
                    toInput.value = toDate;
                    // Save the selected date range
                    saveDateRange(fromDate, toDate);
                }

                // Auto-submit form for immediate filtering
                if (form) {
                    form.submit();
                }
            });
        });

        // Quarter selection functionality
        quarterButtons.forEach(button => {
            button.addEventListener('click', function() {
                // Remove active state from all buttons
                quarterButtons.forEach(btn => btn.classList.remove('active'));
                yearButtons.forEach(btn => btn.classList.remove('active'));

                // Add active state to clicked button
                this.classList.add('active');

                // Set the date inputs
                const fromDate = this.getAttribute('data-from');
                const toDate = this.getAttribute('data-to');

                if (fromInput && toInput) {
                    fromInput.value = fromDate;
                    toInput.value = toDate;
                    // Save the selected date range
                    saveDateRange(fromDate, toDate);
                }

                // Auto-submit form for immediate filtering
                if (form) {
                    form.submit();
                }
            });
        });

        // Reset filters functionality
        if (resetButton) {
            resetButton.addEventListener('click', function() {
                // Calculate default 7-day range (6 days ago to today)
                const today = new Date();
                const defaultFrom = new Date();
                defaultFrom.setDate(today.getDate() - 6);

                // Format dates as YYYY-MM-DD
                const formatDate = (date) => {
                    return date.toISOString().split('T')[0];
                };

                // Set default date range
                if (fromInput && toInput) {
                    fromInput.value = formatDate(defaultFrom);
                    toInput.value = formatDate(today);
                    // Save the default date range
                    saveDateRange(formatDate(defaultFrom), formatDate(today));
                }

                // Remove active state from all buttons
                quarterButtons.forEach(btn => btn.classList.remove('active'));
                yearButtons.forEach(btn => btn.classList.remove('active'));

                // Auto-submit form to apply default filters
                if (form) {
                    form.submit();
                }
            });
        }

        // Highlight current selection if dates match
        function highlightCurrentSelection() {
            if (!fromInput || !toInput) return;

            const currentFrom = fromInput.value;
            const currentTo = toInput.value;

            // Check year buttons first
            yearButtons.forEach(button => {
                if (button.getAttribute('data-from') === currentFrom &&
                    button.getAttribute('data-to') === currentTo) {
                    button.classList.add('active');
                }
            });

            // Check quarter buttons
            quarterButtons.forEach(button => {
                if (button.getAttribute('data-from') === currentFrom &&
                    button.getAttribute('data-to') === currentTo) {
                    button.classList.add('active');
                }
            });
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

                        // Submit form to apply saved dates
                        if (form) {
                            form.submit();
                        }
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

        // Call on page load to highlight any matching selection
        highlightCurrentSelection();

        // Save current URL-based date range for future use
        saveCurrentDateRangeFromURL();

        // Load saved date range if applicable (only if no URL params)
        loadSavedDateRangeOnPageLoad();
    });

})();
