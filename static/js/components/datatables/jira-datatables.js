/**
 * Consolidated JIRA DataTable Configurations
 * Replaces: jira_datatable.js, jira_closed_datatable.js, jira_reported_datatable.js
 * Provides configurable DataTable setup for all JIRA ticket views
 */

// Utility function to safely format dates
function formatJiraDate(data) {
    if (!data) return '';

    // Check if data looks like a date (contains numbers and common date separators)
    if (typeof data === 'string' && !/^\d{4}-\d{2}-\d{2}/.test(data) && !/\d{2}\/\d{2}\/\d{4}/.test(data)) {
        return data; // Return as-is if it doesn't look like a date
    }

    const momentDate = moment(data);
    return momentDate.isValid() ? momentDate.format('YYYY-MM-DD HH:mm') : data;
}

// Factory functions for each JIRA table type
window.JiraDataTables = {
    // Standard JIRA tickets table
    initStandard: (tableId = '#jira-datatable') => {
        window.onload = () => {
            new DataTable(tableId, {
                pageLength: 50,
                lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
                order: [[0, "asc"]], // Sort by Type
                columnDefs: [
                    { targets: [0], width: "90px", className: "text-center" },   // Type
                    { targets: [1], width: "130px", className: "text-center" },  // Key
                    { targets: [2], width: "500px" },                            // Summary
                    { targets: [3], width: "100px", className: "text-center" },  // Status
                    { targets: [4], width: "100px", className: "text-center" },  // Assignee
                    { targets: [5], width: "150px", className: "text-center", render: function(data) {
                        return formatJiraDate(data);
                    }}  // Created
                ]
            });
        };
    },

    // JIRA closed tickets table
    initClosed: (tableId = '#jira-closed-datatable') => {
        window.onload = () => {
            new DataTable(tableId, {
                pageLength: 50,
                lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
                order: [[6, "desc"]], // Sort by Resolved at (most recent first)
                columnDefs: [
                    { targets: [0], width: "90px", className: "text-center" },   // Type
                    { targets: [1], width: "130px", className: "text-center" },  // Key
                    { targets: [2], width: "500px" },                            // Summary
                    { targets: [3], width: "100px", className: "text-center" },  // Status
                    { targets: [4], width: "100px", className: "text-center" },  // Assignee
                    { targets: [5], width: "150px", className: "text-center", render: function(data) {
                        return formatJiraDate(data);
                    }}, // Created
                    { targets: [6], width: "150px", className: "text-center", render: function(data) {
                        return formatJiraDate(data);
                    }}  // Resolved
                ]
            });
        };
    },

    // JIRA reported tickets table
    initReported: (tableId = '#jira-reported-datatable') => {
        window.onload = () => {
            new DataTable(tableId, {
                pageLength: 50,
                lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
                order: [[0, "asc"]], // Sort by Type
                columnDefs: [
                    { targets: [0], width: "90px", className: "text-center" },   // Type
                    { targets: [1], width: "120px", className: "text-center" },  // Key
                    { targets: [2], width: "500px" },                            // Summary
                    { targets: [3], width: "100px", className: "text-center" },  // Status
                    { targets: [4], width: "100px", className: "text-center" },  // Reporter
                    { targets: [5], width: "100px", className: "text-center" },  // Assignee
                    { targets: [6], width: "150px", className: "text-center", render: function(data) {
                        return formatJiraDate(data);
                    }}  // Created
                ]
            });
        };
    }
};
