# service-dashboard
Flask app dashboard for services, deployments, pull requests, and more created as internal tool for my team.

This project is developed using the Flask framework. Configuration settings can be read in from a `.env` file. An example file `.env.example` is provided in the repository. To use the defaults simply

`cp .env.example .env`

Modify as you see fit.


App contains the following main parts:
## Overview page
The 'Overview' page displays the services and their links from the file `/data/services_links.yml`.

If the file does not exist, the example from the file `data/services_links_example.yml` will be displayed.

## Deployments page


## Open Pull Requests page
The 'Open Pull Requests' page displays open PRs from GitHub and GitLab (https://gitlab.cee.redhat.com) repos listed on the 'Overview' page.
The app checks the links on the 'Overview' page, identifies all matches and download all open pull requests into nice datatable.
All downloaded data are stored in the `/data/github_pr_list.json` for GitHub and `/data/gitlab_pr_list.json` for GitLab.
New data are downloaded:

* when file doesn't exist or
* after pushing the 'Update data' button

A GitHub and GitLab token are required to download new data.

## Merged Pull Requests page
The 'Merged Pull Requests' page displays merged PRs for the last 14 days from GitHub repos listed on the 'Oveerview' page.
The app checks the links on the 'Overview' page, identifies all matches and download all merged pull requests into nice datatable.
All downloaded data are stored in the `/data/github_merged_pr_list.json`.
New data are downloaded:

* when file doesn't exist or
* after pushing the 'Update data' button

A GitHub token is required to download new data.

# Mock feature
For demonstrating and testing the app you can use mock data from `mock_data` folder. To use this just set the `MOCK_DATA` environemnt variable to `true` and run the app.
