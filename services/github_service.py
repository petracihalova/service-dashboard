import json
import logging
from datetime import datetime, timezone

from github import Auth, BadCredentialsException, Github, GithubException

import blueprints
import config
from utils import (
    PullRequestInfo,
    get_repos_info,
    load_json_data,
    save_json_data_and_return,
)
from utils.json_utils import PullRequestEncoder

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
                    body=pr.body,
                    created_at=pr.created_at,
                    merged_at=pr.merged_at,
                    merge_commit_sha=pr.merge_commit_sha if pr.merged_at else None,
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
            return save_json_data_and_return(
                pulls, config.GH_OPEN_PR_FILE, PullRequestEncoder
            )

        except GithubException as err:
            logger.error(err)
            return load_json_data(config.GH_OPEN_PR_FILE)

    def get_merged_pull_requests(self, scope="all"):
        """Get list of merged pull requests."""
        if not scope or scope == "all":
            pulls = self.get_pull_requests(state="closed")
            pulls = self.filter_merged_pull_requests(pulls)
        elif scope == "missing":
            pulls = self.get_missing_merged_pull_requests()
        else:
            raise ValueError("Get list of merged pull requests: invalid 'scope'")

        result = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": pulls}

        return save_json_data_and_return(
            result, config.GH_MERGED_PR_FILE, PullRequestEncoder
        )

    def get_missing_merged_pull_requests(self):
        """Get list pull requests merged that are missing in our database."""
        # Get list of GitHub projects from Overview page
        services_links = blueprints.get_services_links()
        github_projects = get_repos_info(services_links, config.GH_REPO_PATTERN)

        with open(config.GH_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            timestamp = data.get("timestamp")
            pulls = data.get("data")

        last_download_timestamp = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d")

        for owner, repo_name in github_projects:
            logger.info(
                f"Downloading missing 'merged' pull requests from '{owner}/{repo_name}'"
            )
            repo = f"{owner}/{repo_name}"
            query = f"is:pr is:merged merged:>={last_download_timestamp} repo:{repo}"

            issues = self.github_api.search_issues(query)

            if repo_name not in pulls:
                pulls[repo_name] = []

            last_pr_number = max(
                [pr.get("number") for pr in pulls[repo_name]], default=-1
            )
            for issue in issues:
                if issue.number > last_pr_number:
                    pulls[repo_name].append(
                        PullRequestInfo(
                            number=issue.number,
                            draft=issue.draft,
                            title=issue.title,
                            body=issue.body,
                            created_at=issue.created_at,
                            merged_at=issue.pull_request.merged_at,
                            user_login=issue.user.login,
                            html_url=issue.html_url,
                        )
                    )
                    logger.info(
                        f"Added new merged pull request PR#{issue.number}: {issue.title}'"
                    )

        return pulls

    def filter_merged_pull_requests(self, pulls):
        """Filter only merged pull requests."""
        merged_pulls = {key: [] for key in pulls}

        for repo, pr_list in pulls.items():
            merged_pulls[repo] = [pr for pr in pr_list if pr.merged_at]

        return merged_pulls

    def get_default_branch(self, repo_name):
        repo = self.github_api.get_repo(repo_name)
        return repo.default_branch

    def get_head_commit_ref(self, repo_name, branch_name=None):
        repo = self.github_api.get_repo(repo_name)
        if not branch_name:
            branch_name = self.get_default_branch(repo_name)
        branch = repo.get_branch(branch_name)
        return branch.commit.sha
