import json
import re
from collections import namedtuple

from utils.json_utils import PullRequestEncoder

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


def save_json_data_and_return(data, path):
    """
    Saves data as a json file and returns the data.
    """
    path.write_text(json.dumps(data, indent=4, cls=PullRequestEncoder))
    return data


def load_json_data(path):
    """
    Loads data from a json file and returns it.
    """
    return json.loads(path.read_text(encoding="UTF-8")) if path.is_file() else {}
