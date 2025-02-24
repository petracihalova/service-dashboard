import logging
from datetime import datetime, timedelta

import requests
from gitlab import Gitlab

import blueprints
import config
from utils import (
    PullRequestInfo,
    get_repos_info,
    load_json_data,
    save_json_data_and_return,
)

logger = logging.getLogger(__name__)


class GitlabAPI:
    def __init__(self):
        """Connection to the GitLab API."""
        self.gitlab_api = Gitlab(
            url=config.GITLAB_HOST, private_token=config.GITLAB_TOKEN, ssl_verify=False
        )
        try:
            self.gitlab_api.auth()
            logger.info(
                f"Successfully connected as {self.gitlab_api.user.username} via GitHub token."
            )
        except requests.exceptions.ConnectionError:
            logger.error("Connection Error: Check your VPN connection")

    def get_merge_requests(self, **kvargs):
        """
        Get open merge requests for GitLab projects (https://gitlab.cee.redhat.com)
        from links obtained from Overview page.
        """
        # Get list of GitHub projects from Overview page
        services_links = blueprints.get_services_links()
        gitlab_projects = get_repos_info(services_links, config.GL_REPO_PATTERN)

        state = kvargs["state"]
        result = {}
        for org, project_name in gitlab_projects:
            logger.info(
                f"Downloading '{state}' pull requests from '{org}/{project_name}'"
            )
            project = self.gitlab_api.projects.get(f"{org}/{project_name}")
            mrs = project.mergerequests.list(**kvargs)

            result[project_name] = [
                PullRequestInfo(
                    number=mr.iid,
                    draft=mr.draft,
                    title=mr.title,
                    created_at=mr.created_at,
                    merged_at=mr.merged_at,
                    user_login=mr.author.get("username"),
                    html_url=mr.web_url,
                )
                for mr in mrs
            ]
        return result

    def get_open_merge_requests(self):
        """Get list of open merge requests."""
        try:
            mrs = self.get_merge_requests(state="opened", order_by="created_at")
            return save_json_data_and_return(mrs, config.GL_OPEN_PR_FILE)

        except Exception as err:
            logger.error(err)
            return load_json_data(config.GL_OPEN_PR_FILE)

    def get_merged_merge_requests(self, days):
        """Get list of merged merge requests in last X days."""
        date_X_days_ago = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        try:
            mrs = self.get_merge_requests(
                state="merged", updated_after=date_X_days_ago, all=True
            )
            return save_json_data_and_return(mrs, config.GL_OPEN_PR_FILE)

        except Exception as err:
            logger.error(err)
            return load_json_data(config.GL_OPEN_PR_FILE)
