import logging
import re

from jira.exceptions import JIRAError
import requests
from flask import Blueprint, flash, render_template, request

import config
from blueprints.pull_requests import get_github_merged_pr
from services import github_service, gitlab_service
from services.jira import JiraAPI
from utils.helpers import load_json_data, save_json_data_and_return

logger = logging.getLogger(__name__)
deployments_bp = Blueprint("deployments", __name__)

try:
    jira_api = JiraAPI()
except JIRAError as err:
    # Log concise error without full HTML response
    error_msg = f"HTTP {err.status_code}" if hasattr(err, "status_code") else str(err)
    logger.error(f"Unable to connect to JIRA API - check your JIRA token: {error_msg}")
    jira_api = None
except Exception as err:
    logger.error(
        f"Unable to connect to JIRA API - check your JIRA token: {type(err).__name__}"
    )
    jira_api = None

try:
    gh = github_service.GithubAPI()
except Exception as err:
    logger.error(f"Unable to connect to GitHub API - check your GitHub token: {err}")
    gh = None


@deployments_bp.route("/")
def index():
    """
    Download and display deployments data.

    reload_data=True: download new deployments data
    reload_data_for=<deployment_name>: download data for specific deployment
    """
    data_file_exists = config.DEPLOYMENTS_FILE.is_file()

    if not config.GITLAB_TOKEN or config.GITLAB_TOKEN == "add_me":
        flash("GITLAB_TOKEN is not set", "warning")
        return render_template("errors/gitlab_token_not_set.html")

    if not config.GITHUB_TOKEN or config.GITHUB_TOKEN == "add_me":
        flash("GITHUB_TOKEN is not set", "warning")
        return render_template("errors/github_token_not_set.html")

    if (
        not config.JIRA_PERSONAL_ACCESS_TOKEN
        or config.JIRA_PERSONAL_ACCESS_TOKEN == "add_me"
    ):
        flash("JIRA_PERSONAL_ACCESS_TOKEN is not set", "warning")
        return render_template("errors/jira_token_not_set.html")

    # Update data for specific deployment
    if "reload_data_for" in request.args:
        deployment_name = request.args.get("reload_data_for")
        update_deployment(deployment_name)

    # Get all deployments data (from file or download new)
    reload_data = "reload_data" in request.args
    deployments = get_all_deployments(reload_data)

    return render_template(
        "deployments/main.html",
        deployments=deployments,
        data_file_exists=data_file_exists,
    )


def get_all_deployments(reload_data=None):
    """
    Get all deployments data (from file or download new).

    reload_data=True: download new deployments data
    """
    if not config.DEPLOYMENTS_FILE.is_file() and not reload_data:
        flash("Deployments data not found, please update the data", "info")
        return {}

    if not config.GITLAB_TOKEN or not config.GITHUB_TOKEN:
        logger.error("GITLAB_TOKEN or GITHUB_TOKEN is not set")
        return {}

    if reload_data:
        try:
            deployments = gitlab_service.GitlabAPI().get_app_interface_deployments()
            add_merged_pr_to_all_deployments(deployments)
            flash("Deployments updated successfully", "success")
        except requests.exceptions.ConnectionError as err:
            flash(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token",
                "warning",
            )
            flash("Deployments data not updated", "warning")
            logger.error(err)

    return load_json_data(config.DEPLOYMENTS_FILE)


def update_deployment(deployment_name):
    """
    Update deployment data.
    The data will be updated with the new commits and related pull requests.

    :param deployment_name: name of the deployment to update
    """
    if not config.GITLAB_TOKEN or not config.GITHUB_TOKEN:
        logger.error("GITLAB_TOKEN or GITHUB_TOKEN is not set")
        return

    try:
        gitlab_service.GitlabAPI().update_deployment_data(deployment_name)
    except requests.exceptions.ConnectionError as err:
        flash(
            "Unable to connect to GitLab API - check your VPN connection and GitLab token",
            "warning",
        )
        flash("Deployments data not updated", "warning")
        logger.error(err)
        return

    deployments = gh.add_github_data_to_deployment(deployment_name)
    deployment = deployments.get(deployment_name)

    repo_name = deployment.get("repo_name")
    merged_pulls = get_github_merged_pr(reload_data=True)[repo_name.split("/")[-1]]

    add_merged_pr_to_deployment(deployment, merged_pulls)

    flash(f"Deployment '{deployment_name}' data updated successfully", "success")

    return save_json_data_and_return(deployments, config.DEPLOYMENTS_FILE)


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


def add_merged_pr_to_all_deployments(deployments):
    """
    Add merged pull requests details to all deployments.
    """
    # Update merged pull requests data
    merged_pulls = get_github_merged_pr(reload_data=True)

    # Add merged pull requests details to each deployment
    for deployment_name, deployment in deployments.items():
        logger.info(
            f"Downloading deployment '{deployment_name}' related merged pull requests."
        )
        repo_name = deployment.get("repo_name")
        deployment = add_merged_pr_to_deployment(
            deployment, merged_pulls[repo_name.split("/")[-1]]
        )

    return save_json_data_and_return(deployments, config.DEPLOYMENTS_FILE)


