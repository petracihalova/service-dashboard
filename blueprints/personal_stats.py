import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request

import config
from blueprints.jira_tickets import get_jira_config_info
from utils import load_json_data

logger = logging.getLogger(__name__)
personal_stats_bp = Blueprint("personal_stats", __name__)


@personal_stats_bp.route("/personal-stats")
def personal_statistics():
    """
    Personal statistics page showing user's activity across GitHub, GitLab, and JIRA.
    """
    # Get date range from URL parameters - default to last 7 days
    from_date = request.args.get("date_from")
    to_date = request.args.get("date_to")

    if not from_date:
        # Default to last 7 days
        from_date_obj = datetime.now() - timedelta(
            days=6
        )  # 6 days ago + today = 7 days
        from_date = from_date_obj.strftime("%Y-%m-%d")

    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"Personal stats accessed with date range: {from_date} to {to_date}")

    # Get user identities
    github_username = config.GITHUB_USERNAME
    gitlab_username = config.GITLAB_USERNAME

    # Get JIRA user info - try API first, then extract from data
    jira_config = get_jira_config_info()
    jira_user = jira_config.get("current_user", "")

    # If JIRA API is not available, extract user from the tickets data since all tickets are for the expected user
    if jira_user in ["Not available", "Unable to fetch user info", ""]:
        jira_user = get_jira_user_from_data()
        logger.info(f"Extracted JIRA user from ticket data: '{jira_user}'")

    # Get personal statistics
    github_stats = get_github_personal_stats(github_username, from_date, to_date)
    gitlab_stats = get_gitlab_personal_stats(gitlab_username, from_date, to_date)
    app_interface_stats = get_app_interface_personal_stats(
        gitlab_username, from_date, to_date
    )
    jira_stats = get_jira_personal_stats(jira_user, from_date, to_date)

    # Get closed PR/MR statistics
    github_closed_stats = get_github_closed_personal_stats(
        github_username, from_date, to_date
    )
    gitlab_closed_stats = get_gitlab_closed_personal_stats(
        gitlab_username, from_date, to_date
    )
    app_interface_closed_stats = get_app_interface_closed_personal_stats(
        gitlab_username, from_date, to_date
    )

    # Calculate overall stats
    github_total_prs = (
        github_stats["merged_prs_count"] + github_closed_stats["closed_prs_count"]
    )
    gitlab_total_mrs = (
        gitlab_stats["merged_prs_count"] + gitlab_closed_stats["closed_prs_count"]
    )
    app_interface_total_mrs = (
        app_interface_stats["merged_prs_count"]
        + app_interface_closed_stats["closed_prs_count"]
    )

    # Get filters for code statistics
    code_stats_source = request.args.get("code_stats_source")
    code_stats_exclude_personal = (
        request.args.get("code_stats_exclude_personal") == "true"
    )

    # Get comprehensive diff statistics (merged PRs/MRs only)
    diff_stats = get_combined_diff_stats(
        github_username,
        gitlab_username,
        from_date,
        to_date,
        code_stats_source,
        code_stats_exclude_personal,
    )

    overall_stats = {
        "github_total_prs": github_total_prs,
        "gitlab_total_mrs": gitlab_total_mrs,
        "app_interface_total_mrs": app_interface_total_mrs,
        "jira_tickets_closed": jira_stats["closed_tickets_count"],
    }

    return render_template(
        "personal_stats.html",
        from_date=from_date,
        to_date=to_date,
        github_username=github_username,
        gitlab_username=gitlab_username,
        jira_user=jira_user,
        github_stats=github_stats,
        gitlab_stats=gitlab_stats,
        app_interface_stats=app_interface_stats,
        jira_stats=jira_stats,
        github_closed_stats=github_closed_stats,
        gitlab_closed_stats=gitlab_closed_stats,
        app_interface_closed_stats=app_interface_closed_stats,
        overall_stats=overall_stats,
        diff_stats=diff_stats,
        jira_config=jira_config,
    )


@personal_stats_bp.route("/all-data-stats")
def all_data_statistics():
    """
    All data statistics page showing activity across all users for GitHub, GitLab, and App-interface.
    Excludes JIRA data since it's user-specific.
    """
    # Get date range from URL parameters - default to last 7 days
    from_date = request.args.get("date_from")
    to_date = request.args.get("date_to")

    if not from_date:
        # Default to last 7 days
        from_date_obj = datetime.now() - timedelta(
            days=6
        )  # 6 days ago + today = 7 days
        from_date = from_date_obj.strftime("%Y-%m-%d")

    if not to_date:
        to_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"All data stats accessed with date range: {from_date} to {to_date}")

    # Get statistics for all users
    github_stats = get_github_all_stats(from_date, to_date)
    gitlab_stats = get_gitlab_all_stats(from_date, to_date)
    app_interface_stats = get_app_interface_all_stats(from_date, to_date)

    # Get closed PR/MR statistics for all users
    github_closed_stats = get_github_closed_all_stats(from_date, to_date)
    gitlab_closed_stats = get_gitlab_closed_all_stats(from_date, to_date)
    app_interface_closed_stats = get_app_interface_closed_all_stats(from_date, to_date)

    # Get Konflux GitHub statistics
    github_konflux_stats = get_github_konflux_stats(from_date, to_date)
    github_konflux_closed_stats = get_github_konflux_closed_stats(from_date, to_date)

    # Calculate overall stats
    github_total_prs = (
        github_stats["merged_prs_count"] + github_closed_stats["closed_prs_count"]
    )
    gitlab_total_mrs = (
        gitlab_stats["merged_prs_count"] + gitlab_closed_stats["closed_prs_count"]
    )
    app_interface_total_mrs = (
        app_interface_stats["merged_prs_count"]
        + app_interface_closed_stats["closed_prs_count"]
    )
    all_repos = (
        github_stats["repos_contributed"]
        + gitlab_stats["repos_contributed"]
        + app_interface_stats["repos_contributed"]
    )
    total_repos = len(set(all_repos))

    # Calculate Konflux PR counts
    konflux_prs_count = get_konflux_prs_count(
        github_stats,
        github_closed_stats,
        gitlab_stats,
        gitlab_closed_stats,
        app_interface_stats,
        app_interface_closed_stats,
    )

    overall_stats = {
        "github_total_prs": github_total_prs,
        "gitlab_total_mrs": gitlab_total_mrs,
        "app_interface_total_mrs": app_interface_total_mrs,
        "total_repos": total_repos,
        "konflux_prs_count": konflux_prs_count,
    }

    return render_template(
        "all_data_stats.html",
        from_date=from_date,
        to_date=to_date,
        github_stats=github_stats,
        gitlab_stats=gitlab_stats,
        app_interface_stats=app_interface_stats,
        github_closed_stats=github_closed_stats,
        gitlab_closed_stats=gitlab_closed_stats,
        app_interface_closed_stats=app_interface_closed_stats,
        github_konflux_stats=github_konflux_stats,
        github_konflux_closed_stats=github_konflux_closed_stats,
        overall_stats=overall_stats,
        app_interface_users=config.APP_INTERFACE_USERS,
        github_username=config.GITHUB_USERNAME,
        gitlab_username=config.GITLAB_USERNAME,
    )


