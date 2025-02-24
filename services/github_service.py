import logging
from datetime import datetime, timedelta

from github import Auth, BadCredentialsException, Github, GithubException

import blueprints
import config
from utils import (
    PullRequestInfo,
    get_repos_info,
    load_json_data,
    save_json_data_and_return,
)

logger = logging.getLogger(__name__)


class GithubAPI:
    def __init__(self):
        """Connection to the GitHub API."""
        token = config.GITHUB_TOKEN

        if token:
            try:
                auth = Auth.Token(token)
                self.github_api = Github(auth=auth)
                user = self.github_api.get_user().login
                logger.info(f"Successfully connected as {user} via GitHub token.")

            except BadCredentialsException:
                logger.info(
                    "Invalid or expired GitHub token. Switching to anonymous mode."
                )
                self.github_api = Github()

        else:
            logger.info("No GitHub token provided. Running in anonymous mode.")
            self.github_api = Github()

    def get_pull_requests(self, state="all"):
        """Get pull requests list for defined state (defaults to 'all')."""
        # Get list of GitHub projects from Overview page
        services_links = blueprints.get_services_links()
        github_projects = get_repos_info(services_links, config.GH_REPO_PATTERN)

        result = {}
        for owner, repo_name in github_projects:
            logger.info(
                f"Downloading '{state}' pull requests from '{owner}/{repo_name}'"
            )
            try:
                repo = self.github_api.get_repo(f"{owner}/{repo_name}")
            except Exception as err:
                logger.error(err)
                continue
            pulls = repo.get_pulls(state=state, sort="created")
            result[repo_name] = [
                PullRequestInfo(
                    number=pr.number,
                    draft=pr.draft,
                    title=pr.title,
                    created_at=pr.created_at,
                    merged_at=pr.merged_at,
                    user_login=pr.user.login,
                    html_url=pr.html_url,
                )
                for pr in pulls
            ]
        return result

    def get_open_pull_requests(self):
        """Get list of open pull requests."""
        try:
            pulls = self.get_pull_requests(state="open")
            return save_json_data_and_return(pulls, config.GH_OPEN_PR_FILE)

        except GithubException as err:
            logger.error(err)
            return load_json_data(config.GH_OPEN_PR_FILE)

    def get_merged_pull_requests(self, days=config.MERGED_IN_LAST_X_DAYS):
        """Get list of all merged pull requests."""
        if not days:
            pulls = self.get_pull_requests(state="closed")
            pulls = self.filter_merged_pull_requests(pulls)
        else:
            pulls = self.get_merged_pull_requests_in_last_X_days(days)
        return save_json_data_and_return(pulls, config.GH_MERGED_PR_FILE)

    def get_merged_pull_requests_in_last_X_days(self, days):
        """Get list pull requests merged in last X days."""
        # Get list of GitHub projects from Overview page
        services_links = blueprints.get_services_links()
        github_projects = get_repos_info(services_links, config.GH_REPO_PATTERN)

        date_X_days_ago = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        result = {}
        for owner, repo_name in github_projects:
            logger.info(
                f"Downloading 'merged' pull requests from '{owner}/{repo_name}'"
            )
            repo = f"{owner}/{repo_name}"
            query = f"is:pr is:merged merged:>={date_X_days_ago} repo:{repo}"

            issues = self.github_api.search_issues(query)
            pulls = []
            for record in issues:
                pr = self.github_api.get_repo(repo).get_pull(record.number)
                pulls.append(pr)

            result[repo_name] = [
                PullRequestInfo(
                    number=pr.number,
                    draft=pr.draft,
                    title=pr.title,
                    created_at=pr.created_at,
                    merged_at=pr.merged_at,
                    user_login=pr.user.login,
                    html_url=pr.html_url,
                )
                for pr in pulls
            ]
        return result

    def filter_merged_pull_requests(self, pulls):
        """Filter only merged pull requests."""
        merged_pulls = {key: [] for key in pulls}

        for repo, pr_list in pulls.items():
            merged_pulls[repo] = [pr for pr in pr_list if pr.merged_at]

        return merged_pulls
