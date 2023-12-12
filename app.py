from flask import Flask, render_template


import routes.overview_page


app = Flask(__name__)

@app.route("/")
def overview():
    services = routes.overview_page.get_services_links()
    return render_template("overview.html", services=services)


@app.route("/deployments")
def deployments():
    return render_template("deployments.html")


@app.route("/open-pr")
def open_pr():
    return render_template("open_pr.html")


@app.route("/merged-pr")
def merged_pr():
    return render_template("merged_pr.html")
