import json
import logging

from flask import Blueprint, render_template, request

import config
from services import gitlab_service

logger = logging.getLogger(__name__)
deployments_bp = Blueprint("deployments", __name__)


@deployments_bp.route("/")
def index():
    """Deployments page."""
    reload_data = "reload_data" in request.args
    deployments = get_deployments(reload_data)
    return render_template("deployments/main.html", deployments=deployments)


def get_deployments(reload_data=None):
    """
    Get deployments data from the file or download them.
    """
    if config.GITLAB_TOKEN and config.GITHUB_TOKEN:
        if not config.DEPLOYMENTS_FILE.is_file() or reload_data:
            try:
                _get_deployments()
            except Exception as err:
                logger.error(err)
    else:
        if not config.DEPLOYMENTS_FILE.is_file():
            return {}

    with open(config.DEPLOYMENTS_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file)


def _get_deployments():
    gitlab_api = gitlab_service.GitlabAPI()
    gitlab_api.get_app_interface_deployments()


def get_stage_commit_style(deployment):
    """
    Returns the color attribute for stage commit.
    """
    if deployment["commit_stage"] == deployment["commit_prod"]:
        return "style=color:green;"
    return ""


def get_default_branch_commit_style(deployment):
    """
    Returns the color attribute for default branch last commit.
    """
    if deployment["commit_default_branch"] == deployment["commit_prod"]:
        return "style=color:green;"
    elif deployment["commit_default_branch"] == deployment["commit_stage"]:
        return ""
    return "style=color:black;"
