# service-dashboard

> **🤝 Created in collaboration with Cursor IDE and Claude-4-Sonnet AI model through vibe coding sessions**

Flask app dashboard for services, deployments, pull requests, and more created as internal tool for my team. Because this app is built for my team's goals and needs, there are a number of settings that are hardcoded. The app was built as a hackathon project, so the code may be messy or inefficient. I'm aware of that and will fix it when I feel like it.

This project is developed using the Flask framework. Configuration settings can be read in from a `.env` file. An example file `.env.example` is provided in the repository. To use the defaults simply

`cp .env.example .env`

**Important configuration variables:**
* `GITHUB_USERNAME` and `GITLAB_USERNAME` - Required for "My PRs" filtering feature
* `GITHUB_TOKEN` and `GITLAB_TOKEN` - Required for downloading PR data from private repositories
* `APP_INTERFACE_USERS` - Comma-separated list of usernames for app-interface pages filtering
* Other settings can be modified as needed

Internal documentation for the app can be found here: https://spaces.redhat.com/x/3AW0Iw


App contains the following main parts:
## Overview page
The 'Overview' page displays the services and their links from the file `/data/services_links.yml`.

**Key Features:**
* **CRUD Operations**: Add, edit, and delete services and categories directly from the UI
* **Edit Mode Toggle**: Switch between read-only and edit mode to show/hide editing controls
* **Compact View Toggle**: Toggle between standard and compact layout for better information density
* **Dark Mode**: Full dark mode support across the entire application
* **Category Management**: Reorder categories with up/down arrows

If the file does not exist, the mock data from `./data/test_data` are copied into `./data/` folder and displayed.

## Deployments page
Lists deployments downloaded from internal App Interface GitLab repo used for deployments configuration.
The app checks links from the 'Overview' page, identifies matches and downloads related deployments.

**Configuration:**
Use `DEPLOY_TEMPLATE_IGNORE_LIST` variable to list deployment templates you don't want to download (partial match is applied).

**Requirements:**
GitHub, GitLab and JIRA tokens are required to download new data and access private repositories.

## Open and Merged Pull Requests page
The pages display open and merged pull and merge requests from GitHub and GitLab (https://gitlab.cee.redhat.com) repos listed on the 'Overview' page.

**Data Storage:**
All downloaded data are stored in `/data` folder.

New data are downloaded:
* when files don't exist or
* after clicking the 'Update data' button

**Requirements:**
GitHub and GitLab tokens are required to download new data. To access private repos, you need to generate tokens with appropriate permissions.

## App-interface open and merged requests page
The pages display open and merged merge requests from app-interface repository for users defined in the `APP_INTERFACE_USERS` variable.

## How to run
1. download the project `git clone git@github.com:petracihalova/service-dashboard.git` and go inside the `service-dashboard` folder
1. copy the configuration file `cp .env.example .env`
1. create a virtual environment `python3 -m venv venv`
1. activate the virtual environment `source venv/bin/activate`
1. install dependencies `pip install -r requirements.txt`
1. run the app `flask run`
1. open `http://127.0.0.1:5000`
