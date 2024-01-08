from flask import Flask, render_template


import routes.overview_page


app = Flask(__name__)

@app.route("/")
def overview():
    services_links = routes.overview_page.get_services_links()
    if not services_links:
        return render_template("errors/404.html")
    return render_template("overview.html", services=services_links)


@app.route("/deployments")
def deployments():
    return render_template("deployments.html")


@app.route("/open-pr")
def open_pr():
    return render_template("open_pr.html")


@app.route("/merged-pr")
def merged_pr():
    return render_template("merged_pr.html")
