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
    const withoutPersonalToggle = document.getElementById('allDataWithoutPersonalToggle');
    const konfluxOnlyToggle = document.getElementById('allDataKonfluxOnlyToggle');
    const nonKonfluxOnlyToggle = document.getElementById('allDataNonKonfluxOnlyToggle');
    const clearCodeStatsFilters = document.getElementById('allDataClearCodeStatsFilters');

    // Initialize toggle states from URL parameters
    function initializeCodeStatsFilters() {
        const urlParams = new URLSearchParams(window.location.search);
        const codeStatsSource = urlParams.get('code_stats_source');
        const excludePersonal = urlParams.get('code_stats_exclude_personal') === 'true';
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

        // Set the exclude personal repos toggle
        if (withoutPersonalToggle) {
            withoutPersonalToggle.checked = excludePersonal;
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

    // Handle exclude personal repos toggle
    if (withoutPersonalToggle) {
        withoutPersonalToggle.addEventListener('change', function() {
            const urlParams = new URLSearchParams(window.location.search);

            if (this.checked) {
                urlParams.set('code_stats_exclude_personal', 'true');
            } else {
                urlParams.delete('code_stats_exclude_personal');
            }

            // Navigate to new URL
            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.location.href = newUrl;
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
            urlParams.delete('code_stats_exclude_personal');
            urlParams.delete('code_stats_konflux_filter');

            const newUrl = window.location.pathname + '?' + urlParams.toString();
            window.location.href = newUrl;
        });
    }

    // Initialize filters on page load
    initializeCodeStatsFilters();
});