def get_github_personal_stats(username, from_date, to_date):
    """Get GitHub statistics for the user in the given date range."""
    if not username:
        return {
            "merged_prs_count": 0,
            "repos_contributed": [],
            "merged_prs": [],
            "organization_stats": {},
            "personal_repos": [],
            "personal_repo_stats": {},
            "organization_repos": [],
        }

    try:
        github_data = load_json_data(config.GH_MERGED_PR_FILE)
        # Extract PRs from the nested data structure
        github_merged_prs = []
        if isinstance(github_data, dict) and "data" in github_data:
            for repo_name, prs in github_data["data"].items():
                for pr in prs:
                    pr["repo_name"] = repo_name  # Add repo name to each PR
                    github_merged_prs.append(pr)
        else:
            # Fallback if data structure is different
            github_merged_prs = github_data if isinstance(github_data, list) else []
    except Exception as e:
        logger.warning(f"GitHub merged PRs data not available: {e}")
        github_merged_prs = []

    # Filter PRs by user and date range
    user_prs = []
    repos_contributed = []
    organization_stats = {}  # org_name: {repos: [], pr_count: 0}
    personal_repos = []
    organization_repos = []

    # Track repos and their organizations
    repo_organizations = {}

    for pr in github_merged_prs:
        # Check if PR is by this user
        if pr.get("user_login") != username:
            continue

        # Check date range
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue

        try:
            # Parse merged_at datetime (assuming ISO format)
            merged_date = datetime.fromisoformat(
                merged_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= merged_date <= to_date_obj:
                user_prs.append(pr)
                repo_name = pr.get("repo_name", "Unknown")

                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)

                # Extract organization from html_url
                html_url = pr.get("html_url", "")
                org_name = None
                if html_url:
                    # Extract organization from URL: https://github.com/ORG/REPO/pull/123
                    url_parts = html_url.split("/")
                    if len(url_parts) >= 5 and url_parts[2] == "github.com":
                        org_name = url_parts[3]

                # Store organization for this repo
                if org_name and repo_name not in repo_organizations:
                    repo_organizations[repo_name] = org_name

        except Exception as e:
            logger.warning(f"Error parsing merged_at date for PR: {e}")
            continue

    # Categorize repositories by organization and count PRs
    personal_repo_stats = {}  # repo_name: pr_count

    for repo_name in repos_contributed:
        org_name = repo_organizations.get(
            repo_name, username
        )  # Default to username if not found

        if org_name == username:
            # Personal repository
            personal_repos.append(repo_name)
            personal_repo_stats[repo_name] = 0  # Initialize PR count
        else:
            # Organization repository
            organization_repos.append(repo_name)
            if org_name not in organization_stats:
                organization_stats[org_name] = {
                    "repos": [],
                    "repo_stats": {},
                    "pr_count": 0,
                }
            organization_stats[org_name]["repos"].append(repo_name)
            organization_stats[org_name]["repo_stats"][repo_name] = (
                0  # Initialize PR count for this repo
            )

    # Count PRs per repository and organization
    for pr in user_prs:
        repo_name = pr.get("repo_name", "Unknown")
        org_name = repo_organizations.get(repo_name, username)

        if org_name == username:
            # Personal repository PR
            if repo_name in personal_repo_stats:
                personal_repo_stats[repo_name] += 1
        else:
            # Organization repository PR
            if org_name in organization_stats:
                organization_stats[org_name]["pr_count"] += 1
                if repo_name in organization_stats[org_name]["repo_stats"]:
                    organization_stats[org_name]["repo_stats"][repo_name] += 1

    return {
        "merged_prs_count": len(user_prs),
        "repos_contributed": repos_contributed,
        "merged_prs": user_prs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": organization_repos,
    }


def get_gitlab_personal_stats(username, from_date, to_date):
    """Get GitLab statistics for the user in the given date range."""
    if not username:
        return {
            "merged_prs_count": 0,
            "repos_contributed": [],
            "merged_prs": [],
            "organization_stats": {},
            "personal_repos": [],
            "personal_repo_stats": {},
            "organization_repos": [],
        }

    try:
        gitlab_data = load_json_data(config.GL_MERGED_PR_FILE)
        # Extract PRs from the nested data structure
        gitlab_merged_prs = []
        if isinstance(gitlab_data, dict) and "data" in gitlab_data:
            for repo_name, prs in gitlab_data["data"].items():
                for pr in prs:
                    pr["repo_name"] = repo_name  # Add repo name to each PR
                    gitlab_merged_prs.append(pr)
        else:
            # Fallback if data structure is different
            gitlab_merged_prs = gitlab_data if isinstance(gitlab_data, list) else []
    except Exception as e:
        logger.warning(f"GitLab merged PRs data not available: {e}")
        gitlab_merged_prs = []

    # Filter PRs by user and date range
    user_prs = []
    repos_contributed = []
    organization_stats = {}  # org_name: {repos: [], repo_stats: {}, pr_count: 0}
    personal_repos = []
    organization_repos = []

    # Track repos and their organizations/groups
    repo_organizations = {}

    for pr in gitlab_merged_prs:
        # Check if PR is by this user
        if pr.get("user_login") != username:
            continue

        # Check date range
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue

        try:
            # Parse merged_at datetime (assuming ISO format)
            merged_date = datetime.fromisoformat(
                merged_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= merged_date <= to_date_obj:
                user_prs.append(pr)
                repo_name = pr.get("repo_name", "Unknown")

                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)

                # Extract organization/group from html_url
                html_url = pr.get("html_url", "")
                org_name = None
                if html_url:
                    # Extract organization from URL: https://gitlab.com/GROUP/REPO/-/merge_requests/123
                    # or https://gitlab.example.com/GROUP/REPO/-/merge_requests/123
                    url_parts = html_url.split("/")
                    if len(url_parts) >= 5 and "gitlab" in url_parts[2]:
                        # Find the position after the domain
                        domain_index = 2
                        if len(url_parts) > domain_index + 1:
                            org_name = url_parts[
                                domain_index + 1
                            ]  # First path segment is usually the group

                # Store organization for this repo
                if org_name and repo_name not in repo_organizations:
                    repo_organizations[repo_name] = org_name

        except Exception as e:
            logger.warning(f"Error parsing merged_at date for MR: {e}")
            continue

    # Categorize repositories by organization and count MRs
    personal_repo_stats = {}  # repo_name: mr_count

    for repo_name in repos_contributed:
        org_name = repo_organizations.get(
            repo_name, username
        )  # Default to username if not found

        if org_name == username:
            # Personal repository
            personal_repos.append(repo_name)
            personal_repo_stats[repo_name] = 0  # Initialize MR count
        else:
            # Organization repository
            organization_repos.append(repo_name)
            if org_name not in organization_stats:
                organization_stats[org_name] = {
                    "repos": [],
                    "repo_stats": {},
                    "pr_count": 0,
                }
            organization_stats[org_name]["repos"].append(repo_name)
            organization_stats[org_name]["repo_stats"][repo_name] = (
                0  # Initialize MR count for this repo
            )

    # Count MRs per repository and organization
    for pr in user_prs:
        repo_name = pr.get("repo_name", "Unknown")
        org_name = repo_organizations.get(repo_name, username)

        if org_name == username:
            # Personal repository MR
            if repo_name in personal_repo_stats:
                personal_repo_stats[repo_name] += 1
        else:
            # Organization repository MR
            if org_name in organization_stats:
                organization_stats[org_name]["pr_count"] += 1
                if repo_name in organization_stats[org_name]["repo_stats"]:
                    organization_stats[org_name]["repo_stats"][repo_name] += 1

    return {
        "merged_prs_count": len(user_prs),
        "repos_contributed": repos_contributed,
        "merged_prs": user_prs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": organization_repos,
    }


