/**
 * DataTable configuration specifically for JIRA reported tickets
 */

$(document).ready(function() {
    $('#jira-reported-datatable').DataTable({
        "pageLength": 50,
        "lengthMenu": [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
        "order": [[0, "asc"]], // Sort by Type column first
        "columnDefs": [
            {
                "targets": [0], // Type column
                "width": "90px",
                "className": "text-center"
            },
            {
                "targets": [1], // Key column
                "width": "120px",
                "className": "text-center"
            },
            {
                "targets": [2], // Title column
                "width": "30%", // Less space since we have an additional Assignee column
                "className": "text-left"
            },
            {
                "targets": [3], // Status column
                "width": "100px",
                "className": "text-center"
            },
            {
                "targets": [4], // Priority column
                "width": "90px",
                "className": "text-center"
            },
            {
                "targets": [5], // Assignee column
                "width": "120px",
                "className": "text-center"
            },
            {
                "targets": [6], // Active Sprint column
                "width": "140px",
                "className": "text-center"
            },
            {
                "targets": [7, 8], // Date columns (Created at, Updated at)
                "width": "110px",
                "className": "text-center",
                "render": function(data, type, row) {
                    if (type === 'display' || type === 'type') {
                        if (data) {
                            // Convert ISO date to more readable format
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
            "search": "Search reported tickets:",
            "lengthMenu": "Show _MENU_ tickets per page",
            "info": "Showing _START_ to _END_ of _TOTAL_ reported tickets",
            "infoEmpty": "No reported tickets available",
            "infoFiltered": "(filtered from _MAX_ total tickets)"
        }
    });
});
