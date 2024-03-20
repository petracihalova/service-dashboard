document.addEventListener('DOMContentLoaded', function () {
    // Function to create a spinner element
    function createSpinner() {
        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");
        spinner.style.marginRight = "10px";
        return spinner;
    }

    var updateButton = document.getElementById("update_button");
    // Add event listener to the button click event
    updateButton.addEventListener("click", function (e) {
        this.textContent = "";
        this.appendChild(createSpinner());
        this.appendChild(document.createTextNode("Loading"));
        this.disabled = true;
        window.location.href = this.dataset.url;
    });
});

new DataTable('#merged_pr_table', {
    columnDefs: [
        {
            targets: 3,
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
                        columns: [1, 2],
                        stripHtml: false
                    },
                },
                "colvis"
            ]
        }
    }
});