def get_app_interface_personal_stats(username, from_date, to_date):
    """Get App-interface statistics for the user in the given date range."""
    if not username:
        return {
            "merged_prs_count": 0,
            "repos_contributed": [],
            "merged_prs": [],
            "organization_stats": {},
            "personal_repos": [],
            "personal_repo_stats": {},
            "organization_repos": [],
        }

    try:
        app_interface_data = load_json_data(config.APP_INTERFACE_MERGED_MR_FILE)
        # Extract MRs from the nested data structure
        if isinstance(app_interface_data, dict) and "data" in app_interface_data:
            app_interface_merged_mrs = app_interface_data["data"]
        else:
            # Fallback if data structure is different
            app_interface_merged_mrs = (
                app_interface_data if isinstance(app_interface_data, list) else []
            )
    except Exception as e:
        logger.warning(f"App-interface merged MRs data not available: {e}")
        app_interface_merged_mrs = []

    # Filter MRs by user and date range
    user_mrs = []
    repos_contributed = []

    for mr in app_interface_merged_mrs:
        # Check if MR is by this user
        if mr.get("user_login") != username:
            continue

        # Check date range
        merged_at = mr.get("merged_at")
        if not merged_at:
            continue

        try:
            # Parse merged_at datetime (assuming ISO format)
            merged_date = datetime.fromisoformat(
                merged_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= merged_date <= to_date_obj:
                user_mrs.append(mr)
                # App-interface is a single repository
                repo_name = "app-interface"
                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)
        except Exception as e:
            logger.warning(f"Error parsing merged_at date for app-interface MR: {e}")
            continue

    return {
        "merged_prs_count": len(user_mrs),
        "repos_contributed": repos_contributed,
        "merged_prs": user_mrs,
        "organization_stats": {},
        "personal_repos": ["app-interface"] if user_mrs else [],
        "personal_repo_stats": {"app-interface": len(user_mrs)} if user_mrs else {},
        "organization_repos": [],
    }


