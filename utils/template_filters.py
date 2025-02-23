from datetime import datetime


def format_datetime(value, format="%B %d, %Y"):
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime(format)
    except ValueError:
        return value
