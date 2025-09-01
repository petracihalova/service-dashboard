import json
import logging
import re
from collections import namedtuple
from datetime import datetime, timezone

import requests
import urllib3
import yaml
from flask import flash
from gitlab import Gitlab

import blueprints
import config
from blueprints.overview import get_services_links
from services import github_service
from utils import (
    PullRequestInfo,
    get_repos_info,
    load_json_data,
    save_json_data_and_return,
)
from utils.json_utils import PullRequestEncoder

# https://urllib3.readthedocs.io/en/latest/advanced-usage.html#tls-warnings
urllib3.disable_warnings()

APP_INTERFACE = "service/app-interface"

DeployConfigMetaData = namedtuple("DeployConfigMetaData", "name, id")

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
                f"Successfully connected as {self.gitlab_api.user.username} via GitLab token."
            )
        except requests.exceptions.ConnectionError as err:
            logger.error(
                "Unable to connect to GitLab API - check your VPN connection and GitLab token"
            )
            raise err

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
                    body=mr.description,
                    created_at=mr.created_at,
                    merged_at=mr.merged_at,
                    merge_commit_sha=mr.merge_commit_sha if mr.merged_at else None,
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
            return save_json_data_and_return(
                mrs, config.GL_OPEN_PR_FILE, PullRequestEncoder
            )

        except Exception as err:
            logger.error(err)
            return load_json_data(config.GL_OPEN_PR_FILE)

    def get_merged_merge_requests(self, scope="all"):
        """Get list of merged merge requests."""
        if not scope or scope == "all":
            try:
                mrs = self.get_merge_requests(state="merged", all=True)
            except Exception as err:
                logger.error(err)
                mrs = {}
        elif scope == "missing":
            with open(config.GL_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
                data = json.load(file)
                timestamp = data.get("timestamp")
            try:
                new_mrs = self.get_merge_requests(
                    state="merged", updated_after=timestamp, all=True
                )
                mrs = self.add_missing_merge_requests(new_mrs)
            except Exception as err:
                logger.error(err)
                mrs = load_json_data(config.GL_MERGED_PR_FILE)
        else:
            raise ValueError("Get list of merged pull requests: invalid 'scope'")

        result = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": mrs}

        return save_json_data_and_return(
            result, config.GL_MERGED_PR_FILE, PullRequestEncoder
        )

    def add_missing_merge_requests(self, new_mrs):
        with open(config.GL_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            mrs = data.get("data")

        for repo_name, mrs_list in new_mrs.items():
            if repo_name not in mrs:
                mrs[repo_name] = []

            mr_numbers = [mr.get("number") for mr in mrs[repo_name]]
            for mr in mrs_list:
                if mr.number not in mr_numbers:
                    mrs[repo_name].append(
                        PullRequestInfo(
                            number=mr.number,
                            draft=mr.draft,
                            title=mr.title,
                            body=mr.body,
                            created_at=mr.created_at,
                            merged_at=mr.merged_at,
                            merge_commit_sha=mr.merge_commit_sha,
                            user_login=mr.user_login,
                            html_url=mr.html_url,
                        )
                    )
                    logger.info(
                        f"Added new merged merge request MR#{mr.number}: {mr.title}'"
                    )

        return mrs

    def update_deployment_data(self, deployment_name):
        logger.info(f"Downloading deployment '{deployment_name}'")
        with open(config.DEPLOYMENTS_FILE, mode="r", encoding="utf-8") as file:
            deployments = json.load(file)

        deployment = deployments.get(deployment_name)

        # Download the current version of the deployment file from app-interface
        self.app_interface_project = self.gitlab_api.projects.get(APP_INTERFACE)
        folder = deployment.get("app_interface_link").split("/")[-2]
        filename = deployment.get("app_interface_deploy_file")
        file_path = f"data/services/insights/{folder}/{filename}"

        file = self.app_interface_project.files.get(file_path=file_path, ref="master")
        file_content = file.decode()
        try:
            file_content_yaml = yaml.safe_load(file_content)
        except yaml.YAMLError as err:
            logger.error(err)

        deployment_original_name = deployment_name
        for key, value in config.DEPLOYMENT_RENAME_LIST.items():
            if value == deployment_original_name:
                deployment_original_name = key

        # Find the stage and prod target in the deployment file
        for template in file_content_yaml.get("resourceTemplates"):
            if template.get("name") == deployment_original_name:
                for target in template.get("targets"):
                    if target.get("namespace").get("$ref") == deployment.get(
                        "stage_target_name"
                    ):
                        deployment["commit_stage"] = target.get("ref")
                        if deployment.get("stage_deployment_type") == "manual":
                            self._get_release_mr(
                                deployments,
                                deployment_name,
                                file_path,
                                file_content,
                                "stage",
                            )

                    if target.get("namespace").get("$ref") == deployment.get(
                        "prod_target_name"
                    ):
                        deployment["commit_prod"] = target.get("ref")
                        if deployment.get("prod_deployment_type") == "manual":
                            self._get_release_mr(
                                deployments,
                                deployment_name,
                                file_path,
                                file_content,
                                "prod",
                            )

        deployments[deployment_name] = deployment
        with open(config.DEPLOYMENTS_FILE, mode="w", encoding="utf-8") as file:
            json.dump(deployments, file, indent=4)

    def get_app_interface_deployments(self):
        """
        Download deployments data from app-interface repository
        (https://gitlab.cee.redhat.com/service/app-interface)
        based on links from the Overview page.
        """
        github_api = github_service.GithubAPI()
        self.app_interface_project = self.gitlab_api.projects.get(APP_INTERFACE)

        app_interface_folders = self._get_app_interface_folders()
        deployments = {}

        # For all app-interface folder found on the Overview page
        for folder in app_interface_folders:
            logger.info(f"Downloading deployments from '{folder}'")

            # Find all deploy config files
            files = self._get_app_interface_deploy_config_files(folder)
            for item in files:
                logger.info(f"..Processing file: {item.name}")

                # Inside the deploy config file find relevant deployments
                folder_path = f"data/services/insights/{folder}/"
                file_path = folder_path + item.name
                file = self.app_interface_project.files.get(
                    file_path=file_path, ref="master"
                )
                file_content = file.decode()

                try:
                    file_content_yaml = yaml.safe_load(file_content)
                except yaml.YAMLError as err:
                    flash(err, category="danger")

                for template in file_content_yaml["resourceTemplates"]:
                    if any(
                        item in template["name"]
                        for item in config.DEPLOY_TEMPLATE_IGNORE_LIST
                    ):
                        continue

                    depl_name = template["name"]
                    depl_name = self._customize_deployment_name(depl_name)
                    logger.info("....Processing template: " + template["name"])

                    if depl_name not in deployments:
                        deployments[depl_name] = {}

                    deployments[depl_name]["app_interface_link"] = (
                        f"{config.GITLAB_HOST}/{APP_INTERFACE}/-/tree/master/{folder_path}"
                    )
                    deployments[depl_name]["app_interface_deploy_file"] = item.name
                    deployments[depl_name]["repo_link"] = template["url"]
                    self._save_deployment_commit_refs(template, deployments[depl_name])
                    self._save_image_links(template, deployments[depl_name])

                    repo_name = "/".join(
                        deployments[depl_name]["repo_link"].split("/")[-2:]
                    )

                    default_branch = github_api.get_default_branch(repo_name)
                    deployments[depl_name]["repo_name"] = repo_name
                    deployments[depl_name]["default_branch"] = default_branch

                    deployments[depl_name]["is_private"] = github_api.get_repo_type(
                        repo_name
                    )
                    deployments[depl_name]["language"] = github_api.get_repo_language(
                        repo_name
                    )

                    default_branch_commit_ref = github_api.get_head_commit_ref(
                        repo_name, default_branch
                    )
                    deployments[depl_name]["commit_default_branch"] = (
                        default_branch_commit_ref
                    )
                    if "stage_deployment_type" in deployments[depl_name]:
                        if deployments[depl_name]["stage_deployment_type"] == "auto":
                            deployments[depl_name]["commit_stage"] = (
                                default_branch_commit_ref
                            )
                        else:
                            self._get_release_mr(
                                deployments,
                                depl_name,
                                file_path,
                                file_content,
                                target="stage",
                            )

                    if "prod_deployment_type" in deployments[depl_name]:
                        if deployments[depl_name]["prod_deployment_type"] == "auto":
                            deployments[depl_name]["commit_prod"] = (
                                default_branch_commit_ref
                            )
                        else:
                            self._get_release_mr(
                                deployments,
                                depl_name,
                                file_path,
                                file_content,
                                target="prod",
                            )

        return save_json_data_and_return(deployments, config.DEPLOYMENTS_FILE)

    @staticmethod
    def _get_app_interface_folders():
        links = get_services_links()
        pattern = config.APP_INTERFACE_PATTERN
        folders = set()
        for category in links.get("categories", ()):
            for repo in category["category_repos"]:
                for link in repo["links"]:
                    if result := re.search(pattern, link["link_value"]):
                        f = result.group("folder").lower()
                        folders.add(f)
        return sorted(folders)

    def _get_app_interface_deploy_config_files(self, folder):
        """
        Get the list with deploy config files from app-interface repository
        (https://gitlab.cee.redhat.com/service/app-interface).
        """
        path = f"data/services/insights/{folder}/"
        files = self.app_interface_project.repository_tree(
            path=path, recursive=False, ref="master"
        )

        deploy_config_files = []
        for item in files:
            if (
                item["type"] == "blob"
                and item["name"] in config.VALID_DEPLOY_CONFIG_FILES
            ):
                deploy_config_files.append(
                    DeployConfigMetaData(name=item["name"], id=item["id"])
                )

        return deploy_config_files

    @staticmethod
    def _save_deployment_commit_refs(depl_config, depl_data):
        for target in depl_config["targets"]:
            if "stage" in target["namespace"]["$ref"]:
                if target["ref"] in ("main", "master"):
                    depl_data["stage_deployment_type"] = "auto"
                    depl_data["commit_stage"] = ""
                else:
                    depl_data["stage_deployment_type"] = "manual"
                    depl_data["commit_stage"] = target["ref"]
                depl_data["stage_target_name"] = target["namespace"]["$ref"]

            elif "prod" in target["namespace"]["$ref"]:
                if target["ref"] in ("main", "master"):
                    depl_data["prod_deployment_type"] = "auto"
                    depl_data["commit_prod"] = ""
                else:
                    depl_data["prod_deployment_type"] = "manual"
                    depl_data["commit_prod"] = target["ref"]
                depl_data["prod_target_name"] = target["namespace"]["$ref"]

    @staticmethod
    def _save_image_links(depl_config, depl_data):
        if depl_data.get("image_link", ""):
            return
        link = ""
        for target in depl_config["targets"]:
            if "stage" in target["namespace"]["$ref"]:
                if "parameters" in target and "IMAGE" in target["parameters"]:
                    link = target["parameters"]["IMAGE"]
                elif "parameters" in target and "REGISTRY_IMG" in target["parameters"]:
                    link = target["parameters"]["REGISTRY_IMG"]
                break
        if link:
            if not link.startswith("https://") or not link.startswith("http://"):
                link = "https://" + link

        depl_data["image_link"] = link

    @staticmethod
    def _customize_deployment_name(depl_name):
        if config.DEPLOYMENT_RENAME_LIST:
            for key, value in config.DEPLOYMENT_RENAME_LIST.items():
                if key == depl_name:
                    return value
        return depl_name

    def _get_release_mr(self, deployments, depl_name, file_path, file_content, target):
        blame = self.app_interface_project.files.blame(
            file_path=file_path, ref="master"
        )
        file_rows = str(file_content, "utf-8").split("\n")
        row = None
        for i, r in enumerate(file_rows):
            if deployments[depl_name][f"commit_{target}"] in r:
                row = i
                break
        counter = 0
        for b in blame:
            if counter >= row:
                commit_sha = b["commit"]["id"]
                break
            counter += len(b["lines"])
        commit = self.app_interface_project.commits.get(commit_sha)
        mrs = commit.merge_requests()
        deployments[depl_name][f"last_release_{target}_MR"] = {
            "url": mrs[0]["web_url"],
            "title": mrs[0]["title"],
            "merged_at": mrs[0]["merged_at"],
            "author": mrs[0]["author"]["username"],
        }

    def get_app_interface_open_mr(self):
        """
        Get list of open merge requests from app-interface repository.
        Apply a filter for users from APP_INTERFACE_USERS configuration.
        """
        logger.info(f"Downloading 'open' pull requests from '{APP_INTERFACE}'")
        project = self.gitlab_api.projects.get(APP_INTERFACE)
        mrs = project.mergerequests.list(state="opened", per_page=100)

        result = [
            PullRequestInfo(
                number=mr.iid,
                draft=mr.draft,
                title=mr.title,
                body=mr.description,
                created_at=mr.created_at,
                merged_at=mr.merged_at,
                merge_commit_sha=mr.merge_commit_sha if mr.merged_at else None,
                user_login=mr.author.get("username"),
                html_url=mr.web_url,
            )
            for mr in mrs
        ]

        # Filter for users from APP_INTERFACE_USERS configuration
        result = [
            mr
            for mr in result
            if mr.user_login.lower()
            in [user.lower() for user in config.APP_INTERFACE_USERS]
        ]

        return save_json_data_and_return(
            result, config.APP_INTERFACE_OPEN_MR_FILE, PullRequestEncoder
        )

    def get_app_interface_merged_mr(self, scope="all", merged_after="2024-01-01"):
        """
        Get list of merged merge requests from app-interface repository.
        """
        if not scope or scope == "all":
            try:
                project = self.gitlab_api.projects.get(APP_INTERFACE)

                merged_mrs = []
                # Download all merged merge requests for given user
                for user in config.APP_INTERFACE_USERS:
                    logger.info(
                        f"Downloading 'merged' pull requests from '{APP_INTERFACE}' merged after {merged_after} for user '{user}'"
                    )
                    # Handle pagination to fetch all merged MRs for the user
                    mrs = []
                    page = 1
                    while True:
                        page_mrs = project.mergerequests.list(
                            state="merged",
                            per_page=100,
                            page=page,
                            author_username=user,
                            merged_after=merged_after,
                        )
                        if not page_mrs:
                            break
                        mrs.extend(page_mrs)
                        if len(page_mrs) < 100:
                            break
                        page += 1
                    merged_mrs.extend(
                        [
                            PullRequestInfo(
                                number=mr.iid,
                                draft=mr.draft,
                                title=mr.title,
                                body=mr.description,
                                created_at=mr.created_at,
                                merged_at=mr.merged_at,
                                merge_commit_sha=(
                                    mr.merge_commit_sha if mr.merged_at else None
                                ),
                                user_login=mr.author.get("username"),
                                html_url=mr.web_url,
                            )
                            for mr in mrs
                            if mr.merged_at
                        ]
                    )
            except Exception as err:
                logger.error(err)
                merged_mrs = []
        elif scope == "missing":
            with open(
                config.APP_INTERFACE_MERGED_MR_FILE, mode="r", encoding="utf-8"
            ) as file:
                data = json.load(file)
                timestamp = data.get("timestamp")
            try:
                logger.info(
                    f"Downloading missing 'merged' pull requests from '{APP_INTERFACE}' since {timestamp}"
                )
                project = self.gitlab_api.projects.get(APP_INTERFACE)

                merged_mrs = []
                # Download missing merged merge requests for given user
                for user in config.APP_INTERFACE_USERS:
                    mrs = project.mergerequests.list(
                        state="merged",
                        per_page=100,
                        author_username=user,
                        updated_after=timestamp,
                    )

                    merged_mrs.extend(
                        [
                            PullRequestInfo(
                                number=mr.iid,
                                draft=mr.draft,
                                title=mr.title,
                                body=mr.description,
                                created_at=mr.created_at,
                                merged_at=mr.merged_at,
                                merge_commit_sha=(
                                    mr.merge_commit_sha if mr.merged_at else None
                                ),
                                user_login=mr.author.get("username"),
                                html_url=mr.web_url,
                            )
                            for mr in mrs
                        ]
                    )

                # Add missing MRs to existing data
                merged_mrs = self.add_missing_app_interface_merge_requests(merged_mrs)
            except Exception as err:
                logger.error(err)
                merged_mrs = load_json_data(config.APP_INTERFACE_MERGED_MR_FILE)
        else:
            raise ValueError(
                "Get list of app-interface merged merge requests: invalid 'scope'"
            )

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": merged_mrs,
        }

        return save_json_data_and_return(
            result, config.APP_INTERFACE_MERGED_MR_FILE, PullRequestEncoder
        )

    def get_app_interface_closed_mr(self, scope="all", closed_after="2024-01-01"):
        """
        Get list of closed merge requests from app-interface repository.
        Apply a filter for users from APP_INTERFACE_USERS configuration.
        """
        if not scope or scope == "all":
            try:
                project = self.gitlab_api.projects.get(APP_INTERFACE)

                closed_mrs = []
                # Download all closed merge requests for given user
                for user in config.APP_INTERFACE_USERS:
                    logger.info(
                        f"Downloading 'closed' pull requests from '{APP_INTERFACE}' closed after {closed_after} for user '{user}'"
                    )
                    # Handle pagination to fetch all closed MRs for the user
                    mrs = []
                    page = 1
                    while True:
                        page_mrs = project.mergerequests.list(
                            state="closed",
                            per_page=100,
                            page=page,
                            author_username=user,
                            updated_after=closed_after,
                        )
                        if not page_mrs:
                            break
                        mrs.extend(page_mrs)
                        if len(page_mrs) < 100:
                            break
                        page += 1
                    closed_mrs.extend(
                        [
                            PullRequestInfo(
                                number=mr.iid,
                                draft=mr.draft,
                                title=mr.title,
                                body=mr.description,
                                created_at=mr.created_at,
                                merged_at=mr.merged_at,
                                closed_at=mr.closed_at,
                                merge_commit_sha=(
                                    mr.merge_commit_sha if mr.merged_at else None
                                ),
                                user_login=mr.author.get("username"),
                                html_url=mr.web_url,
                            )
                            for mr in mrs
                            if mr.closed_at
                        ]
                    )
            except Exception as err:
                logger.error(err)
                closed_mrs = []
        elif scope == "missing":
            with open(
                config.APP_INTERFACE_CLOSED_MR_FILE, mode="r", encoding="utf-8"
            ) as file:
                data = json.load(file)
                timestamp = data.get("timestamp")
                closed_mrs = data.get("data", [])
            try:
                logger.info(
                    f"Downloading missing 'closed' pull requests from '{APP_INTERFACE}' since {timestamp}"
                )
                project = self.gitlab_api.projects.get(APP_INTERFACE)

                # Download missing closed merge requests for given user
                for user in config.APP_INTERFACE_USERS:
                    mrs = project.mergerequests.list(
                        state="closed",
                        per_page=100,
                        author_username=user,
                        updated_after=timestamp,
                    )

                    closed_mrs.extend(
                        [
                            PullRequestInfo(
                                number=mr.iid,
                                draft=mr.draft,
                                title=mr.title,
                                body=mr.description,
                                created_at=mr.created_at,
                                merged_at=mr.merged_at,
                                closed_at=mr.closed_at,
                                merge_commit_sha=(
                                    mr.merge_commit_sha if mr.merged_at else None
                                ),
                                user_login=mr.author.get("username"),
                                html_url=mr.web_url,
                            )
                            for mr in mrs
                            if mr.closed_at
                        ]
                    )
            except Exception as err:
                logger.error(err)
                closed_mrs = []

        result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": closed_mrs,
        }

        return save_json_data_and_return(
            result, config.APP_INTERFACE_CLOSED_MR_FILE, PullRequestEncoder
        )

    def add_missing_app_interface_merge_requests(self, new_mrs):
        """Add new merge requests to existing app-interface merged data."""
        with open(
            config.APP_INTERFACE_MERGED_MR_FILE, mode="r", encoding="utf-8"
        ) as file:
            data = json.load(file)
            existing_mrs = data.get("data", [])

        # Get existing MR numbers to avoid duplicates
        existing_mr_numbers = [mr.get("number") for mr in existing_mrs]

        # Add new MRs that don't exist yet
        for new_mr in new_mrs:
            if new_mr.number not in existing_mr_numbers:
                existing_mrs.append(new_mr)

        return existing_mrs
