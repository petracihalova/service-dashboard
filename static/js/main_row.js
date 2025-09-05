// Show hidden / expandable section
function toggleInfo(cell) {
    var hidden_row = cell.parentElement.nextElementSibling;
    var row = cell.closest("tr");
    if (hidden_row.style.display === "none") {
      hidden_row.style.display = "table-row";
      cell.textContent = "v"
      row.classList.add("table-primary")
    } else {
      hidden_row.style.display = "none";
      cell.textContent = ">"
      row.classList.remove("table-primary")
    }
  }

// Event delegation for deployment table interactions
document.addEventListener('DOMContentLoaded', function() {
    // Handle toggle info clicks
    document.addEventListener('click', function(event) {
        // Check if the clicked element is a toggle info cell
        if (event.target.matches('td[data-toggle="info"]')) {
            toggleInfo(event.target);
        }

        // Check if the clicked element is a copy clipboard button
        if (event.target.matches('.copy-clipboard-btn') || event.target.closest('.copy-clipboard-btn')) {
            const button = event.target.matches('.copy-clipboard-btn') ? event.target : event.target.closest('.copy-clipboard-btn');
            const targetId = button.getAttribute('data-target');
            if (targetId && window.copyToClipboard) {
                window.copyToClipboard(targetId);
            }
        }
    });
});
