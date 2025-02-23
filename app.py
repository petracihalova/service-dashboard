from flask import Flask

from blueprints import deployments_bp, overview_bp, pull_requests_bp
from utils.template_filters import format_datetime

app = Flask(__name__)
app.config.from_object("config")

# Blueprint registration
app.register_blueprint(overview_bp)
app.register_blueprint(pull_requests_bp, url_prefix="/pull-requests")
app.register_blueprint(deployments_bp, url_prefix="/deployments")

# Template filters registration
app.jinja_env.filters["format_datetime"] = format_datetime

if __name__ == "__main__":
    app.run()
