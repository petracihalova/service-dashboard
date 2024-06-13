from datetime import datetime, timedelta

import requests
from flask import flash

import config
import routes.overview_page
from utils import get_repos_info, load_json_data, save_json_data_and_return

BEFORE_14_DAYS = datetime.today() - timedelta(days=14)
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "Authorization": f"Bearer {config.GITHUB_TOKEN}",
}


def get_open_pull_request():
    """
    Get open pull requests for GitHub projects from links obtained from Overview page.
    """
    # Get list of GitHub projects from Overview page
    services_links = routes.overview_page.get_services_links()
    github_projects = get_repos_info(services_links, config.GITHUB_PATTERN)

    pull_requests = {}
    # Download open pull requests
    for owner, repo_name in github_projects:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        params = {"state": "open"}

        try:
            response = requests.get(url, params=params, headers=GITHUB_HEADERS)
            response.raise_for_status()

            json_data = response.json()
            pull_requests[repo_name] = process_open_pull_requests(json_data)

        except Exception as err:
            if response.status_code == 401:
                flash("401 Unauthorized: GitHub data not updated.", category="danger")
            else:
                flash(f"Unexpected error occured: {err}", category="danger")
            break

    else:
        return save_json_data_and_return(pull_requests, config.GITHUB_PR_LIST)

    return load_json_data(config.GITHUB_PR_LIST)


def get_merged_pull_request():
    """
    Get merged pull requests for GitHub projects from links obtained from Overview page.
    """
    BEFORE_14_DAYS = datetime.today() - timedelta(days=14)

    # Get list of GitHub projects from Overview page
    services_links = routes.overview_page.get_services_links()
    github_projects = get_repos_info(services_links, config.GITHUB_PATTERN)

    pull_requests = {}
    # Download merged pull requests
    for owner, repo_name in github_projects:
        url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
        params = {"state": "closed"}

        try:
            response = requests.get(url, params=params, headers=GITHUB_HEADERS)
            response.raise_for_status()

            json_data = response.json()
            pull_requests[repo_name] = process_merged_pull_requests(
                json_data, BEFORE_14_DAYS
            )

        except Exception as err:
            if response.status_code == 401:
                flash("401 Unauthorized: GitHub data not updated.", category="danger")
            else:
                flash(f"Unexpecter error occured: {err}", category="danger")
            break

    else:
        return save_json_data_and_return(pull_requests, config.GITHUB_MERGED_PR_LIST)

    return load_json_data(config.GITHUB_MERGED_PR_LIST)


def process_open_pull_requests(data):
    return [
        {
            "number": f'PR#{pr["number"]}',
            "draft": pr["draft"],
            "title": pr["title"],
            "created_at": pr["created_at"],
            "user_login": pr["user"]["login"],
            "html_url": pr["html_url"],
        }
        for pr in data
    ]


def process_merged_pull_requests(data, before):
    merged_pull_requests = []
    for pr in data:
        if not pr["merged_at"]:
            continue

        merged_at_as_datetime = datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
        if before < merged_at_as_datetime:
            merged_pull_requests.append(
                {
                    "number": f'PR#{pr["number"]}',
                    "title": pr["title"],
                    "merged_at": pr["merged_at"],
                    "user_login": pr["user"]["login"],
                    "html_url": pr["html_url"],
                }
            )
    return merged_pull_requests
