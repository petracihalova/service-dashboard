document.addEventListener('DOMContentLoaded', function () {
    var tableView = document.getElementById("table_view");
    var listView = document.getElementById("list_view");
    var tableButton = document.getElementById("view_table");
    var listButton = document.getElementById("view_list");

    // Load saved view mode from localStorage
    loadSavedViewMode();

    function getStorageKey() {
        // Get page-specific storage key based on URL
        const path = window.location.pathname;
        if (path.includes('/merged')) {
            return 'mergedPRs_viewMode';
        } else if (path.includes('/open')) {
            return 'openPRs_viewMode';
        } else if (path.includes('/jira-tickets/jira-reported-tickets')) {
            return 'jiraReportedTickets_viewMode'; // New key for JIRA reported tickets
        } else if (path.includes('/jira-tickets/jira-closed-tickets')) {
            return 'jiraClosedTickets_viewMode'; // New key for JIRA closed tickets
        } else if (path.includes('/jira-tickets/jira-tickets')) {
            return 'jiraTickets_viewMode'; // Key for JIRA assigned tickets
        } else if (path.includes('/app-interface-merged')) {
            return 'appInterfaceMergedMRs_viewMode';
        } else if (path.includes('/app-interface')) {
            return 'appInterfaceOpenMRs_viewMode';
        } else {
            return 'pullRequests_viewMode'; // fallback
        }
    }

    function loadSavedViewMode() {
        const storageKey = getStorageKey();
        const savedView = localStorage.getItem(storageKey);

        if (savedView === 'list' && listView && listButton) {
            // Switch to list view
            tableView.style.display = "none";
            listView.style.display = "block";
            // Update button states
            tableButton.classList.remove("active");
            listButton.classList.add("active");
        } else {
            // Default to table view (or if saved preference is 'table')
            tableView.style.display = "block";
            if (listView) listView.style.display = "none";
            // Update button states
            if (tableButton) tableButton.classList.add("active");
            if (listButton) listButton.classList.remove("active");
        }
    }

    if (tableButton) {
        tableButton.addEventListener("click", function () {
            tableView.style.display = "block";
            if (listView) listView.style.display = "none";
            // Save preference to localStorage with page-specific key
            const storageKey = getStorageKey();
            localStorage.setItem(storageKey, 'table');
        });
    }

    if (listButton) {
        listButton.addEventListener("click", function () {
            if (tableView) tableView.style.display = "none";
            listView.style.display = "block";
            // Save preference to localStorage with page-specific key
            const storageKey = getStorageKey();
            localStorage.setItem(storageKey, 'list');
        });
    }

    const buttons = document.querySelectorAll(".view-toggle");

    buttons.forEach(button => {
        button.addEventListener("click", function () {
            buttons.forEach(btn => btn.classList.remove("active"));
            this.classList.add("active");
        });
    });

    const checkbox = document.getElementById('labelsCheckbox');
    const labels = document.querySelectorAll('.labels');

    function toggleLabels() {
        if (checkbox.checked) {
            labels.forEach(label => {
                label.style.display = 'inline';
            });
        } else {
            labels.forEach(label => {
                label.style.display = 'none';
            });
        }
    }

    toggleLabels();

    checkbox.addEventListener('change', toggleLabels);
});
