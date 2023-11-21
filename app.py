from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def overview():
    return render_template("overview.html")


@app.route("/deployments")
def deployments():
    return render_template("deployments.html")


@app.route("/open-pr")
def open_pr():
    return render_template("open_pr.html")


@app.route("/merged-pr")
def merged_pr():
    return render_template("merged_pr.html")
