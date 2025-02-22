import json

from flask import Blueprint, render_template, request

import config
from services import github_service, gitlab_service


pull_requests_bp = Blueprint("pull_requests", __name__)
github_service = github_service.GithubAPI()


@pull_requests_bp.route("/open")
def open_pull_requests():
    """Open pull requests page."""
    reload_data = "reload_data" in request.args
    github_open_pr = get_github_open_pr(reload_data)
    gitlab_open_pr = get_gitlab_open_pr(reload_data)
    open_pr_list = github_open_pr | gitlab_open_pr

    return render_template("pull_requests/open_pr.html", open_pr_list=open_pr_list)


@pull_requests_bp.route("/merged")
def merged_pull_requests():
    """Merged pull requests page."""
    reload_data = "reload_data" in request.args
    github_merged_pr = get_github_merged_pr(reload_data)
    gitlab_merged_pr = get_gitlab_merged_pr(reload_data)
    merged_pr_list = github_merged_pr | gitlab_merged_pr
    return render_template(
        "pull_requests/merged_pr.html", merged_pr_list=merged_pr_list
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
            return github_service.get_merged_pull_requests(days=14)
    else:
        if not config.GH_MERGED_PR_FILE.is_file():
            return {}

    with open(config.GH_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_gitlab_merged_pr(reload_data):
    """Get GitLab merged pull requests from a file or download new data."""
    if config.GITLAB_TOKEN:
        if not config.GL_MERGED_PR_FILE.is_file() or reload_data:
            return gitlab_service.get_merged_merge_request(days=14)
    else:
        if not config.GL_MERGED_PR_FILE.is_file():
            return {}

    with open(config.GL_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)
