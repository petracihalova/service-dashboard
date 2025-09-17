from datetime import datetime, timedelta


def get_language_icon(language):
    """
    Return the icon filename for a given programming language.
    Maps language names to corresponding SVG icons in static/icons/.
    """
    if not language:
        return None

    # Create mapping of language names to icon filenames
    language_icons = {
        "python": "python.svg",
        "javascript": "javascript.svg",
        "go": "go.svg",
        "ruby": "ruby.svg",
        "lua": "lua.svg",
    }
    return language_icons.get(language.lower())


def format_datetime(value, format="%B %d, %Y"):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime(format)
    except ValueError:
        return value


def days_since(date_string, format="%Y-%m-%dT%H:%M:%S.%fZ"):
    target_date = datetime.strptime(date_string, format).date()
    return (datetime.today().date() - target_date).days


def date_range_from_days(days):
    """
    Calculate the date range string from number of days.
    Returns format like "24/8 - 26/8" for a 3-day range.
    """
    if not days or days <= 0:
        return ""

    try:
        today = datetime.now().date()
        start_date = today - timedelta(
            days=days - 1
        )  # days-1 because today counts as day 1
        end_date = today

        # Format as Mon dd, yyyy - US format with month names and full year
        start_str = start_date.strftime("%b %d, %Y")
        end_str = end_date.strftime("%b %d, %Y")

        return f"{start_str} - {end_str}"
    except Exception:
        return ""


def get_link_icon(link_name):
    """
    Return the appropriate Bootstrap icon class for different link types.
    Maps common link names to relevant icons.
    """
    if not link_name:
        return "bi-link-45deg"

    # Create mapping of link names to Bootstrap icon classes
    link_icons = {
        "code": "bi-github",
        "github": "bi-github",
        "gitlab": "bi-gitlab",
        "image": "bi-box",
        "quay": "bi-box",
        "docker": "bi-box",
        "konflux image": "bi-boxes",
        "confluence": "bi-journal-text",
        "documentation": "bi-journal-text",
        "docs": "bi-journal-text",
        "app-interface": "bi-diagram-3",
        "interface": "bi-diagram-3",
        "release notes": "bi-clipboard-data",
        "notes": "bi-clipboard-data",
        "changelog": "bi-clipboard-data",
        "konflux pipelines": "bi-diagram-2",
        "pipeline": "bi-diagram-2",
        "pipelines": "bi-diagram-2",
        "ci": "bi-diagram-2",
        "cd": "bi-diagram-2",
        "monitoring": "bi-graph-up",
        "metrics": "bi-graph-up",
        "grafana": "bi-graph-up",
        "logs": "bi-file-text",
        "logging": "bi-file-text",
        "kibana": "bi-file-text",
        "jira": "bi-kanban",
        "issues": "bi-bug",
        "tickets": "bi-ticket-perforated",
        "api": "bi-code-slash",
        "swagger": "bi-code-slash",
        "openapi": "bi-code-slash",
        "database": "bi-database",
        "db": "bi-database",
        "redis": "bi-database",
        "postgres": "bi-database",
        "config": "bi-gear",
        "configuration": "bi-gear",
        "settings": "bi-gear",
        "deploy": "bi-cloud-arrow-up",
        "deployment": "bi-cloud-arrow-up",
        "k8s": "bi-cloud",
        "kubernetes": "bi-cloud",
        "helm": "bi-cloud",
    }

    # Check for partial matches in link name (case insensitive)
    link_name_lower = link_name.lower()
    for key, icon in link_icons.items():
        if key in link_name_lower:
            return icon

    # Default icon for unknown link types
    return "bi-link-45deg"


def calculate_days_between_dates(start_date, end_date=None):
    """
    Calculate the number of days between two date strings (YYYY-MM-DD format).
    If end_date is None, uses today's date.
    Returns the number of days including both start and end dates.
    """
    if not start_date:
        return 0

    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()

        if end_date:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        else:
            end = datetime.now().date()

        # Calculate days difference and add 1 to include both start and end dates
        days_diff = (end - start).days + 1

        # Ensure we return at least 1 day (same day = 1 day)
        return max(1, days_diff)
    except (ValueError, TypeError):
        return 0


def format_date_display(date_string):
    """
    Format a date string (YYYY-MM-DD) for display in MMM d, yyyy format.
    """
    if not date_string:
        return ""

    try:
        date_obj = datetime.strptime(date_string, "%Y-%m-%d").date()
        return date_obj.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return date_string


def to_date(date_string):
    """
    Convert date string (YYYY-MM-DD) to datetime.date object for template calculations.

    Args:
        date_string: Date string in format YYYY-MM-DD

    Returns:
        datetime.date: Date object or original string if conversion fails
    """
    if not date_string:
        return date_string

    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return date_string


def calculate_days_open_from_iso(iso_datetime_string):
    """
    Calculate days open from ISO datetime string to today.

    Args:
        iso_datetime_string: ISO format datetime like "2025-09-17T14:28:29+00:00"

    Returns:
        int: Number of days including both start and end dates (minimum 1)
    """
    if not iso_datetime_string:
        return 0

    try:
        # Parse ISO datetime string and convert to date
        dt = datetime.fromisoformat(iso_datetime_string.replace("Z", "+00:00"))
        created_date = dt.date()

        # Get today's date
        today = datetime.now().date()

        # Calculate days difference and add 1 to include both start and end dates
        days_diff = (today - created_date).days + 1

        # Ensure we return at least 1 day (same day = 1 day)
        return max(1, days_diff)

    except (ValueError, TypeError, AttributeError):
        return 0
