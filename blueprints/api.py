import logging
import re

import requests
from flask import Blueprint, jsonify, request

import config
from services.github_service import GithubAPI
from services.gitlab_service import GitlabAPI
from services.jira import JiraAPI

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


def determine_required_checks(selected_sources):
    """Determine which prerequisite checks are needed based on selected data sources.

    Args:
        selected_sources: List of source IDs (e.g., ['open-prs', 'jira-open'])

    Returns:
        tuple: (needs_github, needs_gitlab, needs_jira)
    """
    needs_github = False
    needs_gitlab = False
    needs_jira = False

    # Check if we have any GitHub/GitLab repos configured
    github_repos_exist = has_github_repos()
    gitlab_repos_exist = has_gitlab_repos()

    logger.debug(
        f"GitHub repos exist: {github_repos_exist}, GitLab repos exist: {gitlab_repos_exist}"
    )

    for source_id in selected_sources:
        # Deployments requires everything (always)
        if source_id == "deployments":
            needs_github = True
            needs_gitlab = True
            needs_jira = True

        # JIRA sources need only JIRA
        elif source_id in ["jira-open", "jira-reported", "jira-closed"]:
            needs_jira = True

        # App-interface sources need only GitLab
        elif source_id in [
            "app-interface-open",
            "app-interface-merged",
            "app-interface-closed",
        ]:
            needs_gitlab = True

        # Regular PR sources need GitHub and/or GitLab depending on what repos exist
        elif source_id in ["open-prs", "merged-prs", "closed-prs"]:
            needs_github = needs_github or github_repos_exist
            needs_gitlab = needs_gitlab or gitlab_repos_exist

    return needs_github, needs_gitlab, needs_jira


def has_github_repos():
    """Check if there are any GitHub repositories configured in services_links.yml"""
    try:
        from blueprints.overview import get_services_links

        services_data = get_services_links()

        # Check if any service has a GitHub repo link
        # Structure: categories -> category_repos -> links -> link_value
        for category in services_data.get("categories", []):
            for repo in category.get("category_repos", []):
                for link in repo.get("links", []):
                    link_value = link.get("link_value", "")
                    if re.match(config.GH_REPO_PATTERN, link_value):
                        return True
        return False
    except Exception as e:
        logger.warning(f"Could not check for GitHub repos: {e}")
        return True  # Assume they exist if we can't check


def has_gitlab_repos():
    """Check if there are any GitLab repositories configured in services_links.yml"""
    try:
        from blueprints.overview import get_services_links

        services_data = get_services_links()

        # Check if any service has a GitLab repo link
        # Structure: categories -> category_repos -> links -> link_value
        for category in services_data.get("categories", []):
            for repo in category.get("category_repos", []):
                for link in repo.get("links", []):
                    link_value = link.get("link_value", "")
                    if re.match(config.GL_REPO_PATTERN, link_value):
                        return True
        return False
    except Exception as e:
        logger.warning(f"Could not check for GitLab repos: {e}")
        return True  # Assume they exist if we can't check


