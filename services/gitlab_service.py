from datetime import datetime, timedelta

import requests
from flask import flash

import blueprints
import config
from utils import get_repos_info, load_json_data, logger, save_json_data_and_return

GITLAB_HEADERS = {"PRIVATE-TOKEN": config.GITLAB_TOKEN}


def get_open_merge_request():
    """
    Get open merge requests for GitLab projects (https://gitlab.cee.redhat.com)
    from links obtained from Overview page.
    """
    # Get list of https://gitlab.cee.redhat.com repos from Overview page
    services_links = blueprints.get_services_links()
    gitlab_projects = get_repos_info(services_links, config.GL_REPO_PATTERN)

    merge_requests = {}
    # Download open merge requests
    for owner, repo_name in gitlab_projects:
        url = f"https://gitlab.cee.redhat.com/api/v4/projects/{owner}%2F{repo_name}/merge_requests"
        params = {"state": "opened"}

        try:
            response = requests.get(
                url, params=params, headers=GITLAB_HEADERS, verify=False
            )
            response.raise_for_status()

            json_data = response.json()
            merge_requests[repo_name] = process_open_merge_requests(json_data)

        except requests.exceptions.ConnectionError:
            flash(
                "Connection Error when downloading the GitLab data: Check your connection to the Red Hat VPN",
                category="danger",
            )
            break

        except Exception as err:
            if response.status_code == 401:
                flash("401 Unauthorized: GitLab data not updated.", category="danger")
            else:
                flash(f"Unexpected error occured: {err}", category="danger")
            break

    else:
        return save_json_data_and_return(merge_requests, config.GL_OPEN_PR_FILE)

    return load_json_data(config.GL_OPEN_PR_FILE)


def get_merged_merge_request(days=config.MERGED_IN_LAST_X_DAYS):
    """
    Get merged merge requests for GitLab projects (https://gitlab.cee.redhat.com)
    from links obtained from Overview page.
    """
    BEFORE_X_DAYS = datetime.today() - timedelta(days=days)
    # Get list of GitLab projects from Overview page
    services_links = blueprints.get_services_links()
    gitlab_projects = get_repos_info(services_links, config.GL_REPO_PATTERN)

    merge_requests = {}
    # Download merged merge requests
    for owner, repo_name in gitlab_projects:
        url = f"https://gitlab.cee.redhat.com/api/v4/projects/{owner}%2F{repo_name}/merge_requests"
        params = {"state": "merged"}
        logger.info(f"Downloading 'open' merge requests from '{owner}/{repo_name}'")

        try:
            response = requests.get(
                url, params=params, headers=GITLAB_HEADERS, verify=False
            )
            response.raise_for_status()

            json_data = response.json()
            merge_requests[repo_name] = process_merged_merge_requests(
                json_data, BEFORE_X_DAYS
            )

        except requests.exceptions.ConnectionError:
            flash(
                "Connection Error when downloading the GitLab data: Check your connection to the Red Hat VPN",
                category="danger",
            )
            break

        except Exception as err:
            if response.status_code == 401:
                flash("401 Unauthorized: GitLab data not updated.", category="danger")
            else:
                flash(f"Unexpected error occured: {err}", category="danger")
            break

    else:
        return save_json_data_and_return(merge_requests, config.GL_MERGED_PR_FILE)

    return load_json_data(config.GL_MERGED_PR_FILE)


def process_open_merge_requests(data):
    return [
        {
            "number": f"MR!{mr['iid']}",
            "title": mr["title"],
            "created_at": mr["created_at"],
            "user_login": mr["author"]["username"],
            "html_url": mr["web_url"],
        }
        for mr in data
    ]


def process_merged_merge_requests(data, before):
    merged_mr = []
    for mr in data:
        if not mr["merged_at"]:
            continue

        merged_at_as_datetime = datetime.strptime(
            mr["merged_at"], "%Y-%m-%dT%H:%M:%S.%fZ"
        )
        if before < merged_at_as_datetime:
            merged_mr.append(
                {
                    "number": f"MR!{mr['iid']}",
                    "title": mr["title"],
                    "merged_at": mr["merged_at"],
                    "user_login": mr["author"]["username"],
                    "html_url": mr["web_url"],
                }
            )
    return merged_mr
