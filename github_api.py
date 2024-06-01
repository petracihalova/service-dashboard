import json
from datetime import datetime, timedelta

import requests
from flask import flash

import config
import routes.overview_page
from utils import get_repos_info

BEFORE_14_DAYS = datetime.today() - timedelta(days=14)


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
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {config.GITHUB_TOKEN}",
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
                flash(
                    "401 Unauthorized: GitHub data not updated. Check the GitHub token.",
                    category="danger",
                )
                break

            response.raise_for_status()

        except Exception as err:
            flash(f"Unexpecter error occured: {err}", category="danger")
            break

    else:
        with open(config.GITHUB_PR_LIST, mode="w", encoding="utf-8") as f:
            json.dump(pull_requests, f, indent=4)
        return pull_requests

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

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        }

        try:
            response = requests.get(url, params=params, headers=headers)

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
                                    "number": pr["number"],
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

            response.raise_for_status()

        except Exception as err:
            flash(f"Unexpecter error occured: {err}", category="danger")
            break

    else:
        with open(config.GITHUB_MERGED_PR_LIST, mode="w", encoding="utf-8") as f:
            json.dump(pull_requests, f, indent=4)
        return pull_requests

    if config.GITHUB_MERGED_PR_LIST.is_file():
        with open(config.GITHUB_MERGED_PR_LIST, mode="r", encoding="utf-8") as file:
            return json.load(file)
    return pull_requests
