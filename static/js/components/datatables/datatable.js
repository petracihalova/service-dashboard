window.onload = function () {
    window.dataTable = new DataTable('#datatable', {
        order: [[0, 'asc']],
        autoWidth: false,
        columnDefs: [

            {
                targets: "dateTimeRenderColumn",
                render: DataTable.render.datetime('MMMM Do YYYY')
            }
        ],
        displayLength: 50,
        drawCallback: function (settings) {
            var api = this.api();
            var rows = api.rows({ page: 'current' }).nodes();
            var last = null;

            api.column(0, { page: 'current' })
                .data()
                .each(function (group, i) {
                    if (last !== group) {
                        rows[i].insertAdjacentHTML('beforebegin', '<tr class="group"><td colspan="6">' +
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
