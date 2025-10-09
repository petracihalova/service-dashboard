import json
import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import gitlab
import requests
from flask import Blueprint, flash, render_template, request

import config
from services import github_service, gitlab_service
from utils import load_json_data, helpers

logger = logging.getLogger(__name__)
pull_requests_bp = Blueprint("pull_requests", __name__)


@pull_requests_bp.route("/open")
def open_pull_requests():
    """
    Open pull requests page.
    Download and/or display open pull requests.
    We cache the data in a file, so we don't need to download it every time.
    """
    if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "add_me":
        flash("GITHUB_TOKEN is not set", "warning")
        return render_template("errors/github_token_not_set.html")

    reload_data = "reload_data" in request.args

    filter_username = request.args.get("username", "").strip()
    show_my_prs_only = request.args.get("my_prs", "").lower() == "true"

    # Get source filter parameter (github, gitlab, both) - default to both
    source_filter = request.args.get("source", "both").lower()
    if source_filter not in ["github", "gitlab", "both"]:
        source_filter = "both"

    # Get organization filter parameter
    organization_filter = request.args.get("organization", "").strip()

    logger.info(
        f"Open PRs page accessed with reload_data={reload_data}, filter_username='{filter_username}', show_my_prs_only={show_my_prs_only}, source_filter={source_filter}, organization_filter='{organization_filter}'"
    )

    # Get data based on source filter
    if source_filter == "github":
        open_pr_list = get_github_open_pr(reload_data)
    elif source_filter == "gitlab":
        open_pr_list = get_gitlab_open_pr(reload_data)
    else:  # both
        open_pr_list = get_github_open_pr(reload_data) | get_gitlab_open_pr(reload_data)
    sort_pr_list_by(open_pr_list, "created_at")

    # Get all available organizations for the dropdown (before filtering)
    available_organizations = get_unique_organizations_from_prs(open_pr_list)

    # Apply filters in sequence
    if filter_username:
        open_pr_list = filter_prs_by_username(open_pr_list, filter_username)
    elif show_my_prs_only:
        open_pr_list = filter_prs_by_configured_usernames(open_pr_list)

    if organization_filter:
        open_pr_list = filter_prs_by_organization(open_pr_list, organization_filter)

    count = get_prs_count(open_pr_list)

    # Check if data files exist for template warning
    github_file_exists = config.GH_OPEN_PR_FILE.is_file()
    gitlab_file_exists = config.GL_OPEN_PR_FILE.is_file()

    return render_template(
        "pull_requests/open_pr.html",
        open_pr_list=open_pr_list,
        github_username=config.GITHUB_USERNAME,
        gitlab_username=config.GITLAB_USERNAME,
        filter_username=filter_username,
        show_my_prs_only=show_my_prs_only,
        source_filter=source_filter,
        organization_filter=organization_filter,
        available_organizations=available_organizations,
        count=count,
        github_file_exists=github_file_exists,
        gitlab_file_exists=gitlab_file_exists,
    )