def get_github_closed_personal_stats(username, from_date, to_date):
    """Get GitHub closed PRs statistics for the user in the given date range."""
    if not username:
        return {"closed_prs_count": 0}

    try:
        github_data = load_json_data(config.GH_CLOSED_PR_FILE)
        # Extract PRs from the nested data structure
        github_closed_prs = []
        if isinstance(github_data, dict) and "data" in github_data:
            for repo_name, prs in github_data["data"].items():
                github_closed_prs.extend(prs)
        else:
            # Fallback if data structure is different
            github_closed_prs = github_data if isinstance(github_data, list) else []
    except Exception as e:
        logger.warning(f"GitHub closed PRs data not available: {e}")
        github_closed_prs = []

    # Filter PRs by user and date range
    user_closed_prs = 0

    for pr in github_closed_prs:
        # Check if PR is by this user
        if pr.get("user_login") != username:
            continue

        # Check date range - use closed_at if available, otherwise use created_at
        closed_at = pr.get("closed_at") or pr.get("created_at")
        if not closed_at:
            continue

        try:
            # Parse closed_at datetime (assuming ISO format)
            closed_date = datetime.fromisoformat(
                closed_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= closed_date <= to_date_obj:
                user_closed_prs += 1
        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing date for closed PR: {e}")
            continue

    return {"closed_prs_count": user_closed_prs}


def get_gitlab_closed_personal_stats(username, from_date, to_date):
    """Get GitLab closed MRs statistics for the user in the given date range."""
    if not username:
        return {"closed_prs_count": 0}

    try:
        gitlab_data = load_json_data(config.GL_CLOSED_PR_FILE)
        # Extract MRs from the nested data structure
        gitlab_closed_prs = []
        if isinstance(gitlab_data, dict) and "data" in gitlab_data:
            for repo_name, prs in gitlab_data["data"].items():
                gitlab_closed_prs.extend(prs)
        else:
            # Fallback if data structure is different
            gitlab_closed_prs = gitlab_data if isinstance(gitlab_data, list) else []
    except Exception as e:
        logger.warning(f"GitLab closed MRs data not available: {e}")
        gitlab_closed_prs = []

    # Filter MRs by user and date range
    user_closed_prs = 0

    for pr in gitlab_closed_prs:
        # Check if PR is by this user
        if pr.get("user_login") != username:
            continue

        # Check date range - use closed_at if available, otherwise use created_at
        closed_at = pr.get("closed_at") or pr.get("created_at")
        if not closed_at:
            continue

        try:
            # Parse closed_at datetime (assuming ISO format)
            closed_date = datetime.fromisoformat(
                closed_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= closed_date <= to_date_obj:
                user_closed_prs += 1
        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing date for closed MR: {e}")
            continue

    return {"closed_prs_count": user_closed_prs}


def get_app_interface_closed_personal_stats(username, from_date, to_date):
    """Get App-interface closed MRs statistics for the user in the given date range."""
    if not username:
        return {"closed_prs_count": 0}

    try:
        app_interface_data = load_json_data(config.APP_INTERFACE_CLOSED_MR_FILE)
        # Extract MRs from the nested data structure
        if isinstance(app_interface_data, dict) and "data" in app_interface_data:
            app_interface_closed_mrs = app_interface_data["data"]
        else:
            # Fallback if data structure is different
            app_interface_closed_mrs = (
                app_interface_data if isinstance(app_interface_data, list) else []
            )
    except Exception as e:
        logger.warning(f"App-interface closed MRs data not available: {e}")
        app_interface_closed_mrs = []

    # Filter MRs by user and date range
    user_closed_mrs = 0

    for mr in app_interface_closed_mrs:
        # Check if MR is by this user
        if mr.get("user_login") != username:
            continue

        # Check date range - use closed_at if available, otherwise use created_at
        closed_at = mr.get("closed_at") or mr.get("created_at")
        if not closed_at:
            continue

        try:
            # Parse closed_at datetime (assuming ISO format)
            closed_date = datetime.fromisoformat(
                closed_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= closed_date <= to_date_obj:
                user_closed_mrs += 1
        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing date for closed app-interface MR: {e}")
            continue

    return {"closed_prs_count": user_closed_mrs}


def get_github_all_stats(from_date, to_date):
    """Get GitHub statistics for all users in the given date range."""
    try:
        github_data = load_json_data(config.GH_MERGED_PR_FILE)
        # Extract PRs from the nested data structure
        github_merged_prs = []
        if isinstance(github_data, dict) and "data" in github_data:
            for repo_name, prs in github_data["data"].items():
                for pr in prs:
                    pr["repo_name"] = repo_name  # Add repo name to each PR
                    github_merged_prs.append(pr)
        else:
            # Fallback if data structure is different
            github_merged_prs = github_data if isinstance(github_data, list) else []
    except Exception as e:
        logger.warning(f"GitHub merged PRs data not available: {e}")
        github_merged_prs = []

    # Filter PRs by date range (all users)
    user_prs = []
    repos_contributed = []
    organization_stats = {}  # org_name: {repos: [], pr_count: 0, repo_stats: {}}
    personal_repos = []
    organization_repos = []

    # Track repos and their organizations
    repo_organizations = {}

    for pr in github_merged_prs:
        # Check date range
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue

        try:
            # Parse merged_at datetime (assuming ISO format)
            merged_date = datetime.fromisoformat(
                merged_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= merged_date <= to_date_obj:
                user_prs.append(pr)
                repo_name = pr.get("repo_name", "Unknown")

                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)

                # Extract organization from html_url
                html_url = pr.get("html_url", "")
                org_name = None
                if html_url:
                    # Extract organization from URL: https://github.com/ORG/REPO/pull/123
                    url_parts = html_url.split("/")
                    if len(url_parts) >= 5 and url_parts[2] == "github.com":
                        org_name = url_parts[3]

                # Store organization for this repo
                if org_name and repo_name not in repo_organizations:
                    repo_organizations[repo_name] = org_name

        except Exception as e:
            logger.warning(f"Error parsing merged_at date for PR: {e}")
            continue

    # Categorize repositories by organization and count PRs
    personal_repo_stats = {}  # repo_name: pr_count

    # Collect all unique users from PRs to determine "personal" repos
    all_users = set(pr.get("user_login") for pr in user_prs if pr.get("user_login"))

    for repo_name in repos_contributed:
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in all_users:
            # Consider it personal if it's a user repo (org name matches a user)
            personal_repos.append(repo_name)
            personal_repo_stats[repo_name] = 0  # Initialize PR count
        else:
            # Organization repository
            organization_repos.append(repo_name)
            if org_name not in organization_stats:
                organization_stats[org_name] = {
                    "repos": [],
                    "repo_stats": {},
                    "pr_count": 0,
                }
            if repo_name not in organization_stats[org_name]["repos"]:
                organization_stats[org_name]["repos"].append(repo_name)
                organization_stats[org_name]["repo_stats"][repo_name] = 0

    # Count PRs per repository and organization
    for pr in user_prs:
        repo_name = pr.get("repo_name", "Unknown")
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in all_users:
            # Personal repository PR
            if repo_name in personal_repo_stats:
                personal_repo_stats[repo_name] += 1
        else:
            # Organization repository PR
            if org_name in organization_stats:
                organization_stats[org_name]["pr_count"] += 1
                if repo_name in organization_stats[org_name]["repo_stats"]:
                    organization_stats[org_name]["repo_stats"][repo_name] += 1

    # Calculate user statistics (count PRs per user, sorted by count)
    user_stats = {}
    for pr in user_prs:
        user_login = pr.get("user_login", "Unknown")
        user_stats[user_login] = user_stats.get(user_login, 0) + 1

    # Sort users by PR count (descending)
    sorted_user_stats = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)

    return {
        "merged_prs_count": len(user_prs),
        "repos_contributed": repos_contributed,
        "merged_prs": user_prs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": organization_repos,
        "user_stats": sorted_user_stats,  # [(username, count), ...] sorted by count
    }


def get_gitlab_all_stats(from_date, to_date):
    """Get GitLab statistics for all users in the given date range."""
    try:
        gitlab_data = load_json_data(config.GL_MERGED_PR_FILE)
        # Extract PRs from the nested data structure
        gitlab_merged_prs = []
        if isinstance(gitlab_data, dict) and "data" in gitlab_data:
            for repo_name, prs in gitlab_data["data"].items():
                for pr in prs:
                    pr["repo_name"] = repo_name  # Add repo name to each PR
                    gitlab_merged_prs.append(pr)
        else:
            # Fallback if data structure is different
            gitlab_merged_prs = gitlab_data if isinstance(gitlab_data, list) else []
    except Exception as e:
        logger.warning(f"GitLab merged PRs data not available: {e}")
        gitlab_merged_prs = []

    # Filter PRs by date range (all users)
    user_prs = []
    repos_contributed = []
    organization_stats = {}  # org_name: {repos: [], pr_count: 0, repo_stats: {}}
    personal_repos = []
    organization_repos = []

    # Track repos and their organizations
    repo_organizations = {}

    for pr in gitlab_merged_prs:
        # Check date range
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue

        try:
            # Parse merged_at datetime (assuming ISO format)
            merged_date = datetime.fromisoformat(
                merged_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= merged_date <= to_date_obj:
                user_prs.append(pr)
                repo_name = pr.get("repo_name", "Unknown")

                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)

                # Extract organization from html_url
                html_url = pr.get("html_url", "")
                org_name = None
                if html_url:
                    # Extract organization from URL: https://gitlab.com/ORG/REPO/-/merge_requests/123
                    url_parts = html_url.split("/")
                    if len(url_parts) >= 5 and "gitlab" in url_parts[2]:
                        org_name = url_parts[3]

                # Store organization for this repo
                if org_name and repo_name not in repo_organizations:
                    repo_organizations[repo_name] = org_name

        except Exception as e:
            logger.warning(f"Error parsing merged_at date for MR: {e}")
            continue

    # Categorize repositories by organization and count PRs
    personal_repo_stats = {}  # repo_name: pr_count

    # Collect all unique users from PRs to determine "personal" repos
    all_users = set(pr.get("user_login") for pr in user_prs if pr.get("user_login"))

    for repo_name in repos_contributed:
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in all_users:
            # Consider it personal if it's a user repo (org name matches a user)
            personal_repos.append(repo_name)
            personal_repo_stats[repo_name] = 0  # Initialize PR count
        else:
            # Organization repository
            organization_repos.append(repo_name)
            if org_name not in organization_stats:
                organization_stats[org_name] = {
                    "repos": [],
                    "repo_stats": {},
                    "pr_count": 0,
                }
            if repo_name not in organization_stats[org_name]["repos"]:
                organization_stats[org_name]["repos"].append(repo_name)
                organization_stats[org_name]["repo_stats"][repo_name] = 0

    # Count PRs per repository and organization
    for pr in user_prs:
        repo_name = pr.get("repo_name", "Unknown")
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in all_users:
            # Personal repository PR
            if repo_name in personal_repo_stats:
                personal_repo_stats[repo_name] += 1
        else:
            # Organization repository PR
            if org_name in organization_stats:
                organization_stats[org_name]["pr_count"] += 1
                if repo_name in organization_stats[org_name]["repo_stats"]:
                    organization_stats[org_name]["repo_stats"][repo_name] += 1

    # Calculate user statistics (count MRs per user, sorted by count)
    user_stats = {}
    for pr in user_prs:
        user_login = pr.get("user_login", "Unknown")
        user_stats[user_login] = user_stats.get(user_login, 0) + 1

    # Sort users by MR count (descending)
    sorted_user_stats = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)

    return {
        "merged_prs_count": len(user_prs),
        "repos_contributed": repos_contributed,
        "merged_prs": user_prs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": organization_repos,
        "user_stats": sorted_user_stats,  # [(username, count), ...] sorted by count
    }


def get_app_interface_all_stats(from_date, to_date):
    """Get App-interface statistics for all users in the given date range."""
    try:
        app_interface_data = load_json_data(config.APP_INTERFACE_MERGED_MR_FILE)
        # Extract MRs from the nested data structure
        if isinstance(app_interface_data, dict) and "data" in app_interface_data:
            app_interface_merged_mrs = app_interface_data["data"]
        else:
            # Fallback if data structure is different
            app_interface_merged_mrs = (
                app_interface_data if isinstance(app_interface_data, list) else []
            )
    except Exception as e:
        logger.warning(f"App-interface merged MRs data not available: {e}")
        app_interface_merged_mrs = []

    # Filter MRs by date range (all users)
    user_mrs = []
    repos_contributed = []
    organization_stats = {}  # For consistency, but app-interface is single repo
    personal_repos = []
    personal_repo_stats = {}

    for mr in app_interface_merged_mrs:
        # Check date range
        merged_at = mr.get("merged_at")
        if not merged_at:
            continue

        try:
            # Parse merged_at datetime (assuming ISO format)
            merged_date = datetime.fromisoformat(
                merged_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= merged_date <= to_date_obj:
                user_mrs.append(mr)
                # App-interface is a single repository
                repo_name = "app-interface"
                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)
        except Exception as e:
            logger.warning(f"Error parsing merged_at date for app-interface MR: {e}")
            continue

    # For app-interface, treat as single personal repository
    if repos_contributed:
        personal_repos = ["app-interface"]
        personal_repo_stats = {"app-interface": len(user_mrs)}

    # Calculate user statistics (count MRs per user, sorted by count)
    user_stats = {}
    for mr in user_mrs:
        user_login = mr.get("user_login", "Unknown")
        user_stats[user_login] = user_stats.get(user_login, 0) + 1

    # Sort users by MR count (descending)
    sorted_user_stats = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)

    return {
        "merged_prs_count": len(user_mrs),
        "repos_contributed": repos_contributed,
        "merged_prs": user_mrs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": [],
        "user_stats": sorted_user_stats,  # [(username, count), ...] sorted by count
    }


