import json
import re

import requests
from flask import abort

import config
import routes.overview_page


def get_gitlab_projects(links):
    # all https://gitlab.cee.redhat.com repos exl "app-interface"
    pattern = r"(?:https?://)?(?:www\.)?gitlab\.cee\.redhat\.com/([\w-]+)/(?!app-interface)([\w-]+)/?"

    gitlab_projects = set()
    for category in links["categories"]:
        for repo in category["category_repos"]:
            for link in repo["links"]:
                if result := re.search(pattern, link["link_value"]):
                    owner = result.group(1).lower()
                    repo_name = result.group(2).lower()
                    gitlab_projects.add((owner, repo_name))
    return sorted(gitlab_projects)


def get_open_pull_request():
    # Get list of https://gitlab.cee.redhat.com repos from Overview page
    services_links = routes.overview_page.get_services_links()
    gitlab_projects = get_gitlab_projects(services_links)

    pull_requests = {}
    gl_token = config.GITLAB_TOKEN

    # Download open pull requests
    for owner, repo_name in gitlab_projects:    
        url = f"https://gitlab.cee.redhat.com/api/v4/projects/{owner}%2F{repo_name}/merge_requests"
        params = {"state": "opened"}
        headers = {"PRIVATE-TOKEN": gl_token}
        
        try:
            response = requests.get(url, params=params, headers=headers, verify=False)

            if response.status_code == 200:
                json_data = response.json()
                if not json_data:
                    pull_requests[repo_name] = []
                else:
                    open_pr_list = []
                    for pr in json_data:
                        open_pr_list.append(
                            {
                                "number": pr["iid"],
                                "draft": pr["draft"],
                                "title": pr["title"],
                                "created_at": pr["created_at"],
                                "user_login": pr["author"]["username"],
                                "html_url": pr["web_url"],
                            }
                        )

                    pull_requests[repo_name] = open_pr_list

            elif response.status_code == 401:
                abort(401, "401 Unauthorized - check the GitLab token.")

            response.raise_for_status()

        except requests.exceptions.ConnectionError as err:
            abort(500, "Check that you use the Red Hat VPN")

        except Exception as err:
            abort(500, err)

    with open(config.GITLAB_PR_LIST, mode="w", encoding="utf-8") as f:
        json.dump(pull_requests, f, indent=4)
    
    return pull_requests
