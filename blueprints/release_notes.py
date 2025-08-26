import json
from datetime import datetime

from flask import Blueprint, render_template
from markupsafe import escape

import blueprints
import config

release_notes_bp = Blueprint("release_notes", __name__)


@release_notes_bp.route("/<depl_name>")
def index(depl_name):
    release_notes = get_release_notes_from_deployment(escape(depl_name))
    today = datetime.now().strftime("%B %d, %Y")
    return render_template("release_notes.html", notes=release_notes, today=today)


def get_release_notes_from_deployment(depl_name):
    with open(config.DEPLOYMENTS_FILE, mode="r", encoding="utf-8") as file:
        notes = json.load(file).get(depl_name)

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
