from flask import Flask, render_template, request

import routes.open_pr_page
import routes.overview_page
import routes.merged_pr_page


app = Flask(__name__)
app.config.from_object("config")


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
    reload_data = "reload_data" in request.args
    github_open_pr = routes.open_pr_page.get_github_open_pr(reload_data)
    gitlab_open_pr = routes.open_pr_page.get_gitlab_open_pr(reload_data)
    open_pr_list = github_open_pr | gitlab_open_pr

    return render_template("open_pr.html", open_pr_list=open_pr_list)


@app.route("/merged_pr")
def merged_pr():
    reload_data = "reload_data" in request.args
    github_merged_pr = routes.merged_pr_page.get_github_merged_pr(reload_data)
    return render_template("merged_pr.html", merged_pr_list=github_merged_pr)
