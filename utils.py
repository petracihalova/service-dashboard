import re
from collections import namedtuple

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
