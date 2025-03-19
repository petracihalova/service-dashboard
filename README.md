# service-dashboard
Flask app dashboard for services, deployments, pull requests, and more created as internal tool for my team. Because this app is built for my team's goals and needs, there are a number of settings that are hardcoded. The app was built as a hackathon project, so the code may be messy or inefficient. I'm aware of that and will fix it when I feel like it.

This project is developed using the Flask framework. Configuration settings can be read in from a `.env` file. An example file `.env.example` is provided in the repository. To use the defaults simply

`cp .env.example .env`

Modify as you see fit.

Internal documentation for the app can be found here: https://spaces.redhat.com/x/3AW0Iw


App contains the following main parts:
## Overview page
The 'Overview' page displays the services and their links from the file `/data/services_links.yml`.

If the file does not exist, the mock data from `./data/test_data` are copied into `./data/` folder and displayed.

## Deployments page
List of deployments downloaded from internal App Interface GitLab repo our team uses for deployments config. The app checks the links from the 'Overview' page, identifies all matches and download all related deployments. You can use `DEPLOY_TEMPLATE_IGNORE_LIST` variable to list all deployment templates you dont want do download (partial match is applied).

Github, Gitlab and Jira tokens are required to download new data.

## Open Pull Requests page
The 'Open Pull Requests' page displays open PRs from GitHub and GitLab (https://gitlab.cee.redhat.com) repos listed on the 'Overview' page.
The app checks the links from the 'Overview' page, identifies all matches and download all open pull requests into nice datatable.
All downloaded data are stored in the `/data/github_pr_list.json` for GitHub and `/data/gitlab_pr_list.json` for GitLab.
New data are downloaded:

* when file doesn't exist or
* after pushing the 'Update data' button

GitHub and GitLab tokens are required to download new data.

## Merged Pull Requests page
The 'Merged Pull Requests' page displays merged PRs for the last X (can be set with `MERGED_IN_LAST_X_DAYS`) days from GitHub repos listed on the 'Overview' page.
The app checks the links on the 'Overview' page, identifies all matches and download all merged pull requests into nice datatable.
All downloaded data are stored in the `/data/github_merged_pr_list.json` for GitHub and `/data/gitlab_merged_pr_list.json` for GitLab.
New data are downloaded:

* when file doesn't exist or
* after pushing the 'Update data' button

GitHub and GitLab tokens are required to download new data.


## How to run
1. download the project `git clone git@github.com:petracihalova/service-dashboard.git` and go inside the `service-dashboard` folder
1. copy the configuration file `cp .env.example .env`
1. create a virtual environment `python3 -m venv venv`
1. activate the virtual environment `source venv/bin/activate`
1. install dependencies `pip install -r requirements.txt`
1. run the app `flask run`
1. open `http://127.0.0.1:5000`
