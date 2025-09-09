# JavaScript Organization Guide

## 📁 Folder Structure

### `/components/` - Reusable UI Components
Organized by component type, these files provide reusable functionality across multiple pages.

#### `/components/buttons/`
- **`update-buttons.js`** - Consolidated update button functionality with loading spinners
  - *Replaces:* `update_button.js`, `update_deployment_button.js`
  - *Usage:* Handles all update buttons with consistent loading states

#### `/components/datatables/`
- **`jira-datatables.js`** - Consolidated JIRA table configurations
  - *Replaces:* `jira_datatable.js`, `jira_closed_datatable.js`, `jira_reported_datatable.js`
  - *Usage:* `JiraDataTables.initStandard()`, `JiraDataTables.initClosed()`, `JiraDataTables.initReported()`
- **`datatable.js`** - Main DataTable configurations
- **`detail_row.js`** - DataTable detail row functionality
- **`main_row.js`** - DataTable main row interactions

#### `/components/filters/`
- **`pr-filters.js`** - Consolidated PR/MR filter functionality
  - *Replaces:* `pr_inline_handlers.js`, `pr_advanced_inline_handlers.js` (partially)
  - *Usage:* Automatic initialization of source, organization, and view filters
- **`pr_filter_shared.js`** - Shared PR filter utilities
- **`date_range_filter.js`** - Date range filtering
- **`days_filter.js`** - Days-based filtering
- **`app_interface_filters.js`** - App-interface specific filters

#### `/components/modals/`
- **`pr_config_modal.js`** - PR configuration modal functionality

### `/pages/` - Page-Specific Functionality
Code that's specific to individual pages or page groups.

#### `/pages/pr-handlers/`
- **`app-interface.js`** - App-interface PR/MR page handlers
  - *Replaces:* `app_interface_inline_handlers.js`
  - *Usage:* Automatic initialization for app-interface pages
- **`pull_requests.js`** - General PR page functionality

#### Main Pages
- **`overview.js`** - Services overview page
- **`personal_stats.js`** - Personal statistics page
- **`all_data_stats.js`** - All data statistics page
- **`deployment_mr.js`** - Deployment MR functionality
- **`release_notes_select.js`** - Release notes selection page

### `/utils/` - Utility Functions
General-purpose utilities used across the application.

- **`layout.js`** - Layout and theme functionality
- **`copy_button.js`** - Copy to clipboard functionality
- **`update_all_data.js`** - Update all data functionality

### `/legacy/` - Deprecated Files
Old files kept for reference during transition. **Do not use these files.**

## 🔄 Migration Guide

### For JIRA Pages
**Old:**
```html
<script src="js/jira_datatable.js"></script>
<script src="js/jira_closed_datatable.js"></script>
<script src="js/jira_reported_datatable.js"></script>
```

**New:**
```html
<script src="js/components/datatables/jira-datatables.js"></script>
<script>
  // Initialize appropriate table type
  JiraDataTables.initStandard('#jira-datatable');
  // or JiraDataTables.initClosed('#jira-closed-datatable');
  // or JiraDataTables.initReported('#jira-reported-datatable');
</script>
```

### For Update Buttons
**Old:**
```html
<script src="js/update_button.js"></script>
<script src="js/update_deployment_button.js"></script>
```

**New:**
```html
<script src="js/components/buttons/update-buttons.js"></script>
<!-- Automatic initialization for #update_button and #update_deployment_button -->
```

### For PR/MR Pages
**Old:**
```html
<script src="js/pr_inline_handlers.js"></script>
<script src="js/pr_advanced_inline_handlers.js"></script>
<script src="js/app_interface_inline_handlers.js"></script>
```

**New:**
```html
<!-- For standard PR pages -->
<script src="js/components/filters/pr-filters.js"></script>

<!-- For app-interface pages -->
<script src="js/pages/pr-handlers/app-interface.js"></script>
```

## ✅ Benefits of New Structure

1. **Eliminated Duplication** - Consolidated ~600 lines of duplicate code
2. **Better Organization** - Logical grouping by functionality
3. **Improved Maintainability** - Clear separation of concerns
4. **Consistent Naming** - Kebab-case for better readability
5. **Modular Design** - Reusable components across pages
6. **Documentation** - Clear usage instructions and migration paths
