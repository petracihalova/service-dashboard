import json

from flask import Blueprint, render_template, request

import config
from services import github_service, gitlab_service
from utils import is_older_than_six_months

pull_requests_bp = Blueprint("pull_requests", __name__)
github_service = github_service.GithubAPI()


@pull_requests_bp.route("/open")
def open_pull_requests():
    """Open pull requests page."""
    reload_data = "reload_data" in request.args
    open_pr_list = get_github_open_pr(reload_data) | get_gitlab_open_pr(reload_data)
    sort_pr_list_by(open_pr_list, "created_at")

    return render_template(
        "pull_requests/open_pr.html",
        open_pr_list=open_pr_list,
        is_older_than_six_months=is_older_than_six_months,
    )


@pull_requests_bp.route("/merged")
def merged_pull_requests():
    """Merged pull requests page."""
    reload_data = "reload_data" in request.args
    merged_pr_list = get_github_merged_pr(reload_data) | get_gitlab_merged_pr(
        reload_data
    )
    sort_pr_list_by(merged_pr_list, "merged_at")

    return render_template(
        "pull_requests/merged_pr.html",
        merged_pr_list=merged_pr_list,
        is_older_than_six_months=is_older_than_six_months,
        merged_in_last_X_days=config.MERGED_IN_LAST_X_DAYS,
    )


def get_github_open_pr(reload_data):
    """Get GitHub open pull requests from a file or download new data."""
    if config.GITHUB_TOKEN:
        if not config.GH_OPEN_PR_FILE.is_file() or reload_data:
            return github_service.get_open_pull_requests()
    else:
        if not config.GH_OPEN_PR_FILE.is_file():
            return {}
    with open(config.GH_OPEN_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_gitlab_open_pr(reload_data):
    """Get GitLub open pull requests from a file or download new data."""
    if config.GITLAB_TOKEN:
        if not config.GL_OPEN_PR_FILE.is_file() or reload_data:
            return gitlab_service.get_open_merge_request()
    else:
        if not config.GL_OPEN_PR_FILE.is_file():
            return {}

    with open(config.GL_OPEN_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_github_merged_pr(reload_data):
    """Get GitHub merged pull requests from a file or download new data."""
    if config.GITHUB_TOKEN:
        if not config.GH_MERGED_PR_FILE.is_file() or reload_data:
            return github_service.get_merged_pull_requests(
                days=config.MERGED_IN_LAST_X_DAYS
            )
    else:
        if not config.GH_MERGED_PR_FILE.is_file():
            return {}

    with open(config.GH_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_gitlab_merged_pr(reload_data):
    """Get GitLab merged pull requests from a file or download new data."""
    if config.GITLAB_TOKEN:
        if not config.GL_MERGED_PR_FILE.is_file() or reload_data:
            return gitlab_service.get_merged_merge_request(
                days=config.MERGED_IN_LAST_X_DAYS
            )
    else:
        if not config.GL_MERGED_PR_FILE.is_file():
            return {}

    with open(config.GL_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def sort_pr_list_by(open_pr_list, sort_by):
    for pr_list in open_pr_list.values():
        pr_list.sort(key=lambda x: x[sort_by], reverse=True)
