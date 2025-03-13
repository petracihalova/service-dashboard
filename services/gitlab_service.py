import logging
import re
from collections import namedtuple
from datetime import datetime, timedelta

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
        self.gitlab_api.auth()
        logger.info(
            f"Successfully connected as {self.gitlab_api.user.username} via GitLub token."
        )

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
            return save_json_data_and_return(
                mrs, config.GL_OPEN_PR_FILE, PullRequestEncoder
            )

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
            return save_json_data_and_return(
                mrs, config.GL_MERGED_PR_FILE, PullRequestEncoder
            )

        except Exception as err:
            logger.error(err)
            return load_json_data(config.GL_MERGED_PR_FILE)

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
                    deployments[depl_name]["repo_link"] = template["url"]
                    self._save_deployment_commit_refs(template, deployments[depl_name])
                    self._save_image_links(template, deployments[depl_name])

                    repo_name = "/".join(
                        deployments[depl_name]["repo_link"].split("/")[-2:]
                    )

                    default_branch = github_api.get_default_branch(repo_name)
                    deployments[depl_name]["default_branch"] = default_branch

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
