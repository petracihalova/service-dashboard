from flask import Flask

from blueprints import (
    api_bp,
    deployments_bp,
    enhance_data_bp,
    get_default_branch_commit_style,
    get_stage_commit_style,
    jira_tickets_bp,
    overview_bp,
    personal_stats_bp,
    pull_requests_bp,
    release_notes_bp,
    release_process_bp,
)
from utils.helpers import is_older_than_six_months
from utils.template_filters import (
    calculate_days_between_dates,
    calculate_days_open_from_iso,
    date_range_from_days,
    days_since,
    format_date_display,
    format_datetime,
    get_language_icon,
    get_link_icon,
    to_date,
)

app = Flask(__name__)
app.config.from_object("config")

# Blueprint registration
app.register_blueprint(api_bp, url_prefix="/api")
app.register_blueprint(enhance_data_bp)
app.register_blueprint(overview_bp)
app.register_blueprint(personal_stats_bp)
app.register_blueprint(pull_requests_bp, url_prefix="/pull-requests")
app.register_blueprint(deployments_bp, url_prefix="/deployments")
app.register_blueprint(release_notes_bp, url_prefix="/release_notes")
app.register_blueprint(jira_tickets_bp, url_prefix="/jira-tickets")
app.register_blueprint(release_process_bp)

# Template filters registration
app.jinja_env.filters["format_datetime"] = format_datetime
app.jinja_env.filters["days_since"] = days_since
app.jinja_env.filters["get_language_icon"] = get_language_icon
app.jinja_env.filters["date_range_from_days"] = date_range_from_days
app.jinja_env.filters["get_link_icon"] = get_link_icon
app.jinja_env.filters["calculate_days_between_dates"] = calculate_days_between_dates
app.jinja_env.filters["calculate_days_open_from_iso"] = calculate_days_open_from_iso
app.jinja_env.filters["format_date_display"] = format_date_display
app.jinja_env.filters["to_date"] = to_date

# Global functions registration
app.jinja_env.globals.update(get_stage_commit_style=get_stage_commit_style)
app.jinja_env.globals.update(
    get_default_branch_commit_style=get_default_branch_commit_style
)
app.jinja_env.globals.update(is_older_than_six_months=is_older_than_six_months)

if __name__ == "__main__":
    app.run()
