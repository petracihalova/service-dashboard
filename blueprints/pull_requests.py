import json
import logging
from datetime import datetime, timedelta, timezone

from flask import Blueprint, render_template, request

import config
from services import github_service, gitlab_service

logger = logging.getLogger(__name__)
pull_requests_bp = Blueprint("pull_requests", __name__)


@pull_requests_bp.route("/open")
def open_pull_requests():
    """Open pull requests page."""
    reload_data = "reload_data" in request.args
    open_pr_list = get_github_open_pr(reload_data) | get_gitlab_open_pr(reload_data)
    sort_pr_list_by(open_pr_list, "created_at")

    count = get_prs_count(open_pr_list)

    return render_template(
        "pull_requests/open_pr.html",
        open_pr_list=open_pr_list,
        count=count,
    )


@pull_requests_bp.route("/merged")
def merged_pull_requests():
    """
    Merged pull requests page.
    Download and/or display merged pull requests within the last X days.
    We cache the data in a file, so we don't need to download it every time
    or we download only the missing data.
    """
    reload_data = "reload_data" in request.args

    merged_pr_list = get_all_merged_pr(reload_data)
    merged_pr_list_in_last_X_days = filter_prs_merged_in_last_X_days(merged_pr_list)

    count = get_prs_count(merged_pr_list_in_last_X_days)

    return render_template(
        "pull_requests/merged_pr.html",
        merged_pr_list=merged_pr_list_in_last_X_days,
        merged_in_last_X_days=config.MERGED_IN_LAST_X_DAYS,
        count=count,
    )


def get_prs_count(pr_list):
    """Return the total number of pull requests in the given pr_list dict."""
    return sum(len(pulls) for pulls in pr_list.values())


def get_all_merged_pr(reload_data):
    """Get all merged pull requests from GitHub and GitLab."""
    return get_github_merged_pr(reload_data).get("data") | get_gitlab_merged_pr(
        reload_data
    ).get("data")


def filter_prs_merged_in_last_X_days(pr_list):
    """Get pull/merge requests merged in last X days according configuration."""
    days = config.MERGED_IN_LAST_X_DAYS
    date_X_days_ago = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%d"
    )
    merged_in_last_x_days = {}
    for repo_name, pulls in pr_list.items():
        merged_in_last_x_days[repo_name] = []
        for pr in pulls:
            try:
                if pr.get("merged_at") >= date_X_days_ago:
                    merged_in_last_x_days[repo_name].append(pr)
            except Exception as err:
                logger.error(err)

    return merged_in_last_x_days


def get_github_open_pr(reload_data):
    """Get GitHub open pull requests from a file or download new data."""
    if config.GITHUB_TOKEN:
        if not config.GH_OPEN_PR_FILE.is_file() or reload_data:
            github_api = github_service.GithubAPI()
            return github_api.get_open_pull_requests()
    else:
        if not config.GH_OPEN_PR_FILE.is_file():
            return {}
    with open(config.GH_OPEN_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_gitlab_open_pr(reload_data):
    """Get GitLab open pull requests from a file or download new data."""
    if config.GITLAB_TOKEN:
        if not config.GL_OPEN_PR_FILE.is_file() or reload_data:
            try:
                gitlab_api = gitlab_service.GitlabAPI()
                return gitlab_api.get_open_merge_requests()
            except Exception as err:
                logger.error(err)
    else:
        if not config.GL_OPEN_PR_FILE.is_file():
            return {}

    with open(config.GL_OPEN_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_github_merged_pr(reload_data):
    """Get GitHub merged pull requests from a file or download new data."""

    if not config.GITHUB_TOKEN:
        # TODO: add a message to the user that the GITHUB_TOKEN is not set
        return {}

    if not config.GH_MERGED_PR_FILE.is_file():
        return github_service.GithubAPI().get_merged_pull_requests(scope="all")

    if reload_data:
        return github_service.GithubAPI().get_merged_pull_requests(scope="missing")

    with open(config.GH_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
        data = json.load(file)
        timestamp = data.get("timestamp")
        # If you see the timestamp to "test", it means that the data is broken,
        # so we need to download the new data.
        if timestamp == "test":
            return github_service.GithubAPI().get_merged_pull_requests(scope="all")
        return data


def get_gitlab_merged_pr(reload_data):
    """Get GitLab merged pull requests from a file or download new data."""
    if config.GITLAB_TOKEN:
        if not config.GL_MERGED_PR_FILE.is_file():
            try:
                gitlab_api = gitlab_service.GitlabAPI()
                return gitlab_api.get_merged_merge_requests(scope="all")
            except Exception as err:
                logger.error(err)
        if reload_data:
            try:
                gitlab_api = gitlab_service.GitlabAPI()
                return gitlab_api.get_merged_merge_requests(scope="missing")
            except Exception as err:
                logger.error(err)
    else:
        if not config.GL_MERGED_PR_FILE.is_file():
            return {}

    with open(config.GL_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def sort_pr_list_by(open_pr_list, sort_by):
    for pr_list in open_pr_list.values():
        pr_list.sort(key=lambda x: x[sort_by], reverse=True)
