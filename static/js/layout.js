window.addEventListener('DOMContentLoaded', event => {

  // Toggle the side navigation
  const sidebarToggle = document.body.querySelector('#sidebarToggle');
  if (sidebarToggle) {
    // Apply stored sidebar state on page load
    if (localStorage.getItem('sb|sidebar-toggle') === 'true') {
      document.body.classList.toggle('sb-sidenav-toggled');
      // Update icon to show correct direction
      const icon = document.getElementById('sidebarToggleIcon');
      if (icon) {
        icon.className = 'bi bi-chevron-right';
      }
    } else {
      // Ensure icon shows correct direction on load
      const icon = document.getElementById('sidebarToggleIcon');
      if (icon) {
        icon.className = 'bi bi-chevron-left';
      }
    }

    sidebarToggle.addEventListener('click', event => {
      event.preventDefault();
      document.body.classList.toggle('sb-sidenav-toggled');
      localStorage.setItem('sb|sidebar-toggle', document.body.classList.contains('sb-sidenav-toggled'));
    });
  };

  // Side nav - arrow icon change
  var toggleButton = document.getElementById("sidebarToggle");
  var toggleIcon = document.getElementById("sidebarToggleIcon");

  if (toggleButton && toggleIcon) {
    toggleButton.addEventListener("click", function () {
      // Update the arrow direction based on sidebar state
      setTimeout(() => {
        if (document.body.classList.contains('sb-sidenav-toggled')) {
          toggleIcon.className = "bi bi-chevron-right";
        } else {
          toggleIcon.className = "bi bi-chevron-left";
        }
      }, 10);
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

// Only add event listener if dropdown exists
if (dropdown) {
    dropdown.addEventListener("change", highlightItems);
}

// Initialize collapsible menus with localStorage persistence
initializeCollapsibleMenus();

function initializeCollapsibleMenus() {
    // JIRA submenu
    const jiraToggle = document.querySelector('.jira-dropdown-toggle');
    const jiraSubmenu = document.querySelector('#jiraSubmenu');

    if (jiraToggle && jiraSubmenu) {
        // Auto-expand if on JIRA pages or if previously expanded
        const currentPath = window.location.pathname;
        const isOnJiraPage = currentPath.includes('/jira-tickets');
        const jiraExpanded = localStorage.getItem('jiraMenuExpanded') === 'true';

        if (isOnJiraPage || jiraExpanded) {
            jiraSubmenu.classList.add('show');
            jiraToggle.setAttribute('aria-expanded', 'true');
            // Save state if we auto-expanded due to being on JIRA page
            if (isOnJiraPage) {
                localStorage.setItem('jiraMenuExpanded', 'true');
            }
        }

        // Handle JIRA submenu events
        jiraSubmenu.addEventListener('shown.bs.collapse', function () {
            jiraToggle.setAttribute('aria-expanded', 'true');
            localStorage.setItem('jiraMenuExpanded', 'true');
        });

        jiraSubmenu.addEventListener('hidden.bs.collapse', function () {
            jiraToggle.setAttribute('aria-expanded', 'false');
            localStorage.setItem('jiraMenuExpanded', 'false');
        });
    }

    // App-interface submenu
    const appInterfaceToggle = document.querySelector('.app-interface-dropdown-toggle');
    const appInterfaceSubmenu = document.querySelector('#appInterfaceSubmenu');

    if (appInterfaceToggle && appInterfaceSubmenu) {
        // Auto-expand if on App-interface pages or if previously expanded
        const currentPath = window.location.pathname;
        const isOnAppInterfacePage = currentPath.includes('/app-interface');
        const appInterfaceExpanded = localStorage.getItem('appInterfaceMenuExpanded') === 'true';

        if (isOnAppInterfacePage || appInterfaceExpanded) {
            appInterfaceSubmenu.classList.add('show');
            appInterfaceToggle.setAttribute('aria-expanded', 'true');
            // Save state if we auto-expanded due to being on App-interface page
            if (isOnAppInterfacePage) {
                localStorage.setItem('appInterfaceMenuExpanded', 'true');
            }
        }

        // Handle App-interface submenu events
        appInterfaceSubmenu.addEventListener('shown.bs.collapse', function () {
            appInterfaceToggle.setAttribute('aria-expanded', 'true');
            localStorage.setItem('appInterfaceMenuExpanded', 'true');
        });

        appInterfaceSubmenu.addEventListener('hidden.bs.collapse', function () {
            appInterfaceToggle.setAttribute('aria-expanded', 'false');
            localStorage.setItem('appInterfaceMenuExpanded', 'false');
        });
    }
}

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
