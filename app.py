from flask import Flask

from blueprints import (
    deployments_bp,
    get_default_branch_commit_style,
    get_stage_commit_style,
    jira_bp,
    overview_bp,
    pull_requests_bp,
    release_notes_bp,
)
from utils.helpers import is_older_than_six_months
from utils.template_filters import (
    days_since,
    format_datetime,
    get_language_icon,
    date_range_from_days,
    get_link_icon,
)

app = Flask(__name__)
app.config.from_object("config")

# Blueprint registration
app.register_blueprint(overview_bp)
app.register_blueprint(pull_requests_bp, url_prefix="/pull-requests")
app.register_blueprint(deployments_bp, url_prefix="/deployments")
app.register_blueprint(release_notes_bp, url_prefix="/release_notes")
app.register_blueprint(jira_bp, url_prefix="/jira")

# Template filters registration
app.jinja_env.filters["format_datetime"] = format_datetime
app.jinja_env.filters["days_since"] = days_since
app.jinja_env.filters["get_language_icon"] = get_language_icon
app.jinja_env.filters["date_range_from_days"] = date_range_from_days
app.jinja_env.filters["get_link_icon"] = get_link_icon

# Global functions registration
app.jinja_env.globals.update(get_stage_commit_style=get_stage_commit_style)
app.jinja_env.globals.update(
    get_default_branch_commit_style=get_default_branch_commit_style
)
app.jinja_env.globals.update(is_older_than_six_months=is_older_than_six_months)

if __name__ == "__main__":
    app.run()
