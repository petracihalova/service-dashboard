from datetime import datetime


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
