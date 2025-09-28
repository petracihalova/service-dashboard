import json
import logging
import re
from collections import namedtuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


RepoMetaData = namedtuple("RepoMetaData", "owner, repo_name")


def get_repos_info(links, pattern):
    """
    Get a list of pairs (owner, repo name) about repositories obtained from 'links' based on 'pattern'.
    """
    repos_info = set()
    for category in links.get("categories", ()):
        for repo in category["category_repos"]:
            for link in repo["links"]:
                if result := re.search(pattern, link["link_value"]):
                    owner = result.group("owner").lower()
                    repo_name = result.group("name").lower()
                    repos_info.add(RepoMetaData(owner=owner, repo_name=repo_name))
    return sorted(repos_info)


def save_json_data_and_return(data, path, encoder=None):
    """
    Saves data as a json file and returns the data.
    """
    path.write_text(json.dumps(data, indent=4, cls=encoder))
    if "data" in load_json_data(path):
        return load_json_data(path).get("data")
    return load_json_data(path)


def load_json_data(path):
    """
    Loads data from a json file and returns it.
    """
    return json.loads(path.read_text(encoding="UTF-8")) if path.is_file() else {}


def is_enhancement_running():
    """
    Check if close_actor enhancement process is currently running.
    Returns True if running, False otherwise.
    """
    try:
        from services.close_actor_enhancer import enhancer

        progress = enhancer.get_progress()
        return progress.get("status") in ["running", "stopping"]
    except Exception as e:
        logger.warning(f"Could not check enhancement status: {e}")
        return False


def is_older_than_six_months(date):
    """Check if date is older than 6 months."""
    if isinstance(date, str):
        date = datetime.fromisoformat(date)

    date = date.replace(tzinfo=None)
    six_months_ago = datetime.now().replace(tzinfo=None) - timedelta(
        days=180
    )  # cca 6 months back
    return date < six_months_ago


def calculate_days_open(created_at, end_at):
    """
    Calculate the number of days a PR/MR was open.

    Args:
        created_at (datetime): When the PR/MR was created
        end_at (datetime): When the PR/MR was merged or closed

    Returns:
        int: Number of days the PR/MR was open, or None if dates are invalid
    """
    if not created_at or not end_at:
        return None

    try:
        # Ensure both dates are datetime objects
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if isinstance(end_at, str):
            end_at = datetime.fromisoformat(end_at.replace("Z", "+00:00"))

        # Remove timezone info for consistent calculation
        created_at = created_at.replace(tzinfo=None)
        end_at = end_at.replace(tzinfo=None)

        # Calculate the difference
        duration = end_at - created_at + timedelta(days=1)
        return duration.days

    except (ValueError, AttributeError):
        # Return None for invalid dates
        return None
