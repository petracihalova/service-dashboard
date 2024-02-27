import re


def get_repos_info(links, pattern):
    repos_info = set()
    for category in links["categories"]:
        for repo in category["category_repos"]:
            for link in repo["links"]:
                if result := re.search(pattern, link["link_value"]):
                    owner = result.group(1).lower()
                    repo_name = result.group(2).lower()
                    repos_info.add((owner, repo_name))
    return sorted(repos_info)
