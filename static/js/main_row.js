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
  };
