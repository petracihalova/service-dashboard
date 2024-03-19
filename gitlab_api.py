import json

import requests
from flask import abort

import config
import routes.overview_page
from utils import get_repos_info


def get_open_pull_request():
    """
    Get open pull requests for GitLub project (https://gitlab.cee.redhat.com)
    from links obtained from Overview page.
    """
    # Get list of https://gitlab.cee.redhat.com repos from Overview page
    services_links = routes.overview_page.get_services_links()
    gitlab_projects = get_repos_info(services_links, config.GITLAB_PATTERN)

    pull_requests = {}
    # Download open pull requests
    for owner, repo_name in gitlab_projects:
        url = f"https://gitlab.cee.redhat.com/api/v4/projects/{owner}%2F{repo_name}/merge_requests"
        params = {"state": "opened"}
        headers = {"PRIVATE-TOKEN": config.GITLAB_TOKEN}

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

        except requests.exceptions.ConnectionError:
            abort(500, "Check that you use the Red Hat VPN")

        except Exception as err:
            abort(500, err)

    with open(config.GITLAB_PR_LIST, mode="w", encoding="utf-8") as f:
        json.dump(pull_requests, f, indent=4)

    return pull_requests
