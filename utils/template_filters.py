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
