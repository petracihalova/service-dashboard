document.addEventListener('DOMContentLoaded', function () {
    var tableView = document.getElementById("table_view");
    var listView = document.getElementById("list_view");

    document.getElementById("view_table").addEventListener("click", function () {
        tableView.style.display = "block";
        listView.style.display = "none";
    });

    document.getElementById("view_list").addEventListener("click", function () {
        tableView.style.display = "none";
        listView.style.display = "block";
    });

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
