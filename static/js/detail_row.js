document.addEventListener('DOMContentLoaded', function () {
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
