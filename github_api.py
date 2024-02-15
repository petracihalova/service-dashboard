import json
import re

import requests
from flask import abort

import config
import routes.overview_page


def get_github_projects(links):
    pattern = r"(?:https?://)?(?:www\.)?github\.com/([\w-]+)/([\w-]+)/?"

    github_projects = set()
    for category in links["categories"]:
        for repo in category["category_repos"]:
            for link in repo["links"]:
                if result := re.search(pattern, link["link_value"]):
                    owner = result.group(1).lower()
                    repo_name = result.group(2).lower()
                    github_projects.add((owner, repo_name))
    return sorted(github_projects)


def get_open_pull_request():
    # Get list of GitHub projects from Overview page
    services_links = routes.overview_page.get_services_links()
    github_projects = get_github_projects(services_links)

    pull_requests = {}
    gh_token = config.GITHUB_TOKEN

    # Download open pull requests
    for owner, repo_name in github_projects:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        params = {"state": "open"}

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {gh_token}",
        }

        try:
            response = requests.get(url, params=params, headers=headers)

            if response.status_code == 200:
                json_data = response.json()
                if not json_data:
                    pull_requests[repo_name] = []
                else:
                    open_pr_list = []
                    for pr in json_data:
                        open_pr_list.append(
                            {
                                "number": pr["number"],
                                "draft": pr["draft"],
                                "title": pr["title"],
                                "created_at": pr["created_at"],
                                "user_login": pr["user"]["login"],
                                "html_url": pr["html_url"],
                            }
                        )

                    pull_requests[repo_name] = open_pr_list

            elif response.status_code == 401:
                abort(401, "401 Unauthorized - check the GitHub token.")

            response.raise_for_status()

        except Exception as err:
            
            abort(500, err)

    with open(config.GITHUB_PR_LIST, mode="w", encoding="utf-8") as f:
        json.dump(pull_requests, f, indent=4)
    
    return pull_requests