@pull_requests_bp.route("/merged")
def merged_pull_requests():
    """
    Merged pull requests page.
    Download and/or display merged pull requests within the last X days.
    We cache the data in a file, so we don't need to download it every time
    or we download only the missing data.
    """
    if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "add_me":
        flash("GITHUB_TOKEN is not set", "warning")
        return render_template("errors/github_token_not_set.html")

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

    # Get date range parameters
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Track if date_to was auto-set to today
    date_to_auto_set = False

    # If only date_from is provided, default date_to to today
    if date_from and not date_to:
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_to_auto_set = True
        logger.debug(f"Auto-setting date_to to today: {date_to}")

    # Get username filter parameters
    filter_username = request.args.get("username", "").strip()
    show_my_prs_only = request.args.get("my_prs", "").lower() == "true"

    # Get source filter parameter (github, gitlab, both) - default to both
    source_filter = request.args.get("source", "both").lower()
    if source_filter not in ["github", "gitlab", "both"]:
        source_filter = "both"

    # Get organization filter parameter
    organization_filter = request.args.get("organization", "").strip()

    # Get data based on source filter
    if source_filter == "github":
        merged_pr_list = get_github_merged_pr(reload_data)
    elif source_filter == "gitlab":
        merged_pr_list = get_gitlab_merged_pr(reload_data)
    else:  # both
        merged_pr_list = get_github_merged_pr(reload_data) | get_gitlab_merged_pr(
            reload_data
        )

    # Apply date filtering - date range takes precedence over days filter
    if date_from and date_to:
        merged_pr_list_filtered = filter_prs_by_date_range(
            merged_pr_list, date_from, date_to
        )
    else:
        merged_pr_list_filtered = filter_prs_merged_in_last_X_days(
            merged_pr_list, custom_days
        )
        # When using default "last X days" behavior, set the actual date range for display consistency
        if not date_from and not date_to:
            today = datetime.now()
            # For "last X days including today", subtract (X-1) days from today
            date_from = (today - timedelta(days=custom_days - 1)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
            date_to_auto_set = True

    # Get all available organizations for the dropdown (before filtering)
    available_organizations = get_unique_organizations_from_prs(merged_pr_list_filtered)

    # Apply username filtering if requested
    if filter_username:
        # Filter by custom username - this overrides "My PRs" if both are somehow present
        merged_pr_list_filtered = filter_prs_by_username(
            merged_pr_list_filtered, filter_username
        )
    elif show_my_prs_only:
        # Filter by configured usernames (GITHUB_USERNAME for GitHub, GITLAB_USERNAME for GitLab)
        merged_pr_list_filtered = filter_prs_by_configured_usernames(
            merged_pr_list_filtered
        )

    # Apply organization filtering if requested
    if organization_filter:
        merged_pr_list_filtered = filter_prs_by_organization(
            merged_pr_list_filtered, organization_filter
        )

    count = get_prs_count(merged_pr_list_filtered)

    # Check if data files exist for template warning
    github_merged_file_exists = config.GH_MERGED_PR_FILE.is_file()
    gitlab_merged_file_exists = config.GL_MERGED_PR_FILE.is_file()

    return render_template(
        "pull_requests/merged_pr.html",
        merged_pr_list=merged_pr_list_filtered,
        merged_in_last_X_days=custom_days,
        date_from=date_from,
        date_to=date_to,
        date_to_auto_set=date_to_auto_set,
        github_username=config.GITHUB_USERNAME,
        gitlab_username=config.GITLAB_USERNAME,
        filter_username=filter_username,
        show_my_prs_only=show_my_prs_only,
        source_filter=source_filter,
        organization_filter=organization_filter,
        available_organizations=available_organizations,
        count=count,
        github_merged_file_exists=github_merged_file_exists,
        gitlab_merged_file_exists=gitlab_merged_file_exists,
    )


@pull_requests_bp.route("/closed")
def closed_pull_requests():
    """
    Closed pull requests page.
    Download and/or display closed pull requests within the last X days.
    We cache the data in a file, so we don't need to download it every time
    or we download only the missing data.
    """
    if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "add_me":
        flash("GITHUB_TOKEN is not set", "warning")
        return render_template("errors/github_token_not_set.html")

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

    # Get date range parameters
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Track if date_to was auto-set to today
    date_to_auto_set = False

    # If only date_from is provided, default date_to to today
    if date_from and not date_to:
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_to_auto_set = True
        logger.debug(f"Auto-setting date_to to today: {date_to}")

    # Get username filter parameters
    filter_username = request.args.get("username", "").strip()
    show_my_prs_only = request.args.get("my_prs", "").lower() == "true"

    # Get source filter parameter (github, gitlab, both) - default to both
    source_filter = request.args.get("source", "both").lower()
    if source_filter not in ["github", "gitlab", "both"]:
        source_filter = "both"

    # Get organization filter parameter
    organization_filter = request.args.get("organization", "").strip()

    # Get data based on source filter
    if source_filter == "github":
        closed_pr_list = get_github_closed_pr(reload_data)
    elif source_filter == "gitlab":
        closed_pr_list = get_gitlab_closed_pr(reload_data)
    else:  # both
        closed_pr_list = get_github_closed_pr(reload_data) | get_gitlab_closed_pr(
            reload_data
        )

    # Apply date filtering - date range takes precedence over days filter
    if date_from and date_to:
        closed_pr_list_filtered = filter_prs_by_date_range_closed(
            closed_pr_list, date_from, date_to
        )
    else:
        closed_pr_list_filtered = filter_prs_closed_in_last_X_days(
            closed_pr_list, custom_days
        )
        # When using default "last X days" behavior, set the actual date range for display consistency
        if not date_from and not date_to:
            today = datetime.now()
            # For "last X days including today", subtract (X-1) days from today
            date_from = (today - timedelta(days=custom_days - 1)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
            date_to_auto_set = True

    # Get all available organizations for the dropdown (before filtering)
    available_organizations = get_unique_organizations_from_prs(closed_pr_list_filtered)

    # Apply username filtering if requested
    if filter_username:
        # Filter by custom username - this overrides "My PRs" if both are somehow present
        closed_pr_list_filtered = filter_prs_by_username(
            closed_pr_list_filtered, filter_username
        )
    elif show_my_prs_only:
        # Filter by configured usernames (GITHUB_USERNAME for GitHub, GITLAB_USERNAME for GitLab)
        closed_pr_list_filtered = filter_prs_by_configured_usernames(
            closed_pr_list_filtered
        )

    # Apply organization filtering if requested
    if organization_filter:
        closed_pr_list_filtered = filter_prs_by_organization(
            closed_pr_list_filtered, organization_filter
        )

    count = get_prs_count(closed_pr_list_filtered)

    # Check if data files exist for template warning
    github_closed_file_exists = config.GH_CLOSED_PR_FILE.is_file()
    gitlab_closed_file_exists = config.GL_CLOSED_PR_FILE.is_file()

    return render_template(
        "pull_requests/closed_pr.html",
        closed_pr_list=closed_pr_list_filtered,
        closed_in_last_X_days=custom_days,
        date_from=date_from,
        date_to=date_to,
        date_to_auto_set=date_to_auto_set,
        github_username=config.GITHUB_USERNAME,
        gitlab_username=config.GITLAB_USERNAME,
        filter_username=filter_username,
        show_my_prs_only=show_my_prs_only,
        source_filter=source_filter,
        organization_filter=organization_filter,
        available_organizations=available_organizations,
        count=count,
        github_closed_file_exists=github_closed_file_exists,
        gitlab_closed_file_exists=gitlab_closed_file_exists,
    )


@pull_requests_bp.route("/app-interface")
def app_interface_open_merge_requests():
    """
    App-interface open merge requests page.
    Display open merge requests from app-interface repository
    filtered by users from APP_INTERFACE_USERS configuration.
    """
    if not config.GITLAB_TOKEN or config.GITLAB_TOKEN == "add_me":
        flash("GITLAB_TOKEN is not set", "warning")
        return render_template("errors/gitlab_token_not_set.html")

    if not config.APP_INTERFACE_USERS or config.APP_INTERFACE_USERS == ["add_me"]:
        flash("APP_INTERFACE_USERS is not set", "warning")
        return render_template("errors/app_interface_users_not_set.html")

    reload_data = "reload_data" in request.args
    show_my_mrs_only = request.args.get("my_mrs", "").lower() == "true"

    # Get username filter parameters
    filter_username = request.args.get("username", "").strip()

    logger.info(
        f"App-interface open MRs page accessed with reload_data={reload_data}, show_my_mrs_only={show_my_mrs_only}, filter_username={filter_username}"
    )

    # Get App-interface open MRs
    open_mrs = get_app_interface_open_mr(reload_data)

    # Apply username filtering if requested
    if filter_username:
        # Filter by custom username - this overrides "My MRs" if both are somehow present
        # Check if filter_username is a substring of the actual username
        open_mrs = [
            mr
            for mr in open_mrs
            if filter_username.lower() in mr.get("user_login", "").lower()
        ]
    elif show_my_mrs_only and config.GITLAB_USERNAME:
        # Apply "My MRs" filtering if no custom username filter
        open_mrs = [
            mr
            for mr in open_mrs
            if mr.get("user_login", "").lower() == config.GITLAB_USERNAME.lower()
        ]

    count = len(open_mrs)

    # Check if data file exists for template warning
    app_interface_file_exists = config.APP_INTERFACE_OPEN_MR_FILE.is_file()

    return render_template(
        "pull_requests/app_interface_open.html",
        open_pr_list=open_mrs,
        count=count,
        app_interface_users=config.APP_INTERFACE_USERS,
        gitlab_username=config.GITLAB_USERNAME,
        filter_username=filter_username,
        show_my_mrs_only=show_my_mrs_only,
        app_interface_file_exists=app_interface_file_exists,
    )


@pull_requests_bp.route("/app-interface-merged")
def app_interface_merged_merge_requests():
    """
    App-interface merged merge requests page.
    Display merged merge requests from app-interface repository
    filtered by users from APP_INTERFACE_USERS configuration.
    """
    if not config.GITLAB_TOKEN or config.GITLAB_TOKEN == "add_me":
        flash("GITLAB_TOKEN is not set", "warning")
        return render_template("errors/gitlab_token_not_set.html")

    if not config.APP_INTERFACE_USERS or config.APP_INTERFACE_USERS == ["add_me"]:
        flash("APP_INTERFACE_USERS is not set", "warning")
        return render_template("errors/app_interface_users_not_set.html")
    reload_data = "reload_data" in request.args
    show_my_mrs_only = request.args.get("my_mrs", "").lower() == "true"

    # Get username filter parameters
    filter_username = request.args.get("username", "").strip()

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

    # Get date range parameters
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Track if date_to was auto-set to today
    date_to_auto_set = False

    # If only date_from is provided, default date_to to today
    if date_from and not date_to:
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_to_auto_set = True
        logger.debug(f"Auto-setting date_to to today: {date_to}")

    logger.info(
        f"App-interface merged MRs page accessed with reload_data={reload_data}, show_my_mrs_only={show_my_mrs_only}, filter_username={filter_username}, days={custom_days}"
    )

    # Get app-interface merged MRs
    merged_mrs = get_app_interface_merged_mr(reload_data)

    # Apply date filtering - date range takes precedence over days filter
    if date_from and date_to:
        merged_mr_filtered = filter_prs_by_date_range(merged_mrs, date_from, date_to)
    else:
        merged_mr_filtered = filter_prs_merged_in_last_X_days(merged_mrs, custom_days)
        # When using default "last X days" behavior, set the actual date range for display consistency
        if not date_from and not date_to:
            today = datetime.now()
            # For "last X days including today", subtract (X-1) days from today
            date_from = (today - timedelta(days=custom_days - 1)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
            date_to_auto_set = True

    # Apply username filtering if requested
    if filter_username:
        # Filter by custom username - this overrides "My MRs" if both are somehow present
        # Check if filter_username is a substring of the actual username
        merged_mr_filtered = [
            mr
            for mr in merged_mr_filtered
            if filter_username.lower() in mr.get("user_login", "").lower()
        ]
    elif show_my_mrs_only and config.GITLAB_USERNAME:
        # Apply "My MRs" filtering if no custom username filter
        merged_mr_filtered = [
            mr
            for mr in merged_mr_filtered
            if mr.get("user_login", "").lower() == config.GITLAB_USERNAME.lower()
        ]

    count = len(merged_mr_filtered)

    # Check if data file exists for template warning
    app_interface_merged_file_exists = config.APP_INTERFACE_MERGED_MR_FILE.is_file()

    return render_template(
        "pull_requests/app_interface_merged.html",
        merged_pr_list=merged_mr_filtered,
        merged_in_last_X_days=custom_days,
        date_from=date_from,
        date_to=date_to,
        date_to_auto_set=date_to_auto_set,
        count=count,
        app_interface_users=config.APP_INTERFACE_USERS,
        gitlab_username=config.GITLAB_USERNAME,
        filter_username=filter_username,
        show_my_mrs_only=show_my_mrs_only,
        app_interface_merged_file_exists=app_interface_merged_file_exists,
    )


@pull_requests_bp.route("/app-interface-closed")
def app_interface_closed_merge_requests():
    """
    App-interface closed merge requests page.
    Display closed merge requests from app-interface repository
    filtered by users from APP_INTERFACE_USERS configuration.
    """
    if not config.GITLAB_TOKEN or config.GITLAB_TOKEN == "add_me":
        flash("GITLAB_TOKEN is not set", "warning")
        return render_template("errors/gitlab_token_not_set.html")

    if not config.APP_INTERFACE_USERS or config.APP_INTERFACE_USERS == ["add_me"]:
        flash("APP_INTERFACE_USERS is not set", "warning")
        return render_template("errors/app_interface_users_not_set.html")

    reload_data = "reload_data" in request.args
    show_my_mrs_only = request.args.get("my_mrs", "").lower() == "true"

    # Get username filter parameters
    filter_username = request.args.get("username", "").strip()

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

    # Get date range parameters
    date_from = request.args.get("date_from", "").strip()
    date_to = request.args.get("date_to", "").strip()

    # Track if date_to was auto-set to today
    date_to_auto_set = False

    # If only date_from is provided, default date_to to today
    if date_from and not date_to:
        date_to = datetime.now().strftime("%Y-%m-%d")
        date_to_auto_set = True
        logger.debug(f"Auto-setting date_to to today: {date_to}")

    logger.info(
        f"App-interface closed MRs page accessed with reload_data={reload_data}, show_my_mrs_only={show_my_mrs_only}, filter_username={filter_username}, days={custom_days}"
    )

    # Get app-interface closed MRs
    closed_mrs = get_app_interface_closed_mr(reload_data)

    # Apply date filtering - date range takes precedence over days filter
    if date_from and date_to:
        closed_mr_filtered = filter_prs_by_date_range_closed(
            closed_mrs, date_from, date_to
        )
    else:
        closed_mr_filtered = filter_prs_closed_in_last_X_days(closed_mrs, custom_days)
        # When using default "last X days" behavior, set the actual date range for display consistency
        if not date_from and not date_to:
            today = datetime.now()
            # For "last X days including today", subtract (X-1) days from today
            date_from = (today - timedelta(days=custom_days - 1)).strftime("%Y-%m-%d")
            date_to = today.strftime("%Y-%m-%d")
            date_to_auto_set = True

    # Apply username filtering if requested
    if filter_username:
        # Filter by custom username - this overrides "My MRs" if both are somehow present
        # Check if filter_username is a substring of the actual username
        closed_mr_filtered = [
            mr
            for mr in closed_mr_filtered
            if filter_username.lower() in mr.get("user_login", "").lower()
        ]
    elif show_my_mrs_only and config.GITLAB_USERNAME:
        # Apply "My MRs" filtering if no custom username filter
        closed_mr_filtered = [
            mr
            for mr in closed_mr_filtered
            if mr.get("user_login", "").lower() == config.GITLAB_USERNAME.lower()
        ]

    count = len(closed_mr_filtered)

    # Check if data file exists for template warning
    app_interface_closed_file_exists = config.APP_INTERFACE_CLOSED_MR_FILE.is_file()

    return render_template(
        "pull_requests/app_interface_closed.html",
        closed_pr_list=closed_mr_filtered,
        closed_in_last_X_days=custom_days,
        date_from=date_from,
        date_to=date_to,
        date_to_auto_set=date_to_auto_set,
        count=count,
        app_interface_users=config.APP_INTERFACE_USERS,
        gitlab_username=config.GITLAB_USERNAME,
        filter_username=filter_username,
        show_my_mrs_only=show_my_mrs_only,
        app_interface_closed_file_exists=app_interface_closed_file_exists,
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
    if isinstance(pr_list, list):
        merged_in_last_x_days = []
        for pr in pr_list:
            if pr.get("merged_at") >= date_X_days_ago:
                merged_in_last_x_days.append(pr)
        return merged_in_last_x_days

    elif isinstance(pr_list, dict):
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

    else:
        raise ValueError(f"Unsupported type: {type(pr_list)}")


def filter_prs_by_date_range(pr_list, date_from, date_to):
    """Get pull/merge requests merged within a specific date range."""
    if not date_from or not date_to:
        return pr_list

    # Ensure date_from is not later than date_to
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    if isinstance(pr_list, list):
        filtered_prs = []
        for pr in pr_list:
            merged_date = pr.get("merged_at", "").split("T")[
                0
            ]  # Get just the date part (YYYY-MM-DD)
            if merged_date and date_from <= merged_date <= date_to:
                filtered_prs.append(pr)
        return filtered_prs

    elif isinstance(pr_list, dict):
        filtered_prs = {}
        for repo_name, pulls in pr_list.items():
            filtered_prs[repo_name] = []
            for pr in pulls:
                try:
                    merged_date = pr.get("merged_at", "").split("T")[
                        0
                    ]  # Get just the date part (YYYY-MM-DD)
                    if merged_date and date_from <= merged_date <= date_to:
                        filtered_prs[repo_name].append(pr)
                except Exception as err:
                    logger.error(err)
                    continue

        return filtered_prs

    else:
        raise ValueError(f"Unsupported type: {type(pr_list)}")


def filter_prs_closed_in_last_X_days(pr_list, days=None):
    """Get pull/merge requests closed in last X days according configuration."""
    if days is None:
        days = config.DEFAULT_MERGED_IN_LAST_X_DAYS

    date_X_days_ago = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%d"
    )
    if isinstance(pr_list, list):
        closed_in_last_x_days = []
        for pr in pr_list:
            try:
                closed_date = pr.get("closed_at", "").split("T")[
                    0
                ]  # Get just the date part (YYYY-MM-DD)
                if closed_date and closed_date >= date_X_days_ago:
                    closed_in_last_x_days.append(pr)
            except Exception as err:
                print(pr)
                logger.error(f"Failed to parse closed_at date for PR: {err}")
                continue
        return closed_in_last_x_days

    elif isinstance(pr_list, dict):
        closed_in_last_x_days = {}
        for repo_name, pulls in pr_list.items():
            closed_in_last_x_days[repo_name] = []
            for pr in pulls:
                try:
                    closed_date = pr.get("closed_at", "").split("T")[
                        0
                    ]  # Get just the date part (YYYY-MM-DD)
                    if closed_date and closed_date >= date_X_days_ago:
                        closed_in_last_x_days[repo_name].append(pr)
                except Exception as err:
                    logger.error(f"Failed to parse closed_at date for PR: {err}")
                    continue
        return closed_in_last_x_days

    else:
        raise ValueError(f"Unsupported type: {type(pr_list)}")


def filter_prs_by_date_range_closed(pr_list, date_from, date_to):
    """Get pull/merge requests closed within a specific date range."""
    if not date_from or not date_to:
        return pr_list

    # Ensure date_from is not later than date_to
    if date_from > date_to:
        date_from, date_to = date_to, date_from

    if isinstance(pr_list, list):
        filtered_prs = []
        for pr in pr_list:
            closed_date = pr.get("closed_at", "")
            if not closed_date:
                closed_date = ""
            closed_date = closed_date.split("T")[
                0
            ]  # Get just the date part (YYYY-MM-DD)
            if closed_date and date_from <= closed_date <= date_to:
                filtered_prs.append(pr)
        return filtered_prs

    elif isinstance(pr_list, dict):
        filtered_prs = {}
        for repo_name, pulls in pr_list.items():
            filtered_prs[repo_name] = []
            for pr in pulls:
                try:
                    closed_date = pr.get("closed_at", "").split("T")[
                        0
                    ]  # Get just the date part (YYYY-MM-DD)
                    if closed_date and date_from <= closed_date <= date_to:
                        filtered_prs[repo_name].append(pr)
                except Exception as err:
                    logger.error(err)
                    continue

        return filtered_prs

    else:
        raise ValueError(f"Unsupported type: {type(pr_list)}")


def filter_prs_by_username(pr_list, username):
    """Filter pull requests by username (case-insensitive)."""
    if not username:
        return pr_list

    username_lower = username.lower()
    filtered_prs = {}

    for repo_name, pulls in pr_list.items():
        filtered_pulls = []
        for pr in pulls:
            pr_username = pr.get("user_login", "").lower()

            # Special case: 'non-konflux' filter excludes konflux users
            if username_lower == "non-konflux":
                if "konflux" not in pr_username:
                    filtered_pulls.append(pr)
            else:
                # Normal username filtering - check if the username matches (case-insensitive)
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

            # Determine if PR is from GitHub or GitLab based on URL hostname
            pr_hostname = urlparse(pr_url).hostname or ""
            if pr_hostname.lower() == "github.com" and config.GITHUB_USERNAME:
                # GitHub PR - check against GITHUB_USERNAME
                if pr_username.lower() == config.GITHUB_USERNAME.lower():
                    filtered_pulls.append(pr)
            elif (
                pr_hostname.lower() == "gitlab.cee.redhat.com"
                and config.GITLAB_USERNAME
            ):
                # GitLab MR - check against GITLAB_USERNAME
                if pr_username.lower() == config.GITLAB_USERNAME.lower():
                    filtered_pulls.append(pr)

        # Only include repos that have matching PRs
        if filtered_pulls:
            filtered_prs[repo_name] = filtered_pulls

    return filtered_prs


def extract_organization_from_url(pr_url):
    """Extract organization name from GitHub/GitLab PR URL."""
    if not pr_url:
        return ""

    try:
        parsed_url = urlparse(pr_url)
        path_parts = parsed_url.path.strip("/").split("/")

        # GitHub URLs: https://github.com/{org}/{repo}/pull/{number}
        # GitLab URLs: https://gitlab.cee.redhat.com/{org}/{repo}/-/merge_requests/{number}
        if len(path_parts) >= 2:
            return path_parts[0]  # First part after domain is the organization

        return ""
    except Exception:
        return ""


def filter_prs_by_organization(pr_list, organization):
    """Filter pull requests by organization name."""
    if not organization:
        return pr_list

    filtered_prs = {}

    for repo_name, pulls in pr_list.items():
        filtered_pulls = []
        for pr in pulls:
            pr_url = pr.get("html_url", "")
            pr_organization = extract_organization_from_url(pr_url)

            if pr_organization.lower() == organization.lower():
                filtered_pulls.append(pr)

        # Only include repos that have matching PRs
        if filtered_pulls:
            filtered_prs[repo_name] = filtered_pulls

    return filtered_prs


def get_unique_organizations_from_prs(pr_list):
    """Get list of unique organizations from PR list for filter options."""
    organizations = set()

    for repo_name, pulls in pr_list.items():
        for pr in pulls:
            pr_url = pr.get("html_url", "")
            org = extract_organization_from_url(pr_url)
            if org:
                organizations.add(org)

    return sorted(organizations)


def get_github_open_pr(reload_data):
    """Get GitHub open pull requests from a file or download new data."""
    logger.info(
        f"get_github_open_pr called with reload_data={reload_data}, file_exists={config.GH_OPEN_PR_FILE.is_file()}"
    )

    if not config.GH_OPEN_PR_FILE.is_file() and not reload_data:
        flash(
            "GitHub open pull requests data not found, please update the data", "info"
        )
        return {}

    if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "add_me":
        flash("GITHUB_TOKEN is not set", "warning")
        return {}

    if reload_data:
        open_prs = github_service.GithubAPI().get_open_pull_request_with_graphql()
        flash("GitHub open pull requests updated successsfully", "success")
        return open_prs

    with open(config.GH_OPEN_PR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_gitlab_open_pr(reload_data):
    """Get GitLab open pull requests from a file or download new data."""
    logger.info(
        f"get_gitlab_open_pr called with reload_data={reload_data}, file_exists={config.GL_OPEN_PR_FILE.is_file()}"
    )

    if not config.GL_OPEN_PR_FILE.is_file() and not reload_data:
        flash(
            "GitLab open pull requests data not found, please update the data", "info"
        )
        return {}

    if not config.GITLAB_TOKEN or config.GITLAB_TOKEN == "add_me":
        logger.error("GITLAB_TOKEN is not set")
        return {}

    if reload_data:
        logger.info("Downloading new GitLab open MRs data")
        try:
            open_prs = gitlab_service.GitlabAPI().get_open_merge_requests_with_graphql()
            flash("GitLab open pull requests updated successsfully", "success")
            return open_prs
        except (
            requests.exceptions.ConnectionError,
            gitlab.exceptions.GitlabAuthenticationError,
        ) as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("GitLab open MRs were not updated", "warning")
            logger.error(err)
            # If download failed and file doesn't exist, return empty dict
            if not config.GL_OPEN_PR_FILE.is_file():
                return {}

    # Only try to read file if it exists
    if config.GL_OPEN_PR_FILE.is_file():
        with open(config.GL_OPEN_PR_FILE, mode="r", encoding="utf-8") as file:
            return json.load(file)

    # File doesn't exist and we didn't download - return empty dict
    return {}


def get_app_interface_open_mr(reload_data):
    """
    Get App-interface open merge requests from a file or download new data.
    """
    logger.info(
        f"get_app_interface_open_mr called with reload_data={reload_data}, file_exists={config.APP_INTERFACE_OPEN_MR_FILE.is_file()}"
    )

    if not config.APP_INTERFACE_OPEN_MR_FILE.is_file() and not reload_data:
        flash("App-interface open MRs data not found, please update the data", "info")
        return {}

    if not config.GITLAB_TOKEN or config.GITLAB_TOKEN == "add_me":
        flash("GITLAB_TOKEN is not set", "warning")
        return {}

    if reload_data:
        logger.info("Downloading new GitLab open MRs data")
        try:
            open_mrs = (
                gitlab_service.GitlabAPI().get_app_interface_open_mr_with_graphql()
            )
            flash("App-interface open MRs updated successsfully", "success")
            return open_mrs
        except requests.exceptions.ConnectionError as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("App-interface open MRs were not updated", "warning")
            logger.error(err)

    with open(config.APP_INTERFACE_OPEN_MR_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_app_interface_merged_mr(reload_data):
    """
    Get App-interface merged merge requests from a file or download new data.
    Filter by merge date within specified days.
    """

    logger.info(
        f"get_app_interface_merged_mr called with reload_data={reload_data}, file_exists={config.APP_INTERFACE_MERGED_MR_FILE.is_file()}"
    )

    if not config.APP_INTERFACE_MERGED_MR_FILE.is_file() and not reload_data:
        flash("App-interface merged MRs data not found, please update the data", "info")
        return []

    if not config.GITLAB_TOKEN:
        logger.error("GITLAB_TOKEN is not set")
        return []

    merged_mrs = []

    # Case 1: File doesn't exist - download all data
    if not config.APP_INTERFACE_MERGED_MR_FILE.is_file():
        try:
            merged_mrs = (
                gitlab_service.GitlabAPI().get_app_interface_merged_mr_with_graphql()
            )
            flash("App-interface merged MRs updated successsfully", "success")
        except requests.exceptions.ConnectionError as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("App-interface merged MRs were not updated", "warning")
            logger.error(err)
            return []

    # Case 2: Reload requested - download missing data
    elif reload_data:
        try:
            merged_mrs = (
                gitlab_service.GitlabAPI().get_app_interface_merged_mr_with_graphql()
            )
            flash("App-interface merged MRs updated successsfully", "success")
        except requests.exceptions.ConnectionError as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("App-interface merged MRs were not updated", "warning")
            logger.error(err)
            # Fall back to loading existing file
            merged_mrs = load_json_data(config.APP_INTERFACE_MERGED_MR_FILE).get(
                "data", []
            )

    # Case 3: Load from existing file
    else:
        with open(
            config.APP_INTERFACE_MERGED_MR_FILE, mode="r", encoding="utf-8"
        ) as file:
            data = json.load(file)
            timestamp = data.get("timestamp")
            # If you see the timestamp to "test", it means that the data is broken,
            # so we need to download the new data.
            if timestamp == "test":
                try:
                    merged_mrs = gitlab_service.GitlabAPI().get_app_interface_merged_mr_with_graphql()
                    flash("App-interface merged MRs updated successsfully", "success")
                except requests.exceptions.ConnectionError as err:
                    flash("App-interface merged MRs were not updated", "warning")
                    logger.error(f"Failed to reload broken data: {err}")
                    merged_mrs = []
            else:
                merged_mrs = data.get("data", [])

    return merged_mrs


def get_app_interface_closed_mr(reload_data):
    """
    Get App-interface closed merge requests from a file or download new data.
    """
    if not config.GITLAB_TOKEN:
        logger.error("GITLAB_TOKEN is not set")
        flash("GITLAB_TOKEN is not set", "warning")
        return []

    closed_mrs = []

    if not config.APP_INTERFACE_CLOSED_MR_FILE.is_file() and not reload_data:
        flash("App-interface closed MRs data not found, please update the data", "info")
        return []

    # Case 1: File doesn't exist - download all data
    if not config.APP_INTERFACE_CLOSED_MR_FILE.is_file():
        try:
            closed_mrs = (
                gitlab_service.GitlabAPI().get_app_interface_closed_mr_with_graphql()
            )
            flash("App-interface closed MRs updated successsfully", "success")
        except requests.exceptions.ConnectionError as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("App-interface closed MRs were not updated", "warning")
            logger.error(err)
            return []

    # Case 2: Reload requested - download missing data
    elif reload_data:
        try:
            closed_mrs = (
                gitlab_service.GitlabAPI().get_app_interface_closed_mr_with_graphql()
            )
            flash("App-interface closed MRs updated successsfully", "success")
        except requests.exceptions.ConnectionError as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("App-interface closed MRs were not updated", "warning")
            logger.error(err)
            # Fall back to loading existing file
            closed_mrs = load_json_data(config.APP_INTERFACE_CLOSED_MR_FILE).get(
                "data", []
            )

    # Case 3: Load from existing file
    else:
        with open(
            config.APP_INTERFACE_CLOSED_MR_FILE, mode="r", encoding="utf-8"
        ) as file:
            data = json.load(file)
            timestamp = data.get("timestamp")
            # If you see the timestamp to "test", it means that the data is broken,
            # so we need to download the new data.
            if timestamp == "test":
                try:
                    closed_mrs = gitlab_service.GitlabAPI().get_app_interface_closed_mr_with_graphql()
                    flash("App-interface closed MRs updated successsfully", "success")
                except requests.exceptions.ConnectionError as err:
                    flash("App-interface closed MRs were not updated", "warning")
                    logger.error(f"Failed to reload broken data: {err}")
                    closed_mrs = []
            else:
                closed_mrs = data.get("data", [])

    return closed_mrs


def get_github_merged_pr(reload_data):
    """Get GitHub merged pull requests from a file or download new data."""

    if not config.GH_MERGED_PR_FILE.is_file() and not reload_data:
        flash(
            "GitHub merged pull requests data not found, please update the data", "info"
        )
        return {}

    if not config.GITHUB_TOKEN:
        # TODO: add a message to the user that the GITHUB_TOKEN is not set
        return {}

    # Check if enhancement is running before allowing data update
    if reload_data and helpers.is_enhancement_running():
        flash(
            "❌ Cannot update merged PRs - Close Actor enhancement is running! "
            "Stop the enhancement process first to avoid data loss.",
            "danger",
        )
        # Return existing data if available
        if config.GH_MERGED_PR_FILE.is_file():
            with open(config.GH_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
                data = json.load(file)
                return data.get("data", [])
        return {}

    if not config.GH_MERGED_PR_FILE.is_file():
        merged_prs = github_service.GithubAPI().get_merged_pull_requests(scope="all")
        flash("GitHub merged pull requests updated successsfully", "success")
        return merged_prs

    if reload_data:
        merged_prs = github_service.GithubAPI().get_merged_pull_requests(
            scope="missing"
        )
        flash("GitHub merged pull requests updated successsfully", "success")
        return merged_prs

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
    if not config.GL_MERGED_PR_FILE.is_file() and not reload_data:
        flash(
            "GitLab merged pull requests data not found, please update the data", "info"
        )
        return {}

    if not config.GITLAB_TOKEN or config.GITLAB_TOKEN == "add_me":
        logger.error("GITLAB_TOKEN is not set")
        return {}

    if not config.GL_MERGED_PR_FILE.is_file():
        try:
            merged_prs = (
                gitlab_service.GitlabAPI().get_merged_merge_requests_with_graphql()
            )
            flash("GitLab merged pull requests updated successsfully", "success")
            return merged_prs
        except (
            requests.exceptions.ConnectionError,
            gitlab.exceptions.GitlabAuthenticationError,
        ) as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("GitLab merged MRs were not updated", "warning")
            logger.error(err)
            return {}

    if reload_data:
        try:
            merged_prs = gitlab_service.GitlabAPI().get_merged_merge_requests(
                scope="missing"
            )
            flash("GitLab merged pull requests updated successsfully", "success")
            return merged_prs
        except (
            requests.exceptions.ConnectionError,
            gitlab.exceptions.GitlabAuthenticationError,
        ) as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("GitLab merged MRs were not updated", "warning")
            logger.error(err)
            # If download failed and file doesn't exist, return empty dict
            if not config.GL_MERGED_PR_FILE.is_file():
                return {}

    # Only try to read file if it exists
    if config.GL_MERGED_PR_FILE.is_file():
        with open(config.GL_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            timestamp = data.get("timestamp")
            # If you see the timestamp to "test", it means that the data is broken,
            # so we need to download the new data.
            if timestamp == "test":
                return (
                    gitlab_service.GitlabAPI().get_merged_merge_requests_with_graphql()
                )
        return data.get("data")

    # File doesn't exist and we didn't download - return empty dict
    return {}


def get_github_closed_pr(reload_data):
    """Get GitHub closed pull requests from a file or download new data."""

    if not config.GH_CLOSED_PR_FILE.is_file() and not reload_data:
        flash(
            "GitHub closed pull requests data not found, please update the data", "info"
        )
        return {}

    if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "add_me":
        flash("GITHUB_TOKEN is not set", "warning")
        return {}

    # Check if enhancement is running before allowing data update
    if reload_data and helpers.is_enhancement_running():
        flash(
            "❌ Cannot update closed PRs - Close Actor enhancement is running! "
            "Stop the enhancement process first to avoid data loss.",
            "danger",
        )
        # Return existing data if available
        if config.GH_CLOSED_PR_FILE.is_file():
            with open(config.GH_CLOSED_PR_FILE, mode="r", encoding="utf-8") as file:
                data = json.load(file)
                return data.get("data", [])
        return {}

    if not config.GH_CLOSED_PR_FILE.is_file():
        closed_prs = github_service.GithubAPI().get_closed_pull_requests(scope="all")
        flash("GitHub closed pull requests updated successfully", "success")
        return closed_prs

    if reload_data:
        closed_prs = github_service.GithubAPI().get_closed_pull_requests(
            scope="missing"
        )
        flash("GitHub closed pull requests updated successfully", "success")
        return closed_prs

    with open(config.GH_CLOSED_PR_FILE, mode="r", encoding="utf-8") as file:
        data = json.load(file)
        timestamp = data.get("timestamp")
        # If you see the timestamp to "test", it means that the data is broken,
        # so we need to download the new data.
        if timestamp == "test":
            return github_service.GithubAPI().get_closed_pull_requests(scope="all")
    return data.get("data")


def get_gitlab_closed_pr(reload_data):
    """Get GitLab closed pull requests from a file or download new data."""
    if not config.GL_CLOSED_PR_FILE.is_file() and not reload_data:
        flash(
            "GitLab closed pull requests data not found, please update the data", "info"
        )
        return {}

    if not config.GITLAB_TOKEN or config.GITLAB_TOKEN == "add_me":
        logger.error("GITLAB_TOKEN is not set")
        return {}

    if not config.GL_CLOSED_PR_FILE.is_file():
        try:
            closed_prs = (
                gitlab_service.GitlabAPI().get_closed_merge_requests_with_graphql()
            )
            flash("GitLab closed pull requests updated successfully", "success")
            return closed_prs
        except (
            requests.exceptions.ConnectionError,
            gitlab.exceptions.GitlabAuthenticationError,
        ) as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("GitLab closed MRs were not updated", "warning")
            logger.error(err)
            return {}

    if reload_data:
        try:
            closed_prs = gitlab_service.GitlabAPI().get_closed_merge_requests(
                scope="missing"
            )
            flash("GitLab closed pull requests updated successfully", "success")
            return closed_prs
        except (
            requests.exceptions.ConnectionError,
            gitlab.exceptions.GitlabAuthenticationError,
        ) as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("GitLab closed MRs were not updated", "warning")
            logger.error(err)
            # If download failed and file doesn't exist, return empty dict
            if not config.GL_CLOSED_PR_FILE.is_file():
                return {}

    # Only try to read file if it exists
    if config.GL_CLOSED_PR_FILE.is_file():
        with open(config.GL_CLOSED_PR_FILE, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            timestamp = data.get("timestamp")
            # If you see the timestamp to "test", it means that the data is broken,
            # so we need to download the new data.
            if timestamp == "test":
                return (
                    gitlab_service.GitlabAPI().get_closed_merge_requests_with_graphql()
                )
        return data.get("data")

    # File doesn't exist and we didn't download - return empty dict
    return {}


def sort_pr_list_by(open_pr_list, sort_by):
    for pr_list in open_pr_list.values():
        pr_list.sort(key=lambda x: x[sort_by], reverse=True)
