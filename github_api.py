import json
from datetime import datetime, timedelta

import requests
from flask import flash

import config
import routes.overview_page
from utils import get_repos_info

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

            if response.status_code == 200:
                json_data = response.json()
                pull_requests[repo_name] = process_open_pull_requests(json_data)

            elif response.status_code == 401:
                flash(
                    "401 Unauthorized: GitHub data not updated. Check the GitHub token.",
                    category="danger",
                )
                break

        except Exception as err:
            flash(f"Unexpecter error occured: {err}", category="danger")
            break

    else:
        return save_json_data_and_return(pull_requests, config.GITHUB_PR_LIST)

    if config.GITHUB_PR_LIST.is_file():
        with open(config.GITHUB_PR_LIST, mode="r", encoding="utf-8") as file:
            return json.load(file)
    return pull_requests


def get_merged_pull_request():
    """
    Get merged pull requests for GitHub projects from links obtained from Overview page.
    """
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

            if response.status_code == 200:
                json_data = response.json()
                if not json_data:
                    pull_requests[repo_name] = []
                else:
                    merged_pr_list = []
                    for pr in json_data:
                        if not pr["merged_at"]:
                            continue
                        merged_at_as_datetime = datetime.strptime(
                            pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ"
                        )
                        if BEFORE_14_DAYS < merged_at_as_datetime:
                            merged_pr_list.append(
                                {
                                    "number": f'PR#{pr["number"]}',
                                    "title": pr["title"],
                                    "merged_at": pr["merged_at"],
                                    "user_login": pr["user"]["login"],
                                    "html_url": pr["html_url"],
                                }
                            )
                    pull_requests[repo_name] = merged_pr_list

            elif response.status_code == 401:
                flash(
                    "401 Unauthorized: GitHub data not updated. Check the GitHub token.",
                    category="danger",
                )
                break

        except Exception as err:
            flash(f"Unexpecter error occured: {err}", category="danger")
            break

    else:
        return save_json_data_and_return(pull_requests, config.GITHUB_MERGED_PR_LIST)

    if config.GITHUB_MERGED_PR_LIST.is_file():
        with open(config.GITHUB_MERGED_PR_LIST, mode="r", encoding="utf-8") as file:
            return json.load(file)
    return pull_requests


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


def save_json_data_and_return(data, filename):
    """
    Saves data as a json file and returns the data.
    """
    with open(filename, mode="w", encoding="utf-8") as file:
        json.dump(data, file, indent=4)
    return data
