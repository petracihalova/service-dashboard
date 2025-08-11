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
                    branch=pr.base.ref,
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

        query = self.generate_graphql_query_for_merged_prs_since(
            github_projects, last_download_timestamp
        )
        output = self.github_api.requester.graphql_query(query, {})

        data = output[1].get("data").get("search").get("edges")
        for item in data:
            pr = item.get("node")
            repo_name = pr.get("repository").get("name").lower()

            if repo_name not in pulls:
                pulls[repo_name] = []

            pr_numbers = [p.get("number") for p in pulls[repo_name]]
            if pr.get("number") not in pr_numbers:
                pulls[repo_name].append(
                    {
                        "number": pr.get("number"),
                        "draft": pr.get("isDraft"),
                        "title": pr.get("title"),
                        "body": pr.get("body"),
                        "created_at": pr.get("createdAt"),
                        "merged_at": pr.get("mergedAt"),
                        "merge_commit_sha": pr.get("mergeCommit").get("oid"),
                        "user_login": pr.get("author").get("login"),
                        "html_url": pr.get("url"),
                    }
                )
                logger.info(
                    f"Added new merged pull request PR#{pr.get('number')}: {pr.get('title')} from '{repo_name}'"
                )

        return pulls

    def generate_graphql_query_for_merged_prs_since(self, repos, merged_since):
        query_repo_param = ""
        for owner, repo in repos:
            query_repo_param += f"repo:{owner}/{repo} "

        query = """
            {
                search(query: "***is:pr is:merged merged:>=&&&", type: ISSUE, first: 100) {
                    edges {
                        node {
                            ... on PullRequest {
                            number
                            repository { name }
                            title
                            isDraft
                            mergedAt
                            createdAt
                            mergeCommit { oid }
                            url
                            author { login }
                            }
                        }
                    }
                }
            }"""
        query = query.replace("***", query_repo_param)
        query = query.replace("&&&", merged_since)
        return query

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
