window.onload = function () {
    window.dataTable = new DataTable('#datatable', {
        order: [[0, 'asc']],
        autoWidth: false,
        columnDefs: [
            {
                targets: "dateTimeRenderColumn",
                render: DataTable.render.datetime('MMMM Do YYYY')
            },
            {
                targets: [6], // Days Open column (0-based index: Repository=0, PR/MR=1, Author=2, Changes=3, Size=4, Days Open=5, Date=6)
                type: 'num',
                className: 'text-center'
            }
        ],
        displayLength: 50,
        drawCallback: function (settings) {
            var api = this.api();
            var rows = api.rows({ page: 'current' }).nodes();
            var last = null;

            // Get the actual number of visible columns dynamically
            var columnCount = api.columns(':visible').count();

            api.column(0, { page: 'current' })
                .data()
                .each(function (group, i) {
                    if (last !== group) {
                        rows[i].insertAdjacentHTML('beforebegin', '<tr class="group"><td colspan="' + columnCount + '">' +
                            group + '</td></tr>');
                        last = group;
                    }
                });
        }
    });

    // Apply initial size filter from URL parameter after DataTable is loaded
    if (window.prFilterUtils && window.prFilterUtils.applyInitialSizeFilter) {
        window.prFilterUtils.applyInitialSizeFilter();
    }
};