def get_github_closed_all_stats(from_date, to_date):
    """Get GitHub closed PRs statistics for all users in the given date range."""
    try:
        github_data = load_json_data(config.GH_CLOSED_PR_FILE)
        # Extract PRs from the nested data structure
        github_closed_prs = []
        if isinstance(github_data, dict) and "data" in github_data:
            for repo_name, prs in github_data["data"].items():
                for pr in prs:
                    pr["repo_name"] = repo_name  # Add repo name to each PR
                    github_closed_prs.append(pr)
        else:
            # Fallback if data structure is different
            github_closed_prs = github_data if isinstance(github_data, list) else []
    except Exception as e:
        logger.warning(f"GitHub closed PRs data not available: {e}")
        github_closed_prs = []

    # Filter PRs by date range (all users)
    user_prs = []
    repos_contributed = []
    organization_stats = {}  # org_name: {repos: [], pr_count: 0, repo_stats: {}}
    personal_repos = []
    organization_repos = []

    # Track repos and their organizations
    repo_organizations = {}

    for pr in github_closed_prs:
        # Check date range - use closed_at if available, otherwise use created_at
        closed_at = pr.get("closed_at") or pr.get("created_at")
        if not closed_at:
            continue

        try:
            # Parse closed_at datetime (assuming ISO format)
            closed_date = datetime.fromisoformat(
                closed_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= closed_date <= to_date_obj:
                user_prs.append(pr)
                repo_name = pr.get("repo_name", "Unknown")

                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)

                # Extract organization from html_url
                html_url = pr.get("html_url", "")
                org_name = None
                if html_url:
                    # Extract organization from URL: https://github.com/ORG/REPO/pull/123
                    url_parts = html_url.split("/")
                    if len(url_parts) >= 5 and url_parts[2] == "github.com":
                        org_name = url_parts[3]

                # Store organization for this repo
                if org_name and repo_name not in repo_organizations:
                    repo_organizations[repo_name] = org_name

        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing date for closed PR: {e}")
            continue

    # Categorize repositories by organization and count PRs
    personal_repo_stats = {}  # repo_name: pr_count

    # Collect all unique users from PRs to determine "personal" repos
    all_users = set(pr.get("user_login") for pr in user_prs if pr.get("user_login"))

    for repo_name in repos_contributed:
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in all_users:
            # Consider it personal if it's a user repo (org name matches a user)
            personal_repos.append(repo_name)
            personal_repo_stats[repo_name] = 0  # Initialize PR count
        else:
            # Organization repository
            organization_repos.append(repo_name)
            if org_name not in organization_stats:
                organization_stats[org_name] = {
                    "repos": [],
                    "repo_stats": {},
                    "pr_count": 0,
                }
            if repo_name not in organization_stats[org_name]["repos"]:
                organization_stats[org_name]["repos"].append(repo_name)
                organization_stats[org_name]["repo_stats"][repo_name] = 0

    # Count PRs per repository and organization
    for pr in user_prs:
        repo_name = pr.get("repo_name", "Unknown")
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in all_users:
            # Personal repository PR
            if repo_name in personal_repo_stats:
                personal_repo_stats[repo_name] += 1
        else:
            # Organization repository PR
            if org_name in organization_stats:
                organization_stats[org_name]["pr_count"] += 1
                if repo_name in organization_stats[org_name]["repo_stats"]:
                    organization_stats[org_name]["repo_stats"][repo_name] += 1

    # Calculate user statistics (count PRs per user, sorted by count)
    user_stats = {}
    for pr in user_prs:
        user_login = pr.get("user_login", "Unknown")
        user_stats[user_login] = user_stats.get(user_login, 0) + 1

    # Sort users by PR count (descending)
    sorted_user_stats = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)

    return {
        "closed_prs_count": len(user_prs),
        "repos_contributed": repos_contributed,
        "closed_prs": user_prs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": organization_repos,
        "user_stats": sorted_user_stats,  # [(username, count), ...] sorted by count
    }


def get_gitlab_closed_all_stats(from_date, to_date):
    """Get GitLab closed MRs statistics for all users in the given date range."""
    try:
        gitlab_data = load_json_data(config.GL_CLOSED_PR_FILE)
        # Extract MRs from the nested data structure
        gitlab_closed_prs = []
        if isinstance(gitlab_data, dict) and "data" in gitlab_data:
            for repo_name, prs in gitlab_data["data"].items():
                for pr in prs:
                    pr["repo_name"] = repo_name  # Add repo name to each PR
                    gitlab_closed_prs.append(pr)
        else:
            # Fallback if data structure is different
            gitlab_closed_prs = gitlab_data if isinstance(gitlab_data, list) else []
    except Exception as e:
        logger.warning(f"GitLab closed MRs data not available: {e}")
        gitlab_closed_prs = []

    # Filter MRs by date range (all users)
    user_prs = []
    repos_contributed = []
    organization_stats = {}  # org_name: {repos: [], pr_count: 0, repo_stats: {}}
    personal_repos = []
    organization_repos = []

    # Track repos and their organizations
    repo_organizations = {}

    for pr in gitlab_closed_prs:
        # Check date range - use closed_at if available, otherwise use created_at
        closed_at = pr.get("closed_at") or pr.get("created_at")
        if not closed_at:
            continue

        try:
            # Parse closed_at datetime (assuming ISO format)
            closed_date = datetime.fromisoformat(
                closed_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= closed_date <= to_date_obj:
                user_prs.append(pr)
                repo_name = pr.get("repo_name", "Unknown")

                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)

                # Extract organization from html_url
                html_url = pr.get("html_url", "")
                org_name = None
                if html_url:
                    # Extract organization from URL: https://gitlab.com/ORG/REPO/-/merge_requests/123
                    url_parts = html_url.split("/")
                    if len(url_parts) >= 5 and "gitlab" in url_parts[2]:
                        org_name = url_parts[3]

                # Store organization for this repo
                if org_name and repo_name not in repo_organizations:
                    repo_organizations[repo_name] = org_name

        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing date for closed MR: {e}")
            continue

    # Categorize repositories by organization and count PRs
    personal_repo_stats = {}  # repo_name: pr_count

    # Collect all unique users from PRs to determine "personal" repos
    all_users = set(pr.get("user_login") for pr in user_prs if pr.get("user_login"))

    for repo_name in repos_contributed:
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in all_users:
            # Consider it personal if it's a user repo (org name matches a user)
            personal_repos.append(repo_name)
            personal_repo_stats[repo_name] = 0  # Initialize PR count
        else:
            # Organization repository
            organization_repos.append(repo_name)
            if org_name not in organization_stats:
                organization_stats[org_name] = {
                    "repos": [],
                    "repo_stats": {},
                    "pr_count": 0,
                }
            if repo_name not in organization_stats[org_name]["repos"]:
                organization_stats[org_name]["repos"].append(repo_name)
                organization_stats[org_name]["repo_stats"][repo_name] = 0

    # Count PRs per repository and organization
    for pr in user_prs:
        repo_name = pr.get("repo_name", "Unknown")
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in all_users:
            # Personal repository PR
            if repo_name in personal_repo_stats:
                personal_repo_stats[repo_name] += 1
        else:
            # Organization repository PR
            if org_name in organization_stats:
                organization_stats[org_name]["pr_count"] += 1
                if repo_name in organization_stats[org_name]["repo_stats"]:
                    organization_stats[org_name]["repo_stats"][repo_name] += 1

    # Calculate user statistics (count MRs per user, sorted by count)
    user_stats = {}
    for pr in user_prs:
        user_login = pr.get("user_login", "Unknown")
        user_stats[user_login] = user_stats.get(user_login, 0) + 1

    # Sort users by MR count (descending)
    sorted_user_stats = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)

    return {
        "closed_prs_count": len(user_prs),
        "repos_contributed": repos_contributed,
        "closed_prs": user_prs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": organization_repos,
        "user_stats": sorted_user_stats,  # [(username, count), ...] sorted by count
    }


