document.addEventListener('DOMContentLoaded', function () {
    var updateButton = document.getElementById("update_button");

    // Function to set Update button text to "Loading" and get the spinner visible
    function setLoadingState() {
        updateButton.textContent = "";
        updateButton.appendChild(createSpinner());
        updateButton.appendChild(document.createTextNode("Loading"));
        updateButton.disabled = true;

        // Construct the URL with the parameter and navigate to it
        var url = "open_pr?reload_data=1";
        window.location.href = url;
    }

    // Function to create a spinner element
    function createSpinner() {
        var spinner = document.createElement("span");
        spinner.className = "spinner-border spinner-border-sm";
        spinner.setAttribute("role", "status");
        spinner.setAttribute("aria-hidden", "true");
        spinner.style.marginRight = "10px";
        return spinner;
    }

    // Attach the setLoadingState function to the button click event
    updateButton.addEventListener("click", () => {
        setLoadingState();
    });
});

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
