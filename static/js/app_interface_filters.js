// App-interface specific filter handling
document.addEventListener('DOMContentLoaded', function() {
    const myMrsToggle = document.getElementById('my-mrs-toggle');
    const clearFilters = document.getElementById('clear-filters');
    const userConfigInfo = document.getElementById('user-config-info');
    const gitlabConfigInfo = document.getElementById('gitlab-config-info');

    if (myMrsToggle) {
        myMrsToggle.addEventListener('click', function() {
            const isActive = this.getAttribute('data-active') === 'true';
            const url = new URL(window.location.href);

            if (isActive) {
                // Remove filter
                url.searchParams.delete('my_mrs');
            } else {
                // Add filter
                url.searchParams.set('my_mrs', 'true');
            }

            window.location.href = url.toString();
        });
    }

    if (clearFilters) {
        clearFilters.addEventListener('click', function() {
            const url = new URL(window.location.href);
            url.searchParams.delete('my_mrs');
            window.location.href = url.toString();
        });
    }

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
