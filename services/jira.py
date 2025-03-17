import logging

from jira import JIRA

import config

logger = logging.getLogger(__name__)

JIRA_SERVER = config.JIRA_SERVER
TICKET_ID = "RHCLOUD-29391"
JIRA_PERSONAL_ACCESS_TOKEN = config.JIRA_PERSONAL_ACCESS_TOKEN


class JiraAPI:
    def __init__(self):
        """Connection to the JIRA API."""
        options = {"server": JIRA_SERVER}
        self.jira_api = JIRA(options, token_auth=JIRA_PERSONAL_ACCESS_TOKEN)
        logger.info("Successfully connected to JIRA API.")

    def get_jira_ticket(self, ticket_id):
        issue = self.jira_api.issue(ticket_id)
        title = issue.fields.summary
        assigned_user = (
            issue.fields.assignee.displayName if issue.fields.assignee else "Unassigned"
        )
        return {
            "ticket_id": ticket_id,
            "title": title,
            "assigned_user": assigned_user,
        }
