import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request

import config
from utils import load_json_data
from blueprints.jira_tickets import get_jira_config_info

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
    gitlab_stats = get_gitlab_personal_stats(
        gitlab_username, from_date, to_date
    )  # Now includes app-interface
    jira_stats = get_jira_personal_stats(jira_user, from_date, to_date)

    # Calculate overall stats
    total_prs = github_stats["merged_prs_count"] + gitlab_stats["merged_prs_count"]
    all_repos = github_stats["repos_contributed"] + gitlab_stats["repos_contributed"]
    total_repos = len(set(all_repos))

    overall_stats = {
        "total_prs": total_prs,
        "total_repos": total_repos,
        "most_active_repo": get_most_active_repo(all_repos),
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
        jira_stats=jira_stats,
        overall_stats=overall_stats,
        jira_config=jira_config,
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

    # Also include app-interface MRs since app-interface is a GitLab repository
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

        # Add app-interface MRs to GitLab MRs
        for mr in app_interface_merged_mrs:
            mr["repo_name"] = "app-interface"  # Set consistent repo name
            gitlab_merged_prs.append(mr)

    except Exception as e:
        logger.warning(f"App-interface merged MRs data not available: {e}")
        # Continue without app-interface data

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
        return {"merged_prs_count": 0, "repos_contributed": [], "merged_prs": []}

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


def get_most_active_repo(repos_list):
    """Get the most frequently contributed repository."""
    if not repos_list:
        return "None"

    # Count repo contributions
    repo_counts = {}
    for repo in repos_list:
        repo_counts[repo] = repo_counts.get(repo, 0) + 1

    # Return the repo with most contributions
    most_active = max(repo_counts, key=repo_counts.get)
    return f"{most_active} ({repo_counts[most_active]})"
