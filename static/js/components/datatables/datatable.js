window.onload = function () {
    // Initialize DataTables with column-specific filters
    window.dataTable = new DataTable('#datatable', {
        order: [[0, 'asc']],
        autoWidth: false,
        columnDefs: [
            {
                targets: "dateTimeRenderColumn",
                render: DataTable.render.datetime('MMMM Do YYYY')
            },
            {
                targets: [6], // Days Open column (0-based index: Repository=0, PR/MR=1, Author=2, Changes=3, Size=4, Days Open=5, Date=6)
                type: 'num',
                className: 'text-center'
            }
        ],
        displayLength: 50,
        initComplete: function () {
            // Add individual column filters
            this.api()
                .columns()
                .every(function (columnIndex) {
                    var column = this;
                    var title = $(column.header()).text();

                    // Skip certain columns from getting filters
                    if (columnIndex === 1 || // PR/MR column (too complex)
                        columnIndex === 3 || // Changes column (numeric, not useful for filtering)
                        columnIndex === 4 || // Hidden Lines column
                        columnIndex === 6 || // Days Open column (numeric)
                        columnIndex === 7) { // Created at column (has date picker below)
                        return;
                    }

                    var filterContainer = $('<div class="column-filter mb-2"></div>')
                        .on('click', function(e) {
                            e.stopPropagation(); // Prevent any clicks in filter area from triggering column sort
                        });

                    if (columnIndex === 0) { // Repository column
                        var multiSelectContainer = $('<div class="multi-select-container"></div>');
                        var toggleButton = $('<button type="button" class="btn btn-outline-secondary btn-sm dropdown-toggle w-100 text-start" data-bs-toggle="dropdown">All Repositories</button>')
                            .appendTo(multiSelectContainer)
                            .on('click', function(e) {
                                e.stopPropagation(); // Prevent triggering column sort
                            });
                        var dropdownMenu = $('<div class="dropdown-menu p-2" style="min-width: 200px;"></div>')
                            .appendTo(multiSelectContainer);

                        // Add "Select All" option
                        var selectAllContainer = $('<div class="form-check mb-2"></div>');
                        var selectAllCheckbox = $('<input class="form-check-input" type="checkbox" id="selectAll-' + columnIndex + '" checked>')
                            .appendTo(selectAllContainer);
                        var selectAllLabel = $('<label class="form-check-label fw-bold" for="selectAll-' + columnIndex + '">Select All</label>')
                            .appendTo(selectAllContainer);
                        dropdownMenu.append(selectAllContainer);
                        dropdownMenu.append('<hr class="dropdown-divider">');

                        var selectedValues = [];

                        // Get unique values and add checkboxes
                        var uniqueValues = [];
                        column.data().unique().sort().each(function (d) {
                            if (d) {
                                uniqueValues.push(d);
                                selectedValues.push(d); // Initially all selected
                            }
                        });

                        uniqueValues.forEach(function(repo, index) {
                            var checkContainer = $('<div class="form-check"></div>');
                            var checkbox = $('<input class="form-check-input repo-checkbox" type="checkbox" id="repo-' + columnIndex + '-' + index + '" checked>')
                                .appendTo(checkContainer);
                            var label = $('<label class="form-check-label" for="repo-' + columnIndex + '-' + index + '">' + repo + '</label>')
                                .appendTo(checkContainer);
                            dropdownMenu.append(checkContainer);
                        });

                        multiSelectContainer.appendTo(filterContainer);

                        // Handle individual checkbox changes
                        dropdownMenu.on('change', '.repo-checkbox', function() {
                            var repoValue = $(this).next('label').text();
                            if ($(this).is(':checked')) {
                                if (!selectedValues.includes(repoValue)) {
                                    selectedValues.push(repoValue);
                                }
                            } else {
                                selectedValues = selectedValues.filter(v => v !== repoValue);
                            }

                            // Update select all checkbox
                            selectAllCheckbox.prop('checked', selectedValues.length === uniqueValues.length);

                            updateRepositoryFilter();
                        });

                        // Handle "Select All" checkbox
                        selectAllCheckbox.on('change', function() {
                            var isChecked = $(this).is(':checked');
                            $('.repo-checkbox').prop('checked', isChecked);

                            if (isChecked) {
                                selectedValues = [...uniqueValues];
                            } else {
                                selectedValues = [];
                            }

                            updateRepositoryFilter();
                        });

                        function updateRepositoryFilter() {
                            if (selectedValues.length === 0 || selectedValues.length === uniqueValues.length) {
                                // All or none selected - show all
                                column.search('').draw();
                                toggleButton.text('All Repositories');
                            } else {
                                // Some selected - create regex pattern
                                var regexPattern = '^(' + selectedValues.map(v => $.fn.dataTable.util.escapeRegex(v)).join('|') + ')$';
                                column.search(regexPattern, true, false).draw();
                                toggleButton.text(selectedValues.length + ' selected');
                            }
                        }

                    } else if (columnIndex === 2) { // Author column
                        var input = $('<input type="text" class="form-control form-control-sm" placeholder="Filter authors...">')
                            .appendTo(filterContainer)
                            .on('keyup change clear', function () {
                                var val = $(this).val();
                                column.search(val ? val : '', true, false).draw();
                            })
                            .on('click', function(e) {
                                e.stopPropagation(); // Prevent triggering column sort
                            });

                    } else if (columnIndex === 5) { // Size column
                        var multiSelectContainer = $('<div class="multi-select-container"></div>');
                        var toggleButton = $('<button type="button" class="btn btn-outline-secondary btn-sm dropdown-toggle w-100 text-start" data-bs-toggle="dropdown">All Sizes</button>')
                            .appendTo(multiSelectContainer)
                            .on('click', function(e) {
                                e.stopPropagation(); // Prevent triggering column sort
                            });
                        var dropdownMenu = $('<div class="dropdown-menu p-2" style="min-width: 180px;"></div>')
                            .appendTo(multiSelectContainer);

                        // Add "Select All" option
                        var selectAllContainer = $('<div class="form-check mb-2"></div>');
                        var selectAllCheckbox = $('<input class="form-check-input" type="checkbox" id="selectAllSize-' + columnIndex + '" checked>')
                            .appendTo(selectAllContainer);
                        var selectAllLabel = $('<label class="form-check-label fw-bold" for="selectAllSize-' + columnIndex + '">Select All</label>')
                            .appendTo(selectAllContainer);
                        dropdownMenu.append(selectAllContainer);
                        dropdownMenu.append('<hr class="dropdown-divider">');

                        var sizeOptions = ['No Changes', 'Small', 'Medium', 'Large', 'Huge'];
                        var selectedSizes = [...sizeOptions]; // Initially all selected

                        sizeOptions.forEach(function(size, index) {
                            var checkContainer = $('<div class="form-check"></div>');
                            var checkbox = $('<input class="form-check-input size-checkbox" type="checkbox" id="size-' + columnIndex + '-' + index + '" checked>')
                                .appendTo(checkContainer);
                            var label = $('<label class="form-check-label" for="size-' + columnIndex + '-' + index + '">' + size + '</label>')
                                .appendTo(checkContainer);
                            dropdownMenu.append(checkContainer);
                        });

                        multiSelectContainer.appendTo(filterContainer);

                        // Handle individual checkbox changes
                        dropdownMenu.on('change', '.size-checkbox', function() {
                            var sizeValue = $(this).next('label').text();
                            if ($(this).is(':checked')) {
                                if (!selectedSizes.includes(sizeValue)) {
                                    selectedSizes.push(sizeValue);
                                }
                            } else {
                                selectedSizes = selectedSizes.filter(v => v !== sizeValue);
                            }

                            // Update select all checkbox
                            selectAllCheckbox.prop('checked', selectedSizes.length === sizeOptions.length);

                            updateSizeFilter();
                        });

                        // Handle "Select All" checkbox
                        selectAllCheckbox.on('change', function() {
                            var isChecked = $(this).is(':checked');
                            $('.size-checkbox').prop('checked', isChecked);

                            if (isChecked) {
                                selectedSizes = [...sizeOptions];
                            } else {
                                selectedSizes = [];
                            }

                            updateSizeFilter();
                        });

                        function updateSizeFilter() {
                            if (selectedSizes.length === 0 || selectedSizes.length === sizeOptions.length) {
                                // All or none selected - show all
                                column.search('').draw();
                                toggleButton.text('All Sizes');
                            } else {
                                // Some selected - create regex pattern for hidden spans
                                var regexPattern = '(' + selectedSizes.join('|') + ')';
                                column.search(regexPattern, true, false).draw();
                                toggleButton.text(selectedSizes.length + ' selected');
                            }
                        }
                    }

                    // Add the filter container to the column header
                    if (filterContainer.children().length > 0) {
                        $(column.header()).append(filterContainer);
                    }
                });

                // Restore previously saved column filter state after all column filters are created
                setTimeout(function() {
                    restoreColumnFilterState();
                }, 100); // Small delay to ensure all DOM elements are ready
        },
        drawCallback: function (settings) {
            var api = this.api();
            var rows = api.rows({ page: 'current' }).nodes();
            var last = null;

            // Get the actual number of visible columns dynamically
            var columnCount = api.columns(':visible').count();

            api.column(0, { page: 'current' })
                .data()
                .each(function (group, i) {
                    if (last !== group) {
                        rows[i].insertAdjacentHTML('beforebegin', '<tr class="group"><td colspan="' + columnCount + '">' +
                            group + '</td></tr>');
                        last = group;
                    }
                });
        }
    });

    // Apply initial size filter from URL parameter after DataTable is loaded
    if (window.prFilterUtils && window.prFilterUtils.applyInitialSizeFilter) {
        window.prFilterUtils.applyInitialSizeFilter();
    }

    // Column filters clear functionality - now integrated with main "Clear filters" button
    window.clearColumnFilters = function() {
        if (!window.dataTable) return; // Guard clause if DataTable not initialized

        // Clear all column-specific searches
        window.dataTable.columns().every(function() {
            this.search('');
        });

        // Reset all column filter inputs/selects
        $('.column-filter select').val('');
        $('.column-filter input').val('');

        // Reset multi-select checkboxes and buttons
        $('.column-filter .form-check-input').prop('checked', true);
        $('.column-filter button[data-bs-toggle="dropdown"]').each(function() {
            var buttonText = $(this).text();
            if (buttonText.includes('Repositories')) {
                $(this).text('All Repositories');
            } else if (buttonText.includes('Sizes') || buttonText.includes('selected')) {
                $(this).text('All Sizes');
            }
        });

        // Redraw table
        window.dataTable.draw();

        // Clear any saved column filter state since we're clearing filters
        try {
            localStorage.removeItem('openPR_columnFilters');
        } catch (e) {
            // Silent fail
        }
    };

    // Prevent dropdown from closing when clicking inside multi-select menus
    // Note: This only prevents Bootstrap dropdown closing, not column sorting (handled above)
    $(document).on('click', '.multi-select-container .dropdown-menu', function(e) {
        e.stopPropagation();
    });

    // Global functions for saving/restoring column filter state
    window.saveColumnFilterState = function() {
        if (!window.dataTable) {
            return;
        }

        const filterState = {
            timestamp: Date.now(),
            filters: {}
        };

        try {
            // Save repository filter state
            const repoButton = $('.column-filter button[data-bs-toggle="dropdown"]').first(); // First dropdown is repository
            if (repoButton.length > 0) {
                const selectedRepos = [];
                const totalRepos = $('.repo-checkbox').length;
                $('.repo-checkbox:checked').each(function() {
                    selectedRepos.push($(this).next('label').text());
                });
                // Only save if it's a subset (not all selected)
                if (selectedRepos.length > 0 && selectedRepos.length < totalRepos) {
                    filterState.filters.repositories = {
                        selected: selectedRepos,
                        buttonText: repoButton.text(),
                        isFiltered: true
                    };
                } else if (selectedRepos.length === 0) {
                    filterState.filters.repositories = {
                        selected: [],
                        buttonText: repoButton.text(),
                        isFiltered: true
                    };
                }
            }

            // Save size filter state
            const sizeButton = $('.column-filter button[data-bs-toggle="dropdown"]').eq(1); // Second dropdown is size
            if (sizeButton.length > 0) {
                const selectedSizes = [];
                $('.size-checkbox:checked').each(function() {
                    selectedSizes.push($(this).next('label').text());
                });
                filterState.filters.sizes = {
                    selected: selectedSizes,
                    buttonText: sizeButton.text()
                };
            }

            // Save author filter state
            const authorInput = $('.column-filter input[placeholder*="author"]');
            if (authorInput.length > 0) {
                filterState.filters.author = authorInput.val();
            }

            // Save to localStorage with page-specific key
            const storageKey = 'openPR_columnFilters';
            localStorage.setItem(storageKey, JSON.stringify(filterState));

        } catch (e) {
            console.warn('Could not save column filter state:', e);
        }
    };

    function restoreColumnFilterState() {
        try {
            const storageKey = 'openPR_columnFilters';
            const savedState = localStorage.getItem(storageKey);

            if (!savedState) return;

            const filterState = JSON.parse(savedState);

            // Only restore if saved within last 5 minutes (to avoid stale data)
            if (!filterState.timestamp || Date.now() - filterState.timestamp > 5 * 60 * 1000) {
                localStorage.removeItem(storageKey);
                return;
            }

            // Restore repository filter
            if (filterState.filters.repositories && filterState.filters.repositories.isFiltered) {
                const repoData = filterState.filters.repositories;
                const repoButton = $('.column-filter button[data-bs-toggle="dropdown"]').first(); // First dropdown is repository

                if (repoButton.length > 0) {
                    // Uncheck all first
                    $('.repo-checkbox').prop('checked', false);
                    $('#selectAll-0').prop('checked', false);

                    // Check selected repositories
                    if (repoData.selected && repoData.selected.length > 0) {
                        repoData.selected.forEach(function(repoName) {
                            $('.repo-checkbox').each(function() {
                                if ($(this).next('label').text() === repoName) {
                                    $(this).prop('checked', true);
                                }
                            });
                        });

                        // Apply the filter
                        const regexPattern = '^(' + repoData.selected.map(v => $.fn.dataTable.util.escapeRegex(v)).join('|') + ')$';
                        window.dataTable.column(0).search(regexPattern, true, false).draw();
                    } else {
                        // No repositories selected - apply filter that matches nothing
                        window.dataTable.column(0).search('^$', true, false).draw(); // Pattern that matches nothing
                    }

                    // Update button text
                    repoButton.text(repoData.buttonText);
                }
            }

            // Restore size filter
            if (filterState.filters.sizes) {
                const sizeData = filterState.filters.sizes;
                const sizeButton = $('.column-filter button[data-bs-toggle="dropdown"]').eq(1); // Second dropdown is size

                if (sizeButton.length > 0 && sizeData.selected && sizeData.selected.length > 0) {
                    // Uncheck all first
                    $('.size-checkbox').prop('checked', false);
                    $('#selectAllSize-5').prop('checked', false);

                    // Check selected sizes
                    sizeData.selected.forEach(function(sizeName) {
                        $('.size-checkbox').each(function() {
                            if ($(this).next('label').text() === sizeName) {
                                $(this).prop('checked', true);
                            }
                        });
                    });

                    // Update button text and apply filter
                    sizeButton.text(sizeData.buttonText);

                    // Apply the filter
                    const selectedSizes = sizeData.selected;
                    if (selectedSizes.length > 0 && selectedSizes.length < 5) { // 5 total size options
                        const regexPattern = '(' + selectedSizes.join('|') + ')';
                        window.dataTable.column(5).search(regexPattern, true, false).draw();
                    }
                }
            }

            // Restore author filter
            if (filterState.filters.author && filterState.filters.author.trim() !== '') {
                const authorInput = $('.column-filter input[placeholder*="author"]');
                if (authorInput.length > 0) {
                    authorInput.val(filterState.filters.author);
                    window.dataTable.column(2).search(filterState.filters.author, true, false).draw();
                }
            }

            // Clear the saved state after successful restore
            localStorage.removeItem(storageKey);

        } catch (e) {
            console.warn('Could not restore column filter state:', e);
        }
    }
};