def add_merged_pr_to_deployment(deployment, merged_pulls):
    """
    Add merged pull requests details to the specific deployment.
    """
    repo_name = deployment.get("repo_name")
    github_repo = gh.github_api.get_repo(repo_name)
    deployment = add_commits_related_with_deployment(deployment, github_repo)
    deployment = add_merged_pull_requests_to_deployment(deployment, merged_pulls)
    return deployment


def add_commits_related_with_deployment(deployment, github_repo):
    """
    Add data about commits related to the specific deployment.
    """
    commit_default_branch = deployment.get("commit_default_branch")
    commit_prod = deployment.get("commit_prod")
    commit_stage = deployment.get("commit_stage")
    stage_deployment_type = deployment.get("stage_deployment_type")
    prod_deployment_type = deployment.get("prod_deployment_type")
    deployment["prod_stage_commits"] = []
    deployment["stage_default_commits"] = []
    deployment["prod_default_commits"] = []

    if (
        prod_deployment_type == "manual"
        and commit_prod
        and commit_stage
        and commit_prod != commit_stage
    ):
        comparison = github_repo.compare(commit_prod, commit_stage)
        deployment["prod_stage_commits"] = [commit.sha for commit in comparison.commits]

    if (
        stage_deployment_type == "manual"
        and commit_stage
        and commit_default_branch
        and commit_stage != commit_default_branch
    ):
        comparison = github_repo.compare(commit_stage, commit_default_branch)
        deployment["stage_default_commits"] = [
            commit.sha for commit in comparison.commits
        ]

    if (
        prod_deployment_type == "manual"
        and commit_prod
        and commit_default_branch
        and commit_prod != commit_default_branch
    ):
        comparison = github_repo.compare(commit_prod, commit_default_branch)
        deployment["prod_default_commits"] = [
            commit.sha for commit in comparison.commits
        ]

    return deployment


def add_merged_pull_requests_to_deployment(depl_data, merged_pulls):
    """
    Add data about merged pull requests related to a specific deployment.
    """
    depl_data["prod_stage_pulls"] = []
    depl_data["stage_default_pulls"] = []
    depl_data["prod_default_pulls"] = []
    if not merged_pulls:
        return depl_data

    related_pulls_ids = set()
    for env in ("prod_stage", "stage_default", "prod_default"):
        for commit in depl_data[f"{env}_commits"]:
            for pr in merged_pulls:
                if pr.get("merge_commit_sha") == commit:
                    related_pulls_ids.add(int(pr.get("number")))
                    pr = add_jira_ticket_ref_to_pull_request(pr)
                    depl_data[f"{env}_pulls"].append(pr)
                    break
        if related_pulls_ids:
            depl_data = add_qe_comments_to_pull_requests(depl_data, related_pulls_ids)

    return depl_data


def add_qe_comments_to_pull_requests(depl_data, pulls_ids):
    """
    Add data about QE comments related to a specific deployment.
    """
    repo_owner, repo_name = depl_data.get("repo_name").split("/")
    query_parts = []
    for pr_id in pulls_ids:
        query_parts.append(
            f"""
            pr{pr_id}: pullRequest(number: {pr_id}) {{
                ...prFields
            }}
        """
        )

    query = f"""
    {{
    repository(owner: "{repo_owner}", name: "{repo_name}") {{
        {"".join(query_parts)}
    }}
    }}

    fragment prFields on PullRequest {{
    number
    comments(first: 50) {{
        nodes {{
        body
        author {{
            login
        }}
        }}
    }}
    }}
    """

    output = gh.github_api.requester.graphql_query(query, {})
    data = output[1].get("data").get("repository")

    for pr_data in data.values():
        if not pr_data.get("comments").get("nodes"):
            continue
        for comment in pr_data.get("comments").get("nodes"):
            body = comment.get("body")
            if body.startswith("QE:") or body.startswith("QA:"):
                author = comment.get("author").get("login")
                pr_ids = pr_data.get("number")
                qe_comment = {
                    "comment_body": body[3:],
                    "comment_author": author,
                }
                # Add QE comment to all pull request lists
                for pull_list_key in [
                    "prod_stage_pulls",
                    "prod_default_pulls",
                    "stage_default_pulls",
                ]:
                    for i, pr in enumerate(depl_data[pull_list_key]):
                        if pr.get("number") == pr_ids:
                            pr["qe_comment"] = qe_comment
                            depl_data[pull_list_key][i] = pr

    return depl_data


def add_jira_ticket_ref_to_pull_request(pr):
    """
    Add data about Jira tickets related to a specific pull request.
    """
    jira_tickets = set()
    jira_project_id = config.JIRA_PROJECT
    pattern = f"{jira_project_id}-\\d+"

    matches = re.findall(pattern, pr.get("title"))
    for match in matches:
        jira_tickets.add(match)

    if pr.get("description"):
        matches = re.findall(pattern, pr.get("description"))
        for match in matches:
            jira_tickets.add(match)

    if jira_tickets:
        pr["jira_tickets"] = []
        for ticket in jira_tickets:
            ticket_data = jira_api.get_jira_ticket(ticket)
            pr["jira_tickets"].append(ticket_data)

    return pr
