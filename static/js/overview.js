document.addEventListener('DOMContentLoaded', function() {
    const compactModeToggle = document.getElementById('compactModeToggle');
    const editModeToggle = document.getElementById('editModeToggle');
    // Target the overview content container (direct child), not the navbar's container-fluid
    const container = document.querySelector('#page-content-wrapper > .container-fluid');



    if (!compactModeToggle || !editModeToggle || !container) {
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
            // Responsive compact layout: 6 on XXL+, 4 on XL/LG, 3 on MD, 2 on SM, 1 on XS
            col.className = 'col-xxl-2 col-xl-3 col-lg-3 col-md-4 col-sm-6 col-12';
        });

        // Apply ultra compact styling to cards - keep nice text sizes
        allCards.forEach(card => {
            card.style.fontSize = '0.85rem';
            card.style.marginBottom = '0.75rem'; // Ensure adequate spacing to prevent overlapping
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

        // Fix left alignment and reduce overall spacing - TARGET ONLY OVERVIEW CONTENT
        const overviewContainer = document.querySelector('#page-content-wrapper > .container-fluid');
        if (overviewContainer) {
            overviewContainer.style.paddingLeft = '0.5rem';
            overviewContainer.style.paddingRight = '0.5rem';
        }

        // Apply ultra-tight category spacing with aggressive overrides
        setTimeout(() => {
            // Target category wrappers (mb-5) and force override Bootstrap
            const categoryWrappers = document.querySelectorAll('.mb-5');
            categoryWrappers.forEach((wrapper, index) => {
                wrapper.style.setProperty('margin-bottom', '1.5rem', 'important'); // More space to prevent card overlap
                wrapper.style.setProperty('margin-top', index === 0 ? '0' : '2rem', 'important'); // More space between categories
                wrapper.style.setProperty('padding-left', '0.375rem', 'important');
                wrapper.style.setProperty('margin-left', '0', 'important');
                // Remove Bootstrap class and add custom class
                wrapper.classList.remove('mb-5');
                wrapper.classList.add('compact-category-wrapper');
            });

            // Target category headers (mb-3) and force override Bootstrap
            const categoryHeaders = document.querySelectorAll('.mb-3');
            categoryHeaders.forEach((header, index) => {
                header.style.setProperty('margin-bottom', '0.75rem', 'important'); // More space between header and cards
                // Remove Bootstrap class and add custom class
                header.classList.remove('mb-3');
                header.classList.add('compact-category-header');
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
        const allCols = document.querySelectorAll('.col-xxl-2, .col-xl-3, .col-lg-3, .col-md-4, .col-sm-6, .col-12');
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

        // Reset container padding - TARGET ONLY OVERVIEW CONTENT
        const overviewContainer = document.querySelector('#page-content-wrapper > .container-fluid');
        if (overviewContainer) {
            overviewContainer.style.paddingLeft = '';
            overviewContainer.style.paddingRight = '';
        }

        // Reset category wrappers - restore Bootstrap classes
        const compactWrappers = document.querySelectorAll('.compact-category-wrapper');
        compactWrappers.forEach(wrapper => {
            wrapper.style.paddingLeft = '';
            wrapper.style.marginLeft = '';
            wrapper.style.marginBottom = '';
            wrapper.style.marginTop = '';
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

    // Edit Mode Toggle functionality
    // Load saved edit mode preference
    const isEditMode = localStorage.getItem('overviewEditMode') === 'true';

    // Apply the correct initial state
    if (isEditMode) {
        editModeToggle.checked = true;
        document.body.classList.add('edit-mode');
    } else {
        editModeToggle.checked = false;
        document.body.classList.remove('edit-mode');

        // Force hide all edit elements on initial load
        setTimeout(() => {
            const editElements = document.querySelectorAll('.edit-mode-element');
            editElements.forEach((el) => {
                el.style.setProperty('display', 'none', 'important');
                el.style.setProperty('visibility', 'hidden', 'important');
                el.style.setProperty('opacity', '0', 'important');
            });
        }, 100);
    }

    // Handle edit mode toggle changes
    editModeToggle.addEventListener('change', function() {
        if (this.checked) {
            document.body.classList.add('edit-mode');
            localStorage.setItem('overviewEditMode', 'true');

            // Reset any force-hidden inline styles when entering edit mode
            const editElements = document.querySelectorAll('.edit-mode-element');
            editElements.forEach((el) => {
                el.style.removeProperty('display');
                el.style.removeProperty('visibility');
                el.style.removeProperty('opacity');
            });

        } else {
            document.body.classList.remove('edit-mode');
            localStorage.setItem('overviewEditMode', 'false');

            // Force hide elements when switching to read mode
            const editElements = document.querySelectorAll('.edit-mode-element');
            editElements.forEach((el) => {
                el.style.setProperty('display', 'none', 'important');
                el.style.setProperty('visibility', 'hidden', 'important');
                el.style.setProperty('opacity', '0', 'important');
            });
        }
    });

    // Service editing functionality
    initServiceEditing();
});

function initServiceEditing() {
    let currentLinks = [];

    // Add cleanup for all modals that can be canceled
    const modalsToCleanup = ['editServiceModal', 'addServiceModal', 'addCategoryModal'];

    modalsToCleanup.forEach(modalId => {
        const modalElement = document.getElementById(modalId);
        if (modalElement) {
            modalElement.addEventListener('hidden.bs.modal', function () {
                // Force remove any remaining backdrop
                const backdrops = document.querySelectorAll('.modal-backdrop');
                backdrops.forEach(backdrop => backdrop.remove());

                // Reset body styles
                document.body.classList.remove('modal-open');
                document.body.style.overflow = '';
                document.body.style.paddingRight = '';

                // Reset forms specific to each modal
                if (modalId === 'editServiceModal') {
                    document.getElementById('modalServiceName').value = '';
                    document.getElementById('modalOriginalServiceName').value = '';
                    document.getElementById('modalServiceId').value = '';
                    document.getElementById('modalCategoryName').value = '';
                    document.getElementById('linksContainer').innerHTML = '';
                } else if (modalId === 'addServiceModal') {
                    document.getElementById('addServiceName').value = '';
                    document.getElementById('addLinksContainer').innerHTML = '';
                } else if (modalId === 'addCategoryModal') {
                    document.getElementById('newCategoryName').value = '';
                }
            }, { once: false }); // Not using once: true since we want this cleanup every time
        }
    });

    // Handle edit service button clicks
    document.addEventListener('click', function(e) {
        if (e.target.closest('.edit-service-btn')) {
            const btn = e.target.closest('.edit-service-btn');
            const serviceId = btn.dataset.serviceId;
            const serviceName = btn.dataset.serviceName;
            const categoryName = btn.dataset.categoryName;
            const links = JSON.parse(btn.dataset.serviceLinks);
            const serviceColor = btn.dataset.serviceColor || 'default';

            openEditModal(serviceId, serviceName, categoryName, links, serviceColor);
        }

        // Handle add service button clicks
        if (e.target.closest('.add-service-btn')) {
            const btn = e.target.closest('.add-service-btn');
            const categoryName = btn.dataset.categoryName;

            openAddModal(categoryName);
        }

        // Handle delete service button clicks
        if (e.target.closest('.delete-service-btn')) {
            const btn = e.target.closest('.delete-service-btn');
            const serviceId = btn.dataset.serviceId;
            const serviceName = btn.dataset.serviceName;
            const categoryName = btn.dataset.categoryName;

            openDeleteModal(serviceId, serviceName, categoryName);
        }

        // Handle edit category button clicks
        if (e.target.closest('.edit-category-btn')) {
            const btn = e.target.closest('.edit-category-btn');
            const categoryName = btn.dataset.categoryName;
            openEditCategoryModal(categoryName);
        }

        // Handle delete category button clicks
        if (e.target.closest('.delete-category-btn')) {
            const btn = e.target.closest('.delete-category-btn');
            const categoryName = btn.dataset.categoryName;
            const serviceCount = parseInt(btn.dataset.serviceCount) || 0;
            openDeleteCategoryModal(categoryName, serviceCount);
        }

        // Handle move category up button clicks
        if (e.target.closest('.move-category-up-btn')) {
            const btn = e.target.closest('.move-category-up-btn');
            const categoryName = btn.dataset.categoryName;
            const categoryIndex = parseInt(btn.dataset.categoryIndex);
            moveCategoryUp(categoryName, categoryIndex);
        }

        // Handle move category down button clicks
        if (e.target.closest('.move-category-down-btn')) {
            const btn = e.target.closest('.move-category-down-btn');
            const categoryName = btn.dataset.categoryName;
            const categoryIndex = parseInt(btn.dataset.categoryIndex);
            moveCategoryDown(categoryName, categoryIndex);
        }
    });

    // Add link button (Edit modal)
    document.getElementById('addLinkBtn').addEventListener('click', function() {
        addLinkRow('', '', 'linksContainer');
    });

    // Add link button (Add modal)
    document.getElementById('addNewLinkBtn').addEventListener('click', function() {
        addLinkRow('', '', 'addLinksContainer');
    });

    // Save service button
    document.getElementById('saveServiceBtn').addEventListener('click', function() {
        saveServiceChanges();
    });

    // Create service button
    document.getElementById('createServiceBtn').addEventListener('click', function() {
        createNewService();
    });

    // Confirm delete button
    document.getElementById('confirmDeleteBtn').addEventListener('click', function() {
        deleteService();
    });

    // Save category button
    document.getElementById('saveCategoryBtn').addEventListener('click', function() {
        saveCategoryChanges();
    });

    // Create category button
    document.getElementById('createCategoryBtn').addEventListener('click', function() {
        createNewCategory();
    });

    // Confirm delete category button
    document.getElementById('confirmDeleteCategoryBtn').addEventListener('click', function() {
        deleteCategory();
    });

    function openEditModal(serviceId, serviceName, categoryName, links, serviceColor = 'default') {
        currentLinks = links;

        document.getElementById('modalServiceId').value = serviceId;
        document.getElementById('modalServiceName').value = serviceName;
        document.getElementById('modalOriginalServiceName').value = serviceName;
        document.getElementById('modalCategoryName').value = categoryName;

        // Set the color picker selection
        document.querySelectorAll('#editServiceModal .color-option').forEach(opt => opt.classList.remove('selected'));
        const colorOption = document.querySelector(`#editServiceModal .color-option[data-color="${serviceColor}"]`);
        if (colorOption) {
            colorOption.classList.add('selected');
        }
        document.getElementById('selectedColor').value = serviceColor;

        const linksContainer = document.getElementById('linksContainer');
        linksContainer.innerHTML = '';

        // Add existing links
        links.forEach(link => {
            addLinkRow(link.link_name, link.link_value, 'linksContainer');
        });

        // Add at least one empty row if no links exist
        if (links.length === 0) {
            addLinkRow('', '', 'linksContainer');
        }
    }

    function openAddModal(categoryName) {
        document.getElementById('addModalCategoryName').textContent = categoryName;
        document.getElementById('addModalCategoryNameHidden').value = categoryName;

        // Clear form
        document.getElementById('newServiceId').value = '';
        document.getElementById('newServiceName').value = '';

        const addLinksContainer = document.getElementById('addLinksContainer');
        addLinksContainer.innerHTML = '';

        // Add one empty link row to start
        addLinkRow('', '', 'addLinksContainer');
    }

    function openDeleteModal(serviceId, serviceName, categoryName) {
        document.getElementById('deleteServiceId').value = serviceId;
        document.getElementById('deleteServiceName').textContent = serviceName;
        document.getElementById('deleteServiceCategory').textContent = categoryName;
        document.getElementById('deleteServiceCategoryName').value = categoryName;

        // Show the modal
        const modalElement = document.getElementById('deleteServiceModal');
        const modal = new bootstrap.Modal(modalElement);

        // Add event listener to clean up when modal is hidden (canceled or closed)
        modalElement.addEventListener('hidden.bs.modal', function () {
            // Reset form
            document.getElementById('deleteServiceId').value = '';
            document.getElementById('deleteServiceName').textContent = '';
            document.getElementById('deleteServiceCategory').textContent = '';
            document.getElementById('deleteServiceCategoryName').value = '';

            // Force remove any remaining backdrop
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());

            // Reset body styles
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true }); // Use once: true to prevent multiple listeners

        modal.show();
    }

    function addLinkRow(name, value, containerId) {
        const linksContainer = document.getElementById(containerId);
        const linkRow = document.createElement('div');
        linkRow.className = 'row mb-2 link-row';
        linkRow.innerHTML = `
            <div class="col-md-4">
                <input type="text" class="form-control form-control-sm link-name" placeholder="Link name" value="${name}">
            </div>
            <div class="col-md-7">
                <input type="url" class="form-control form-control-sm link-value" placeholder="Link URL" value="${value}">
            </div>
            <div class="col-md-1">
                <button type="button" class="btn btn-outline-danger btn-sm remove-link-btn" title="Remove link">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;

        linksContainer.appendChild(linkRow);

        // Add remove functionality
        linkRow.querySelector('.remove-link-btn').addEventListener('click', function() {
            linkRow.remove();
        });

        // Add URL auto-correction functionality
        const urlInput = linkRow.querySelector('.link-value');
        urlInput.addEventListener('blur', function() {
            const url = this.value.trim();
            if (url && !isValidUrl(url)) {
                // Try to fix the URL by adding https://
                const fixedUrl = ensureProtocol(url);
                if (isValidUrl(fixedUrl)) {
                    this.value = fixedUrl;
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');

                    // Show helpful feedback
                    showUrlFixedFeedback(this, fixedUrl);
                } else {
                    this.classList.add('is-invalid');
                    this.classList.remove('is-valid');
                }
            } else if (url) {
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            } else {
                this.classList.remove('is-invalid', 'is-valid');
            }
        });

        // Remove validation classes on focus
        urlInput.addEventListener('focus', function() {
            this.classList.remove('is-invalid', 'is-valid');
        });
    }

    function saveServiceChanges() {
        const serviceId = document.getElementById('modalServiceId').value;
        const serviceName = document.getElementById('modalServiceName').value.trim();
        const originalServiceName = document.getElementById('modalOriginalServiceName').value;
        const categoryName = document.getElementById('modalCategoryName').value;

        if (!serviceName) {
            showToast('Service name cannot be empty', 'error');
            return;
        }
        const linkRows = document.querySelectorAll('.link-row');

        const links = [];
        linkRows.forEach(row => {
            const name = row.querySelector('.link-name').value.trim();
            let value = row.querySelector('.link-value').value.trim();

            if (name && value) {
                // Ensure URL has proper protocol before saving
                value = ensureProtocol(value);

                links.push({
                    link_name: name,
                    link_value: value
                });
            }
        });

        const data = {
            service_id: serviceId,
            service_name: serviceName,
            original_service_name: originalServiceName,
            category_name: categoryName,
            links: links,
            color: document.getElementById('selectedColor').value
        };

        // Show loading state
        const saveBtn = document.getElementById('saveServiceBtn');
        const originalText = saveBtn.textContent;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Saving...';

        // Send to backend
        fetch('/update-service-links', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showToast('Service links updated successfully!', 'success');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('editServiceModal'));
                modal.hide();

                // Reload page to show changes
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showToast('Error updating service links: ' + data.error, 'error');
            }
        })
        .catch(error => {
            showToast('Error updating service links', 'error');
        })
        .finally(() => {
            // Reset button
            saveBtn.disabled = false;
            saveBtn.textContent = originalText;
        });
    }

    function createNewService() {
        const serviceId = document.getElementById('newServiceId').value.trim();
        const serviceName = document.getElementById('newServiceName').value.trim();
        const categoryName = document.getElementById('addModalCategoryNameHidden').value;
        const linkRows = document.querySelectorAll('#addLinksContainer .link-row');

        // Validation
        if (!serviceId) {
            showToast('Service ID is required', 'error');
            return;
        }

        if (!serviceName) {
            showToast('Service Name is required', 'error');
            return;
        }

        // Validate service ID format (lowercase, no spaces, alphanumeric and hyphens only)
        const serviceIdRegex = /^[a-z0-9-]+$/;
        if (!serviceIdRegex.test(serviceId)) {
            showToast('Service ID must be lowercase with no spaces (use hyphens instead)', 'error');
            return;
        }

        const links = [];
        linkRows.forEach(row => {
            const name = row.querySelector('.link-name').value.trim();
            let value = row.querySelector('.link-value').value.trim();

            if (name && value) {
                // Ensure URL has proper protocol before saving
                value = ensureProtocol(value);

                links.push({
                    link_name: name,
                    link_value: value
                });
            }
        });

        const data = {
            service_id: serviceId,
            service_name: serviceName,
            category_name: categoryName,
            links: links,
            color: document.getElementById('newSelectedColor').value
        };

        // Show loading state
        const createBtn = document.getElementById('createServiceBtn');
        const originalText = createBtn.textContent;
        createBtn.disabled = true;
        createBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Creating...';

        // Send to backend
        fetch('/add-service', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showToast('Service created successfully!', 'success');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('addServiceModal'));
                modal.hide();

                // Reload page to show new service
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showToast('Error creating service: ' + data.error, 'error');
            }
        })
        .catch(error => {
            showToast('Error creating service', 'error');
        })
        .finally(() => {
            // Reset button
            createBtn.disabled = false;
            createBtn.textContent = originalText;
        });
    }

    function deleteService() {
        const serviceId = document.getElementById('deleteServiceId').value;
        const categoryName = document.getElementById('deleteServiceCategoryName').value;

        const data = {
            service_id: serviceId,
            category_name: categoryName
        };

        // Show loading state
        const deleteBtn = document.getElementById('confirmDeleteBtn');
        const originalHtml = deleteBtn.innerHTML;
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Deleting...';

        // Send to backend
        fetch('/delete-service', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showToast('Service deleted successfully!', 'success');

                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteServiceModal'));
                modal.hide();

                // Reload page to show changes
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showToast('Error deleting service: ' + data.error, 'error');
            }
        })
        .catch(error => {
            showToast('Error deleting service', 'error');
        })
        .finally(() => {
            // Reset button
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalHtml;
        });
    }

    // Note: showToast() function is now global in layout.js - no need to define it here

    function openEditCategoryModal(categoryName) {
        document.getElementById('editCategoryName').value = categoryName;
        document.getElementById('editCategoryOriginalName').value = categoryName;

        const modalElement = document.getElementById('editCategoryModal');
        const modal = new bootstrap.Modal(modalElement);

        // Add event listener to clean up when modal is hidden (canceled or closed)
        modalElement.addEventListener('hidden.bs.modal', function () {
            // Reset form
            document.getElementById('editCategoryName').value = '';
            document.getElementById('editCategoryOriginalName').value = '';

            // Force remove any remaining backdrop
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());

            // Reset body styles
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true }); // Use once: true to prevent multiple listeners

        modal.show();
    }

    function saveCategoryChanges() {
        const originalName = document.getElementById('editCategoryOriginalName').value;
        const newName = document.getElementById('editCategoryName').value.trim();

        if (!newName) {
            showToast('Category name cannot be empty', 'error');
            return;
        }

        if (originalName === newName) {
            const modal = bootstrap.Modal.getInstance(document.getElementById('editCategoryModal'));
            modal.hide();
            return;
        }

        const data = {
            original_name: originalName,
            new_name: newName
        };

        const saveBtn = document.getElementById('saveCategoryBtn');
        const originalHtml = saveBtn.innerHTML;
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Saving...';

        fetch('/update-category-name', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                // Hide modal and reload page to show changes
                const modal = bootstrap.Modal.getInstance(document.getElementById('editCategoryModal'));
                modal.hide();
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showToast(data.error || 'Failed to update category name', 'error');
            }
        })
        .catch(error => {
            showToast('An error occurred while updating the category name', 'error');
        })
        .finally(() => {
            saveBtn.disabled = false;
            saveBtn.innerHTML = originalHtml;
        });
    }

    function openDeleteCategoryModal(categoryName, serviceCount) {
        document.getElementById('deleteCategoryName').textContent = categoryName;
        document.getElementById('deleteCategoryServiceCount').textContent = serviceCount;
        document.getElementById('deleteCategoryNameHidden').value = categoryName;
        document.getElementById('deleteCategoryServiceCountHidden').value = serviceCount;

        const warningDiv = document.getElementById('categoryNotEmptyWarning');
        const deleteBtn = document.getElementById('confirmDeleteCategoryBtn');

        if (serviceCount > 0) {
            warningDiv.style.display = 'block';
            deleteBtn.disabled = true;
        } else {
            warningDiv.style.display = 'none';
            deleteBtn.disabled = false;
        }

        // Get or create modal instance
        const modalElement = document.getElementById('deleteCategoryModal');
        let modal = bootstrap.Modal.getInstance(modalElement);
        if (!modal) {
            modal = new bootstrap.Modal(modalElement);
        }

        // Add event listener to clean up backdrop on modal hide
        modalElement.addEventListener('hidden.bs.modal', function () {
            // Force remove any remaining backdrop
            const backdrops = document.querySelectorAll('.modal-backdrop');
            backdrops.forEach(backdrop => backdrop.remove());

            // Reset body styles
            document.body.classList.remove('modal-open');
            document.body.style.overflow = '';
            document.body.style.paddingRight = '';
        }, { once: true }); // Use once: true to prevent multiple listeners

        modal.show();
    }

    function createNewCategory() {
        const categoryName = document.getElementById('newCategoryName').value.trim();

        if (!categoryName) {
            showToast('Category name cannot be empty', 'error');
            return;
        }

        const data = {
            category_name: categoryName
        };

        const createBtn = document.getElementById('createCategoryBtn');
        const originalHtml = createBtn.innerHTML;
        createBtn.disabled = true;
        createBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Creating...';

        fetch('/add-category', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                // Hide modal and reload page to show changes
                const modal = bootstrap.Modal.getInstance(document.getElementById('addCategoryModal'));
                modal.hide();
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showToast(data.error || 'Failed to create category', 'error');
            }
        })
        .catch(error => {
            showToast('An error occurred while creating the category', 'error');
        })
        .finally(() => {
            createBtn.disabled = false;
            createBtn.innerHTML = originalHtml;
        });
    }

    function deleteCategory() {
        const categoryName = document.getElementById('deleteCategoryNameHidden').value;
        const serviceCount = parseInt(document.getElementById('deleteCategoryServiceCountHidden').value) || 0;

        if (serviceCount > 0) {
            showToast('Cannot delete category with services', 'error');
            return;
        }

        const data = {
            category_name: categoryName
        };

        const deleteBtn = document.getElementById('confirmDeleteCategoryBtn');
        const originalHtml = deleteBtn.innerHTML;
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<i class="bi bi-arrow-clockwise spin"></i> Deleting...';

        fetch('/delete-category', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                // Hide modal and reload page to show changes
                const modal = bootstrap.Modal.getInstance(document.getElementById('deleteCategoryModal'));
                modal.hide();
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            } else {
                showToast(data.error || 'Failed to delete category', 'error');
            }
        })
        .catch(error => {
            showToast('An error occurred while deleting the category', 'error');
        })
        .finally(() => {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = originalHtml;
        });
    }

    function moveCategoryUp(categoryName, categoryIndex) {
        if (categoryIndex <= 0) {
            showToast('Category is already at the top', 'warning');
            return;
        }

        moveCategoryToPosition(categoryName, categoryIndex, categoryIndex - 1);
    }

    function moveCategoryDown(categoryName, categoryIndex) {
        moveCategoryToPosition(categoryName, categoryIndex, categoryIndex + 1);
    }

    function moveCategoryToPosition(categoryName, fromIndex, toIndex) {
        const data = {
            category_name: categoryName,
            from_index: fromIndex,
            to_index: toIndex
        };

        fetch('/move-category', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast(data.message, 'success');
                // Reload page to show changes
                setTimeout(() => {
                    window.location.reload();
                }, 500);
            } else {
                showToast(data.error || 'Failed to move category', 'error');
            }
        })
        .catch(error => {
            showToast('An error occurred while moving the category', 'error');
        });
    }

    // URL validation and fixing helper functions
    function isValidUrl(string) {
        try {
            new URL(string);
            return true;
        } catch (_) {
            return false;
        }
    }

    function ensureProtocol(url) {
        // If URL doesn't start with protocol, add https://
        if (!/^https?:\/\//i.test(url)) {
            return 'https://' + url;
        }
        return url;
    }

    function showUrlFixedFeedback(inputElement, fixedUrl) {
        // Create a small tooltip showing the URL was auto-fixed
        const tooltip = document.createElement('div');
        tooltip.className = 'url-fixed-tooltip';
        tooltip.innerHTML = `<small class="text-success"><i class="bi bi-check-circle"></i> Auto-fixed to: ${fixedUrl}</small>`;
        tooltip.style.position = 'absolute';
        tooltip.style.zIndex = '1000';
        tooltip.style.background = 'var(--bs-success-bg-subtle)';
        tooltip.style.border = '1px solid var(--bs-success-border-subtle)';
        tooltip.style.borderRadius = '0.375rem';
        tooltip.style.padding = '0.25rem 0.5rem';
        tooltip.style.fontSize = '0.75rem';
        tooltip.style.marginTop = '0.25rem';

        // Position tooltip below the input
        const inputRect = inputElement.getBoundingClientRect();
        const container = inputElement.closest('.modal-body');
        if (container) {
            container.style.position = 'relative';
            tooltip.style.position = 'absolute';
            tooltip.style.left = inputElement.offsetLeft + 'px';
            tooltip.style.top = (inputElement.offsetTop + inputElement.offsetHeight + 5) + 'px';
            tooltip.style.width = inputElement.offsetWidth + 'px';
            container.appendChild(tooltip);

            // Remove tooltip after 3 seconds
            setTimeout(() => {
                if (tooltip.parentNode) {
                    tooltip.parentNode.removeChild(tooltip);
                }
            }, 3000);
        }
    }
}

// Color picker functionality
function initializeColorPickers() {
    // Handle color selection in Edit Service modal
    document.querySelectorAll('#editServiceModal .color-option').forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options in edit modal
            document.querySelectorAll('#editServiceModal .color-option').forEach(opt => opt.classList.remove('selected'));
            // Add selected class to clicked option
            this.classList.add('selected');
            // Update hidden input value
            document.getElementById('selectedColor').value = this.dataset.color;
        });
    });

    // Handle color selection in Add Service modal
    document.querySelectorAll('#addServiceModal .color-option').forEach(option => {
        option.addEventListener('click', function() {
            // Remove selected class from all options in add modal
            document.querySelectorAll('#addServiceModal .color-option').forEach(opt => opt.classList.remove('selected'));
            // Add selected class to clicked option
            this.classList.add('selected');
            // Update hidden input value
            document.getElementById('newSelectedColor').value = this.dataset.color;
        });
    });
}

// Initialize color pickers when DOM is ready
initializeColorPickers();
