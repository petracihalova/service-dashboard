import json
import logging
from datetime import datetime, timezone

from jira import JIRA

import config
from utils import save_json_data_and_return

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

    def create_jira_ticket(self, options):
        new_issue = self.jira_api.create_issue(fields=options)
        logger.info(f"New Jira ticket created: {new_issue.key}")
        return {
            "ticket_id": new_issue.key,
            "title": new_issue.fields.summary,
            "description": new_issue.fields.description,
            "url": f"{JIRA_SERVER}/browse/{new_issue.key}",
        }

    def get_open_tickets_assigned_to_me(self):
        """Get open JIRA tickets assigned to the current user (not closed or resolved)."""
        try:
            # Get current user from JIRA API
            current_user = self.jira_api.current_user()
            logger.info(f"Fetching open tickets for user: {current_user}")

            # JQL query to get open tickets assigned to current user
            # Let's start with a simpler query first
            jql = "assignee = currentUser() AND resolution is EMPTY"
            logger.info(f"Using JQL query: {jql}")

            # Search for issues with all fields
            issues = self.jira_api.search_issues(
                jql,
                expand="changelog",
                maxResults=1000,  # Adjust based on expected ticket count
            )

            logger.info(f"Found {len(issues)} issues from JIRA API")

            tickets = []
            for i, issue in enumerate(issues):
                logger.debug(f"Processing issue {i + 1}/{len(issues)}: {issue.key}")
                # Get priority safely
                priority = (
                    getattr(issue.fields.priority, "name", "None")
                    if issue.fields.priority
                    else "None"
                )

                # Get status
                status = issue.fields.status.name if issue.fields.status else "Unknown"

                # Get issue type
                issue_type = (
                    issue.fields.issuetype.name if issue.fields.issuetype else "Unknown"
                )

                # Get reporter
                reporter = (
                    issue.fields.reporter.displayName
                    if issue.fields.reporter
                    else "Unknown"
                )

                # Get assignee
                assignee = (
                    issue.fields.assignee.displayName
                    if issue.fields.assignee
                    else "Unassigned"
                )

                # Get components
                components = (
                    [comp.name for comp in issue.fields.components]
                    if issue.fields.components
                    else []
                )

                # Get sprint information
                sprint_info = self._get_sprint_info(issue)

                # Parse created date
                created_at = issue.fields.created
                if created_at:
                    # Convert to ISO format string for consistency with PR data
                    created_dt = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    created_at = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                # Parse updated date
                updated_at = issue.fields.updated
                if updated_at:
                    updated_dt = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                    updated_at = updated_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                ticket_data = {
                    "key": issue.key,
                    "title": issue.fields.summary,
                    "description": getattr(issue.fields, "description", "") or "",
                    "status": status,
                    "priority": priority,
                    "issue_type": issue_type,
                    "assignee": assignee,
                    "reporter": reporter,
                    "components": components,
                    "sprint_name": sprint_info.get("name"),
                    "sprint_state": sprint_info.get("state"),
                    "in_active_sprint": sprint_info.get("in_active_sprint", False),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "url": f"{JIRA_SERVER}/browse/{issue.key}",
                }
                tickets.append(ticket_data)

            # Sort by created date (newest first)
            tickets.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            logger.info(f"Processed {len(tickets)} tickets successfully")

            # Save to file with timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            data_to_save = {
                "timestamp": timestamp,
                "data": tickets,
                "total_count": len(tickets),
            }

            logger.info(
                f"Attempting to save data to file: {config.JIRA_OPEN_TICKETS_FILE}"
            )

            try:
                save_json_data_and_return(data_to_save, config.JIRA_OPEN_TICKETS_FILE)
                logger.info(f"Successfully saved {len(tickets)} tickets to file")
            except Exception as save_error:
                logger.error(f"Failed to save JIRA tickets to file: {save_error}")
                # Return the tickets anyway, even if saving failed

            logger.info(f"Successfully fetched {len(tickets)} open JIRA tickets")
            return tickets

        except Exception as e:
            logger.error(f"Error fetching JIRA tickets: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

    def get_closed_tickets_assigned_to_me(self, scope="all", debug_mode=False):
        """Get closed JIRA tickets assigned to the current user.

        Args:
            scope (str): 'all' for full download from 2024-01-01, 'missing' for incremental
            debug_mode (bool): Enable debug logging
        """
        # Determine the date range based on scope
        if scope == "missing":
            # Read timestamp from existing file for incremental download
            try:
                with open(
                    config.JIRA_CLOSED_TICKETS_FILE, mode="r", encoding="utf-8"
                ) as file:
                    data = json.load(file)
                    timestamp = data.get("timestamp")
                    if timestamp:
                        # Convert ISO timestamp to date format for JIRA query
                        last_download = datetime.fromisoformat(
                            timestamp.replace("Z", "+00:00")
                        )
                        resolved_since = last_download.strftime("%Y-%m-%d")
                        logger.info(
                            f"Incremental download: fetching tickets resolved since {resolved_since}"
                        )
                    else:
                        # Fallback to full download if no timestamp
                        resolved_since = "2024-01-01"
                        logger.warning(
                            "No timestamp in existing file, falling back to full download"
                        )
            except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                logger.warning(
                    f"Could not read timestamp from existing file: {e}, falling back to full download"
                )
                resolved_since = "2024-01-01"
        else:
            # Full download from the beginning
            resolved_since = "2024-01-01"
            logger.info("Full download: fetching all tickets since 2024-01-01")

        try:
            current_user = self.jira_api.current_user()
            logger.info(f"Fetching closed tickets assigned to user: {current_user}")

            # JQL to get closed tickets assigned to current user since the specified date
            jql = f"assignee = currentUser() AND resolution is not EMPTY AND resolved >= '{resolved_since}'"
            logger.info(f"Using JQL query: {jql}")

            # Search for issues with all fields
            issues = self.jira_api.search_issues(
                jql,
                expand="changelog",
                maxResults=1000,  # Adjust based on expected ticket count
            )

            logger.info(f"Found {len(issues)} closed issues from JIRA API")

            tickets = []
            for i, issue in enumerate(issues):
                logger.debug(f"Processing issue {i + 1}/{len(issues)}: {issue.key}")
                # Get priority safely
                priority = (
                    getattr(issue.fields.priority, "name", "None")
                    if issue.fields.priority
                    else "None"
                )

                # Get status
                status = issue.fields.status.name if issue.fields.status else "Unknown"

                # Get issue type
                issue_type = (
                    issue.fields.issuetype.name if issue.fields.issuetype else "Unknown"
                )

                # Get reporter
                reporter = (
                    issue.fields.reporter.displayName
                    if issue.fields.reporter
                    else "Unknown"
                )

                # Get assignee (should be current user)
                assignee = (
                    issue.fields.assignee.displayName
                    if issue.fields.assignee
                    else "Unassigned"
                )

                # Get components
                components = (
                    [comp.name for comp in issue.fields.components]
                    if issue.fields.components
                    else []
                )

                # Get sprint information
                sprint_info = self._get_sprint_info(issue)

                # Parse created date
                created_at = issue.fields.created
                if created_at:
                    # Convert to ISO format string for consistency with PR data
                    created_dt = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    created_at = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                # Parse updated date
                updated_at = issue.fields.updated
                if updated_at:
                    updated_dt = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                    updated_at = updated_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                # Parse resolved date
                resolved_at = issue.fields.resolutiondate
                if resolved_at:
                    resolved_dt = datetime.fromisoformat(
                        resolved_at.replace("Z", "+00:00")
                    )
                    resolved_at = resolved_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                else:
                    resolved_at = None

                # Get resolution
                resolution = (
                    issue.fields.resolution.name
                    if issue.fields.resolution
                    else "Unknown"
                )

                ticket_data = {
                    "key": issue.key,
                    "title": issue.fields.summary,
                    "description": getattr(issue.fields, "description", "") or "",
                    "status": status,
                    "resolution": resolution,
                    "priority": priority,
                    "issue_type": issue_type,
                    "assignee": assignee,
                    "reporter": reporter,
                    "components": components,
                    "sprint_name": sprint_info.get("name"),
                    "sprint_state": sprint_info.get("state"),
                    "in_active_sprint": sprint_info.get("in_active_sprint", False),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "resolved_at": resolved_at,
                    "url": f"{JIRA_SERVER}/browse/{issue.key}",
                }
                tickets.append(ticket_data)

            # Handle incremental download - merge with existing data
            if scope == "missing":
                try:
                    # Read existing tickets from file
                    with open(
                        config.JIRA_CLOSED_TICKETS_FILE, mode="r", encoding="utf-8"
                    ) as file:
                        existing_data = json.load(file)
                        existing_tickets = existing_data.get("data", [])

                    # Create a set of existing ticket keys to avoid duplicates
                    existing_keys = {ticket["key"] for ticket in existing_tickets}

                    # Add only new tickets that don't already exist
                    new_tickets = [
                        ticket
                        for ticket in tickets
                        if ticket["key"] not in existing_keys
                    ]

                    # Combine existing and new tickets
                    all_tickets = existing_tickets + new_tickets

                    logger.info(
                        f"Incremental download: {len(new_tickets)} new tickets added to {len(existing_tickets)} existing tickets"
                    )
                    tickets = all_tickets

                except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                    logger.warning(
                        f"Could not read existing tickets for incremental update: {e}"
                    )
                    logger.info("Proceeding with full download data")

            # Sort by resolved date (most recent first)
            tickets.sort(key=lambda x: x.get("resolved_at", ""), reverse=True)

            logger.info(f"Processed {len(tickets)} total closed tickets successfully")

            # Save to file with timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            data_to_save = {
                "timestamp": timestamp,
                "data": tickets,
                "total_count": len(tickets),
            }

            logger.info(
                f"Attempting to save data to file: {config.JIRA_CLOSED_TICKETS_FILE}"
            )

            try:
                save_json_data_and_return(data_to_save, config.JIRA_CLOSED_TICKETS_FILE)
                logger.info(f"Successfully saved {len(tickets)} closed tickets to file")
            except Exception as save_error:
                logger.error(
                    f"Failed to save JIRA closed tickets to file: {save_error}"
                )
                # Return the tickets anyway, even if saving failed

            logger.info(f"Successfully fetched {len(tickets)} closed JIRA tickets")
            return tickets

        except Exception as e:
            logger.error(f"Error fetching JIRA closed tickets: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

    def get_open_tickets_reported_by_me(self, debug_mode=False):
        """Get open JIRA tickets reported by the current user (not closed or resolved)."""
        try:
            current_user = self.jira_api.current_user()
            logger.info(f"Fetching open tickets reported by user: {current_user}")

            jql = "reporter = currentUser() AND resolution is EMPTY"
            logger.info(f"Using JQL query: {jql}")

            # Search for issues with all fields
            issues = self.jira_api.search_issues(
                jql,
                expand="changelog",
                maxResults=1000,  # Adjust based on expected ticket count
            )

            logger.info(f"Found {len(issues)} issues from JIRA API")

            tickets = []
            for i, issue in enumerate(issues):
                logger.debug(f"Processing issue {i + 1}/{len(issues)}: {issue.key}")
                # Get priority safely
                priority = (
                    getattr(issue.fields.priority, "name", "None")
                    if issue.fields.priority
                    else "None"
                )

                # Get status
                status = issue.fields.status.name if issue.fields.status else "Unknown"

                # Get issue type
                issue_type = (
                    issue.fields.issuetype.name if issue.fields.issuetype else "Unknown"
                )

                # Get reporter (should be current user)
                reporter = (
                    issue.fields.reporter.displayName
                    if issue.fields.reporter
                    else "Unknown"
                )

                # Get assignee
                assignee = (
                    issue.fields.assignee.displayName
                    if issue.fields.assignee
                    else "Unassigned"
                )

                # Get components
                components = (
                    [comp.name for comp in issue.fields.components]
                    if issue.fields.components
                    else []
                )

                # Get sprint information
                sprint_info = self._get_sprint_info(issue)

                # Parse created date
                created_at = issue.fields.created
                if created_at:
                    # Convert to ISO format string for consistency with PR data
                    created_dt = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    created_at = created_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                # Parse updated date
                updated_at = issue.fields.updated
                if updated_at:
                    updated_dt = datetime.fromisoformat(
                        updated_at.replace("Z", "+00:00")
                    )
                    updated_at = updated_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

                ticket_data = {
                    "key": issue.key,
                    "title": issue.fields.summary,
                    "description": getattr(issue.fields, "description", "") or "",
                    "status": status,
                    "priority": priority,
                    "issue_type": issue_type,
                    "assignee": assignee,
                    "reporter": reporter,
                    "components": components,
                    "sprint_name": sprint_info.get("name"),
                    "sprint_state": sprint_info.get("state"),
                    "in_active_sprint": sprint_info.get("in_active_sprint", False),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "url": f"{JIRA_SERVER}/browse/{issue.key}",
                }
                tickets.append(ticket_data)

            # Sort by created date (newest first)
            tickets.sort(key=lambda x: x.get("created_at", ""), reverse=True)

            logger.info(f"Processed {len(tickets)} reported tickets successfully")

            # Save to file with timestamp
            timestamp = datetime.now(timezone.utc).isoformat()
            data_to_save = {
                "timestamp": timestamp,
                "data": tickets,
                "total_count": len(tickets),
            }

            logger.info(
                f"Attempting to save data to file: {config.JIRA_REPORTED_TICKETS_FILE}"
            )

            try:
                save_json_data_and_return(
                    data_to_save, config.JIRA_REPORTED_TICKETS_FILE
                )
                logger.info(
                    f"Successfully saved {len(tickets)} reported tickets to file"
                )
            except Exception as save_error:
                logger.error(
                    f"Failed to save JIRA reported tickets to file: {save_error}"
                )
                # Return the tickets anyway, even if saving failed

            logger.info(
                f"Successfully fetched {len(tickets)} open JIRA reported tickets"
            )
            return tickets

        except Exception as e:
            logger.error(f"Error fetching JIRA reported tickets: {e}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

    def _get_sprint_info(self, issue):
        """Extract sprint information from JIRA issue."""
        try:
            sprint_info = {"name": None, "state": None, "in_active_sprint": False}

            # Check if sprint field exists directly
            if hasattr(issue.fields, "sprint") and issue.fields.sprint:
                sprints = (
                    issue.fields.sprint
                    if isinstance(issue.fields.sprint, list)
                    else [issue.fields.sprint]
                )
                for sprint in sprints:
                    if hasattr(sprint, "state") and sprint.state == "ACTIVE":
                        sprint_info["name"] = getattr(sprint, "name", "Unknown Sprint")
                        sprint_info["state"] = sprint.state
                        sprint_info["in_active_sprint"] = True
                        return sprint_info

                # If no active sprint, get the latest sprint
                if sprints:
                    latest_sprint = sprints[-1]
                    sprint_info["name"] = getattr(
                        latest_sprint, "name", "Unknown Sprint"
                    )
                    sprint_info["state"] = getattr(latest_sprint, "state", "UNKNOWN")
                    return sprint_info

            # Check custom field for sprint information (customfield_12310940 found to contain sprint data)
            sprint_field_names = [
                "customfield_12310940",  # Primary sprint field
                "customfield_10020",
                "customfield_10010",
                "customfield_10014",  # Common fallbacks
            ]

            for field_name in sprint_field_names:
                if hasattr(issue.fields, field_name):
                    sprint_field = getattr(issue.fields, field_name)
                    if sprint_field:
                        # Handle string representation
                        if isinstance(sprint_field, str):
                            if (
                                "state=ACTIVE" in sprint_field
                                and "name=" in sprint_field
                            ):
                                name_match = (
                                    sprint_field.split("name=")[1].split(",")[0]
                                    if "name=" in sprint_field
                                    else "Unknown Sprint"
                                )
                                sprint_info["name"] = name_match
                                sprint_info["state"] = "ACTIVE"
                                sprint_info["in_active_sprint"] = True
                                return sprint_info
                            elif "name=" in sprint_field:
                                name_match = (
                                    sprint_field.split("name=")[1].split(",")[0]
                                    if "name=" in sprint_field
                                    else "Unknown Sprint"
                                )
                                state_match = (
                                    sprint_field.split("state=")[1].split(",")[0]
                                    if "state=" in sprint_field
                                    else "UNKNOWN"
                                )
                                sprint_info["name"] = name_match
                                sprint_info["state"] = state_match
                                return sprint_info

                        # Handle list format
                        elif isinstance(sprint_field, list):
                            active_sprint_found = None
                            latest_sprint_found = None
                            latest_sequence = -1

                            for sprint in sprint_field:
                                if isinstance(sprint, str):
                                    # Check for ACTIVE sprint
                                    if "state=ACTIVE" in sprint and "name=" in sprint:
                                        name_start = sprint.find("name=") + 5
                                        name_end = sprint.find(",", name_start)
                                        if name_end == -1:
                                            name_end = sprint.find("]", name_start)
                                        name_match = (
                                            sprint[name_start:name_end]
                                            if name_end > name_start
                                            else "Unknown Sprint"
                                        )

                                        active_sprint_found = {
                                            "name": name_match,
                                            "state": "ACTIVE",
                                            "in_active_sprint": True,
                                        }

                                    # Track latest sprint by sequence number
                                    elif "name=" in sprint:
                                        sequence = -1
                                        if "sequence=" in sprint:
                                            seq_start = sprint.find("sequence=") + 9
                                            seq_end = sprint.find(",", seq_start)
                                            if seq_end == -1:
                                                seq_end = sprint.find("]", seq_start)
                                            try:
                                                sequence = (
                                                    int(sprint[seq_start:seq_end])
                                                    if seq_end > seq_start
                                                    else -1
                                                )
                                            except ValueError:
                                                sequence = -1

                                        if sequence > latest_sequence:
                                            latest_sequence = sequence

                                            name_start = sprint.find("name=") + 5
                                            name_end = sprint.find(",", name_start)
                                            if name_end == -1:
                                                name_end = sprint.find("]", name_start)
                                            name_match = (
                                                sprint[name_start:name_end]
                                                if name_end > name_start
                                                else "Unknown Sprint"
                                            )

                                            state_start = sprint.find("state=") + 6
                                            state_end = sprint.find(",", state_start)
                                            if state_end == -1:
                                                state_end = sprint.find(
                                                    "]", state_start
                                                )
                                            state_match = (
                                                sprint[state_start:state_end]
                                                if state_end > state_start
                                                else "UNKNOWN"
                                            )

                                            latest_sprint_found = {
                                                "name": name_match,
                                                "state": state_match,
                                                "in_active_sprint": state_match
                                                == "ACTIVE",
                                            }

                                # Handle object format
                                elif sprint and hasattr(sprint, "state"):
                                    if sprint.state == "ACTIVE":
                                        active_sprint_found = {
                                            "name": getattr(
                                                sprint, "name", "Unknown Sprint"
                                            ),
                                            "state": sprint.state,
                                            "in_active_sprint": True,
                                        }

                            # Return active sprint if found, otherwise latest sprint
                            if active_sprint_found:
                                sprint_info.update(active_sprint_found)
                                return sprint_info
                            elif latest_sprint_found:
                                sprint_info.update(latest_sprint_found)
                                return sprint_info

                        # Handle single object format
                        else:
                            sprint = sprint_field
                            if sprint and hasattr(sprint, "state"):
                                if sprint.state == "ACTIVE":
                                    sprint_info["name"] = getattr(
                                        sprint, "name", "Unknown Sprint"
                                    )
                                    sprint_info["state"] = sprint.state
                                    sprint_info["in_active_sprint"] = True
                                    return sprint_info
                                else:
                                    sprint_info["name"] = getattr(
                                        sprint, "name", "Unknown Sprint"
                                    )
                                    sprint_info["state"] = getattr(
                                        sprint, "state", "UNKNOWN"
                                    )
                                    return sprint_info

            return sprint_info

        except Exception as e:
            logger.debug(f"Could not get sprint info for {issue.key}: {e}")
            return {"name": None, "state": None, "in_active_sprint": False}
