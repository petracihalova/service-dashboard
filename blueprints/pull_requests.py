import json
import logging

from flask import Blueprint, render_template, request

import config
from services import github_service, gitlab_service
from utils import is_older_than_six_months

logger = logging.getLogger(__name__)
pull_requests_bp = Blueprint("pull_requests", __name__)


@pull_requests_bp.route("/open")
def open_pull_requests():
    """Open pull requests page."""
    reload_data = "reload_data" in request.args
    open_pr_list = get_github_open_pr(reload_data) | get_gitlab_open_pr(reload_data)
    sort_pr_list_by(open_pr_list, "created_at")

    count = sum([len(pulls) for pulls in open_pr_list.values()])

    return render_template(
        "pull_requests/open_pr.html",
        open_pr_list=open_pr_list,
        is_older_than_six_months=is_older_than_six_months,
        count=count,
    )


@pull_requests_bp.route("/merged")
def merged_pull_requests():
    """Merged pull requests page."""
    reload_data = "reload_data" in request.args
    merged_pr_list = get_github_merged_pr(reload_data) | get_gitlab_merged_pr(
        reload_data
    )

    count = sum([len(pulls) for pulls in merged_pr_list.values()])

    return render_template(
        "pull_requests/merged_pr.html",
        merged_pr_list=merged_pr_list,
        is_older_than_six_months=is_older_than_six_months,
        merged_in_last_X_days=config.MERGED_IN_LAST_X_DAYS,
        count=count,
    )


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
    """Get GitLub open pull requests from a file or download new data."""
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
    if config.GITHUB_TOKEN:
        if not config.GH_MERGED_PR_FILE.is_file() or reload_data:
            github_api = github_service.GithubAPI()
            return github_api.get_merged_pull_requests(
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
            try:
                gitlab_api = gitlab_service.GitlabAPI()
                return gitlab_api.get_merged_merge_requests(
                    days=config.MERGED_IN_LAST_X_DAYS
                )
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
