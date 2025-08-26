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
