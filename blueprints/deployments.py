from flask import Blueprint, render_template

deployments_bp = Blueprint("deployments", __name__)


@deployments_bp.route("/")
def index():
    """Deployments page."""
    return render_template("deployments.html")
