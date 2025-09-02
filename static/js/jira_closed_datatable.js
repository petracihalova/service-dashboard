/**
 * DataTable configuration specifically for JIRA closed tickets
 */

window.onload = function () {
    new DataTable('#jira-closed-datatable', {
        "pageLength": 50,
        "lengthMenu": [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        "order": [[6, "desc"]], // Sort by Resolved at column (most recent first)
        "columnDefs": [
            {
                "targets": [0], // Type column
                "width": "90px",
                "className": "text-center"
            },
            {
                "targets": [1], // Key column
                "width": "130px",
                "className": "text-center"
            },
            {
                "targets": [2], // Title column
                "width": "30%",
                "className": "text-left"
            },
            {
                "targets": [3], // Status column
                "width": "120px",
                "className": "text-center"
            },
            {
                "targets": [4], // Resolution column
                "width": "120px",
                "className": "text-center"
            },
            {
                "targets": [5], // Priority column
                "width": "90px",
                "className": "text-center"
            },
            {
                "targets": [6, 7], // Date columns (Resolved at, Created at)
                "width": "120px",
                "className": "text-center",
                "render": function(data, type, row) {
                    if (type === 'display' || type === 'type') {
                        if (data) {
                            try {
                                const date = new Date(data);
                                return date.toLocaleDateString('en-US', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric'
                                });
                            } catch (e) {
                                return data;
                            }
                        }
                    }
                    return data;
                }
            }
        ],
        "responsive": {
            "details": {
                "type": 'column',
                "target": 'tr'
            }
        },
        "dom": '<"row"<"col-sm-12 col-md-4"l><"col-sm-12 col-md-8 text-end"f>>' +
               '<"row"<"col-sm-12"tr>>' +
               '<"row"<"col-sm-12 col-md-4"i><"col-sm-12 col-md-8 text-end"p>>',
        "language": {
            "search": "Search tickets:",
            "lengthMenu": "Show _MENU_ tickets per page",
            "info": "Showing _START_ to _END_ of _TOTAL_ tickets",
            "infoEmpty": "No tickets available",
            "infoFiltered": "(filtered from _MAX_ total tickets)"
        }
    });
};
