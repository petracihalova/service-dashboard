/**
 * Fix for List View link clicks not working
 * Ensures that links inside list items work properly by preventing event interference
 */

document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for other scripts to load and attach their handlers
    setTimeout(function() {
        fixListViewLinks();
    }, 100);
});

function fixListViewLinks() {
    // Find all links within list view items
    const listViewLinks = document.querySelectorAll('#list_view li a[href]');

    listViewLinks.forEach(function(link) {
        // Add click handler that ensures the link works
        link.addEventListener('click', function(event) {
            // Stop propagation to prevent other handlers from interfering
            event.stopPropagation();

            // Get the link details
            const href = this.getAttribute('href');
            const target = this.getAttribute('target');

            // Manually handle the link navigation since other handlers might be interfering
            if (href) {
                event.preventDefault(); // Prevent the default to avoid double navigation

                if (target === '_blank') {
                    window.open(href, '_blank', 'noopener,noreferrer');
                } else {
                    window.location.href = href;
                }
            }
        }, true); // Use capture phase to run before other handlers

        // Also add a fallback handler for the normal event phase
        link.addEventListener('click', function(event) {
            // This will only run if the capture handler didn't already handle it
            if (!event.defaultPrevented) {
                event.stopPropagation(); // Prevent bubbling to parent elements
            }
        }, false);
    });
}
