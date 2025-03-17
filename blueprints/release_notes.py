from flask import Blueprint


release_notes_bp = Blueprint("release_notes", __name__)


@release_notes_bp.route("/<depl_name>")
def index(depl_name):
    return f"Tohle je stránka pro release notes '''{depl_name}'''"