def get_app_interface_closed_all_stats(from_date, to_date):
    """Get App-interface closed MRs statistics for all users in the given date range."""
    try:
        app_interface_data = load_json_data(config.APP_INTERFACE_CLOSED_MR_FILE)
        # Extract MRs from the nested data structure
        if isinstance(app_interface_data, dict) and "data" in app_interface_data:
            app_interface_closed_mrs = app_interface_data["data"]
        else:
            # Fallback if data structure is different
            app_interface_closed_mrs = (
                app_interface_data if isinstance(app_interface_data, list) else []
            )
    except Exception as e:
        logger.warning(f"App-interface closed MRs data not available: {e}")
        app_interface_closed_mrs = []

    # Filter MRs by date range (all users)
    user_mrs = []
    repos_contributed = []
    organization_stats = {}  # For consistency, but app-interface is single repo
    personal_repos = []
    personal_repo_stats = {}

    for mr in app_interface_closed_mrs:
        # Check date range - use closed_at if available, otherwise use created_at
        closed_at = mr.get("closed_at") or mr.get("created_at")
        if not closed_at:
            continue

        try:
            # Parse closed_at datetime (assuming ISO format)
            closed_date = datetime.fromisoformat(
                closed_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= closed_date <= to_date_obj:
                user_mrs.append(mr)
                # App-interface is a single repository
                repo_name = "app-interface"
                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)
        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing date for closed app-interface MR: {e}")
            continue

    # For app-interface, treat as single personal repository
    if repos_contributed:
        personal_repos = ["app-interface"]
        personal_repo_stats = {"app-interface": len(user_mrs)}

    # Calculate user statistics (count MRs per user, sorted by count)
    user_stats = {}
    for mr in user_mrs:
        user_login = mr.get("user_login", "Unknown")
        user_stats[user_login] = user_stats.get(user_login, 0) + 1

    # Sort users by MR count (descending)
    sorted_user_stats = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)

    return {
        "closed_prs_count": len(user_mrs),
        "repos_contributed": repos_contributed,
        "closed_prs": user_mrs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": [],
        "user_stats": sorted_user_stats,  # [(username, count), ...] sorted by count
    }


def get_konflux_prs_count(
    github_stats,
    github_closed_stats,
    gitlab_stats,
    gitlab_closed_stats,
    app_interface_stats,
    app_interface_closed_stats,
):
    """Count all merged and closed PRs/MRs where user_login contains 'konflux'."""
    konflux_count = 0

    # Count GitHub PRs
    if "merged_prs" in github_stats:
        for pr in github_stats["merged_prs"]:
            user_login = pr.get("user_login", "").lower()
            if "konflux" in user_login:
                konflux_count += 1

    if "closed_prs" in github_closed_stats:
        for pr in github_closed_stats["closed_prs"]:
            user_login = pr.get("user_login", "").lower()
            if "konflux" in user_login:
                konflux_count += 1

    # Count GitLab MRs
    if "merged_prs" in gitlab_stats:
        for pr in gitlab_stats["merged_prs"]:
            user_login = pr.get("user_login", "").lower()
            if "konflux" in user_login:
                konflux_count += 1

    if "closed_prs" in gitlab_closed_stats:
        for pr in gitlab_closed_stats["closed_prs"]:
            user_login = pr.get("user_login", "").lower()
            if "konflux" in user_login:
                konflux_count += 1

    # Count App-interface MRs
    if "merged_prs" in app_interface_stats:
        for pr in app_interface_stats["merged_prs"]:
            user_login = pr.get("user_login", "").lower()
            if "konflux" in user_login:
                konflux_count += 1

    if "closed_prs" in app_interface_closed_stats:
        for pr in app_interface_closed_stats["closed_prs"]:
            user_login = pr.get("user_login", "").lower()
            if "konflux" in user_login:
                konflux_count += 1

    return konflux_count


def get_github_konflux_stats(from_date, to_date):
    """Get GitHub statistics for konflux users only in the given date range."""
    try:
        github_data = load_json_data(config.GH_MERGED_PR_FILE)
        # Extract PRs from the nested data structure
        github_merged_prs = []
        if isinstance(github_data, dict) and "data" in github_data:
            for repo_name, prs in github_data["data"].items():
                for pr in prs:
                    pr["repo_name"] = repo_name  # Add repo name to each PR
                    github_merged_prs.append(pr)
        else:
            # Fallback if data structure is different
            github_merged_prs = github_data if isinstance(github_data, list) else []
    except Exception as e:
        logger.warning(f"GitHub merged PRs data not available: {e}")
        github_merged_prs = []

    # Filter PRs by date range and konflux users only
    user_prs = []
    repos_contributed = []
    organization_stats = {}  # org_name: {repos: [], pr_count: 0, repo_stats: {}}
    personal_repos = []
    organization_repos = []

    # Track repos and their organizations
    repo_organizations = {}

    for pr in github_merged_prs:
        # Check if user is a konflux user
        user_login = pr.get("user_login", "").lower()
        if "konflux" not in user_login:
            continue

        # Check date range
        merged_at = pr.get("merged_at")
        if not merged_at:
            continue

        try:
            # Parse merged_at datetime (assuming ISO format)
            merged_date = datetime.fromisoformat(
                merged_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= merged_date <= to_date_obj:
                user_prs.append(pr)
                repo_name = pr.get("repo_name", "Unknown")

                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)

                # Extract organization from html_url
                html_url = pr.get("html_url", "")
                org_name = None
                if html_url:
                    # Extract organization from URL: https://github.com/ORG/REPO/pull/123
                    url_parts = html_url.split("/")
                    if len(url_parts) >= 5 and url_parts[2] == "github.com":
                        org_name = url_parts[3]

                # Store organization for this repo
                if org_name and repo_name not in repo_organizations:
                    repo_organizations[repo_name] = org_name

        except Exception as e:
            logger.warning(f"Error parsing merged_at date for PR: {e}")
            continue

    # Categorize repositories by organization and count PRs
    personal_repo_stats = {}  # repo_name: pr_count

    # Collect all konflux users from PRs
    konflux_users = set(pr.get("user_login") for pr in user_prs if pr.get("user_login"))

    for repo_name in repos_contributed:
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in konflux_users:
            # Consider it personal if it's a user repo (org name matches a user)
            personal_repos.append(repo_name)
            personal_repo_stats[repo_name] = 0  # Initialize PR count
        else:
            # Organization repository
            organization_repos.append(repo_name)
            if org_name not in organization_stats:
                organization_stats[org_name] = {
                    "repos": [],
                    "repo_stats": {},
                    "pr_count": 0,
                }
            if repo_name not in organization_stats[org_name]["repos"]:
                organization_stats[org_name]["repos"].append(repo_name)
                organization_stats[org_name]["repo_stats"][repo_name] = 0

    # Count PRs per repository and organization
    for pr in user_prs:
        repo_name = pr.get("repo_name", "Unknown")
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in konflux_users:
            # Personal repository PR
            if repo_name in personal_repo_stats:
                personal_repo_stats[repo_name] += 1
        else:
            # Organization repository PR
            if org_name in organization_stats:
                organization_stats[org_name]["pr_count"] += 1
                if repo_name in organization_stats[org_name]["repo_stats"]:
                    organization_stats[org_name]["repo_stats"][repo_name] += 1

    return {
        "merged_prs_count": len(user_prs),
        "repos_contributed": repos_contributed,
        "merged_prs": user_prs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": organization_repos,
    }


