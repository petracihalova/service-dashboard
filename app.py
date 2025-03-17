from flask import Flask

from blueprints import (
    deployments_bp,
    get_default_branch_commit_style,
    get_stage_commit_style,
    overview_bp,
    pull_requests_bp,
    release_notes_bp,
)
from utils.template_filters import format_datetime, days_since

app = Flask(__name__)
app.config.from_object("config")

# Blueprint registration
app.register_blueprint(overview_bp)
app.register_blueprint(pull_requests_bp, url_prefix="/pull-requests")
app.register_blueprint(deployments_bp, url_prefix="/deployments")
app.register_blueprint(release_notes_bp, url_prefix="/release_notes")

# Template filters registration
app.jinja_env.filters["format_datetime"] = format_datetime
app.jinja_env.filters["days_since"] = days_since

# Global functions registration
app.jinja_env.globals.update(get_stage_commit_style=get_stage_commit_style)
app.jinja_env.globals.update(
    get_default_branch_commit_style=get_default_branch_commit_style
)


if __name__ == "__main__":
    app.run()
