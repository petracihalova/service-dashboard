from datetime import datetime


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
