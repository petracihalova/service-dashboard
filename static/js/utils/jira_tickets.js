/**
 * JIRA Tickets page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // JIRA Config Modal Handler
    const jiraConfigInfo = document.getElementById('jira-config-info');
    const jiraConfigModal = document.getElementById('jiraConfigModal');

    if (jiraConfigInfo && jiraConfigModal) {
        jiraConfigInfo.addEventListener('click', function() {
            const modal = new bootstrap.Modal(jiraConfigModal);
            modal.show();
        });

        // Clean up modal when hidden
        jiraConfigModal.addEventListener('hidden.bs.modal', function() {
            // Remove any leftover modal backdrop
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());

            // Reset body classes
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        });
    }

    // Labels Toggle functionality
    const labelsCheckbox = document.getElementById('labelsCheckbox');
    const labels = document.querySelectorAll('.labels');

    if (labelsCheckbox) {
        function toggleLabels() {
            if (labelsCheckbox.checked) {
                labels.forEach(label => {
                    label.style.display = 'inline';
                });
            } else {
                labels.forEach(label => {
                    label.style.display = 'none';
                });
            }
        }

        // Initialize labels visibility
        toggleLabels();

        // Handle checkbox change
        labelsCheckbox.addEventListener('change', toggleLabels);
    }

    // View Toggle Switch functionality
    const viewToggleSwitch = document.getElementById('viewToggleSwitch');
    const tableView = document.getElementById('table_view');
    const listView = document.getElementById('list_view');
    const switchLabel = document.querySelector('label[for="viewToggleSwitch"]');

    if (viewToggleSwitch) {
        // Handle switch toggle
        viewToggleSwitch.addEventListener('change', function() {
            if (this.checked) {
                // Switch ON = Table View
                if (tableView) tableView.style.display = 'block';
                if (listView) listView.style.display = 'none';
                switchLabel.textContent = 'Table View';
            } else {
                // Switch OFF = List View
                if (tableView) tableView.style.display = 'none';
                if (listView) listView.style.display = 'block';
                switchLabel.textContent = 'List View';
            }
        });
    }
});
