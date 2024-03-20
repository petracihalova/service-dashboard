new DataTable('#open_pr_table', {
    columnDefs: [
        {
            targets: 4,
            render: DataTable.render.datetime('MMMM Do YY, h:mm a')
        }
    ],
    order: [[0, 'asc']],
    displayLength: 25,
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
    },
    layout: {
        topStart: {
            buttons: [
                {
                    extend: 'copyHtml5',
                    text: "Copy to Clipboard",
                    fieldSeparator: ", ",
                    header: null,
                    title: null,
                    exportOptions: {
                        columns: [1, 3],
                        stripHtml: false
                    },
                },
                "colvis"
            ]
        }
    }
});
