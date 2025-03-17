import json
import logging
import re

from flask import Blueprint, render_template, request

import config
from services import github_service, gitlab_service
from services.jira import JiraAPI
from utils.helpers import save_json_data_and_return

logger = logging.getLogger(__name__)
deployments_bp = Blueprint("deployments", __name__)

jira_api = JiraAPI()


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
    try:
        gitlab_api = gitlab_service.GitlabAPI()
        deployments = gitlab_api.get_app_interface_deployments()
    except Exception as err:
        logger.error(err)
        with open(config.DEPLOYMENTS_FILE, mode="r", encoding="utf-8") as file:
            deployments = json.load(file)
    _add_merged_pr_to_deployments(deployments)


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


def _add_merged_pr_to_deployments(deployments):
    with open(config.GH_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
        merged_pulls = json.load(file).get("data")

    github_api = github_service.GithubAPI().github_api
    for name, depl_data in deployments.items():
        logger.info(f"Downloading deployment '{name}' related merged pull requests.")
        repo_name = depl_data.get("repo_name")

        github_repo = github_api.get_repo(repo_name)
        depl_data = _add_commits_related_with_deployment(depl_data, github_repo)
        depl_data = _add_merged_pull_requests_to_deployment(
            depl_data, github_api, merged_pulls[repo_name.split("/")[-1]]
        )

    return save_json_data_and_return(deployments, config.DEPLOYMENTS_FILE)


def _add_commits_related_with_deployment(data, github_repo):
    commit_default_branch = data.get("commit_default_branch")
    commit_prod = data.get("commit_prod")
    commit_stage = data.get("commit_stage")
    stage_deployment_type = data.get("stage_deployment_type")
    prod_deployment_type = data.get("prod_deployment_type")
    data["prod_stage_commits"] = []
    data["stage_default_commits"] = []
    data["prod_default_commits"] = []

    if prod_deployment_type == "manual" and commit_prod != commit_stage:
        comparison = github_repo.compare(commit_prod, commit_stage)
        data["prod_stage_commits"] = [commit.sha for commit in comparison.commits]

    if stage_deployment_type == "manual" and commit_stage != commit_default_branch:
        comparison = github_repo.compare(commit_stage, commit_default_branch)
        data["stage_default_commits"] = [commit.sha for commit in comparison.commits]

    if stage_deployment_type == "manual" and commit_prod != commit_default_branch:
        comparison = github_repo.compare(commit_prod, commit_default_branch)
        data["prod_default_commits"] = [commit.sha for commit in comparison.commits]

    return data


def _add_merged_pull_requests_to_deployment(depl_data, github_api, merged_pulls):
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
                    pr = _add_jira_ticket_ref_to_pull_request(pr)
                    depl_data[f"{env}_pulls"].append(pr)
                    break
        if related_pulls_ids:
            depl_data = _add_qe_comments_to_pull_requests(
                depl_data, related_pulls_ids, github_api
            )

    return depl_data


def _add_qe_comments_to_pull_requests(depl_data, pulls_ids, github_api):
    depl_data["stage_default_pulls"] = []
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

    output = github_api.requester.graphql_query(query, {})
    data = output[1].get("data").get("repository")

    for pr_data in data.values():
        if len(pr_data.get("comments")) > 0:
            for comment in pr_data.get("comments").get("nodes"):
                body = comment.get("body")
                if body.startswith("QE:") or body.startswith("QA:"):
                    author = comment.get("author").get("login")
                    pr_ids = pr_data.get("number")
                    qe_comment = {
                        "comment_body": body[3:],
                        "comment_author": author,
                    }
                    for i, pr in enumerate(depl_data["prod_stage_pulls"]):
                        if pr.get("number") == pr_ids:
                            pr["qe_comment"] = qe_comment
                            depl_data["prod_stage_pulls"][i] = pr

                    for i, pr in enumerate(depl_data["prod_default_pulls"]):
                        if pr.get("number") == pr_ids:
                            pr["qe_comment"] = qe_comment
                            depl_data["prod_default_pulls"][i] = pr

                    for i, pr in enumerate(depl_data["stage_default_pulls"]):
                        if pr.get("number") == pr_ids:
                            pr["qe_comment"] = qe_comment
                            depl_data["stage_default_pulls"][i] = pr

    return depl_data


def _add_jira_ticket_ref_to_pull_request(pr):
    jira_tickets = set()
    jira_project_id = config.JIRA_PROJECT
    pattern = f"{jira_project_id}-\d+"

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
