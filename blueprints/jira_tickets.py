import json
import logging

from flask import Blueprint, flash, render_template, request, jsonify

import config
from services.jira import JiraAPI

logger = logging.getLogger(__name__)
jira_tickets_bp = Blueprint("jira_tickets", __name__)


@jira_tickets_bp.route("/jira-tickets")
def jira_open_tickets():
    """
    JIRA open tickets page.
    Display open JIRA tickets assigned to the current user (not closed or resolved).
    """
    reload_data = "reload_data" in request.args

    logger.info(f"JIRA open tickets page accessed with reload_data={reload_data}")

    # Get JIRA tickets
    jira_tickets = get_jira_open_tickets(reload_data)
    logger.info(f"Route function received {len(jira_tickets)} tickets")

    count = len(jira_tickets)

    # Check if data file exists for template warning
    jira_file_exists = config.JIRA_OPEN_TICKETS_FILE.is_file()
    logger.info(f"JIRA file exists: {jira_file_exists}")

    # Debug: Log if we have data but no file or vice versa
    if jira_tickets and not jira_file_exists:
        logger.warning("Have tickets in memory but no file exists")
    elif not jira_tickets and jira_file_exists:
        logger.warning("File exists but no tickets in memory")

    return render_template(
        "pull_requests/jira_tickets.html",
        jira_tickets=jira_tickets,
        count=count,
        jira_file_exists=jira_file_exists,
    )


@jira_tickets_bp.route("/jira-reported-tickets")
def jira_reported_tickets():
    """
    JIRA reported tickets page.
    Display open JIRA tickets reported by the current user (not closed or resolved).
    """
    reload_data = "reload_data" in request.args

    logger.info(f"JIRA reported tickets page accessed with reload_data={reload_data}")

    # Get JIRA reported tickets
    jira_reported_tickets = get_jira_reported_tickets(reload_data)
    logger.info(
        f"Route function received {len(jira_reported_tickets)} reported tickets"
    )

    count = len(jira_reported_tickets)

    # Check if data file exists for template warning
    jira_reported_file_exists = config.JIRA_REPORTED_TICKETS_FILE.is_file()
    logger.info(f"JIRA reported file exists: {jira_reported_file_exists}")

    return render_template(
        "pull_requests/jira_reported_tickets.html",
        jira_tickets=jira_reported_tickets,
        count=count,
        jira_file_exists=jira_reported_file_exists,
    )


@jira_tickets_bp.route("/create_jira_ticket", methods=["POST"])
def create_new_jira_ticket():
    """Create a new JIRA ticket for prod releases."""
    data = request.get_json()
    repo_name = data.get("repo_name").split("/")[1]
    # Security ID 11697 = Red Hat Employee
    options = {
        "project": {"key": config.JIRA_PROJECT},
        "summary": f"[{repo_name}] prod release",
        "description": "",
        "issuetype": {"name": "Task"},
        "labels": ["platform-accessmanagement"],
        "security": {"id": "11697"},
    }
    jira_api = JiraAPI()
    new_issue = jira_api.create_jira_ticket(options)
    link = new_issue.get("url")
    id = new_issue.get("ticket_id")
    message = f'New JIRA ticket \'<a href="{link}" target="_blank">{id}</a>\' created!'
    return jsonify({"message": message})


def get_jira_open_tickets(reload_data):
    """Get open JIRA tickets assigned to current user from file or download new data."""
    logger.info(
        f"get_jira_open_tickets called with reload_data={reload_data}, file_exists={config.JIRA_OPEN_TICKETS_FILE.is_file()}"
    )

    if not config.JIRA_OPEN_TICKETS_FILE.is_file() and not reload_data:
        flash("JIRA open tickets data not found, please update the data", "info")
        return []

    if not config.JIRA_PERSONAL_ACCESS_TOKEN:
        flash("JIRA_PERSONAL_ACCESS_TOKEN is not configured", "warning")
        logger.error("JIRA_PERSONAL_ACCESS_TOKEN is not set")
        return []

    if reload_data:
        logger.info("Downloading new JIRA tickets data")
        try:
            jira_api = JiraAPI()
            tickets = jira_api.get_open_tickets_assigned_to_me()
            logger.info(f"JiraAPI returned {len(tickets)} tickets")

            # Debug: Log first few tickets if any
            if tickets:
                logger.debug(f"First ticket: {tickets[0]}")
            else:
                logger.warning("No tickets returned from JIRA API")

            flash("JIRA open tickets updated successfully", "success")
            return tickets
        except Exception as err:
            flash(
                "Unable to connect to JIRA API - check your JIRA token and configuration",
                "warning",
            )
            flash("JIRA open tickets were not updated", "warning")
            logger.error(f"JIRA API error: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Try to return existing data if available
            if config.JIRA_OPEN_TICKETS_FILE.is_file():
                with open(
                    config.JIRA_OPEN_TICKETS_FILE, mode="r", encoding="utf-8"
                ) as file:
                    data = json.load(file)
                    return data.get("data", [])
            return []

    # Load from existing file
    with open(config.JIRA_OPEN_TICKETS_FILE, mode="r", encoding="utf-8") as file:
        data = json.load(file)
        return data.get("data", [])


def get_jira_reported_tickets(reload_data):
    """Get JIRA tickets reported by the current user."""
    logger.info(
        f"get_jira_reported_tickets called with reload_data={reload_data}, file_exists={config.JIRA_REPORTED_TICKETS_FILE.is_file()}"
    )
    if not config.JIRA_REPORTED_TICKETS_FILE.is_file() and not reload_data:
        flash("JIRA reported tickets data not found, please update the data", "info")
        return []
    if not config.JIRA_PERSONAL_ACCESS_TOKEN:
        flash("JIRA_PERSONAL_ACCESS_TOKEN is not configured", "warning")
        logger.error("JIRA_PERSONAL_ACCESS_TOKEN is not set")
        return []
    if reload_data:
        logger.info("Downloading new JIRA reported tickets data")
        try:
            jira_api = JiraAPI()
            tickets = jira_api.get_open_tickets_reported_by_me()
            logger.info(f"JiraAPI returned {len(tickets)} reported tickets")
            if tickets:
                logger.debug(f"First reported ticket: {tickets[0]}")
            else:
                logger.warning("No reported tickets returned from JIRA API")
            flash("JIRA reported tickets updated successfully", "success")
            return tickets
        except Exception as err:
            flash(
                "Unable to connect to JIRA API - check your JIRA token and configuration",
                "warning",
            )
            flash("JIRA reported tickets were not updated", "warning")
            logger.error(f"JIRA API error: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            if config.JIRA_REPORTED_TICKETS_FILE.is_file():
                with open(
                    config.JIRA_REPORTED_TICKETS_FILE, mode="r", encoding="utf-8"
                ) as file:
                    data = json.load(file)
                    return data.get("data", [])
            return []

    # Load from existing file
    with open(config.JIRA_REPORTED_TICKETS_FILE, mode="r", encoding="utf-8") as file:
        data = json.load(file)
        return data.get("data", [])
