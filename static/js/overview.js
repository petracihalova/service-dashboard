document.addEventListener('DOMContentLoaded', function() {
    const compactModeToggle = document.getElementById('compactModeToggle');
    const container = document.querySelector('.container-fluid');

    if (!compactModeToggle || !container) {
        return;
    }

    // Helper function to apply compact styles
    function applyCompactStyles() {
        // Find elements to modify
        const allRows = document.querySelectorAll('.row.g-4');
        const allCols = document.querySelectorAll('.col-xl-3.col-lg-4.col-md-6.col-12');
        const allCards = document.querySelectorAll('.card');
        const allLinks = document.querySelectorAll('.overview-link');
        const allTitles = document.querySelectorAll('.card-title');
        const allCardHeaders = document.querySelectorAll('.card-header');
        const allCardBodies = document.querySelectorAll('.card-body');

        if (allCards.length === 0) return;

        // Change grid layout - more cards per row with minimal spacing
        allRows.forEach(row => {
            row.className = row.className.replace('g-4', 'g-1'); // Minimal gutters
        });

        allCols.forEach(col => {
            // Change to 6 cards per row on most screens: 6 on XL/LG, 4 on MD, 3 on SM, 2 on XS
            col.className = 'col-xl-2 col-lg-2 col-md-3 col-sm-4 col-6';
        });

        // Apply ultra compact styling to cards - keep nice text sizes
        allCards.forEach(card => {
            card.style.fontSize = '0.85rem';
            card.style.marginBottom = '0.25rem'; // Ultra minimal spacing between cards
        });

        // Extremely compact card headers and bodies
        allCardHeaders.forEach(header => {
            header.style.padding = '0.25rem 0.375rem'; // Extremely tight padding
            header.style.paddingBottom = '0.125rem';
        });

        allCardBodies.forEach(body => {
            body.style.padding = '0.125rem 0.375rem'; // Ultra tight body padding
            body.style.paddingTop = '0.0625rem'; // Almost no top padding
        });

        // Keep nice title sizes but ultra tight spacing
        allTitles.forEach(title => {
            title.style.fontSize = '0.95rem';
            title.style.marginBottom = '0';
            title.style.lineHeight = '1.1'; // Much tighter line height
            title.style.paddingBottom = '0.125rem'; // Minimal space after title
        });

        // Ultra compact link styling with minimal spacing
        allLinks.forEach(link => {
            link.style.fontSize = '0.8rem';
            link.style.padding = '0.0625rem 0'; // Ultra minimal vertical padding
            link.style.marginBottom = '0';
            link.style.lineHeight = '1.2'; // Tighter line height
        });

        // Fix left alignment and reduce overall spacing
        const container = document.querySelector('.container-fluid');
        if (container) {
            container.style.paddingLeft = '0.5rem';
            container.style.paddingRight = '0.5rem';
        }

        // Apply ultra-tight category spacing with aggressive overrides
        setTimeout(() => {
            // Target category wrappers (mb-5) and force override Bootstrap
            const categoryWrappers = document.querySelectorAll('.mb-5');
            console.log('✅ Found category wrappers:', categoryWrappers.length);
            categoryWrappers.forEach((wrapper, index) => {
                wrapper.style.setProperty('margin-bottom', '0.5rem', 'important');
                wrapper.style.setProperty('padding-left', '0.375rem', 'important');
                wrapper.style.setProperty('margin-left', '0', 'important');
                // Remove Bootstrap class and add custom class
                wrapper.classList.remove('mb-5');
                wrapper.classList.add('compact-category-wrapper');
                console.log('Applied ultra-tight spacing to wrapper', index);
            });

            // Target category headers (mb-3) and force override Bootstrap
            const categoryHeaders = document.querySelectorAll('.mb-3');
            console.log('✅ Found category headers:', categoryHeaders.length);
            categoryHeaders.forEach((header, index) => {
                header.style.setProperty('margin-bottom', '0.25rem', 'important');
                // Remove Bootstrap class and add custom class
                header.classList.remove('mb-3');
                header.classList.add('compact-category-header');
                console.log('Applied ultra-tight header spacing to', index);
            });
        }, 100);

        // Ultra minimal page title area spacing
        const mainHeader = document.querySelector('.d-flex.justify-content-between.align-items-center.mb-4');
        if (mainHeader) {
            mainHeader.style.marginBottom = '0.5rem'; // Very tight header spacing
        }
    }

    // Helper function to remove compact styles
    function removeCompactStyles() {
        // Find elements to reset
        const allRows = document.querySelectorAll('.row');
        const allCols = document.querySelectorAll('.col-xl-2, .col-lg-2, .col-md-3, .col-sm-4, .col-6');
        const allCards = document.querySelectorAll('.card');
        const allLinks = document.querySelectorAll('.overview-link');
        const allTitles = document.querySelectorAll('.card-title');
        const allCardHeaders = document.querySelectorAll('.card-header');
        const allCardBodies = document.querySelectorAll('.card-body');

        // Reset grid layout to original
        allRows.forEach(row => {
            row.className = row.className.replace('g-1', 'g-4'); // Restore original gutters
        });

        allCols.forEach(col => {
            // Reset to original grid: 4 on XL, 3 on LG, 2 on MD, 1 on small
            col.className = 'col-xl-3 col-lg-4 col-md-6 col-12';
        });

        // Reset all card styles
        allCards.forEach(card => {
            card.style.fontSize = '';
            card.style.marginBottom = '';
        });

        // Reset card headers - remove all custom padding
        allCardHeaders.forEach(header => {
            header.style.padding = '';
            header.style.paddingBottom = '';
        });

        // Reset card bodies - remove all custom padding
        allCardBodies.forEach(body => {
            body.style.padding = '';
            body.style.paddingTop = '';
        });

        // Reset titles - remove all custom styling
        allTitles.forEach(title => {
            title.style.fontSize = '';
            title.style.marginBottom = '';
            title.style.lineHeight = '';
            title.style.paddingBottom = '';
        });

        // Reset links - remove all custom styling
        allLinks.forEach(link => {
            link.style.fontSize = '';
            link.style.padding = '';
            link.style.marginBottom = '';
            link.style.lineHeight = '';
        });

        // Reset container padding
        const container = document.querySelector('.container-fluid');
        if (container) {
            container.style.paddingLeft = '';
            container.style.paddingRight = '';
        }

        // Reset category wrappers - restore Bootstrap classes
        const compactWrappers = document.querySelectorAll('.compact-category-wrapper');
        compactWrappers.forEach(wrapper => {
            wrapper.style.paddingLeft = '';
            wrapper.style.marginLeft = '';
            wrapper.style.marginBottom = '';
            wrapper.classList.remove('compact-category-wrapper');
            wrapper.classList.add('mb-5'); // Restore Bootstrap spacing
        });

        // Reset category headers - restore Bootstrap classes
        const compactHeaders = document.querySelectorAll('.compact-category-header');
        compactHeaders.forEach(header => {
            header.style.marginBottom = '';
            header.classList.remove('compact-category-header');
            header.classList.add('mb-3'); // Restore Bootstrap spacing
        });

        // Reset main header
        const mainHeader = document.querySelector('.d-flex.justify-content-between.align-items-center');
        if (mainHeader) {
            mainHeader.style.marginBottom = '';
        }
    }

    // Load saved preference
    const isCompactMode = localStorage.getItem('overviewCompactMode') === 'true';

    if (isCompactMode) {
        compactModeToggle.checked = true;
        container.classList.add('compact-mode');

        // Apply compact styles with retry mechanism for DOM readiness
        function attemptApplyStyles(attempt = 1) {
            const cards = document.querySelectorAll('.card');
            if (cards.length > 0) {
                applyCompactStyles();
            } else if (attempt < 5) {
                setTimeout(() => attemptApplyStyles(attempt + 1), attempt * 200);
            }
        }

        attemptApplyStyles();
    }

    // Handle toggle changes
    compactModeToggle.addEventListener('change', function() {
        if (this.checked) {
            container.classList.add('compact-mode');
            localStorage.setItem('overviewCompactMode', 'true');
            setTimeout(applyCompactStyles, 100);
        } else {
            container.classList.remove('compact-mode');
            localStorage.setItem('overviewCompactMode', 'false');
            removeCompactStyles();
        }
    });
});
