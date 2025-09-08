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
});
