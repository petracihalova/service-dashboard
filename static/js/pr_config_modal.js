// My PRs config info modal handling
document.addEventListener('DOMContentLoaded', function() {
    const myPrsConfigInfo = document.getElementById('my-prs-config-info');

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

    // My PRs config info icon click handler
    if (myPrsConfigInfo) {
        myPrsConfigInfo.addEventListener('click', function() {
            const myPrsConfigModalElement = document.getElementById('myPrsConfigModal');
            const myPrsConfigModal = new bootstrap.Modal(myPrsConfigModalElement);
            myPrsConfigModal.show();

            myPrsConfigModalElement.addEventListener('hidden.bs.modal', cleanupModal);
        });
    }
});
