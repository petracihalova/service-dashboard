import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

import requests
from github import Auth, BadCredentialsException, Github

import blueprints
import config
from utils import (
    PullRequestInfo,
    calculate_days_open,
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

    def get_merged_pull_requests(self, scope="all"):
        """Get list of merged pull requests."""
        if not scope or scope == "all":
            pulls = self.get_all_merged_pull_requests_per_repo()
        elif scope == "missing":
            pulls = self.get_missing_merged_pull_requests()
        else:
            raise ValueError("Get list of merged pull requests: invalid 'scope'")

        result = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": pulls}

        return save_json_data_and_return(
            result, config.GH_MERGED_PR_FILE, PullRequestEncoder
        )

    def get_closed_pull_requests(self, scope="all"):
        """Get list of closed (but not merged) pull requests."""
        if not scope or scope == "all":
            pulls = self.get_all_closed_pull_requests_per_repo()
        elif scope == "missing":
            pulls = self.get_missing_closed_pull_requests()
        else:
            raise ValueError("Get list of closed pull requests: invalid 'scope'")

        result = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": pulls}

        return save_json_data_and_return(
            result, config.GH_CLOSED_PR_FILE, PullRequestEncoder
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
                        "additions": pr.get("additions"),
                        "deletions": pr.get("deletions"),
                    }
                )
                logger.info(
                    f"Added new merged pull request PR#{pr.get('number')}: {pr.get('title')} from '{repo_name}'"
                )

        return pulls

    def get_missing_closed_pull_requests(self):
        """Get list of pull requests closed that are missing in our database."""
        # Get list of GitHub projects from Overview page
        services_links = blueprints.get_services_links()
        github_projects = get_repos_info(services_links, config.GH_REPO_PATTERN)

        with open(config.GH_CLOSED_PR_FILE, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            timestamp = data.get("timestamp")
            pulls = data.get("data")

        last_download_timestamp = datetime.fromisoformat(timestamp).strftime("%Y-%m-%d")

        query = self.generate_graphql_query_for_closed_prs_since(
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
                        "merged_at": None,  # Closed but not merged
                        "closed_at": pr.get("closedAt"),
                        "merge_commit_sha": None,
                        "user_login": pr.get("author").get("login"),
                        "html_url": pr.get("url"),
                        "additions": pr.get("additions"),
                        "deletions": pr.get("deletions"),
                    }
                )
                logger.info(
                    f"Added new closed pull request PR#{pr.get('number')}: {pr.get('title')} from '{repo_name}'"
                )

        return pulls

    def generate_graphql_query_for_merged_prs_since(self, repos, merged_since):
        query_repo_param = ""
        for owner, repo in repos:
            query_repo_param += f"repo:{owner}/{repo} "

        query = """
            {
                search(query: "*** is:pr is:merged merged:>=&&&", type: ISSUE, first: 100) {
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
                            additions
                            deletions
                            }
                        }
                    }
                }
            }"""
        query = query.replace("***", query_repo_param)
        query = query.replace("&&&", merged_since)
        return query

    def generate_graphql_query_for_closed_prs_since(self, repos, closed_since):
        query_repo_param = ""
        for owner, repo in repos:
            query_repo_param += f"repo:{owner}/{repo} "

        query = """
            {
                search(query: "*** is:pr is:closed is:unmerged closed:>=&&&", type: ISSUE, first: 100) {
                    edges {
                        node {
                            ... on PullRequest {
                            number
                            repository { name }
                            title
                            isDraft
                            closedAt
                            createdAt
                            url
                            author { login }
                            additions
                            deletions
                            }
                        }
                    }
                }
            }"""
        query = query.replace("***", query_repo_param)
        query = query.replace("&&&", closed_since)
        return query

    def generate_graphql_query_for_single_repo_merged_prs(
        self, owner: str, repo: str, after_cursor: str = None
    ) -> str:
        """Generate GraphQL query for merged pull requests from a single repository with pagination."""

        # Add pagination cursor if provided
        after_param = f', after: "{after_cursor}"' if after_cursor else ""

        query = f"""
        {{
            repository(owner: "{owner}", name: "{repo}") {{
                pullRequests(states: [MERGED], first: 100{after_param}, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    edges {{
                        node {{
                            number
                            title
                            body
                            isDraft
                            createdAt
                            mergedAt
                            mergeCommit {{
                                oid
                            }}
                            url
                            author {{
                                login
                            }}
                            baseRef {{
                                name
                            }}
                            additions
                            deletions
                            changedFiles
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def get_all_merged_pull_requests_per_repo(self) -> Dict[str, List[PullRequestInfo]]:
        """Get all merged pull requests using repository-based GraphQL queries with pagination (bypasses 1000 search limit)."""
        if not config.GITHUB_TOKEN:
            logger.error("GitHub token is required for GraphQL API")
            return {}

        try:
            # Get list of GitHub projects from Overview page
            services_links = blueprints.get_services_links()
            github_projects = get_repos_info(services_links, config.GH_REPO_PATTERN)

            if not github_projects:
                logger.warning("No GitHub projects found")
                return {}

            logger.info(
                f"Fetching all merged PRs using GraphQL per repository for {len(github_projects)} repositories"
            )

            all_pulls = {}
            total_processed = 0

            # Fetch PRs per repository using GraphQL to bypass search API limit
            for owner, repo_name in github_projects:
                logger.info(f"Processing repository: {owner}/{repo_name}")

                try:
                    repo_pulls = []
                    has_next_page = True
                    after_cursor = None
                    page_count = 0

                    # Paginate through all results for this repository
                    while has_next_page:
                        # Generate GraphQL query for this specific repository
                        query = self.generate_graphql_query_for_single_repo_merged_prs(
                            owner, repo_name, after_cursor
                        )
                        logger.debug(
                            f"GraphQL query for {owner}/{repo_name} (cursor: {after_cursor})"
                        )

                        # Execute GraphQL query
                        response_data = self._execute_graphql_query(query)

                        # Check for repository data
                        repo_data = response_data.get("data", {}).get("repository")
                        if not repo_data or not repo_data.get("pullRequests"):
                            logger.warning(f"No PR data found for {owner}/{repo_name}")
                            break

                        pull_requests = repo_data["pullRequests"]

                        # Check for pagination info
                        page_info = pull_requests.get("pageInfo", {})
                        has_next_page = page_info.get("hasNextPage", False)
                        after_cursor = page_info.get("endCursor")

                        # Process current page results
                        edges = pull_requests.get("edges", [])
                        page_prs = []

                        for edge in edges:
                            node = edge["node"]
                            if not node:
                                continue

                            # Parse datetime strings
                            created_at = datetime.fromisoformat(
                                node["createdAt"].replace("Z", "+00:00")
                            )
                            merged_at = datetime.fromisoformat(
                                node["mergedAt"].replace("Z", "+00:00")
                            )

                            # Extract merge commit SHA
                            merge_commit_sha = None
                            if node.get("mergeCommit"):
                                merge_commit_sha = node["mergeCommit"]["oid"]

                            # Get author login (handle case where author might be null)
                            author_login = "unknown"
                            if node.get("author") and node["author"].get("login"):
                                author_login = node["author"]["login"]

                            # Get base branch name
                            base_branch = ""
                            if node.get("baseRef") and node["baseRef"].get("name"):
                                base_branch = node["baseRef"]["name"]

                            # Calculate days the PR was open (for merged PRs)
                            days_open = calculate_days_open(created_at, merged_at)

                            pr_info = PullRequestInfo(
                                number=node["number"],
                                draft=node["isDraft"],
                                title=node["title"],
                                body=node["body"] or "",
                                created_at=created_at,
                                merged_at=merged_at,
                                merge_commit_sha=merge_commit_sha,
                                user_login=author_login,
                                html_url=node["url"],
                                branch=base_branch,
                                additions=node.get("additions"),
                                deletions=node.get("deletions"),
                                changed_files=node.get("changedFiles"),
                                days_open=days_open,
                            )

                            page_prs.append(pr_info)

                        repo_pulls.extend(page_prs)
                        page_count += 1

                        logger.debug(
                            f"Processed page {page_count} with {len(page_prs)} PRs from {owner}/{repo_name}"
                        )

                    if repo_pulls:
                        all_pulls[repo_name] = repo_pulls
                        total_processed += len(repo_pulls)
                        logger.info(
                            f"Found {len(repo_pulls)} merged PRs in {owner}/{repo_name}"
                        )
                    else:
                        logger.info(f"No merged PRs found in {owner}/{repo_name}")

                except Exception as repo_err:
                    logger.error(f"Error processing {owner}/{repo_name}: {repo_err}")
                    continue

            # Log final results
            total_prs = sum(len(pr_list) for pr_list in all_pulls.values())
            logger.info(
                f"GraphQL API returned {total_prs} merged pull requests across {len(all_pulls)} repositories"
            )

            return all_pulls

        except Exception as err:
            logger.error(f"GraphQL API request failed: {err}")
            return {}

    def generate_graphql_query_for_single_repo_open_prs(
        self, owner: str, repo: str, after_cursor: str = None
    ) -> str:
        """Generate GraphQL query for open pull requests from a single repository with pagination."""

        # Add pagination cursor if provided
        after_param = f', after: "{after_cursor}"' if after_cursor else ""

        query = f"""
        {{
            repository(owner: "{owner}", name: "{repo}") {{
                pullRequests(states: [OPEN], first: 100{after_param}, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    edges {{
                        node {{
                            number
                            title
                            body
                            isDraft
                            createdAt
                            url
                            author {{
                                login
                            }}
                            baseRef {{
                                name
                            }}
                            additions
                            deletions
                            changedFiles
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def generate_graphql_query_for_single_repo_closed_prs(
        self, owner: str, repo: str, after_cursor: str = None
    ) -> str:
        """Generate GraphQL query for closed (but not merged) pull requests from a single repository with pagination."""

        # Add pagination cursor if provided
        after_param = f', after: "{after_cursor}"' if after_cursor else ""

        query = f"""
        {{
            repository(owner: "{owner}", name: "{repo}") {{
                pullRequests(states: [CLOSED], first: 100{after_param}, orderBy: {{field: UPDATED_AT, direction: DESC}}) {{
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    edges {{
                        node {{
                            number
                            title
                            body
                            isDraft
                            createdAt
                            closedAt
                            mergedAt
                            url
                            author {{
                                login
                            }}
                            baseRef {{
                                name
                            }}
                            additions
                            deletions
                            changedFiles
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def get_all_closed_pull_requests_per_repo(self) -> Dict[str, List[PullRequestInfo]]:
        """Get all closed (but not merged) pull requests using repository-based GraphQL queries with pagination (bypasses 1000 search limit)."""
        if not config.GITHUB_TOKEN:
            logger.error("GitHub token is required for GraphQL API")
            return {}

        try:
            # Get list of GitHub projects from Overview page
            services_links = blueprints.get_services_links()
            github_projects = get_repos_info(services_links, config.GH_REPO_PATTERN)

            if not github_projects:
                logger.warning("No GitHub projects found")
                return {}

            logger.info(
                f"Fetching all closed (unmerged) PRs using GraphQL per repository for {len(github_projects)} repositories"
            )

            all_pulls = {}
            total_processed = 0

            # Fetch PRs per repository using GraphQL to bypass search API limit
            for owner, repo_name in github_projects:
                logger.info(
                    f"Processing repository for closed PRs: {owner}/{repo_name}"
                )

                try:
                    repo_pulls = []
                    has_next_page = True
                    after_cursor = None
                    page_count = 0

                    # Paginate through all results for this repository
                    while has_next_page:
                        # Generate GraphQL query for this specific repository
                        query = self.generate_graphql_query_for_single_repo_closed_prs(
                            owner, repo_name, after_cursor
                        )
                        logger.debug(
                            f"GraphQL query for closed PRs {owner}/{repo_name} (cursor: {after_cursor})"
                        )

                        # Execute GraphQL query
                        response_data = self._execute_graphql_query(query)

                        # Check for repository data
                        repo_data = response_data.get("data", {}).get("repository")
                        if not repo_data or not repo_data.get("pullRequests"):
                            logger.warning(f"No PR data found for {owner}/{repo_name}")
                            break

                        pull_requests = repo_data["pullRequests"]

                        # Check for pagination info
                        page_info = pull_requests.get("pageInfo", {})
                        has_next_page = page_info.get("hasNextPage", False)
                        after_cursor = page_info.get("endCursor")

                        # Process current page results
                        edges = pull_requests.get("edges", [])
                        page_prs = []

                        for edge in edges:
                            node = edge["node"]
                            if not node:
                                continue

                            # Skip merged PRs - we only want closed but not merged
                            if node.get("mergedAt"):
                                continue

                            # Parse datetime strings
                            created_at = datetime.fromisoformat(
                                node["createdAt"].replace("Z", "+00:00")
                            )
                            closed_at = None
                            if node.get("closedAt"):
                                closed_at = datetime.fromisoformat(
                                    node["closedAt"].replace("Z", "+00:00")
                                )

                            # Get author login (handle case where author might be null)
                            author_login = "unknown"
                            if node.get("author") and node["author"].get("login"):
                                author_login = node["author"]["login"]

                            # Get base branch name
                            base_branch = ""
                            if node.get("baseRef") and node["baseRef"].get("name"):
                                base_branch = node["baseRef"]["name"]

                            # Calculate days the PR was open (for closed PRs)
                            days_open = calculate_days_open(created_at, closed_at)

                            pr_info = PullRequestInfo(
                                number=node["number"],
                                draft=node["isDraft"],
                                title=node["title"],
                                body=node["body"] or "",
                                created_at=created_at,
                                merged_at=None,  # Not merged
                                closed_at=closed_at,
                                merge_commit_sha=None,  # No merge commit
                                user_login=author_login,
                                html_url=node["url"],
                                branch=base_branch,
                                additions=node.get("additions"),
                                deletions=node.get("deletions"),
                                changed_files=node.get("changedFiles"),
                                days_open=days_open,
                            )

                            page_prs.append(pr_info)

                        repo_pulls.extend(page_prs)
                        page_count += 1

                        logger.debug(
                            f"Processed page {page_count} with {len(page_prs)} closed PRs from {owner}/{repo_name}"
                        )

                    if repo_pulls:
                        all_pulls[repo_name] = repo_pulls
                        total_processed += len(repo_pulls)
                        logger.info(
                            f"Found {len(repo_pulls)} closed (unmerged) PRs in {owner}/{repo_name}"
                        )
                    else:
                        logger.info(
                            f"No closed (unmerged) PRs found in {owner}/{repo_name}"
                        )

                except Exception as repo_err:
                    logger.error(
                        f"Error processing closed PRs in {owner}/{repo_name}: {repo_err}"
                    )
                    continue

            # Log final results
            total_prs = sum(len(pr_list) for pr_list in all_pulls.values())
            logger.info(
                f"GraphQL API returned {total_prs} closed pull requests across {len(all_pulls)} repositories"
            )

            return all_pulls

        except Exception as err:
            logger.error(f"GraphQL API request failed: {err}")
            return {}

    def _process_graphql_closed_prs_response(
        self, response_data: Dict[str, Any]
    ) -> Dict[str, List[PullRequestInfo]]:
        """Process GraphQL response data for closed PRs into PullRequestInfo objects organized by repository."""
        result = {}

        if "data" not in response_data or "search" not in response_data["data"]:
            logger.error(f"Unexpected GraphQL response structure: {response_data}")
            return result

        edges = response_data["data"]["search"]["edges"]

        for edge in edges:
            node = edge["node"]
            if not node:
                continue
            repo_name = node["repository"]["name"]

            # Initialize repository list if not exists
            if repo_name not in result:
                result[repo_name] = []

            # Parse datetime strings
            created_at = datetime.fromisoformat(
                node["createdAt"].replace("Z", "+00:00")
            )
            closed_at = None
            if node["closedAt"]:
                closed_at = datetime.fromisoformat(
                    node["closedAt"].replace("Z", "+00:00")
                )

            # Get author login (handle case where author might be null)
            author_login = "unknown"
            if node["author"] and node["author"]["login"]:
                author_login = node["author"]["login"]

            # Get base branch name
            base_branch = ""
            if node["baseRef"] and node["baseRef"]["name"]:
                base_branch = node["baseRef"]["name"]

            # Get additions and deletions
            additions = node.get("additions")
            deletions = node.get("deletions")

            # Calculate days the PR was open (for closed PRs)
            days_open = calculate_days_open(created_at, closed_at)

            pr_info = PullRequestInfo(
                number=node["number"],
                draft=node["isDraft"],
                title=node["title"],
                body=node["body"] or "",  # Handle null body
                created_at=created_at,
                merged_at=None,  # Closed but not merged
                closed_at=closed_at,
                merge_commit_sha=None,  # No merge commit for closed PRs
                user_login=author_login,
                html_url=node["url"],
                branch=base_branch,
                additions=additions,
                deletions=deletions,
                days_open=days_open,
            )

            result[repo_name].append(pr_info)

        return result

    def get_default_branch(self, repo_name):
        repo = self.github_api.get_repo(repo_name)
        return repo.default_branch

    def get_repo_type(self, repo_name):
        repo = self.github_api.get_repo(repo_name)
        return repo.private

    def get_repo_language(self, repo_name):
        repo = self.github_api.get_repo(repo_name)
        return repo.language

    def get_head_commit_ref(self, repo_name, branch_name=None):
        repo = self.github_api.get_repo(repo_name)
        if not branch_name:
            branch_name = self.get_default_branch(repo_name)
        branch = repo.get_branch(branch_name)
        return branch.commit.sha

    def _execute_graphql_query(self, query: str) -> Dict[str, Any]:
        """Execute a GraphQL query against GitHub API."""
        headers = {
            "Authorization": f"Bearer {config.GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }

        data = {"query": query}

        response = requests.post(
            "https://api.github.com/graphql", headers=headers, json=data, timeout=30
        )

        if response.status_code != 200:
            logger.error(
                f"GraphQL request failed with status {response.status_code}: {response.text}"
            )
            raise Exception(f"GraphQL request failed: {response.status_code}")

        result = response.json()

        if "errors" in result:
            logger.error(f"GraphQL errors: {result['errors']}")
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result

    def generate_graphql_query_for_open_prs(self, repos: List[tuple]) -> str:
        """Generate GraphQL query for open pull requests from specified repositories."""
        query_repo_param = ""
        for owner, repo in repos:
            query_repo_param += f"repo:{owner}/{repo} "

        query = """
        {
            search(query: "*** is:pr is:open", type: ISSUE, first: 100) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                edges {
                    node {
                        ... on PullRequest {
                            number
                            repository { name }
                            title
                            body
                            isDraft
                            createdAt
                            mergedAt
                            mergeCommit { oid }
                            url
                            author { login }
                            baseRef { name }
                            additions
                            deletions
                            changedFiles
                        }
                    }
                }
            }
        }"""

        query = query.replace("***", query_repo_param.strip())
        return query

    def _process_graphql_prs_response(
        self, response_data: Dict[str, Any]
    ) -> Dict[str, List[PullRequestInfo]]:
        """Process GraphQL response data into PullRequestInfo objects organized by repository."""
        result = {}

        if "data" not in response_data or "search" not in response_data["data"]:
            logger.error(f"Unexpected GraphQL response structure: {response_data}")
            return result

        edges = response_data["data"]["search"]["edges"]

        for edge in edges:
            node = edge["node"]
            if not node:
                continue
            repo_name = node["repository"]["name"]

            # Initialize repository list if not exists
            if repo_name not in result:
                result[repo_name] = []

            # Parse datetime strings
            created_at = datetime.fromisoformat(
                node["createdAt"].replace("Z", "+00:00")
            )
            merged_at = None
            if node["mergedAt"]:
                merged_at = datetime.fromisoformat(
                    node["mergedAt"].replace("Z", "+00:00")
                )

            # Extract merge commit SHA
            merge_commit_sha = None
            if node["mergeCommit"]:
                merge_commit_sha = node["mergeCommit"]["oid"]

            # Get author login (handle case where author might be null)
            author_login = "unknown"
            if node["author"] and node["author"]["login"]:
                author_login = node["author"]["login"]

            # Get base branch name
            base_branch = ""
            if node["baseRef"] and node["baseRef"]["name"]:
                base_branch = node["baseRef"]["name"]

            # Get additions and deletions
            additions = node["additions"]
            deletions = node["deletions"]

            # Get changed files
            changed_files = node["changedFiles"]

            # Calculate days the PR was open (for merged PRs)
            days_open = calculate_days_open(created_at, merged_at)

            pr_info = PullRequestInfo(
                number=node["number"],
                draft=node["isDraft"],
                title=node["title"],
                body=node["body"] or "",  # Handle null body
                created_at=created_at,
                merged_at=merged_at,
                merge_commit_sha=merge_commit_sha,
                user_login=author_login,
                html_url=node["url"],
                branch=base_branch,
                additions=additions,
                deletions=deletions,
                changed_files=changed_files,
                days_open=days_open,
            )

            result[repo_name].append(pr_info)

        return result

    def get_open_pull_request_with_graphql(self) -> Dict[str, List[PullRequestInfo]]:
        """Get list of open pull requests using GraphQL API."""
        if not config.GITHUB_TOKEN:
            logger.error("GitHub token is required for GraphQL API")
            return load_json_data(config.GH_OPEN_PR_FILE).get("data", {})

        try:
            # Get list of GitHub projects from Overview page
            services_links = blueprints.get_services_links()
            github_projects = get_repos_info(services_links, config.GH_REPO_PATTERN)

            if not github_projects:
                logger.warning("No GitHub projects found")
                return {}

            logger.info(
                f"Fetching open PRs using GraphQL for {len(github_projects)} repositories"
            )

            # Generate GraphQL query
            query = self.generate_graphql_query_for_open_prs(github_projects)
            logger.debug(f"GraphQL query: {query}")

            # Execute GraphQL query
            response_data = self._execute_graphql_query(query)

            # Process response
            pulls = self._process_graphql_prs_response(response_data)

            # Log results
            total_prs = sum(len(pr_list) for pr_list in pulls.values())
            logger.info(
                f"GraphQL API returned {total_prs} open pull requests across {len(pulls)} repositories"
            )

            # Save to file and return
            return save_json_data_and_return(
                pulls, config.GH_OPEN_PR_FILE, PullRequestEncoder
            )

        except Exception as err:
            logger.error(f"GraphQL API request failed: {err}")
            # Fallback to existing data
            return load_json_data(config.GH_OPEN_PR_FILE).get("data", {})

    def add_github_data_to_deployment(self, deployment_name):
        """
        Update data from Github API for a specific deployment.
        Download the default branch commit ref and update references in the deployment file.
        """
        with open(config.DEPLOYMENTS_FILE, mode="r", encoding="utf-8") as file:
            deployments = json.load(file)
        deployment = deployments.get(deployment_name)

        repo_name = "/".join(deployment["repo_link"].split("/")[-2:])
        default_branch = deployment.get("default_branch")
        default_branch_commit_ref = self.get_head_commit_ref(repo_name, default_branch)

        deployment["commit_default_branch"] = default_branch_commit_ref
        if deployment.get("stage_deployment_type") == "auto":
            deployment["commit_stage"] = default_branch_commit_ref

        deployments[deployment_name] = deployment

        return save_json_data_and_return(deployments, config.DEPLOYMENTS_FILE)