def get_github_konflux_closed_stats(from_date, to_date):
    """Get GitHub closed PR statistics for konflux users only in the given date range."""
    try:
        github_data = load_json_data(config.GH_CLOSED_PR_FILE)
        # Extract PRs from the nested data structure
        github_closed_prs = []
        if isinstance(github_data, dict) and "data" in github_data:
            for repo_name, prs in github_data["data"].items():
                for pr in prs:
                    pr["repo_name"] = repo_name  # Add repo name to each PR
                    github_closed_prs.append(pr)
        else:
            # Fallback if data structure is different
            github_closed_prs = github_data if isinstance(github_data, list) else []
    except Exception as e:
        logger.warning(f"GitHub closed PRs data not available: {e}")
        github_closed_prs = []

    # Filter PRs by date range and konflux users only
    user_prs = []
    repos_contributed = []
    organization_stats = {}  # org_name: {repos: [], pr_count: 0, repo_stats: {}}
    personal_repos = []
    organization_repos = []

    # Track repos and their organizations
    repo_organizations = {}

    for pr in github_closed_prs:
        # Check if user is a konflux user
        user_login = pr.get("user_login", "").lower()
        if "konflux" not in user_login:
            continue

        # Check date range - use closed_at if available, otherwise use created_at
        closed_at = pr.get("closed_at") or pr.get("created_at")
        if not closed_at:
            continue

        try:
            # Parse closed_at datetime (assuming ISO format)
            closed_date = datetime.fromisoformat(
                closed_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= closed_date <= to_date_obj:
                user_prs.append(pr)
                repo_name = pr.get("repo_name", "Unknown")

                if repo_name not in repos_contributed:
                    repos_contributed.append(repo_name)

                # Extract organization from html_url
                html_url = pr.get("html_url", "")
                org_name = None
                if html_url:
                    # Extract organization from URL: https://github.com/ORG/REPO/pull/123
                    url_parts = html_url.split("/")
                    if len(url_parts) >= 5 and url_parts[2] == "github.com":
                        org_name = url_parts[3]

                # Store organization for this repo
                if org_name and repo_name not in repo_organizations:
                    repo_organizations[repo_name] = org_name

        except (ValueError, AttributeError) as e:
            logger.debug(f"Error parsing date for closed PR: {e}")
            continue

    # Categorize repositories by organization and count PRs
    personal_repo_stats = {}  # repo_name: pr_count

    # Collect all konflux users from PRs
    konflux_users = set(pr.get("user_login") for pr in user_prs if pr.get("user_login"))

    for repo_name in repos_contributed:
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in konflux_users:
            # Consider it personal if it's a user repo (org name matches a user)
            personal_repos.append(repo_name)
            personal_repo_stats[repo_name] = 0  # Initialize PR count
        else:
            # Organization repository
            organization_repos.append(repo_name)
            if org_name not in organization_stats:
                organization_stats[org_name] = {
                    "repos": [],
                    "repo_stats": {},
                    "pr_count": 0,
                }
            if repo_name not in organization_stats[org_name]["repos"]:
                organization_stats[org_name]["repos"].append(repo_name)
                organization_stats[org_name]["repo_stats"][repo_name] = 0

    # Count PRs per repository and organization
    for pr in user_prs:
        repo_name = pr.get("repo_name", "Unknown")
        org_name = repo_organizations.get(repo_name)

        if not org_name or org_name in konflux_users:
            # Personal repository PR
            if repo_name in personal_repo_stats:
                personal_repo_stats[repo_name] += 1
        else:
            # Organization repository PR
            if org_name in organization_stats:
                organization_stats[org_name]["pr_count"] += 1
                if repo_name in organization_stats[org_name]["repo_stats"]:
                    organization_stats[org_name]["repo_stats"][repo_name] += 1

    return {
        "closed_prs_count": len(user_prs),
        "repos_contributed": repos_contributed,
        "closed_prs": user_prs,
        "organization_stats": organization_stats,
        "personal_repos": personal_repos,
        "personal_repo_stats": personal_repo_stats,
        "organization_repos": organization_repos,
    }


def get_jira_user_from_data():
    """Extract JIRA user from the tickets data since all tickets are for the expected user."""
    try:
        jira_data = load_json_data(config.JIRA_CLOSED_TICKETS_FILE)
        # Extract tickets from the nested data structure
        if isinstance(jira_data, dict) and "data" in jira_data:
            jira_closed_tickets = jira_data["data"]
        else:
            # Fallback if data structure is different
            jira_closed_tickets = jira_data if isinstance(jira_data, list) else []

        # Get assignee from the first ticket (all tickets should be for the same user)
        if jira_closed_tickets:
            first_ticket = jira_closed_tickets[0]
            assignee = first_ticket.get("assignee", "")
            if assignee:
                logger.info(f"Extracted JIRA user from ticket data: '{assignee}'")
                return assignee
    except Exception as e:
        logger.warning(f"Could not extract JIRA user from ticket data: {e}")

    return ""


def get_jira_personal_stats(username, from_date, to_date):
    """Get JIRA statistics for the user in the given date range."""
    if not username or username in ["Not available", "Unable to fetch user info"]:
        return {
            "closed_tickets_count": 0,
            "closed_tickets": [],
            "tickets_by_type": {},
            "issue_types": [],
        }

    try:
        jira_data = load_json_data(config.JIRA_CLOSED_TICKETS_FILE)
        # Extract tickets from the nested data structure
        if isinstance(jira_data, dict) and "data" in jira_data:
            jira_closed_tickets = jira_data["data"]
        else:
            # Fallback if data structure is different
            jira_closed_tickets = jira_data if isinstance(jira_data, list) else []
    except Exception as e:
        logger.warning(f"JIRA closed tickets data not available: {e}")
        jira_closed_tickets = []

    # Filter tickets by date range and group by issue type
    user_tickets = []
    tickets_by_type = {}

    for ticket in jira_closed_tickets:
        # Check date range - use resolved_at date
        resolved_at = ticket.get("resolved_at")
        if not resolved_at:
            continue

        try:
            # Parse resolved_at datetime
            resolved_date = datetime.fromisoformat(
                resolved_at.replace("Z", "+00:00")
            ).date()
            from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
            to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

            if from_date_obj <= resolved_date <= to_date_obj:
                user_tickets.append(ticket)

                # Group by issue type
                issue_type = ticket.get("issue_type", "Unknown")
                if issue_type not in tickets_by_type:
                    tickets_by_type[issue_type] = []
                tickets_by_type[issue_type].append(ticket)

        except Exception as e:
            logger.warning(f"Error parsing resolved_at date for ticket: {e}")
            continue

    # Get sorted list of issue types
    issue_types = sorted(tickets_by_type.keys())

    return {
        "closed_tickets_count": len(user_tickets),
        "closed_tickets": user_tickets,
        "tickets_by_type": tickets_by_type,
        "issue_types": issue_types,
    }


def calculate_comprehensive_diff_stats(all_prs_mrs):
    """Calculate comprehensive diff statistics from all PRs/MRs."""
    if not all_prs_mrs:
        return {
            "total_additions": 0,
            "total_deletions": 0,
            "total_files_changed": 0,
            "total_net_changes": 0,
            "avg_additions": 0,
            "avg_deletions": 0,
            "avg_files_changed": 0,
            "avg_net_changes": 0,
            "top_by_additions": [],
            "top_by_deletions": [],
            "top_by_total_changes": [],
            "top_by_files": [],
            "size_distribution": {"small": 0, "medium": 0, "large": 0, "huge": 0},
            "size_percentages": {"small": 0, "medium": 0, "large": 0, "huge": 0},
            "review_worthy_count": 0,
            "total_count": 0,
        }

    # Filter PRs/MRs with valid diff stats
    valid_prs = []
    for pr in all_prs_mrs:
        additions = pr.get("additions")
        deletions = pr.get("deletions")
        files = pr.get("changed_files")

        if additions is not None and deletions is not None:
            valid_prs.append(
                {
                    "title": pr.get("title", ""),
                    "html_url": pr.get("html_url", ""),
                    "number": pr.get("number", ""),
                    "repo_name": pr.get("repo_name", ""),
                    "additions": additions,
                    "deletions": deletions,
                    "changed_files": files or 0,
                    "total_changes": additions + deletions,
                    "net_changes": additions - deletions,
                    "created_at": pr.get("created_at"),
                    "merged_at": pr.get("merged_at"),
                }
            )

    if not valid_prs:
        return {
            "total_additions": 0,
            "total_deletions": 0,
            "total_files_changed": 0,
            "total_net_changes": 0,
            "avg_additions": 0,
            "avg_deletions": 0,
            "avg_files_changed": 0,
            "avg_net_changes": 0,
            "top_by_additions": [],
            "top_by_deletions": [],
            "top_by_total_changes": [],
            "top_by_files": [],
            "size_distribution": {"small": 0, "medium": 0, "large": 0, "huge": 0},
            "size_percentages": {"small": 0, "medium": 0, "large": 0, "huge": 0},
            "review_worthy_count": 0,
            "total_count": 0,
        }

    # Calculate totals
    total_additions = sum(pr["additions"] for pr in valid_prs)
    total_deletions = sum(pr["deletions"] for pr in valid_prs)
    total_files = sum(pr["changed_files"] for pr in valid_prs)
    total_net_changes = total_additions - total_deletions
    count = len(valid_prs)

    # Calculate averages
    avg_additions = round(total_additions / count, 1)
    avg_deletions = round(total_deletions / count, 1)
    avg_files = round(total_files / count, 1)
    avg_net_changes = round(total_net_changes / count, 1)

    # Size categorization (industry-standard thresholds)
    size_counts = {"small": 0, "medium": 0, "large": 0, "huge": 0}
    review_worthy_count = 0

    for pr in valid_prs:
        total_changes = pr["total_changes"]
        if total_changes <= 50:  # Small: 1-50 lines
            size_counts["small"] += 1
        elif total_changes <= 300:  # Medium: 51-300 lines
            size_counts["medium"] += 1
        elif total_changes <= 1000:  # Large: 301-1000 lines
            size_counts["large"] += 1
            review_worthy_count += 1  # Large PRs need more attention
        else:  # Huge: 1000+ lines
            size_counts["huge"] += 1
            review_worthy_count += 1

    # Calculate percentages
    size_percentages = {
        size: round((count / len(valid_prs)) * 100, 1)
        for size, count in size_counts.items()
    }

    # Top lists (top 10 each)
    top_by_additions = sorted(valid_prs, key=lambda x: x["additions"], reverse=True)[
        :10
    ]
    top_by_deletions = sorted(valid_prs, key=lambda x: x["deletions"], reverse=True)[
        :10
    ]
    top_by_total_changes = sorted(
        valid_prs, key=lambda x: x["total_changes"], reverse=True
    )[:10]
    top_by_files = sorted(valid_prs, key=lambda x: x["changed_files"], reverse=True)[
        :10
    ]

    return {
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "total_files_changed": total_files,
        "total_net_changes": total_net_changes,
        "avg_additions": avg_additions,
        "avg_deletions": avg_deletions,
        "avg_files_changed": avg_files,
        "avg_net_changes": avg_net_changes,
        "top_by_additions": top_by_additions,
        "top_by_deletions": top_by_deletions,
        "top_by_total_changes": top_by_total_changes,
        "top_by_files": top_by_files,
        "size_distribution": size_counts,
        "size_percentages": size_percentages,
        "review_worthy_count": review_worthy_count,
        "total_count": count,
    }


def get_combined_diff_stats(
    username_github,
    username_gitlab,
    from_date,
    to_date,
    source_filter=None,
    exclude_personal=False,
):
    """Get combined diff statistics from GitHub, GitLab, and App-interface.

    Note: This function only includes MERGED PRs/MRs since diff statistics are only
    meaningful for changes that were actually merged into the codebase.

    Args:
        username_github: GitHub username
        username_gitlab: GitLab username
        from_date: Start date string
        to_date: End date string
        source_filter: Filter by source - 'github', 'gitlab', 'app-interface', or None for all
        exclude_personal: If True, exclude personal repositories from statistics
    """
    all_prs_mrs = []

    # Get GitHub merged PRs only - only if not filtered out
    if username_github and (source_filter is None or source_filter == "github"):
        try:
            github_merged_data = load_json_data(config.GH_MERGED_PR_FILE)
            if isinstance(github_merged_data, dict) and "data" in github_merged_data:
                for repo_name, prs in github_merged_data["data"].items():
                    for pr in prs:
                        if pr.get("user_login") == username_github:
                            pr["repo_name"] = repo_name
                            pr["source"] = "GitHub"
                            pr["type"] = "merged"
                            if is_in_date_range(
                                pr.get("merged_at"), from_date, to_date
                            ):
                                all_prs_mrs.append(pr)

        except Exception as e:
            logger.warning(f"Error loading GitHub data for diff stats: {e}")

    # Get GitLab merged MRs only - only if not filtered out
    if username_gitlab and (source_filter is None or source_filter == "gitlab"):
        try:
            gitlab_merged_data = load_json_data(config.GL_MERGED_PR_FILE)
            if isinstance(gitlab_merged_data, dict) and "data" in gitlab_merged_data:
                for repo_name, mrs in gitlab_merged_data["data"].items():
                    for mr in mrs:
                        if mr.get("user_login") == username_gitlab:
                            mr["repo_name"] = repo_name
                            mr["source"] = "GitLab"
                            mr["type"] = "merged"
                            if is_in_date_range(
                                mr.get("merged_at"), from_date, to_date
                            ):
                                all_prs_mrs.append(mr)

        except Exception as e:
            logger.warning(f"Error loading GitLab data for diff stats: {e}")

    # Get App-interface merged MRs only - only if not filtered out
    if username_gitlab and (source_filter is None or source_filter == "app-interface"):
        try:
            app_merged_data = load_json_data(config.APP_INTERFACE_MERGED_MR_FILE)
            if isinstance(app_merged_data, dict) and "data" in app_merged_data:
                for mr in app_merged_data["data"]:
                    if mr.get("user_login") == username_gitlab:
                        mr["repo_name"] = "app-interface"
                        mr["source"] = "App-interface"
                        mr["type"] = "merged"
                        if is_in_date_range(mr.get("merged_at"), from_date, to_date):
                            all_prs_mrs.append(mr)

        except Exception as e:
            logger.warning(f"Error loading App-interface data for diff stats: {e}")

    # Filter out personal repositories if requested
    if exclude_personal and all_prs_mrs:
        # Get personal repository lists from the stats
        github_personal_repos = set()
        gitlab_personal_repos = set()

        if username_github:
            github_stats = get_github_personal_stats(
                username_github, from_date, to_date
            )
            if github_stats.get("personal_repos"):
                github_personal_repos = set(github_stats["personal_repos"])

        if username_gitlab:
            gitlab_stats = get_gitlab_personal_stats(
                username_gitlab, from_date, to_date
            )
            if gitlab_stats.get("personal_repos"):
                gitlab_personal_repos = set(gitlab_stats["personal_repos"])

        # Filter out PRs/MRs from personal repositories
        filtered_prs_mrs = []
        for pr_mr in all_prs_mrs:
            repo_name = pr_mr.get("repo_name", "")
            source = pr_mr.get("source", "")

            # Skip if it's from a personal repository
            if source == "GitHub" and repo_name in github_personal_repos:
                continue
            elif source == "GitLab" and repo_name in gitlab_personal_repos:
                continue
            # App-interface is never personal, so include it

            filtered_prs_mrs.append(pr_mr)

        all_prs_mrs = filtered_prs_mrs

    return calculate_comprehensive_diff_stats(all_prs_mrs)


def is_in_date_range(date_str, from_date, to_date):
    """Check if a date string is within the given date range."""
    if not date_str:
        return False

    try:
        # Parse the date (handle both ISO format and simple date format)
        if "T" in date_str:
            date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        else:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()

        from_date_obj = datetime.strptime(from_date, "%Y-%m-%d").date()
        to_date_obj = datetime.strptime(to_date, "%Y-%m-%d").date()

        return from_date_obj <= date_obj <= to_date_obj
    except Exception:
        return False
