from flask import Flask

from blueprints import deployments_bp, overview_bp, pull_requests_bp

app = Flask(__name__)
app.config.from_object("config")

# Blueprint registration
app.register_blueprint(overview_bp)
app.register_blueprint(pull_requests_bp, url_prefix="/pull-requests")
app.register_blueprint(deployments_bp, url_prefix="/deployments")

if __name__ == "__main__":
    app.run()
