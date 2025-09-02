import hashlib
import json
import logging
import time

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for

import config
from services.jira import JiraAPI
from utils.helpers import load_json_data

logger = logging.getLogger(__name__)
jira_tickets_bp = Blueprint("jira_tickets", __name__)

# Cache for JIRA user info to avoid repeated API calls
_jira_user_cache = {"user": None, "timestamp": None, "token_hash": None}


def _load_persistent_cache():
    """Load JIRA user cache from disk if it exists."""
    cache_file = config.JIRA_OPEN_TICKETS_FILE.parent / "jira_user_cache.json"
    try:
        if cache_file.exists():
            with open(cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                return cache_data
    except Exception as e:
        logger.debug(f"Could not load persistent cache: {e}")
    return {"user": None, "timestamp": None, "token_hash": None}


def _save_persistent_cache():
    """Save JIRA user cache to disk."""
    cache_file = config.JIRA_OPEN_TICKETS_FILE.parent / "jira_user_cache.json"
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(_jira_user_cache, f)
    except Exception as e:
        logger.debug(f"Could not save persistent cache: {e}")


# Load cache from disk on startup
persistent_cache = _load_persistent_cache()
if persistent_cache.get("user"):
    logger.debug(f"Loaded JIRA user cache from disk: {persistent_cache['user']}")
_jira_user_cache.update(persistent_cache)


def get_jira_config_info():
    """Get JIRA configuration information for templates."""
    global _jira_user_cache

    jira_info = {
        "token_configured": bool(config.JIRA_PERSONAL_ACCESS_TOKEN),
        "token_masked": "",
        "current_user": "Not available",
        "project": config.JIRA_PROJECT
        if hasattr(config, "JIRA_PROJECT")
        else "Not configured",
    }

    if config.JIRA_PERSONAL_ACCESS_TOKEN:
        # Mask token - show first 3 characters and mask the rest
        token = config.JIRA_PERSONAL_ACCESS_TOKEN
        if len(token) > 3:
            jira_info["token_masked"] = token[:3] + "*" * (len(token) - 3)
        else:
            jira_info["token_masked"] = "*" * len(token)

        # Create hash of current token to detect changes
        current_token_hash = hashlib.sha256(token.encode()).hexdigest()

        # Check cache first - refresh if expired (24 hours) OR token changed
        current_time = time.time()
        cache_expired = (
            _jira_user_cache["timestamp"] is None
            or current_time - _jira_user_cache["timestamp"] > 86400
        )
        token_changed = _jira_user_cache["token_hash"] != current_token_hash

        # Debug cache state
        logger.debug(
            f"Cache state - user: {_jira_user_cache['user'] is not None}, expired: {cache_expired}, token_changed: {token_changed}"
        )
        if _jira_user_cache["timestamp"]:
            cache_age = current_time - _jira_user_cache["timestamp"]
            logger.debug(f"Cache age: {cache_age:.2f} seconds (expires at 86400s)")

        if _jira_user_cache["user"] is None or cache_expired or token_changed:
            # Cache miss, expired, or token changed - fetch from JIRA API
            try:
                if token_changed:
                    logger.debug("Fetching JIRA user info from API (token changed)")
                elif cache_expired:
                    logger.debug("Fetching JIRA user info from API (cache expired)")
                else:
                    logger.debug("Fetching JIRA user info from API (cache miss)")

                jira_api = JiraAPI()
                current_user = jira_api.jira_api.current_user()
                user_display_name = (
                    current_user.displayName
                    if hasattr(current_user, "displayName")
                    else str(current_user)
                )
                # Update cache with new data and token hash
                _jira_user_cache["user"] = user_display_name
                _jira_user_cache["timestamp"] = current_time
                _jira_user_cache["token_hash"] = current_token_hash
                jira_info["current_user"] = user_display_name
                # Save to disk
                _save_persistent_cache()
            except Exception as e:
                logger.debug(f"Could not get JIRA current user: {e}")
                jira_info["current_user"] = "Unable to fetch user info"
                # Cache the failure to avoid repeated API calls
                _jira_user_cache["user"] = "Unable to fetch user info"
                _jira_user_cache["timestamp"] = current_time
                _jira_user_cache["token_hash"] = current_token_hash
                # Save to disk
                _save_persistent_cache()
        else:
            # Use cached value
            logger.debug(f"Using cached JIRA user info: {_jira_user_cache['user']}")
            jira_info["current_user"] = _jira_user_cache["user"]

    return jira_info


def clear_jira_user_cache():
    """Manually clear the JIRA user cache. Useful for debugging or forcing refresh."""
    global _jira_user_cache
    _jira_user_cache = {"user": None, "timestamp": None, "token_hash": None}

    # Also clear persistent cache file
    cache_file = config.JIRA_OPEN_TICKETS_FILE.parent / "jira_user_cache.json"
    try:
        if cache_file.exists():
            cache_file.unlink()
            logger.debug("Persistent JIRA user cache file deleted")
    except Exception as e:
        logger.debug(f"Could not delete persistent cache file: {e}")

    logger.debug("JIRA user cache manually cleared")


@jira_tickets_bp.route("/jira-tickets")
def jira_open_tickets():
    """
    JIRA open tickets page.
    Display open JIRA tickets assigned to the current user (not closed or resolved).
    """
    reload_data = "reload_data" in request.args

    logger.debug(f"JIRA open tickets page accessed with reload_data={reload_data}")

    # Get JIRA tickets
    jira_tickets = get_jira_open_tickets(reload_data)
    logger.debug(f"Route function received {len(jira_tickets)} tickets")

    count = len(jira_tickets)

    # Check if data file exists for template warning
    jira_file_exists = config.JIRA_OPEN_TICKETS_FILE.is_file()
    logger.debug(f"JIRA file exists: {jira_file_exists}")

    # Debug: Log if we have data but no file or vice versa
    if jira_tickets and not jira_file_exists:
        logger.warning("Have tickets in memory but no file exists")
    elif not jira_tickets and jira_file_exists:
        logger.warning("File exists but no tickets in memory")

    # Get JIRA configuration info for template
    jira_config = get_jira_config_info()

    return render_template(
        "jira/jira_tickets.html",
        jira_tickets=jira_tickets,
        count=count,
        jira_file_exists=jira_file_exists,
        jira_config=jira_config,
    )


@jira_tickets_bp.route("/jira-reported-tickets")
def jira_reported_tickets():
    """
    JIRA reported tickets page.
    Display open JIRA tickets reported by the current user (not closed or resolved).
    """
    reload_data = "reload_data" in request.args

    logger.debug(f"JIRA reported tickets page accessed with reload_data={reload_data}")

    # Get JIRA reported tickets
    jira_reported_tickets = get_jira_reported_tickets(reload_data)
    logger.debug(
        f"Route function received {len(jira_reported_tickets)} reported tickets"
    )

    count = len(jira_reported_tickets)

    # Check if data file exists for template warning
    jira_reported_file_exists = config.JIRA_REPORTED_TICKETS_FILE.is_file()
    logger.debug(f"JIRA reported file exists: {jira_reported_file_exists}")

    # Get JIRA configuration info for template
    jira_config = get_jira_config_info()

    return render_template(
        "jira/jira_reported_tickets.html",
        jira_tickets=jira_reported_tickets,
        count=count,
        jira_file_exists=jira_reported_file_exists,
        jira_config=jira_config,
    )


@jira_tickets_bp.route("/jira-closed-tickets")
def jira_closed_tickets():
    """
    JIRA closed tickets page.
    Display closed JIRA tickets assigned to the current user (resolved since January 1st, 2024).
    """
    reload_data = "reload_data" in request.args

    # Get custom days parameter from URL, default to config value
    try:
        custom_days = int(
            request.args.get("days", config.DEFAULT_MERGED_IN_LAST_X_DAYS)
        )
        # Validate reasonable range
        if custom_days < 1 or custom_days > 10000:
            custom_days = config.DEFAULT_MERGED_IN_LAST_X_DAYS
    except (ValueError, TypeError):
        custom_days = config.DEFAULT_MERGED_IN_LAST_X_DAYS

    # Get date range parameters
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Track if date_to was auto-set to today
    date_to_auto_set = False

    # If only date_from is provided, default date_to to today
    if date_from and not date_to:
        from datetime import datetime

        date_to = datetime.now().strftime("%Y-%m-%d")
        date_to_auto_set = True
        logger.debug(f"Auto-setting date_to to today: {date_to}")

    logger.info(
        f"JIRA closed tickets page accessed with reload_data={reload_data}, days={custom_days}"
    )

    # Get JIRA closed tickets
    jira_closed_tickets_all = get_jira_closed_tickets(reload_data)
    logger.info(
        f"Route function received {len(jira_closed_tickets_all)} total closed tickets"
    )

    # Apply date filtering - date range takes precedence over days filter
    if date_from and date_to:
        jira_closed_tickets = filter_tickets_by_date_range(
            jira_closed_tickets_all, date_from, date_to
        )
    else:
        jira_closed_tickets = filter_tickets_resolved_in_last_X_days(
            jira_closed_tickets_all, custom_days
        )
    logger.info(
        f"After filtering by {custom_days} days: {len(jira_closed_tickets)} tickets"
    )

    count = len(jira_closed_tickets)

    # Check if data file exists for template warning
    jira_closed_file_exists = config.JIRA_CLOSED_TICKETS_FILE.is_file()
    logger.debug(f"JIRA closed file exists: {jira_closed_file_exists}")

    # Get JIRA configuration info for template
    jira_config = get_jira_config_info()

    return render_template(
        "jira/jira_closed_tickets.html",
        jira_tickets=jira_closed_tickets,
        count=count,
        closed_in_last_X_days=custom_days,
        date_from=date_from,
        date_to=date_to,
        date_to_auto_set=date_to_auto_set,
        jira_file_exists=jira_closed_file_exists,
        jira_config=jira_config,
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


@jira_tickets_bp.route("/clear-jira-cache")
def clear_cache_endpoint():
    """Development endpoint to manually clear JIRA user cache."""
    clear_jira_user_cache()
    flash("JIRA user cache cleared successfully", "success")
    # Redirect back to the referring page or JIRA tickets page
    return redirect(request.referrer or url_for("jira_tickets.jira_open_tickets"))


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
    return load_json_data(config.JIRA_OPEN_TICKETS_FILE).get("data", [])


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
    return load_json_data(config.JIRA_REPORTED_TICKETS_FILE).get("data", [])


def get_jira_closed_tickets(reload_data):
    """Get closed JIRA tickets assigned to current user from file or download new data."""
    logger.debug(
        f"get_jira_closed_tickets called with reload_data={reload_data}, file_exists={config.JIRA_CLOSED_TICKETS_FILE.is_file()}"
    )

    # Case 1: File doesn't exist and no reload requested
    if not config.JIRA_CLOSED_TICKETS_FILE.is_file() and not reload_data:
        flash("JIRA closed tickets data not found, please update the data", "info")
        return []

    # Check for required configuration
    if not config.JIRA_PERSONAL_ACCESS_TOKEN:
        flash("JIRA_PERSONAL_ACCESS_TOKEN is not configured", "warning")
        logger.error("JIRA_PERSONAL_ACCESS_TOKEN is not set")
        return []

    # Case 2: First time download - file doesn't exist
    if not config.JIRA_CLOSED_TICKETS_FILE.is_file():
        logger.info(
            "First download: downloading all JIRA closed tickets since 2024-01-01"
        )
        try:
            jira_api = JiraAPI()
            tickets = jira_api.get_closed_tickets_assigned_to_me(scope="all")
            logger.info(f"JiraAPI returned {len(tickets)} closed tickets")
            flash("JIRA closed tickets updated successfully", "success")
            return tickets
        except Exception as err:
            flash(
                "Unable to connect to JIRA API - check your JIRA token and configuration",
                "warning",
            )
            flash("JIRA closed tickets were not updated", "warning")
            logger.error(f"JIRA API error: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return []

    # Case 3: Reload requested - incremental download
    if reload_data:
        logger.info(
            "Incremental download: downloading new JIRA closed tickets since last update"
        )
        try:
            jira_api = JiraAPI()
            tickets = jira_api.get_closed_tickets_assigned_to_me(scope="missing")
            logger.info(
                f"JiraAPI returned updated dataset with {len(tickets)} total closed tickets"
            )
            flash("JIRA closed tickets updated successfully", "success")
            return tickets
        except Exception as err:
            flash(
                "Unable to connect to JIRA API - check your JIRA token and configuration",
                "warning",
            )
            flash("JIRA closed tickets were not updated", "warning")
            logger.error(f"JIRA API error: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            # Fall back to existing data
            try:
                with open(
                    config.JIRA_CLOSED_TICKETS_FILE, mode="r", encoding="utf-8"
                ) as file:
                    data = json.load(file)
                    return data.get("data", [])
            except Exception:
                return []

    # Case 4: Load from existing file
    try:
        with open(config.JIRA_CLOSED_TICKETS_FILE, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            timestamp = data.get("timestamp")
            # If you see the timestamp to "test", it means that the data is broken,
            # so we need to download the new data.
            if timestamp == "test":
                logger.warning(
                    "Detected broken data (test timestamp), redownloading all data"
                )
                try:
                    jira_api = JiraAPI()
                    tickets = jira_api.get_closed_tickets_assigned_to_me(scope="all")
                    flash("JIRA closed tickets updated successfully", "success")
                    return tickets
                except Exception as err:
                    flash("JIRA closed tickets were not updated", "warning")
                    logger.error(f"Failed to reload broken data: {err}")
                    return []
            return data.get("data", [])
    except Exception:
        return []


def filter_tickets_resolved_in_last_X_days(tickets_list, days=None):
    """Get JIRA tickets resolved in last X days according configuration."""
    if days is None:
        days = config.DEFAULT_MERGED_IN_LAST_X_DAYS

    from datetime import datetime, timedelta, timezone

    date_X_days_ago = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%d"
    )

    resolved_in_last_x_days = []
    for ticket in tickets_list:
        if ticket.get("resolved_at") and ticket.get("resolved_at") >= date_X_days_ago:
            resolved_in_last_x_days.append(ticket)

    return resolved_in_last_x_days


def filter_tickets_by_date_range(tickets_list, date_from, date_to):
    """Get JIRA tickets resolved within a specific date range."""
    if not date_from or not date_to:
        return tickets_list

    # Ensure date_from is not later than date_to
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    filtered_tickets = []
    for ticket in tickets_list:
        resolved_date = ticket.get("resolved_at", "").split("T")[
            0
        ]  # Get just the date part (YYYY-MM-DD)
        if resolved_date and date_from <= resolved_date <= date_to:
            filtered_tickets.append(ticket)

    return filtered_tickets
