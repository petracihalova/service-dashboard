import json
from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for
from markupsafe import escape

import blueprints
import config

release_notes_bp = Blueprint("release_notes", __name__)


@release_notes_bp.route("/<depl_name>")
def index(depl_name):
    """Direct route to release notes - redirects to selection page for user choice."""
    return redirect(url_for("release_notes.select_scope", depl_name=depl_name))


@release_notes_bp.route("/<depl_name>/select")
def select_scope(depl_name):
    """Show PR selection page to choose release scope."""
    deployment_data = get_deployment_data(escape(depl_name))
    if not deployment_data:
        return render_template("errors/404.html")

    # Sort PRs by merged_at to ensure chronological order
    prod_stage_pulls = deployment_data.get("prod_stage_pulls", [])
    prod_stage_pulls.sort(key=lambda pr: pr.get("merged_at", ""))

    return render_template(
        "release_notes_select.html",
        deployment_name=depl_name,
        deployment=deployment_data,
        prod_stage_pulls=prod_stage_pulls,
    )


@release_notes_bp.route("/<depl_name>/generate")
def generate(depl_name):
    """Generate release notes with selected scope."""
    up_to_pr = request.args.get("up_to_pr", type=int)

    release_notes = get_release_notes_from_deployment(escape(depl_name), up_to_pr)
    if not release_notes:
        return render_template("errors/404.html")

    today = datetime.now().strftime("%B %d, %Y")
    return render_template("release_notes.html", notes=release_notes, today=today)


def get_deployment_data(depl_name):
    """Get raw deployment data from JSON file."""
    with open(config.DEPLOYMENTS_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file).get(depl_name)


def get_release_notes_from_deployment(depl_name, up_to_pr=None):
    """Get release notes data, optionally filtered to a specific PR cutoff point."""
    notes = get_deployment_data(depl_name)
    if not notes:
        return None

    # If up_to_pr is specified, filter the prod_stage_pulls to only include PRs up to that point
    if up_to_pr is not None:
        prod_stage_pulls = notes.get("prod_stage_pulls", [])
        prod_stage_pulls.sort(key=lambda pr: pr.get("merged_at", ""))

        # Find the cutoff point and slice the array
        cutoff_index = None
        for i, pr in enumerate(prod_stage_pulls):
            if pr.get("number") == up_to_pr:
                cutoff_index = i
                break

        if cutoff_index is not None:
            notes["prod_stage_pulls"] = prod_stage_pulls[: cutoff_index + 1]
            # Update the target commit to the last selected PR's merge commit
            if notes["prod_stage_pulls"]:
                last_pr = notes["prod_stage_pulls"][-1]
                notes["target_prod_commit"] = last_pr.get(
                    "merge_commit_sha", notes.get("commit_stage")
                )
            else:
                notes["target_prod_commit"] = notes.get("commit_prod")  # No change
        else:
            # PR not found, use current stage as fallback
            notes["target_prod_commit"] = notes.get("commit_stage")
    else:
        # No filtering, use current stage commit
        notes["target_prod_commit"] = notes.get("commit_stage")

    add_release_notes_google_link(notes)
    return notes


def add_release_notes_google_link(notes):
    links = blueprints.get_services_links()
    repo_link = notes.get("repo_link").lower()

    for category in links.get("categories", ()):
        for repo in category["category_repos"]:
            for link in repo["links"]:
                if link.get("link_value").lower() == repo_link:
                    for link in repo["links"]:
                        if link.get("link_name") == "release notes":
                            notes["release_notes_link"] = link.get("link_value")
                            return notes