@api_bp.route("/check-prerequisites", methods=["POST"])
def check_prerequisites():
    """Check if required tokens are valid based on selected data sources.

    Accepts a list of selected data sources and only checks the prerequisites
    that are actually needed for those sources.
    """
    try:
        # Get selected data sources from request
        data = request.get_json() or {}
        selected_sources = data.get("selected_sources", [])

        logger.info(f"Checking prerequisites for sources: {selected_sources}")

        # Determine which checks are needed
        needs_github, needs_gitlab, needs_jira = determine_required_checks(
            selected_sources
        )

        logger.info(
            f"Required checks - GitHub: {needs_github}, GitLab: {needs_gitlab}, JIRA: {needs_jira}"
        )

        results = {
            "github_token": None,  # None means not checked/not needed
            "gitlab_token": None,
            "jira_token": None,
            "github_needed": needs_github,
            "gitlab_needed": needs_gitlab,
            "jira_needed": needs_jira,
            "all_valid": False,
            "error_message": "",
        }

        errors = []

        # Check GitHub token (only if needed)
        if needs_github:
            try:
                if config.GITHUB_TOKEN:
                    # Try to make a simple API call to verify token
                    GithubAPI()  # This will test the token during initialization
                    results["github_token"] = True
                    logger.debug("GitHub token is valid")
                else:
                    results["github_token"] = False
                    errors.append("GitHub token not configured")
                    logger.debug("GitHub token not configured")
            except Exception as e:
                results["github_token"] = False
                errors.append(f"GitHub token invalid: {str(e)}")
                logger.debug(f"GitHub token check failed: {e}")
        else:
            results["github_token"] = (
                True  # Set to True if not needed (so it doesn't block)
            )
            logger.debug("GitHub check skipped (not needed for selected sources)")

        # Check GitLab token and VPN connectivity (only if needed)
        if needs_gitlab:
            try:
                if config.GITLAB_TOKEN:
                    # Try to connect to GitLab API to verify token and VPN
                    gitlab_api = GitlabAPI()
                    # Test connection by trying to authenticate
                    gitlab_api.gitlab_api.auth()
                    results["gitlab_token"] = True
                    logger.debug("GitLab token and VPN connectivity verified")
                else:
                    results["gitlab_token"] = False
                    errors.append("GitLab token not configured")
                    logger.debug("GitLab token not configured")
            except requests.exceptions.ConnectionError:
                results["gitlab_token"] = False
                errors.append("GitLab connection failed - check VPN connection")
                logger.debug("GitLab connection failed - VPN issue")
            except Exception as e:
                results["gitlab_token"] = False
                errors.append(f"GitLab token invalid: {str(e)}")
                logger.debug(f"GitLab token check failed: {e}")
        else:
            results["gitlab_token"] = True  # Set to True if not needed
            logger.debug("GitLab check skipped (not needed for selected sources)")

        # Check JIRA token (only if needed)
        if needs_jira:
            try:
                if config.JIRA_PERSONAL_ACCESS_TOKEN:
                    # Try to connect to JIRA API
                    jira_api = JiraAPI()
                    # Test by getting current user
                    current_user = jira_api.jira_api.current_user()
                    if current_user:
                        results["jira_token"] = True
                        logger.debug("JIRA token is valid")
                    else:
                        results["jira_token"] = False
                        errors.append("JIRA token verification failed")
                else:
                    results["jira_token"] = False
                    errors.append("JIRA token not configured")
                    logger.debug("JIRA token not configured")
            except Exception as e:
                results["jira_token"] = False
                errors.append(f"JIRA token invalid: {str(e)}")
                logger.debug(f"JIRA token check failed: {e}")
        else:
            results["jira_token"] = True  # Set to True if not needed
            logger.debug("JIRA check skipped (not needed for selected sources)")

        # Check if all REQUIRED checks are valid
        results["all_valid"] = all(
            [results["github_token"], results["gitlab_token"], results["jira_token"]]
        )

        if not results["all_valid"]:
            results["error_message"] = "Prerequisites not met: " + "; ".join(errors)

        logger.info(f"Prerequisites check result: {results['all_valid']}")
        return jsonify(results)

    except Exception as e:
        logger.error(f"Error checking prerequisites: {e}")
        return jsonify(
            {
                "github_token": False,
                "gitlab_token": False,
                "jira_token": False,
                "all_valid": False,
                "error_message": "An internal error has occurred.",
            }
        ), 500


@api_bp.route("/bulk-update-status")
def bulk_update_status():
    """Get the current status of bulk update process."""
    # This could be implemented with Redis or database if needed
    # For now, just return a simple response
    return jsonify(
        {
            "status": "idle",
            "progress": 0,
            "current_step": None,
            "message": "No update in progress",
        }
    )
