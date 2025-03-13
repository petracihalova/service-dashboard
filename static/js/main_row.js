// Show hidden / expandable section
function toggleInfo(cell) {
    var hidden_row = cell.parentElement.nextElementSibling;
    if (hidden_row.style.display === "none") {
      hidden_row.style.display = "table-row";
      cell.textContent = "v"
    } else {
      hidden_row.style.display = "none";
      cell.textContent = ">"
    }
  };
