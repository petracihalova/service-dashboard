from flask import Flask, render_template, request
from datetime import datetime

import routes.open_pr_page
import routes.overview_page

app = Flask(__name__)
app.config.from_object("config")


@app.template_filter("format_time")
def format_time(date_str, format="%m/%d/%Y %H:%M:%S"):
    date = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
    return date.strftime(format)


@app.route("/")
def overview():
    services_links = routes.overview_page.get_services_links()
    if not services_links:
        return render_template("errors/404.html")
    return render_template("overview.html", services=services_links)


@app.route("/deployments")
def deployments():
    return render_template("deployments.html")


@app.route("/open_pr")
def open_pr():
    reload_data = True if request.args.get("reload_data") == "true" else False
    github_open_pr = routes.open_pr_page.get_github_open_pr(reload_data)

    return render_template("open_pr.html", github_open_pr=github_open_pr)


@app.route("/merged-pr")
def merged_pr():
    return render_template("merged_pr.html")
