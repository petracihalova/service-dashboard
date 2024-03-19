import re


def get_repos_info(links, pattern):
    """
    Get a list of pairs (owner, repo name) about repositories obtained from 'links' based on 'pattern'.
    """
    repos_info = set()
    for category in links["categories"]:
        for repo in category["category_repos"]:
            for link in repo["links"]:
                if result := re.search(pattern, link["link_value"]):
                    owner = result.group("owner").lower()
                    repo_name = result.group("name").lower()
                    repos_info.add((owner, repo_name))
    return sorted(repos_info)
