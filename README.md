# service-dashboard
Flask app dashboard for services, deployments, pull requests, and more created as internal tool for my team.

App contains the following main parts:
## Overview page
The Overview page displays the services and their links from the file `/data/services_links.yml`.

If the file does not exist, the example from the file `data/services_links_example.yml` will be displayed.

## Deployments page


## Open Pull Requests page
The Open Pull Requests page displays open PRs from GitHub repos listed on the Overview page. The app check
the links on the Overview page, identifies all GitHub repos and then download all open pull requests into nice datatable.
All downloaded data are stored in the `/data/github_pr_list.json`.
New data are downloaded:

* when `/data/github_pr_list.json` doesn't exist or
* after pushing the Update data button

A GitHub token is required to download new data.

`export GITHUB_TOKEN=<your token>`

## Merged Pull Requests page
