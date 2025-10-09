/**
 * JIRA DataTables Initialization
 * Provides initialization functions for different JIRA ticket pages
 */

const JiraInit = {
    /**
     * Initialize standard JIRA tickets datatable
     */
    initStandard: function() {
        JiraDataTables.initStandard('#jira-datatable');
    },

    /**
     * Initialize JIRA reported tickets datatable
     */
    initReported: function() {
        JiraDataTables.initReported('#jira-reported-datatable');
    },

    /**
     * Initialize JIRA closed tickets datatable
     */
    initClosed: function() {
        JiraDataTables.initClosed('#jira-closed-datatable');
    }
};
