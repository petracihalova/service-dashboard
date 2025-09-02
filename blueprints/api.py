import logging

import requests
from flask import Blueprint, jsonify

import config
from services.github_service import GithubAPI
from services.gitlab_service import GitlabAPI
from services.jira import JiraAPI

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__)


@api_bp.route("/check-prerequisites", methods=["POST"])
def check_prerequisites():
    """Check if all required tokens are valid and services are accessible."""
    try:
        results = {
            "github_token": False,
            "gitlab_token": False,
            "jira_token": False,
            "all_valid": False,
            "error_message": "",
        }

        errors = []

        # Check GitHub token
        try:
            if config.GITHUB_TOKEN:
                # Try to make a simple API call to verify token
                GithubAPI()  # This will test the token during initialization
                results["github_token"] = True
                logger.debug("GitHub token is valid")
            else:
                errors.append("GitHub token not configured")
                logger.debug("GitHub token not configured")
        except Exception as e:
            errors.append(f"GitHub token invalid: {str(e)}")
            logger.debug(f"GitHub token check failed: {e}")

        # Check GitLab token and VPN connectivity
        try:
            if config.GITLAB_TOKEN:
                # Try to connect to GitLab API to verify token and VPN
                gitlab_api = GitlabAPI()
                # Test connection by trying to authenticate
                gitlab_api.gitlab_api.auth()
                results["gitlab_token"] = True
                logger.debug("GitLab token and VPN connectivity verified")
            else:
                errors.append("GitLab token not configured")
                logger.debug("GitLab token not configured")
        except requests.exceptions.ConnectionError:
            errors.append("GitLab connection failed - check VPN connection")
            logger.debug("GitLab connection failed - VPN issue")
        except Exception as e:
            errors.append(f"GitLab token invalid: {str(e)}")
            logger.debug(f"GitLab token check failed: {e}")

        # Check JIRA token
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
                    errors.append("JIRA token verification failed")
            else:
                errors.append("JIRA token not configured")
                logger.debug("JIRA token not configured")
        except Exception as e:
            errors.append(f"JIRA token invalid: {str(e)}")
            logger.debug(f"JIRA token check failed: {e}")

        # Check if all are valid
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
                "error_message": f"Internal error: {str(e)}",
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
