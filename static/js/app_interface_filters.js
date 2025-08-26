/**
 * App-interface specific modal handling
 * Filter buttons (my-mrs-toggle, clear-filters) are handled by pr_filter_shared.js
 */
document.addEventListener('DOMContentLoaded', function() {
    const userConfigInfo = document.getElementById('user-config-info');
    const gitlabConfigInfo = document.getElementById('gitlab-config-info');

    // Note: Filter button handlers (my-mrs-toggle, clear-filters) are now handled
    // by pr_filter_shared.js to avoid conflicts and ensure consistent behavior

    // Helper function to clean up modal backdrop
    function cleanupModal() {
        // Remove any remaining backdrop
        const backdrop = document.querySelector('.modal-backdrop');
        if (backdrop) {
            backdrop.remove();
        }
        // Ensure body classes are cleaned up
        document.body.classList.remove('modal-open');
        document.body.style.removeProperty('overflow');
        document.body.style.removeProperty('padding-right');
    }

    // User list config info icon click handler
    if (userConfigInfo) {
        userConfigInfo.addEventListener('click', function() {
            const configModalElement = document.getElementById('configModal');
            const configModal = new bootstrap.Modal(configModalElement);
            configModal.show();

            configModalElement.addEventListener('hidden.bs.modal', cleanupModal);
        });
    }

    // GitLab username config info icon click handler
    if (gitlabConfigInfo) {
        gitlabConfigInfo.addEventListener('click', function() {
            const gitlabConfigModalElement = document.getElementById('gitlabConfigModal');
            const gitlabConfigModal = new bootstrap.Modal(gitlabConfigModalElement);
            gitlabConfigModal.show();

            gitlabConfigModalElement.addEventListener('hidden.bs.modal', cleanupModal);
        });
    }
});
