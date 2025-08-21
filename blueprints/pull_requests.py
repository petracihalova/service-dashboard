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
    """
    Open pull requests page.
    Download and/or display open pull requests.
    We cache the data in a file, so we don't need to download it every time.
    """
    reload_data = "reload_data" in request.args

    # Get username filter parameters
    filter_username = request.args.get("username", "").strip()
    show_my_prs_only = request.args.get("my_prs", "").lower() == "true"

    logger.info(
        f"Open PRs page accessed with reload_data={reload_data}, filter_username='{filter_username}', show_my_prs_only={show_my_prs_only}"
    )

    open_pr_list = get_github_open_pr(reload_data) | get_gitlab_open_pr(reload_data)
    sort_pr_list_by(open_pr_list, "created_at")

    # Apply username filtering if requested
    if filter_username:
        # Filter by custom username - this overrides "My PRs" if both are somehow present
        open_pr_list = filter_prs_by_username(open_pr_list, filter_username)
    elif show_my_prs_only:
        # Filter by configured usernames (GITHUB_USERNAME for GitHub, GITLAB_USERNAME for GitLab)
        open_pr_list = filter_prs_by_configured_usernames(open_pr_list)

    count = get_prs_count(open_pr_list)

    return render_template(
        "pull_requests/open_pr.html",
        open_pr_list=open_pr_list,
        github_username=config.GITHUB_USERNAME,
        gitlab_username=config.GITLAB_USERNAME,
        filter_username=filter_username,
        show_my_prs_only=show_my_prs_only,
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

    # Get custom days parameter from URL, default to config value
    try:
        custom_days = int(
            request.args.get("days", config.DEFAULT_MERGED_IN_LAST_X_DAYS)
        )
        # Validate reasonable range
        if custom_days < 1 or custom_days > 10000:
            custom_days = config.DEFAULT_MERGED_IN_LAST_X_DAYS
    except (ValueError, TypeError):
        custom_days = config.DEFAULT_MERGED_IN_LAST_X_DAYS

    # Get username filter parameters
    filter_username = request.args.get("username", "").strip()
    show_my_prs_only = request.args.get("my_prs", "").lower() == "true"

    merged_pr_list = get_github_merged_pr(reload_data) | get_gitlab_merged_pr(
        reload_data
    )
    merged_pr_list_in_last_X_days = filter_prs_merged_in_last_X_days(
        merged_pr_list, custom_days
    )

    # Apply username filtering if requested
    if filter_username:
        # Filter by custom username - this overrides "My PRs" if both are somehow present
        merged_pr_list_in_last_X_days = filter_prs_by_username(
            merged_pr_list_in_last_X_days, filter_username
        )
    elif show_my_prs_only:
        # Filter by configured usernames (GITHUB_USERNAME for GitHub, GITLAB_USERNAME for GitLab)
        merged_pr_list_in_last_X_days = filter_prs_by_configured_usernames(
            merged_pr_list_in_last_X_days
        )

    count = get_prs_count(merged_pr_list_in_last_X_days)

    return render_template(
        "pull_requests/merged_pr.html",
        merged_pr_list=merged_pr_list_in_last_X_days,
        merged_in_last_X_days=custom_days,
        github_username=config.GITHUB_USERNAME,
        gitlab_username=config.GITLAB_USERNAME,
        filter_username=filter_username,
        show_my_prs_only=show_my_prs_only,
        count=count,
    )


def get_prs_count(pr_list):
    """Return the total number of pull requests in the given pr_list dict."""
    return sum(len(pulls) for pulls in pr_list.values())


def filter_prs_merged_in_last_X_days(pr_list, days=None):
    """Get pull/merge requests merged in last X days according configuration."""
    if days is None:
        days = config.DEFAULT_MERGED_IN_LAST_X_DAYS

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


def filter_prs_by_username(pr_list, username):
    """Filter pull requests by username (case-insensitive)."""
    if not username:
        return pr_list

    username_lower = username.lower()
    filtered_prs = {}

    for repo_name, pulls in pr_list.items():
        filtered_pulls = []
        for pr in pulls:
            # Check if the username matches (case-insensitive)
            pr_username = pr.get("user_login", "").lower()
            if username_lower in pr_username:
                filtered_pulls.append(pr)

        # Only include repos that have matching PRs
        if filtered_pulls:
            filtered_prs[repo_name] = filtered_pulls

    return filtered_prs


def filter_prs_by_configured_usernames(pr_list):
    """Filter pull requests by GITHUB_USERNAME for GitHub PRs and GITLAB_USERNAME for GitLab PRs."""
    if not config.GITHUB_USERNAME and not config.GITLAB_USERNAME:
        return pr_list

    filtered_prs = {}

    for repo_name, pulls in pr_list.items():
        filtered_pulls = []
        for pr in pulls:
            pr_url = pr.get("html_url", "")
            pr_username = pr.get("user_login", "")

            # Determine if PR is from GitHub or GitLab based on URL
            if "github.com" in pr_url and config.GITHUB_USERNAME:
                # GitHub PR - check against GITHUB_USERNAME
                if pr_username.lower() == config.GITHUB_USERNAME.lower():
                    filtered_pulls.append(pr)
            elif "gitlab" in pr_url and config.GITLAB_USERNAME:
                # GitLab MR - check against GITLAB_USERNAME
                if pr_username.lower() == config.GITLAB_USERNAME.lower():
                    filtered_pulls.append(pr)

        # Only include repos that have matching PRs
        if filtered_pulls:
            filtered_prs[repo_name] = filtered_pulls

    return filtered_prs


def get_github_open_pr(reload_data):
    """Get GitHub open pull requests from a file or download new data."""
    logger.info(
        f"get_github_open_pr called with reload_data={reload_data}, file_exists={config.GH_OPEN_PR_FILE.is_file()}"
    )

    if not config.GITHUB_TOKEN:
        # TODO: add a message to the user that the GITHUB_TOKEN is not set
        return {}

    if not config.GH_OPEN_PR_FILE.is_file() or reload_data:
        return github_service.GithubAPI().get_open_pull_request_with_graphql()

    with open(config.GH_OPEN_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_gitlab_open_pr(reload_data):
    """Get GitLab open pull requests from a file or download new data."""
    logger.info(
        f"get_gitlab_open_pr called with reload_data={reload_data}, file_exists={config.GL_OPEN_PR_FILE.is_file()}"
    )

    if not config.GITLAB_TOKEN:
        # TODO: add a message to the user that the GITLAB_TOKEN is not set
        return {}

    if not config.GL_OPEN_PR_FILE.is_file():
        logger.info("Downloading new GitLab open MRs data")
        try:
            return gitlab_service.GitlabAPI().get_open_merge_requests()
        except Exception as err:
            logger.error(err)
            # Return empty dict if download fails
            return {}

    if reload_data:
        logger.info("Downloading new GitLab open MRs data")
        try:
            return gitlab_service.GitlabAPI().get_open_merge_requests()
        except Exception as err:
            logger.error(err)
            # Continue with the cached data
            pass

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
        return data.get("data")


def get_gitlab_merged_pr(reload_data):
    """Get GitLab merged pull requests from a file or download new data."""
    if not config.GITLAB_TOKEN:
        # TODO: add a message to the user that the GITLAB_TOKEN is not set
        return {}

    if not config.GL_MERGED_PR_FILE.is_file():
        try:
            return gitlab_service.GitlabAPI().get_merged_merge_requests(scope="all")
        except Exception as err:
            # TODO: add a message for user (VPN not on)
            logger.error(err)

    if reload_data:
        try:
            return gitlab_service.GitlabAPI().get_merged_merge_requests(scope="missing")
        except Exception as err:
            # TODO: add a message for user (VPN not on)
            logger.error(err)

    with open(config.GL_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
        data = json.load(file)
        timestamp = data.get("timestamp")
        # If you see the timestamp to "test", it means that the data is broken,
        # so we need to download the new data.
        if timestamp == "test":
            return gitlab_service.GitlabAPI().get_merged_merge_requests(scope="all")
        return data.get("data")


def sort_pr_list_by(open_pr_list, sort_by):
    for pr_list in open_pr_list.values():
        pr_list.sort(key=lambda x: x[sort_by], reverse=True)
