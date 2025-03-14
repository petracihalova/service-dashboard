import json
import re
from collections import namedtuple
from datetime import datetime, timedelta

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
    return load_json_data(path)


def load_json_data(path):
    """
    Loads data from a json file and returns it.
    """
    return json.loads(path.read_text(encoding="UTF-8")) if path.is_file() else {}


def is_older_than_six_months(date):
    """Check if date is older than 6 months."""
    if isinstance(date, str):
        date = datetime.fromisoformat(date)

    date = date.replace(tzinfo=None)
    six_months_ago = datetime.now().replace(tzinfo=None) - timedelta(
        days=180
    )  # cca 6 months back
    return date < six_months_ago
