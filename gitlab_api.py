import json
from datetime import datetime

import requests
from flask import flash

import config
import routes.overview_page
from github_api import BEFORE_14_DAYS
from utils import get_repos_info


def get_open_pull_request():
    """
    Get open pull requests for GitLab projects (https://gitlab.cee.redhat.com)
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
                flash(
                    "401 Unauthorized: GitLab data not updated. Check the GitLab token.",
                    category="danger",
                )
                break

            response.raise_for_status()

        except requests.exceptions.ConnectionError:
            flash(
                "Connection Error when downloading the GitLab data: Check your connection to the Red Hat VPN",
                category="danger",
            )
            break

        except Exception as err:
            flash(f"Unexpecter error occured: {err}", category="danger")
            break

    else:
        with open(config.GITLAB_PR_LIST, mode="w", encoding="utf-8") as f:
            json.dump(pull_requests, f, indent=4)
        return pull_requests

    if config.GITLAB_PR_LIST.is_file():
        with open(config.GITLAB_PR_LIST, mode="r", encoding="utf-8") as file:
            return json.load(file)
    return pull_requests


def get_merged_pull_request():
    """
    Get merged pull requests for GitLab projects (https://gitlab.cee.redhat.com)
    from links obtained from Overview page.
    """
    # Get list of GitLab projects from Overview page
    services_links = routes.overview_page.get_services_links()
    gitlab_projects = get_repos_info(services_links, config.GITLAB_PATTERN)

    pull_requests = {}
    # Download merged pull requests
    for owner, repo_name in gitlab_projects:
        url = f"https://gitlab.cee.redhat.com/api/v4/projects/{owner}%2F{repo_name}/merge_requests"
        params = {"state": "merged"}
        headers = {"PRIVATE-TOKEN": config.GITLAB_TOKEN}

        try:
            response = requests.get(url, params=params, headers=headers, verify=False)

            if response.status_code == 200:
                json_data = response.json()
                if not json_data:
                    pull_requests[repo_name] = []
                else:
                    merged_pr_list = []
                    for pr in json_data:
                        merged_at_as_datetime = datetime.strptime(
                            pr["merged_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
                        )
                        if BEFORE_14_DAYS < merged_at_as_datetime:
                            merged_pr_list.append(
                                {
                                    "number": pr["iid"],
                                    "title": pr["title"],
                                    "merged_at": pr["merged_at"],
                                    "user_login": pr["author"]["username"],
                                    "html_url": pr["web_url"],
                                }
                            )
                    pull_requests[repo_name] = merged_pr_list

            elif response.status_code == 401:
                flash(
                    "401 Unauthorized: GitLab data not updated. Check the GitLab token.",
                    category="danger",
                )
                break

            response.raise_for_status()

        except requests.exceptions.ConnectionError:
            flash(
                "Connection Error when downloading the GitLab data: Check your connection to the Red Hat VPN",
                category="danger",
            )
            break

        except Exception as err:
            flash(f"Unexpecter error occured: {err}", category="danger")
            break

    else:
        with open(config.GITLAB_MERGED_PR_LIST, mode="w", encoding="utf-8") as f:
            json.dump(pull_requests, f, indent=4)
        return pull_requests

    if config.GITLAB_MERGED_PR_LIST.is_file():
        with open(config.GITLAB_MERGED_PR_LIST, mode="r", encoding="utf-8") as file:
            return json.load(file)
    return pull_requests
