/**
 * Favicon Manager
 * Handles loading, displaying, and selecting favicons
 */

document.addEventListener('DOMContentLoaded', function() {
    const faviconModal = document.getElementById('faviconModal');
    const faviconList = document.getElementById('faviconList');
    const faviconLoadingState = document.getElementById('faviconLoadingState');
    const faviconEmptyState = document.getElementById('faviconEmptyState');
    const currentFaviconPreview = document.getElementById('currentFaviconPreview');
    const currentFaviconName = document.getElementById('currentFaviconName');

    // Load favicons when modal is shown
    if (faviconModal) {
        faviconModal.addEventListener('show.bs.modal', function() {
            loadFavicons();
        });
    }

    /**
     * Load available favicons from the server
     */
    async function loadFavicons() {
        faviconList.innerHTML = '';
        faviconLoadingState.style.display = 'block';
        faviconEmptyState.style.display = 'none';

        try {
            const response = await fetch('/settings/favicons');
            const data = await response.json();

            faviconLoadingState.style.display = 'none';

            if (!data.favicons || data.favicons.length === 0) {
                faviconEmptyState.style.display = 'block';
                return;
            }

            // Get current favicon
            const currentFavicon = localStorage.getItem('selected-favicon') || '/static/favicon.ico';
            updateCurrentFaviconDisplay(currentFavicon);

            // Display favicons
            data.favicons.forEach(favicon => {
                const isSelected = currentFavicon === favicon.path;
                const faviconCard = createFaviconCard(favicon, isSelected);
                faviconList.appendChild(faviconCard);
            });

        } catch (error) {
            console.error('Error loading favicons:', error);
            faviconLoadingState.style.display = 'none';
            faviconEmptyState.style.display = 'block';
            faviconEmptyState.innerHTML = `
                <i class="bi bi-exclamation-triangle me-2"></i>
                Error loading favicons: ${error.message}
            `;
        }
    }

    /**
     * Create a favicon card element
     */
    function createFaviconCard(favicon, isSelected) {
        const col = document.createElement('div');
        col.className = 'col-6 col-md-4 col-lg-3';

        const card = document.createElement('div');
        card.className = 'card h-100 favicon-card';
        card.style.cursor = 'pointer';
        card.style.transition = 'all 0.2s';

        if (isSelected) {
            card.classList.add('border-primary');
            card.style.boxShadow = '0 0 10px rgba(13, 110, 253, 0.5)';
        }

        card.innerHTML = `
            <div class="card-body text-center p-3">
                <img src="${favicon.path}" alt="${favicon.name}"
                     style="width: 48px; height: 48px; object-fit: contain;"
                     onerror="this.src='/static/favicon.ico'">
                <p class="mt-2 mb-0 small text-truncate" title="${favicon.name}">${favicon.name}</p>
                ${isSelected ? '<span class="badge bg-primary mt-1">Selected</span>' : ''}
            </div>
        `;

        // Add hover effect
        card.addEventListener('mouseenter', function() {
            if (!isSelected) {
                this.style.boxShadow = '0 0 8px rgba(0, 0, 0, 0.2)';
            }
        });

        card.addEventListener('mouseleave', function() {
            if (!isSelected) {
                this.style.boxShadow = '';
            }
        });

        // Handle click to select favicon
        card.addEventListener('click', function() {
            selectFavicon(favicon);
        });

        col.appendChild(card);
        return col;
    }

    /**
     * Select and apply a favicon
     */
    function selectFavicon(favicon) {
        // Update favicon in browser
        const faviconLink = document.getElementById('favicon-link');
        if (faviconLink) {
            faviconLink.href = favicon.path;
        }

        // Update sidebar logo (both full and compact)
        const sidebarLogos = document.querySelectorAll('.sidebar-heading img, .sidebar-heading-compact img');
        sidebarLogos.forEach(logo => {
            logo.src = favicon.path;
        });

        // Save to localStorage
        localStorage.setItem('selected-favicon', favicon.path);
        localStorage.setItem('selected-favicon-name', favicon.name);

        // Reload the favicon list to show the new selection
        loadFavicons();

        // Show success message
        showToast(`Favicon changed to "${favicon.name}"`, 'success');
    }

    /**
     * Update the current favicon display
     */
    function updateCurrentFaviconDisplay(faviconPath) {
        const faviconName = localStorage.getItem('selected-favicon-name') || 'default';
        currentFaviconPreview.src = faviconPath;
        currentFaviconName.textContent = faviconName;
    }

    /**
     * Initialize favicon on page load (for sidebar logos)
     */
    function initializeFavicon() {
        const savedFavicon = localStorage.getItem('selected-favicon');
        if (savedFavicon) {
            const sidebarLogos = document.querySelectorAll('.sidebar-heading img, .sidebar-heading-compact img');
            sidebarLogos.forEach(logo => {
                logo.src = savedFavicon;
            });
        }
    }

    // Initialize on page load
    initializeFavicon();
});
