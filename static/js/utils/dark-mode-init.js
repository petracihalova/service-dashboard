/**
 * Dark Mode Initialization
 * This script must run before the page renders to avoid flash of wrong theme
 * It checks localStorage and applies dark mode class to html element if needed
 */
(function() {
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    if (isDarkMode) {
        document.documentElement.classList.add('dark-mode');
    }
})();
