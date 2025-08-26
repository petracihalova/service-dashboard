window.addEventListener('DOMContentLoaded', event => {

  // Toggle the side navigation
  const sidebarToggle = document.body.querySelector('#sidebarToggle');
  if (sidebarToggle) {
    if (localStorage.getItem('sb|sidebar-toggle') === 'true') {
      document.body.classList.toggle('sb-sidenav-toggled');
    }
    sidebarToggle.addEventListener('click', event => {
      event.preventDefault();
      document.body.classList.toggle('sb-sidenav-toggled');
      localStorage.setItem('sb|sidebar-toggle', document.body.classList.contains('sb-sidenav-toggled'));
    });
  };

  // Side nav - text content change
  var toggleButton = document.getElementById("sidebarToggle");
  var menuVisible = false;

  if (toggleButton) {
    toggleButton.addEventListener("click", function () {
      if (menuVisible) {
        toggleButton.textContent = "Hide Sidebar";
      } else {
        toggleButton.textContent = "Show Sidebar";
      }

      menuVisible = !menuVisible;
    });
  }

  // Dark mode functionality
  initializeDarkMode();
});

// Dark mode initialization and toggle functionality
function initializeDarkMode() {
  const darkModeToggle = document.getElementById('darkModeToggle');
  const darkModeIcon = document.getElementById('darkModeIcon');

  if (!darkModeToggle || !darkModeIcon) {
    return; // Exit if elements don't exist
  }

  // Set initial icon based on current dark mode state (already applied in HTML head)
  const isDarkMode = document.documentElement.classList.contains('dark-mode');
  setDarkModeIcon(isDarkMode);

  // Add click event listener to toggle button
  darkModeToggle.addEventListener('click', function() {
    const currentMode = document.documentElement.classList.contains('dark-mode');
    const newMode = !currentMode;

    applyTheme(newMode);
    localStorage.setItem('darkMode', newMode);
  });
}

function applyTheme(isDarkMode) {
  const htmlElement = document.documentElement;

  if (isDarkMode) {
    htmlElement.classList.add('dark-mode');
  } else {
    htmlElement.classList.remove('dark-mode');
  }

  setDarkModeIcon(isDarkMode);
}

function setDarkModeIcon(isDarkMode) {
  const darkModeIcon = document.getElementById('darkModeIcon');

  if (darkModeIcon) {
    if (isDarkMode) {
      darkModeIcon.classList.remove('bi-moon-fill');
      darkModeIcon.classList.add('bi-sun-fill');
    } else {
      darkModeIcon.classList.remove('bi-sun-fill');
      darkModeIcon.classList.add('bi-moon-fill');
    }
  }
}

// Note: Initial dark mode application now happens in HTML head to prevent flash

// Highlight PRs by selected name
var dropdown = document.getElementById("dropdown_names");
var lists = document.querySelectorAll("#pr_list");

dropdown.addEventListener("change", highlightItems);

function highlightItems() {
  var selectedText = dropdown.value;

  lists.forEach(function (list) {
    var items = list.getElementsByTagName("li");

    for (var i = 0; i < items.length; i++) {
      var itemText = items[i].innerText.toLowerCase();

      if (itemText.includes(selectedText.toLowerCase())) {
        items[i].classList.add("name-highlight");
      } else {
        items[i].classList.remove("name-highlight");
      }
    }
  });
}

// Copy commit SHA into clipboard
function copyToClipboard(elementId) {
  var commitShaElement = document.getElementById(elementId);
  var commitShaText = commitShaElement.innerText;

  navigator.clipboard.writeText(commitShaText)
    .catch(function (error) {
      console.error("Error:", error);
    });
}
