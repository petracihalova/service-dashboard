from flask import Blueprint, jsonify, request

import config
from services.jira import JiraAPI

jira_bp = Blueprint("jira", __name__)


@jira_bp.route("/create_jira_ticket", methods=["POST"])
def create_new_jira_ticket():
    data = request.get_json()
    repo_name = data.get("repo_name").split("/")[1]
    # Security ID 11697 = Red Hat Employee
    options = {
        "project": {"key": config.JIRA_PROJECT},
        "summary": f"[{repo_name}] prod release",
        "description": "",
        "issuetype": {"name": "Task"},
        "labels": ["platform-accessmanagement"],
        "security": {"id": "11697"},
    }
    jira_api = JiraAPI()
    new_issue = jira_api.create_jira_ticket(options)
    link = new_issue.get("url")
    id = new_issue.get("ticket_id")
    message = f'New JIRA ticket \'<a href="{link}" target="_blank">{id}</a>\' created!'
    return jsonify({"message": message})
