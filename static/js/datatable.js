new DataTable('#datatable', {
    autoWidth: false,
    columnDefs: [
        {
            targets: "dateTimeRenderColumn",
            render: DataTable.render.datetime('MMMM Do YYYY')
        },
        {
            width: "40%",
            targets: 1
        }
    ],
    order: [[0, 'asc'], [1, 'asc']],
    displayLength: 50,
    drawCallback: function (settings) {
        var api = this.api();
        var rows = api.rows({ page: 'current' }).nodes();
        var last = null;

        api.column(0, { page: 'current' })
            .data()
            .each(function (group, i) {
                if (last !== group) {
                    $(rows).eq(i).before('<tr class="group"><td colspan="5">' +
                        group + '</td></tr>'
                    );
                    last = group;
                }
            });
    }
});
