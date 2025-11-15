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
    calculate_days_open,
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

    def _download_mrs_for_specific_repos(self, repos_list, **kvargs):
        """Download MRs for specific repositories.

        Args:
            repos_list: List of (org, project_name) tuples
            **kvargs: Additional parameters (state, updated_after, etc.)

        Returns:
            Dict mapping project_name to list of MRs
        """
        state = kvargs.get("state", "merged")
        result = {}

        for org, project_name in repos_list:
            logger.info(
                f"Downloading '{state}' MRs from '{org}/{project_name}' (new repository)"
            )
            try:
                project = self.gitlab_api.projects.get(f"{org}/{project_name}")
                mrs = project.mergerequests.list(**kvargs)

                mr_list = []
                for mr in mrs:
                    try:
                        detailed_mr = project.mergerequests.get(mr.iid)
                        changes = (
                            getattr(detailed_mr, "changes_count", None)
                            if hasattr(detailed_mr, "changes_count")
                            else None
                        )

                        mr_list.append(
                            PullRequestInfo(
                                number=mr.iid,
                                draft=mr.draft,
                                title=mr.title,
                                body=mr.description,
                                created_at=mr.created_at,
                                merged_at=mr.merged_at,
                                closed_at=mr.closed_at,
                                merge_commit_sha=mr.merge_commit_sha
                                if mr.merged_at
                                else None,
                                user_login=mr.author.get("username"),
                                html_url=mr.web_url,
                                additions=None,
                                deletions=None,
                                changed_files=changes,
                            )
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not fetch detailed stats for MR {mr.iid}: {e}"
                        )
                        mr_list.append(
                            PullRequestInfo(
                                number=mr.iid,
                                draft=mr.draft,
                                title=mr.title,
                                body=mr.description,
                                created_at=mr.created_at,
                                merged_at=mr.merged_at,
                                closed_at=mr.closed_at,
                                merge_commit_sha=mr.merge_commit_sha
                                if mr.merged_at
                                else None,
                                user_login=mr.author.get("username"),
                                html_url=mr.web_url,
                                additions=None,
                                deletions=None,
                                changed_files=None,
                            )
                        )

                result[project_name] = mr_list
                logger.info(
                    f"✅ Downloaded {len(mr_list)} {state} MRs from {project_name}"
                )
            except Exception as e:
                logger.error(f"❌ Error downloading MRs from {org}/{project_name}: {e}")
                result[project_name] = []

        return result

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

            mr_list = []
            for mr in mrs:
                # Get detailed MR info to fetch diff statistics
                try:
                    detailed_mr = project.mergerequests.get(mr.iid)
                    # For GitLab, diff stats are available in the detailed MR object
                    changes = (
                        getattr(detailed_mr, "changes_count", None)
                        if hasattr(detailed_mr, "changes_count")
                        else None
                    )

                    mr_list.append(
                        PullRequestInfo(
                            number=mr.iid,
                            draft=mr.draft,
                            title=mr.title,
                            body=mr.description,
                            created_at=mr.created_at,
                            merged_at=mr.merged_at,
                            closed_at=mr.closed_at,
                            merge_commit_sha=mr.merge_commit_sha
                            if mr.merged_at
                            else None,
                            user_login=mr.author.get("username"),
                            html_url=mr.web_url,
                            # GitLab provides diff stats differently - need to extract from changes
                            additions=None,  # GitLab doesn't provide separate additions/deletions easily
                            deletions=None,  # Will need additional API calls for precise stats
                            changed_files=changes,
                        )
                    )
                except Exception as e:
                    logger.warning(
                        f"Could not fetch detailed stats for MR {mr.iid}: {e}"
                    )
                    # Fall back to basic info without diff stats
                    mr_list.append(
                        PullRequestInfo(
                            number=mr.iid,
                            draft=mr.draft,
                            title=mr.title,
                            body=mr.description,
                            created_at=mr.created_at,
                            merged_at=mr.merged_at,
                            closed_at=mr.closed_at,
                            merge_commit_sha=mr.merge_commit_sha
                            if mr.merged_at
                            else None,
                            user_login=mr.author.get("username"),
                            html_url=mr.web_url,
                            additions=None,
                            deletions=None,
                            changed_files=None,
                        )
                    )

            result[project_name] = mr_list
        return result

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

    def get_closed_merge_requests(self, scope="all"):
        """Get list of closed (but not merged) merge requests."""
        if not scope or scope == "all":
            try:
                mrs = self.get_merge_requests(state="closed", all=True)
            except Exception as err:
                logger.error(err)
                mrs = {}
        elif scope == "missing":
            with open(config.GL_CLOSED_PR_FILE, mode="r", encoding="utf-8") as file:
                data = json.load(file)
                timestamp = data.get("timestamp")
            try:
                new_mrs = self.get_merge_requests(
                    state="closed", updated_after=timestamp, all=True
                )
                mrs = self.add_missing_closed_merge_requests(new_mrs)
            except Exception as err:
                logger.error(err)
                mrs = load_json_data(config.GL_CLOSED_PR_FILE)
        else:
            raise ValueError("Get list of closed merge requests: invalid 'scope'")

        result = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": mrs}

        return save_json_data_and_return(
            result, config.GL_CLOSED_PR_FILE, PullRequestEncoder
        )

    def add_missing_merge_requests(self, new_mrs):
        """Add missing merged MRs and handle new/removed repositories.

        Handles:
        - Incremental updates (adding new MRs to existing repos)
        - Full download for newly added repositories
        - Cleanup of removed repositories
        """
        # Get current list of GitLab projects from Overview page
        services_links = blueprints.get_services_links()
        gitlab_projects = get_repos_info(services_links, config.GL_REPO_PATTERN)
        current_repo_names = {repo_name.lower() for _, repo_name in gitlab_projects}

        with open(config.GL_MERGED_PR_FILE, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            mrs = data.get("data")

        # Get existing repository names from data
        existing_repo_names = set(mrs.keys())

        # Detect new and removed repositories
        new_repos = current_repo_names - existing_repo_names
        removed_repos = existing_repo_names - current_repo_names

        # Log changes
        if new_repos:
            logger.info(
                f"🆕 Detected {len(new_repos)} new GitLab repositories: {sorted(new_repos)}"
            )
        if removed_repos:
            logger.info(
                f"🗑️  Detected {len(removed_repos)} removed GitLab repositories: {sorted(removed_repos)}"
            )

        # STEP 1: Remove data for repositories no longer in overview
        for repo_name in removed_repos:
            del mrs[repo_name]
            logger.info(f"✅ Removed data for GitLab repository: {repo_name}")

        # STEP 2: Download full history for new repositories
        if new_repos:
            new_repo_projects = [
                (owner, repo)
                for owner, repo in gitlab_projects
                if repo.lower() in new_repos
            ]
            logger.info(
                f"📥 Downloading full merged MR history for {len(new_repo_projects)} new GitLab repositories..."
            )

            try:
                full_mrs = self._download_mrs_for_specific_repos(
                    new_repo_projects, state="merged", all=True
                )

                for repo_name, repo_mrs in full_mrs.items():
                    mrs[repo_name] = repo_mrs
                    logger.info(
                        f"✅ Downloaded {len(repo_mrs)} merged MRs for new GitLab repository: {repo_name}"
                    )
            except Exception as e:
                logger.error(f"❌ Error downloading MRs for new repositories: {e}")

        # STEP 3: Add incremental updates for existing repositories
        incremental_count = 0
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
                    incremental_count += 1

        if incremental_count > 0:
            logger.info(
                f"✅ Added {incremental_count} new merged MRs from incremental update"
            )

        logger.info(
            f"📊 GitLab Summary: {len(mrs)} repositories tracked, {sum(len(mr_list) for mr_list in mrs.values())} total merged MRs"
        )
        return mrs

    def add_missing_closed_merge_requests(self, new_mrs):
        """Add missing closed MRs and handle new/removed repositories.

        Handles:
        - Incremental updates (adding new MRs to existing repos)
        - Full download for newly added repositories
        - Cleanup of removed repositories
        """
        # Get current list of GitLab projects from Overview page
        services_links = blueprints.get_services_links()
        gitlab_projects = get_repos_info(services_links, config.GL_REPO_PATTERN)
        current_repo_names = {repo_name.lower() for _, repo_name in gitlab_projects}

        with open(config.GL_CLOSED_PR_FILE, mode="r", encoding="utf-8") as file:
            data = json.load(file)
            mrs = data.get("data")

        # Get existing repository names from data
        existing_repo_names = set(mrs.keys())

        # Detect new and removed repositories
        new_repos = current_repo_names - existing_repo_names
        removed_repos = existing_repo_names - current_repo_names

        # Log changes
        if new_repos:
            logger.info(
                f"🆕 Detected {len(new_repos)} new GitLab repositories: {sorted(new_repos)}"
            )
        if removed_repos:
            logger.info(
                f"🗑️  Detected {len(removed_repos)} removed GitLab repositories: {sorted(removed_repos)}"
            )

        # STEP 1: Remove data for repositories no longer in overview
        for repo_name in removed_repos:
            del mrs[repo_name]
            logger.info(f"✅ Removed data for GitLab repository: {repo_name}")

        # STEP 2: Download full history for new repositories
        if new_repos:
            new_repo_projects = [
                (owner, repo)
                for owner, repo in gitlab_projects
                if repo.lower() in new_repos
            ]
            logger.info(
                f"📥 Downloading full closed MR history for {len(new_repo_projects)} new GitLab repositories..."
            )

            try:
                full_mrs = self._download_mrs_for_specific_repos(
                    new_repo_projects, state="closed", all=True
                )

                for repo_name, repo_mrs in full_mrs.items():
                    mrs[repo_name] = repo_mrs
                    logger.info(
                        f"✅ Downloaded {len(repo_mrs)} closed MRs for new GitLab repository: {repo_name}"
                    )
            except Exception as e:
                logger.error(
                    f"❌ Error downloading closed MRs for new repositories: {e}"
                )

        # STEP 3: Add incremental updates for existing repositories
        incremental_count = 0
        for repo_name, mrs_list in new_mrs.items():
            if repo_name not in mrs:
                mrs[repo_name] = []

            mr_numbers = [mr.get("number") for mr in mrs[repo_name]]
            for mr in mrs_list:
                if mr.get("number") not in mr_numbers:
                    mrs[repo_name].append(mr)
                    incremental_count += 1

        if incremental_count > 0:
            logger.info(
                f"✅ Added {incremental_count} new closed MRs from incremental update"
            )

        logger.info(
            f"📊 GitLab Summary: {len(mrs)} repositories tracked, {sum(len(mr_list) for mr_list in mrs.values())} total closed MRs"
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

        # If row is None, we couldn't find the commit in the file
        if row is None:
            logger.warning(
                f"Could not find commit for {depl_name} {target} in file content"
            )
            return None

        commit_sha = None
        counter = 0
        for b in blame:
            if counter >= row:
                commit_sha = b["commit"]["id"]
                break
            counter += len(b["lines"])

        # If commit_sha is still None, we couldn't find it in blame data
        if commit_sha is None:
            logger.warning(
                f"Could not find commit_sha in blame data for {depl_name} {target}"
            )
            return None

        commit = self.app_interface_project.commits.get(commit_sha)
        mrs = commit.merge_requests()

        # Filter to only merged MRs (exclude closed/open ones)
        merged_mrs = [mr for mr in mrs if mr.get("state") == "merged"]

        if merged_mrs:
            # Sort by merged_at to get the most recent merged MR
            merged_mrs.sort(key=lambda x: x.get("merged_at", ""), reverse=True)

            # Get the opposite target (if looking for prod, check stage and vice versa)
            opposite_target = "stage" if target == "prod" else "prod"
            opposite_target_name = deployments[depl_name].get(
                f"{opposite_target}_target_name", ""
            )

            # Try to find an MR that modified ONLY this target, not both
            target_only_mrs = []
            for mr in merged_mrs:
                try:
                    # Get the MR changes to see what was actually modified
                    mr_obj = self.app_interface_project.mergerequests.get(mr["iid"])
                    changes = mr_obj.changes()

                    # Check if this file was modified in the MR
                    file_was_modified = False
                    target_was_modified = False
                    opposite_was_modified = False

                    for change in changes.get("changes", []):
                        if (
                            change.get("new_path") == file_path
                            or change.get("old_path") == file_path
                        ):
                            file_was_modified = True
                            diff = change.get("diff", "")

                            # Check if this target's namespace was modified
                            target_name = deployments[depl_name].get(
                                f"{target}_target_name", ""
                            )
                            if target_name and target_name in diff:
                                target_was_modified = True

                            # Check if the opposite target's namespace was modified
                            if opposite_target_name and opposite_target_name in diff:
                                opposite_was_modified = True

                            break

                    # If this MR modified only our target (not both), prefer it
                    if (
                        file_was_modified
                        and target_was_modified
                        and not opposite_was_modified
                    ):
                        target_only_mrs.append(mr)

                except Exception as e:
                    logger.debug(f"Could not check MR changes for {mr['iid']}: {e}")
                    continue

            # Prefer MRs that modified only this target
            if target_only_mrs:
                selected_mr = target_only_mrs[0]
                logger.info(
                    f"Found {target}-only MR for {depl_name}: '{selected_mr.get('title', '')}'"
                )
            else:
                # Fallback: try to find MR with target name in title
                target_specific_mrs = [
                    mr
                    for mr in merged_mrs
                    if target.lower() in mr.get("title", "").lower()
                ]

                selected_mr = (
                    target_specific_mrs[0] if target_specific_mrs else merged_mrs[0]
                )

                if not target_specific_mrs:
                    logger.info(
                        f"Using potentially shared MR for {depl_name} {target}: '{selected_mr.get('title', '')}'"
                    )
        elif mrs:
            # Fallback to first MR if no merged ones found (shouldn't happen in normal cases)
            logger.warning(
                f"No merged MR found for {depl_name} {target}, using first MR from {len(mrs)} total"
            )
            selected_mr = mrs[0]
        else:
            # No MRs at all
            logger.error(
                f"No MRs found for commit {commit_sha} in {depl_name} {target}"
            )
            return

        deployments[depl_name][f"last_release_{target}_MR"] = {
            "url": selected_mr["web_url"],
            "title": selected_mr["title"],
            "merged_at": selected_mr["merged_at"],
            "author": selected_mr["author"]["username"],
        }

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

    def _execute_gitlab_graphql_query(self, query: str) -> dict:
        """Execute a GraphQL query against GitLab API."""
        headers = {
            "Authorization": f"Bearer {config.GITLAB_TOKEN}",
            "Content-Type": "application/json",
        }

        payload = {"query": query}

        # GitLab GraphQL endpoint
        graphql_url = f"{config.GITLAB_HOST}/api/graphql"

        logger.debug(f"Executing GitLab GraphQL query: {query[:100]}...")

        response = requests.post(
            graphql_url, json=payload, headers=headers, verify=False
        )
        response.raise_for_status()

        response_data = response.json()

        if "errors" in response_data:
            logger.error(f"GitLab GraphQL errors: {response_data['errors']}")

        return response_data

    def generate_gitlab_graphql_query_for_open_mrs(self, projects: list) -> str:
        """Generate GraphQL query for open merge requests from specified GitLab projects."""

        # Build project paths for query
        project_paths = []
        for org, project_name in projects:
            project_paths.append(f'"{org}/{project_name}"')

        project_filter = "[" + ", ".join(project_paths) + "]"

        query = f"""
        {{
            projects(fullPaths: {project_filter}) {{
                nodes {{
                    name
                    mergeRequests(state: opened, first: 100) {{
                        pageInfo {{
                            hasNextPage
                            endCursor
                        }}
                        nodes {{
                            iid
                            title
                            description
                            draft
                            createdAt
                            webUrl
                            author {{
                                username
                            }}
                            targetBranch
                            diffStatsSummary {{
                                additions
                                deletions
                                fileCount
                            }}
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def generate_gitlab_graphql_query_for_merged_mrs(self, projects: list) -> str:
        """Generate GraphQL query for merged merge requests from specified GitLab projects."""

        # Build project paths for query
        project_paths = []
        for org, project_name in projects:
            project_paths.append(f'"{org}/{project_name}"')

        project_filter = "[" + ", ".join(project_paths) + "]"

        query = f"""
        {{
            projects(fullPaths: {project_filter}) {{
                nodes {{
                    name
                    mergeRequests(state: merged, first: 100) {{
                        pageInfo {{
                            hasNextPage
                            endCursor
                        }}
                        nodes {{
                            iid
                            title
                            description
                            draft
                            createdAt
                            mergedAt
                            webUrl
                            author {{
                                username
                            }}
                            targetBranch
                            diffStatsSummary {{
                                additions
                                deletions
                                fileCount
                            }}
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def generate_gitlab_graphql_query_for_closed_mrs(self, projects: list) -> str:
        """Generate GraphQL query for closed (but not merged) merge requests from specified GitLab projects."""

        # Build project paths for query
        project_paths = []
        for org, project_name in projects:
            project_paths.append(f'"{org}/{project_name}"')

        project_filter = "[" + ", ".join(project_paths) + "]"

        query = f"""
        {{
            projects(fullPaths: {project_filter}) {{
                nodes {{
                    name
                    mergeRequests(state: closed, first: 100) {{
                        pageInfo {{
                            hasNextPage
                            endCursor
                        }}
                        nodes {{
                            iid
                            title
                            description
                            draft
                            createdAt
                            closedAt
                            mergedAt
                            webUrl
                            author {{
                                username
                            }}
                            targetBranch
                            diffStatsSummary {{
                                additions
                                deletions
                                fileCount
                            }}
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def get_open_merge_requests_with_graphql(self):
        """Get list of open merge requests using GitLab GraphQL API."""
        if not config.GITLAB_TOKEN:
            logger.error("GitLab token is required for GraphQL API")
            return load_json_data(config.GL_OPEN_PR_FILE)

        try:
            # Get list of GitLab projects from Overview page
            services_links = blueprints.get_services_links()
            gitlab_projects = get_repos_info(services_links, config.GL_REPO_PATTERN)

            if not gitlab_projects:
                logger.warning("No GitLab projects found")
                return {}

            logger.info(
                f"Fetching open MRs using GitLab GraphQL for {len(gitlab_projects)} projects"
            )

            # Generate GraphQL query
            query = self.generate_gitlab_graphql_query_for_open_mrs(gitlab_projects)
            logger.debug(f"GitLab GraphQL query: {query}")

            # Execute GraphQL query
            response_data = self._execute_gitlab_graphql_query(query)
            logger.debug(f"GitLab GraphQL response keys: {list(response_data.keys())}")
            if "data" in response_data:
                logger.debug(
                    f"Response data keys: {list(response_data['data'].keys())}"
                )
            if "errors" in response_data:
                logger.error(f"GraphQL errors in response: {response_data['errors']}")

            # Process response
            mrs = self._process_gitlab_graphql_open_mrs_response(response_data)
            logger.info(
                f"Processed MRs by project: {[(p, len(mr_list)) for p, mr_list in mrs.items()]}"
            )

            # Log results
            total_mrs = sum(len(mr_list) for mr_list in mrs.values())
            logger.info(
                f"GitLab GraphQL API returned {total_mrs} open merge requests across {len(mrs)} projects"
            )

            # Save to file and return
            return save_json_data_and_return(
                mrs, config.GL_OPEN_PR_FILE, PullRequestEncoder
            )

        except Exception as err:
            logger.error(f"GitLab GraphQL API request failed: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return load_json_data(config.GL_OPEN_PR_FILE)

    def get_merged_merge_requests_with_graphql(self):
        """Get list of merged merge requests using GitLab GraphQL API."""
        if not config.GITLAB_TOKEN:
            logger.error("GitLab token is required for GraphQL API")
            return load_json_data(config.GL_MERGED_PR_FILE)

        try:
            # Get list of GitLab projects from Overview page
            services_links = blueprints.get_services_links()
            gitlab_projects = get_repos_info(services_links, config.GL_REPO_PATTERN)

            if not gitlab_projects:
                logger.warning("No GitLab projects found")
                return {}

            logger.info(
                f"Fetching merged MRs using GitLab GraphQL for {len(gitlab_projects)} projects"
            )

            # Generate GraphQL query
            query = self.generate_gitlab_graphql_query_for_merged_mrs(gitlab_projects)
            logger.debug(f"GitLab merged MRs GraphQL query: {query}")

            # Execute GraphQL query
            response_data = self._execute_gitlab_graphql_query(query)
            logger.debug(
                f"GitLab merged MRs GraphQL response keys: {list(response_data.keys())}"
            )
            if "data" in response_data:
                logger.debug(
                    f"Response data keys: {list(response_data['data'].keys())}"
                )
            if "errors" in response_data:
                logger.error(f"GraphQL errors in response: {response_data['errors']}")

            # Process response
            mrs = self._process_gitlab_graphql_merged_mrs_response(response_data)
            logger.info(
                f"Processed merged MRs by project: {[(p, len(mr_list)) for p, mr_list in mrs.items()]}"
            )

            # Log results
            total_mrs = sum(len(mr_list) for mr_list in mrs.values())
            logger.info(
                f"GitLab GraphQL API returned {total_mrs} merged merge requests across {len(mrs)} projects"
            )

            # Prepare result with timestamp
            result = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": mrs}

            # Save to file and return
            return save_json_data_and_return(
                result, config.GL_MERGED_PR_FILE, PullRequestEncoder
            )

        except Exception as err:
            logger.error(f"GitLab merged MRs GraphQL API request failed: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return load_json_data(config.GL_MERGED_PR_FILE)

    def get_closed_merge_requests_with_graphql(self):
        """Get list of closed (but not merged) merge requests using GitLab GraphQL API."""
        if not config.GITLAB_TOKEN:
            logger.error("GitLab token is required for GraphQL API")
            return load_json_data(config.GL_CLOSED_PR_FILE)

        try:
            # Get list of GitLab projects from Overview page
            services_links = blueprints.get_services_links()
            gitlab_projects = get_repos_info(services_links, config.GL_REPO_PATTERN)

            if not gitlab_projects:
                logger.warning("No GitLab projects found")
                return {}

            logger.info(
                f"Fetching closed MRs using GitLab GraphQL for {len(gitlab_projects)} projects"
            )

            # Generate GraphQL query
            query = self.generate_gitlab_graphql_query_for_closed_mrs(gitlab_projects)
            logger.debug(f"GitLab closed MRs GraphQL query: {query}")

            # Execute GraphQL query
            response_data = self._execute_gitlab_graphql_query(query)
            logger.debug(
                f"GitLab closed MRs GraphQL response keys: {list(response_data.keys())}"
            )
            if "data" in response_data:
                logger.debug(
                    f"Response data keys: {list(response_data['data'].keys())}"
                )
            if "errors" in response_data:
                logger.error(f"GraphQL errors in response: {response_data['errors']}")

            # Process response
            mrs = self._process_gitlab_graphql_closed_mrs_response(response_data)
            logger.info(
                f"Processed closed MRs by project: {[(p, len(mr_list)) for p, mr_list in mrs.items()]}"
            )

            # Log results
            total_mrs = sum(len(mr_list) for mr_list in mrs.values())
            logger.info(
                f"GitLab GraphQL API returned {total_mrs} closed merge requests across {len(mrs)} projects"
            )

            # Prepare result with timestamp
            result = {"timestamp": datetime.now(timezone.utc).isoformat(), "data": mrs}

            # Save to file and return
            return save_json_data_and_return(
                result, config.GL_CLOSED_PR_FILE, PullRequestEncoder
            )

        except Exception as err:
            logger.error(f"GitLab closed MRs GraphQL API request failed: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return load_json_data(config.GL_CLOSED_PR_FILE)

    def _process_gitlab_graphql_open_mrs_response(self, response_data: dict) -> dict:
        """Process GitLab GraphQL response data into PullRequestInfo objects organized by project."""
        result = {}

        if "data" not in response_data or "projects" not in response_data["data"]:
            logger.error(
                f"Unexpected GitLab GraphQL response structure: {response_data}"
            )
            return result

        projects = response_data["data"]["projects"]["nodes"]
        logger.debug(f"Found {len(projects)} projects in GraphQL response")

        for i, project in enumerate(projects):
            logger.debug(
                f"Project {i}: type={type(project)}, keys={list(project.keys()) if isinstance(project, dict) else 'not dict'}"
            )

        for project in projects:
            if not project or "mergeRequests" not in project:
                logger.debug(f"Skipping project: {project} (no mergeRequests)")
                continue

            project_name = project["name"]
            merge_requests = project["mergeRequests"]["nodes"]

            logger.debug(f"Project '{project_name}' has {len(merge_requests)} open MRs")
            logger.debug(f"merge_requests type: {type(merge_requests)}")
            if merge_requests:
                logger.debug(
                    f"First MR type: {type(merge_requests[0])}, sample: {str(merge_requests[0])[:100]}..."
                )

            if not merge_requests:
                logger.debug(f"No open MRs found for project '{project_name}'")
                continue

            # Initialize project list if not exists
            result[project_name] = []

            for i, mr in enumerate(merge_requests):
                if not mr:
                    logger.debug(f"Skipping empty MR at index {i}")
                    continue

                logger.debug(
                    f"Processing MR {i + 1}/{len(merge_requests)}: type={type(mr)}, content={str(mr)[:200]}..."
                )

                if not isinstance(mr, dict):
                    logger.error(f"Expected dict for MR, got {type(mr)}: {mr}")
                    continue

                # Parse datetime strings
                try:
                    created_at = datetime.fromisoformat(
                        mr["createdAt"].replace("Z", "+00:00")
                    )
                except Exception as e:
                    logger.error(
                        f"Error parsing createdAt for MR {mr.get('iid', 'unknown')}: {e}"
                    )
                    continue

                # Get author username (handle case where author might be null)
                author_username = "unknown"
                try:
                    if mr.get("author") and mr["author"].get("username"):
                        author_username = mr["author"]["username"]
                except Exception as e:
                    logger.debug(
                        f"Error getting author for MR {mr.get('iid', 'unknown')}: {e}"
                    )

                # Get diff statistics from GitLab GraphQL
                additions = None
                deletions = None
                changed_files = None

                try:
                    if mr.get("diffStatsSummary") and isinstance(
                        mr["diffStatsSummary"], dict
                    ):
                        diff_stats = mr["diffStatsSummary"]
                        additions = diff_stats.get("additions")
                        deletions = diff_stats.get("deletions")
                        changed_files = diff_stats.get(
                            "fileCount"
                        )  # GitLab uses fileCount
                        logger.debug(
                            f"MR {mr.get('iid')}: +{additions} -{deletions} ({changed_files} files)"
                        )
                except Exception as e:
                    logger.debug(
                        f"Error getting diff stats for MR {mr.get('iid', 'unknown')}: {e}"
                    )

                # Note: No need for commit counting fallback since diffStatsSummary.fileCount should provide this

                try:
                    mr_info = PullRequestInfo(
                        number=mr.get("iid", 0),
                        draft=mr.get("draft", False),
                        title=mr.get("title", ""),
                        body=mr.get("description", "") or "",
                        created_at=created_at,
                        merged_at=None,  # Open MRs are not merged
                        closed_at=None,  # Open MRs are not closed
                        merge_commit_sha=None,  # No merge commit for open MRs
                        user_login=author_username,
                        html_url=mr.get("webUrl", ""),
                        branch=mr.get("targetBranch", ""),
                        additions=additions,
                        deletions=deletions,
                        changed_files=changed_files,
                    )

                    result[project_name].append(mr_info)
                    logger.debug(
                        f"Successfully processed MR {mr.get('iid')} from {project_name}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error creating PullRequestInfo for MR {mr.get('iid', 'unknown')}: {e}"
                    )
                    continue

        return result

    def _process_gitlab_graphql_merged_mrs_response(self, response_data: dict) -> dict:
        """Process GitLab GraphQL response data for merged MRs into PullRequestInfo objects organized by project."""
        result = {}

        if "data" not in response_data or "projects" not in response_data["data"]:
            logger.error(
                f"Unexpected GitLab merged MRs GraphQL response structure: {response_data}"
            )
            return result

        projects = response_data["data"]["projects"]["nodes"]
        logger.debug(f"Found {len(projects)} projects in merged MRs GraphQL response")

        for project in projects:
            if not project or "mergeRequests" not in project:
                logger.debug(
                    f"Skipping merged MRs project: {project} (no mergeRequests)"
                )
                continue

            project_name = project["name"]
            merge_requests = project["mergeRequests"]["nodes"]

            logger.debug(
                f"Project '{project_name}' has {len(merge_requests)} merged MRs"
            )

            if not merge_requests:
                logger.debug(f"No merged MRs found for project '{project_name}'")
                continue

            # Initialize project list if not exists
            result[project_name] = []

            for i, mr in enumerate(merge_requests):
                if not mr or not isinstance(mr, dict):
                    logger.debug(f"Skipping invalid merged MR at index {i}")
                    continue

                # Parse datetime strings
                try:
                    created_at = datetime.fromisoformat(
                        mr["createdAt"].replace("Z", "+00:00")
                    )
                    merged_at = datetime.fromisoformat(
                        mr["mergedAt"].replace("Z", "+00:00")
                    )
                except Exception as e:
                    logger.error(
                        f"Error parsing dates for merged MR {mr.get('iid', 'unknown')}: {e}"
                    )
                    continue

                # Get author username
                author_username = "unknown"
                try:
                    if mr.get("author") and mr["author"].get("username"):
                        author_username = mr["author"]["username"]
                except Exception as e:
                    logger.debug(
                        f"Error getting author for merged MR {mr.get('iid', 'unknown')}: {e}"
                    )

                # Get diff statistics
                additions = None
                deletions = None
                changed_files = None

                try:
                    if mr.get("diffStatsSummary") and isinstance(
                        mr["diffStatsSummary"], dict
                    ):
                        diff_stats = mr["diffStatsSummary"]
                        additions = diff_stats.get("additions")
                        deletions = diff_stats.get("deletions")
                        changed_files = diff_stats.get("fileCount")
                        logger.debug(
                            f"Merged MR {mr.get('iid')}: +{additions} -{deletions} ({changed_files} files)"
                        )
                except Exception as e:
                    logger.debug(
                        f"Error getting diff stats for merged MR {mr.get('iid', 'unknown')}: {e}"
                    )

                try:
                    # Calculate days the MR was open (for merged MRs)
                    days_open = calculate_days_open(created_at, merged_at)

                    mr_info = PullRequestInfo(
                        number=mr.get("iid", 0),
                        draft=mr.get("draft", False),
                        title=mr.get("title", ""),
                        body=mr.get("description", "") or "",
                        created_at=created_at,
                        merged_at=merged_at,
                        closed_at=None,  # Merged MRs are not closed, they're merged
                        merge_commit_sha=None,  # Would need additional query for this
                        user_login=author_username,
                        html_url=mr.get("webUrl", ""),
                        branch=mr.get("targetBranch", ""),
                        additions=additions,
                        deletions=deletions,
                        changed_files=changed_files,
                        days_open=days_open,
                    )

                    result[project_name].append(mr_info)
                    logger.debug(
                        f"Successfully processed merged MR {mr.get('iid')} from {project_name}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error creating PullRequestInfo for merged MR {mr.get('iid', 'unknown')}: {e}"
                    )
                    continue

        return result

    def _process_gitlab_graphql_closed_mrs_response(self, response_data: dict) -> dict:
        """Process GitLab GraphQL response data for closed MRs into PullRequestInfo objects organized by project."""
        result = {}

        if "data" not in response_data or "projects" not in response_data["data"]:
            logger.error(
                f"Unexpected GitLab closed MRs GraphQL response structure: {response_data}"
            )
            return result

        projects = response_data["data"]["projects"]["nodes"]
        logger.debug(f"Found {len(projects)} projects in closed MRs GraphQL response")

        for project in projects:
            if not project or "mergeRequests" not in project:
                logger.debug(
                    f"Skipping closed MRs project: {project} (no mergeRequests)"
                )
                continue

            project_name = project["name"]
            merge_requests = project["mergeRequests"]["nodes"]

            logger.debug(
                f"Project '{project_name}' has {len(merge_requests)} closed MRs"
            )

            if not merge_requests:
                logger.debug(f"No closed MRs found for project '{project_name}'")
                continue

            # Initialize project list if not exists
            result[project_name] = []

            for i, mr in enumerate(merge_requests):
                if not mr or not isinstance(mr, dict):
                    logger.debug(f"Skipping invalid closed MR at index {i}")
                    continue

                # Skip merged MRs - we only want closed but not merged
                if mr.get("mergedAt"):
                    logger.debug(f"Skipping merged MR {mr.get('iid')} in closed query")
                    continue

                # Parse datetime strings
                try:
                    created_at = datetime.fromisoformat(
                        mr["createdAt"].replace("Z", "+00:00")
                    )
                    closed_at = None
                    if mr.get("closedAt"):
                        closed_at = datetime.fromisoformat(
                            mr["closedAt"].replace("Z", "+00:00")
                        )
                except Exception as e:
                    logger.error(
                        f"Error parsing dates for closed MR {mr.get('iid', 'unknown')}: {e}"
                    )
                    continue

                # Get author username
                author_username = "unknown"
                try:
                    if mr.get("author") and mr["author"].get("username"):
                        author_username = mr["author"]["username"]
                except Exception as e:
                    logger.debug(
                        f"Error getting author for closed MR {mr.get('iid', 'unknown')}: {e}"
                    )

                # Get diff statistics
                additions = None
                deletions = None
                changed_files = None

                try:
                    if mr.get("diffStatsSummary") and isinstance(
                        mr["diffStatsSummary"], dict
                    ):
                        diff_stats = mr["diffStatsSummary"]
                        additions = diff_stats.get("additions")
                        deletions = diff_stats.get("deletions")
                        changed_files = diff_stats.get("fileCount")
                        logger.debug(
                            f"Closed MR {mr.get('iid')}: +{additions} -{deletions} ({changed_files} files)"
                        )
                except Exception as e:
                    logger.debug(
                        f"Error getting diff stats for closed MR {mr.get('iid', 'unknown')}: {e}"
                    )

                try:
                    # Calculate days the MR was open (for closed MRs)
                    days_open = calculate_days_open(created_at, closed_at)

                    mr_info = PullRequestInfo(
                        number=mr.get("iid", 0),
                        draft=mr.get("draft", False),
                        title=mr.get("title", ""),
                        body=mr.get("description", "") or "",
                        created_at=created_at,
                        merged_at=None,  # Closed MRs are not merged
                        closed_at=closed_at,
                        merge_commit_sha=None,  # No merge commit for closed MRs
                        user_login=author_username,
                        html_url=mr.get("webUrl", ""),
                        branch=mr.get("targetBranch", ""),
                        additions=additions,
                        deletions=deletions,
                        changed_files=changed_files,
                        days_open=days_open,
                    )

                    result[project_name].append(mr_info)
                    logger.debug(
                        f"Successfully processed closed MR {mr.get('iid')} from {project_name}"
                    )

                except Exception as e:
                    logger.error(
                        f"Error creating PullRequestInfo for closed MR {mr.get('iid', 'unknown')}: {e}"
                    )
                    continue

        return result

    def generate_gitlab_graphql_query_for_app_interface_open_mrs(
        self, after_cursor: str = None
    ) -> str:
        """Generate GraphQL query for open merge requests from app-interface repository."""

        # Build pagination parameter
        after_param = f', after: "{after_cursor}"' if after_cursor else ""

        query = f"""
        {{
            project(fullPath: "{APP_INTERFACE}") {{
                mergeRequests(state: opened, first: 100{after_param}) {{
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    nodes {{
                        iid
                        title
                        description
                        draft
                        createdAt
                        webUrl
                        author {{
                            username
                        }}
                        targetBranch
                        diffStatsSummary {{
                            additions
                            deletions
                            fileCount
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def generate_gitlab_graphql_query_for_app_interface_merged_mrs(
        self,
        author_username: str = None,
        after_cursor: str = None,
        merged_after: str = None,
    ) -> str:
        """Generate GraphQL query for merged merge requests from app-interface repository."""

        # Build author filter if provided
        author_filter = (
            f', authorUsername: "{author_username}"' if author_username else ""
        )

        # Build pagination parameter
        after_param = f', after: "{after_cursor}"' if after_cursor else ""

        # Build date filter if provided (format: "2024-01-01T00:00:00Z")
        merged_after_param = ""
        if merged_after:
            # Convert YYYY-MM-DD to ISO format for GraphQL
            merged_after_param = f', mergedAfter: "{merged_after}T00:00:00Z"'

        query = f"""
        {{
            project(fullPath: "{APP_INTERFACE}") {{
                mergeRequests(state: merged, first: 100{author_filter}{merged_after_param}{after_param}) {{
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    nodes {{
                        iid
                        title
                        description
                        draft
                        createdAt
                        mergedAt
                        webUrl
                        author {{
                            username
                        }}
                        targetBranch
                        diffStatsSummary {{
                            additions
                            deletions
                            fileCount
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def generate_gitlab_graphql_query_for_app_interface_closed_mrs(
        self,
        author_username: str = None,
        after_cursor: str = None,
        closed_after: str = None,
    ) -> str:
        """Generate GraphQL query for closed merge requests from app-interface repository.

        Note: GitLab's GraphQL API doesn't support closedAfter filtering, so we fetch all closed MRs
        and filter by date in the application layer.
        """

        # Build author filter if provided
        author_filter = (
            f', authorUsername: "{author_username}"' if author_username else ""
        )

        # Build pagination parameter
        after_param = f', after: "{after_cursor}"' if after_cursor else ""

        # Note: closedAfter is not supported by GitLab's GraphQL API
        # Date filtering will be done in the application layer

        query = f"""
        {{
            project(fullPath: "{APP_INTERFACE}") {{
                mergeRequests(state: closed, first: 100{author_filter}{after_param}) {{
                    pageInfo {{
                        hasNextPage
                        endCursor
                    }}
                    nodes {{
                        iid
                        title
                        description
                        draft
                        createdAt
                        closedAt
                        mergedAt
                        webUrl
                        author {{
                            username
                        }}
                        targetBranch
                        diffStatsSummary {{
                            additions
                            deletions
                            fileCount
                        }}
                    }}
                }}
            }}
        }}"""

        return query

    def get_app_interface_open_mr_with_graphql(self):
        """Get list of open merge requests from app-interface repository using GitLab GraphQL API."""
        if not config.GITLAB_TOKEN:
            logger.error("GitLab token is required for GraphQL API")
            return load_json_data(config.APP_INTERFACE_OPEN_MR_FILE)

        try:
            logger.info("Fetching open MRs from app-interface using GitLab GraphQL")

            all_mrs = []
            has_next_page = True
            after_cursor = None
            page_num = 1

            # Paginate through all results
            while has_next_page:
                logger.info(f"Fetching page {page_num} of open MRs...")

                # Generate GraphQL query with cursor
                query = self.generate_gitlab_graphql_query_for_app_interface_open_mrs(
                    after_cursor=after_cursor
                )
                logger.debug(
                    f"App-interface open MRs GraphQL query (page {page_num}): {query[:200]}..."
                )

                # Execute GraphQL query
                response_data = self._execute_gitlab_graphql_query(query)
                if "errors" in response_data:
                    logger.error(
                        f"GraphQL errors in response: {response_data['errors']}"
                    )

                # Process response
                mrs, page_info = self._process_app_interface_graphql_open_mrs_response(
                    response_data
                )
                logger.info(f"Processed {len(mrs)} open MRs from page {page_num}")

                all_mrs.extend(mrs)

                # Check if there are more pages
                has_next_page = page_info.get("hasNextPage", False)
                after_cursor = page_info.get("endCursor")
                page_num += 1

                if has_next_page:
                    logger.info(
                        f"More pages available, continuing to page {page_num}..."
                    )

            logger.info(
                f"Processed total of {len(all_mrs)} open MRs from app-interface across {page_num - 1} page(s)"
            )

            # Filter for users from APP_INTERFACE_USERS configuration
            if not config.APP_INTERFACE_USERS:
                logger.warning(
                    f"APP_INTERFACE_USERS is not configured! Using all {len(all_mrs)} MRs without filtering."
                )
                logger.warning(
                    "Set APP_INTERFACE_USERS environment variable to enable user filtering."
                )
                filtered_mrs = all_mrs  # Don't filter if no users configured
            else:
                filtered_mrs = [
                    mr
                    for mr in all_mrs
                    if mr.user_login.lower()
                    in [user.lower() for user in config.APP_INTERFACE_USERS]
                ]
                logger.info(
                    f"Filtered to {len(filtered_mrs)} MRs for app-interface users: {config.APP_INTERFACE_USERS}"
                )

            # Save to file and return
            return save_json_data_and_return(
                filtered_mrs, config.APP_INTERFACE_OPEN_MR_FILE, PullRequestEncoder
            )

        except Exception as err:
            logger.error(f"App-interface open MRs GraphQL API request failed: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return load_json_data(config.APP_INTERFACE_OPEN_MR_FILE)

    def get_app_interface_merged_mr_with_graphql(self, merged_after="2024-01-01"):
        """Get list of merged merge requests from app-interface repository using GitLab GraphQL API."""
        if not config.GITLAB_TOKEN:
            logger.error("GitLab token is required for GraphQL API")
            return load_json_data(config.APP_INTERFACE_MERGED_MR_FILE)

        try:
            logger.info(
                f"Fetching merged MRs from app-interface using GitLab GraphQL (after {merged_after})"
            )

            all_mrs = []

            if not config.APP_INTERFACE_USERS:
                logger.warning(
                    "APP_INTERFACE_USERS not configured! Fetching all merged MRs with pagination."
                )
                logger.warning(
                    "Set APP_INTERFACE_USERS environment variable to filter by specific users."
                )

                # Paginate through all results without user filter
                has_next_page = True
                after_cursor = None
                page_num = 1

                while has_next_page:
                    logger.info(
                        f"Fetching page {page_num} of merged MRs (no user filter)..."
                    )

                    query = (
                        self.generate_gitlab_graphql_query_for_app_interface_merged_mrs(
                            after_cursor=after_cursor, merged_after=merged_after
                        )
                    )
                    logger.debug(
                        f"App-interface merged MRs GraphQL query (page {page_num}, no user filter): {query[:200]}..."
                    )

                    response_data = self._execute_gitlab_graphql_query(query)
                    if "errors" in response_data:
                        logger.error(
                            f"GraphQL errors in response: {response_data['errors']}"
                        )
                        break

                    mrs, page_info = (
                        self._process_app_interface_graphql_merged_mrs_response(
                            response_data
                        )
                    )
                    logger.info(f"Processed {len(mrs)} merged MRs from page {page_num}")

                    all_mrs.extend(mrs)

                    # Check if there are more pages
                    has_next_page = page_info.get("hasNextPage", False)
                    after_cursor = page_info.get("endCursor")
                    page_num += 1

                    if has_next_page:
                        logger.info(
                            f"More pages available, continuing to page {page_num}..."
                        )

                logger.info(
                    f"Total: {len(all_mrs)} merged MRs across {page_num - 1} page(s)"
                )

            else:
                # Multiple queries - one per user for optimal filtering
                logger.info(
                    f"Fetching MRs for {len(config.APP_INTERFACE_USERS)} users: {config.APP_INTERFACE_USERS}"
                )

                for user in config.APP_INTERFACE_USERS:
                    logger.info(f"Fetching merged MRs for user: {user}")

                    # Paginate through all results for this user
                    user_has_next_page = True
                    user_after_cursor = None
                    user_page_num = 1
                    user_total_mrs = []

                    while user_has_next_page:
                        logger.info(
                            f"Fetching page {user_page_num} of merged MRs for user {user}..."
                        )

                        query = self.generate_gitlab_graphql_query_for_app_interface_merged_mrs(
                            author_username=user,
                            after_cursor=user_after_cursor,
                            merged_after=merged_after,
                        )
                        logger.debug(
                            f"App-interface merged MRs GraphQL query for {user} (page {user_page_num}): {query[:200]}..."
                        )

                        response_data = self._execute_gitlab_graphql_query(query)
                        if "errors" in response_data:
                            logger.error(
                                f"GraphQL errors for user {user}: {response_data['errors']}"
                            )
                            break

                        user_mrs, page_info = (
                            self._process_app_interface_graphql_merged_mrs_response(
                                response_data
                            )
                        )
                        logger.info(
                            f"Processed {len(user_mrs)} merged MRs from page {user_page_num} for user {user}"
                        )

                        user_total_mrs.extend(user_mrs)

                        # Check if there are more pages for this user
                        user_has_next_page = page_info.get("hasNextPage", False)
                        user_after_cursor = page_info.get("endCursor")
                        user_page_num += 1

                        if user_has_next_page:
                            logger.info(
                                f"More pages available for user {user}, continuing to page {user_page_num}..."
                            )

                    logger.info(
                        f"Total: {len(user_total_mrs)} merged MRs for user {user} across {user_page_num - 1} page(s)"
                    )
                    all_mrs.extend(user_total_mrs)

                logger.info(
                    f"Total processed {len(all_mrs)} merged MRs from app-interface"
                )
                filtered_mrs = all_mrs  # Already filtered by GraphQL queries

                # Prepare result with timestamp
                result = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": filtered_mrs,
                }

                # Save to file and return
                return save_json_data_and_return(
                    result, config.APP_INTERFACE_MERGED_MR_FILE, PullRequestEncoder
                )

        except Exception as err:
            logger.error(f"App-interface merged MRs GraphQL API request failed: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return load_json_data(config.APP_INTERFACE_MERGED_MR_FILE)

    def get_app_interface_closed_mr_with_graphql(self, closed_after="2024-01-01"):
        """Get list of closed merge requests from app-interface repository using GitLab GraphQL API."""
        if not config.GITLAB_TOKEN:
            logger.error("GitLab token is required for GraphQL API")
            return load_json_data(config.APP_INTERFACE_CLOSED_MR_FILE)

        try:
            logger.info(
                f"Fetching closed MRs from app-interface using GitLab GraphQL (after {closed_after})"
            )

            all_mrs = []

            if not config.APP_INTERFACE_USERS:
                logger.warning(
                    "APP_INTERFACE_USERS not configured! Fetching all closed MRs with pagination."
                )
                logger.warning(
                    "Set APP_INTERFACE_USERS environment variable to filter by specific users."
                )

                # Paginate through all results without user filter
                has_next_page = True
                after_cursor = None
                page_num = 1

                while has_next_page:
                    logger.info(
                        f"Fetching page {page_num} of closed MRs (no user filter)..."
                    )

                    query = (
                        self.generate_gitlab_graphql_query_for_app_interface_closed_mrs(
                            after_cursor=after_cursor, closed_after=closed_after
                        )
                    )
                    logger.debug(
                        f"App-interface closed MRs GraphQL query (page {page_num}, no user filter): {query[:200]}..."
                    )

                    response_data = self._execute_gitlab_graphql_query(query)
                    if "errors" in response_data:
                        logger.error(
                            f"GraphQL errors in response: {response_data['errors']}"
                        )
                        break

                    mrs, page_info = (
                        self._process_app_interface_graphql_closed_mrs_response(
                            response_data
                        )
                    )
                    logger.info(f"Processed {len(mrs)} closed MRs from page {page_num}")

                    all_mrs.extend(mrs)

                    # Check if there are more pages
                    has_next_page = page_info.get("hasNextPage", False)
                    after_cursor = page_info.get("endCursor")
                    page_num += 1

                    if has_next_page:
                        logger.info(
                            f"More pages available, continuing to page {page_num}..."
                        )

                logger.info(
                    f"Total: {len(all_mrs)} closed MRs across {page_num - 1} page(s)"
                )

            else:
                # Multiple queries - one per user for optimal filtering
                logger.info(
                    f"Fetching MRs for {len(config.APP_INTERFACE_USERS)} users: {config.APP_INTERFACE_USERS}"
                )

                for user in config.APP_INTERFACE_USERS:
                    logger.info(f"Fetching closed MRs for user: {user}")

                    # Paginate through all results for this user
                    user_has_next_page = True
                    user_after_cursor = None
                    user_page_num = 1
                    user_total_mrs = []

                    while user_has_next_page:
                        logger.info(
                            f"Fetching page {user_page_num} of closed MRs for user {user}..."
                        )

                        query = self.generate_gitlab_graphql_query_for_app_interface_closed_mrs(
                            author_username=user,
                            after_cursor=user_after_cursor,
                            closed_after=closed_after,
                        )
                        logger.debug(
                            f"App-interface closed MRs GraphQL query for {user} (page {user_page_num}): {query[:200]}..."
                        )

                        response_data = self._execute_gitlab_graphql_query(query)
                        if "errors" in response_data:
                            logger.error(
                                f"GraphQL errors for user {user}: {response_data['errors']}"
                            )
                            break

                        user_mrs, page_info = (
                            self._process_app_interface_graphql_closed_mrs_response(
                                response_data
                            )
                        )
                        logger.info(
                            f"Processed {len(user_mrs)} closed MRs from page {user_page_num} for user {user}"
                        )

                        user_total_mrs.extend(user_mrs)

                        # Check if there are more pages for this user
                        user_has_next_page = page_info.get("hasNextPage", False)
                        user_after_cursor = page_info.get("endCursor")
                        user_page_num += 1

                        if user_has_next_page:
                            logger.info(
                                f"More pages available for user {user}, continuing to page {user_page_num}..."
                            )

                    logger.info(
                        f"Total: {len(user_total_mrs)} closed MRs for user {user} across {user_page_num - 1} page(s)"
                    )
                    all_mrs.extend(user_total_mrs)

            logger.info(f"Total processed {len(all_mrs)} closed MRs from app-interface")
            filtered_mrs = all_mrs  # Already filtered by GraphQL queries

            # Prepare result with timestamp
            result = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": filtered_mrs,
            }

            # Save to file and return
            return save_json_data_and_return(
                result, config.APP_INTERFACE_CLOSED_MR_FILE, PullRequestEncoder
            )

        except Exception as err:
            logger.error(f"App-interface closed MRs GraphQL API request failed: {err}")
            import traceback

            logger.error(f"Full traceback: {traceback.format_exc()}")
            return load_json_data(config.APP_INTERFACE_CLOSED_MR_FILE)

    def _process_app_interface_graphql_open_mrs_response(
        self, response_data: dict
    ) -> tuple[list, dict]:
        """Process GitLab GraphQL response data for app-interface open MRs into PullRequestInfo objects.

        Returns:
            tuple: (list of PullRequestInfo objects, pageInfo dict with hasNextPage and endCursor)
        """
        result = []
        page_info = {"hasNextPage": False, "endCursor": None}

        if "data" not in response_data or "project" not in response_data["data"]:
            logger.error(
                f"Unexpected app-interface open MRs GraphQL response structure: {response_data}"
            )
            return result, page_info

        project = response_data["data"]["project"]
        if not project or "mergeRequests" not in project:
            logger.debug("No mergeRequests in app-interface project response")
            return result, page_info

        merge_requests_data = project["mergeRequests"]
        merge_requests = merge_requests_data["nodes"]

        # Extract pagination info
        if "pageInfo" in merge_requests_data:
            page_info = merge_requests_data["pageInfo"]

        logger.debug(
            f"Found {len(merge_requests)} open MRs in app-interface GraphQL response (hasNextPage: {page_info.get('hasNextPage', False)})"
        )

        for i, mr in enumerate(merge_requests):
            if not mr or not isinstance(mr, dict):
                logger.debug(f"Skipping invalid app-interface open MR at index {i}")
                continue

            # Parse datetime strings
            try:
                created_at = datetime.fromisoformat(
                    mr["createdAt"].replace("Z", "+00:00")
                )
            except Exception as e:
                logger.error(
                    f"Error parsing createdAt for app-interface open MR {mr.get('iid', 'unknown')}: {e}"
                )
                continue

            # Get author username
            author_username = "unknown"
            try:
                if mr.get("author") and mr["author"].get("username"):
                    author_username = mr["author"]["username"]
            except Exception as e:
                logger.debug(
                    f"Error getting author for app-interface open MR {mr.get('iid', 'unknown')}: {e}"
                )

            # Get diff statistics
            additions = None
            deletions = None
            changed_files = None

            try:
                if mr.get("diffStatsSummary") and isinstance(
                    mr["diffStatsSummary"], dict
                ):
                    diff_stats = mr["diffStatsSummary"]
                    additions = diff_stats.get("additions")
                    deletions = diff_stats.get("deletions")
                    changed_files = diff_stats.get("fileCount")
                    logger.debug(
                        f"App-interface open MR {mr.get('iid')}: +{additions} -{deletions} ({changed_files} files)"
                    )
            except Exception as e:
                logger.debug(
                    f"Error getting diff stats for app-interface open MR {mr.get('iid', 'unknown')}: {e}"
                )

            try:
                # Calculate days the MR has been open (using current date)
                days_open = calculate_days_open(created_at, datetime.now())

                mr_info = PullRequestInfo(
                    number=mr.get("iid", 0),
                    draft=mr.get("draft", False),
                    title=mr.get("title", ""),
                    body=mr.get("description", "") or "",
                    created_at=created_at,
                    merged_at=None,  # Open MRs are not merged
                    closed_at=None,  # Open MRs are not closed
                    merge_commit_sha=None,  # No merge commit for open MRs
                    user_login=author_username,
                    html_url=mr.get("webUrl", ""),
                    branch=mr.get("targetBranch", ""),
                    additions=additions,
                    deletions=deletions,
                    changed_files=changed_files,
                    days_open=days_open,
                )

                result.append(mr_info)
                logger.debug(
                    f"Successfully processed app-interface open MR {mr.get('iid')}"
                )

            except Exception as e:
                logger.error(
                    f"Error creating PullRequestInfo for app-interface open MR {mr.get('iid', 'unknown')}: {e}"
                )
                continue

        return result, page_info

    def _process_app_interface_graphql_merged_mrs_response(
        self, response_data: dict
    ) -> tuple[list, dict]:
        """Process GitLab GraphQL response data for app-interface merged MRs into PullRequestInfo objects.

        Returns:
            tuple: (list of PullRequestInfo objects, pageInfo dict with hasNextPage and endCursor)
        """
        result = []
        page_info = {"hasNextPage": False, "endCursor": None}

        if "data" not in response_data or "project" not in response_data["data"]:
            logger.error(
                f"Unexpected app-interface merged MRs GraphQL response structure: {response_data}"
            )
            return result, page_info

        project = response_data["data"]["project"]
        if not project or "mergeRequests" not in project:
            logger.debug("No mergeRequests in app-interface project response")
            return result, page_info

        merge_requests_data = project["mergeRequests"]
        merge_requests = merge_requests_data["nodes"]

        # Extract pagination info
        if "pageInfo" in merge_requests_data:
            page_info = merge_requests_data["pageInfo"]

        logger.debug(
            f"Found {len(merge_requests)} merged MRs in app-interface GraphQL response (hasNextPage: {page_info.get('hasNextPage', False)})"
        )

        for i, mr in enumerate(merge_requests):
            if not mr or not isinstance(mr, dict):
                logger.debug(f"Skipping invalid app-interface merged MR at index {i}")
                continue

            # Parse datetime strings
            try:
                created_at = datetime.fromisoformat(
                    mr["createdAt"].replace("Z", "+00:00")
                )
                merged_at = datetime.fromisoformat(
                    mr["mergedAt"].replace("Z", "+00:00")
                )
            except Exception as e:
                logger.error(
                    f"Error parsing dates for app-interface merged MR {mr.get('iid', 'unknown')}: {e}"
                )
                continue

            # Filter out MRs merged before 2024-01-01
            cutoff_date = datetime(2024, 1, 1, tzinfo=merged_at.tzinfo)
            if merged_at < cutoff_date:
                logger.debug(
                    f"Skipping app-interface merged MR {mr.get('iid')} merged before 2024-01-01: {merged_at}"
                )
                continue

            # Get author username
            author_username = "unknown"
            try:
                if mr.get("author") and mr["author"].get("username"):
                    author_username = mr["author"]["username"]
            except Exception as e:
                logger.debug(
                    f"Error getting author for app-interface merged MR {mr.get('iid', 'unknown')}: {e}"
                )

            # Get diff statistics
            additions = None
            deletions = None
            changed_files = None

            try:
                if mr.get("diffStatsSummary") and isinstance(
                    mr["diffStatsSummary"], dict
                ):
                    diff_stats = mr["diffStatsSummary"]
                    additions = diff_stats.get("additions")
                    deletions = diff_stats.get("deletions")
                    changed_files = diff_stats.get("fileCount")
                    logger.debug(
                        f"App-interface merged MR {mr.get('iid')}: +{additions} -{deletions} ({changed_files} files)"
                    )
            except Exception as e:
                logger.debug(
                    f"Error getting diff stats for app-interface merged MR {mr.get('iid', 'unknown')}: {e}"
                )

            try:
                # Calculate days the MR was open (for merged MRs)
                days_open = calculate_days_open(created_at, merged_at)

                mr_info = PullRequestInfo(
                    number=mr.get("iid", 0),
                    draft=mr.get("draft", False),
                    title=mr.get("title", ""),
                    body=mr.get("description", "") or "",
                    created_at=created_at,
                    merged_at=merged_at,
                    closed_at=None,  # Merged MRs are not closed, they're merged
                    merge_commit_sha=None,  # Would need additional query for this
                    user_login=author_username,
                    html_url=mr.get("webUrl", ""),
                    branch=mr.get("targetBranch", ""),
                    additions=additions,
                    deletions=deletions,
                    changed_files=changed_files,
                    days_open=days_open,
                )

                result.append(mr_info)
                logger.debug(
                    f"Successfully processed app-interface merged MR {mr.get('iid')}"
                )

            except Exception as e:
                logger.error(
                    f"Error creating PullRequestInfo for app-interface merged MR {mr.get('iid', 'unknown')}: {e}"
                )
                continue

        return result, page_info

    def _process_app_interface_graphql_closed_mrs_response(
        self, response_data: dict
    ) -> tuple[list, dict]:
        """Process GitLab GraphQL response data for app-interface closed MRs into PullRequestInfo objects.

        Returns:
            tuple: (list of PullRequestInfo objects, pageInfo dict with hasNextPage and endCursor)
        """
        result = []
        page_info = {"hasNextPage": False, "endCursor": None}

        if "data" not in response_data or "project" not in response_data["data"]:
            logger.error(
                f"Unexpected app-interface closed MRs GraphQL response structure: {response_data}"
            )
            return result, page_info

        project = response_data["data"]["project"]
        if not project or "mergeRequests" not in project:
            logger.debug("No mergeRequests in app-interface project response")
            return result, page_info

        merge_requests_data = project["mergeRequests"]
        merge_requests = merge_requests_data["nodes"]

        # Extract pagination info
        if "pageInfo" in merge_requests_data:
            page_info = merge_requests_data["pageInfo"]

        logger.debug(
            f"Found {len(merge_requests)} closed MRs in app-interface GraphQL response (hasNextPage: {page_info.get('hasNextPage', False)})"
        )

        for i, mr in enumerate(merge_requests):
            if not mr or not isinstance(mr, dict):
                logger.debug(f"Skipping invalid app-interface closed MR at index {i}")
                continue

            # Skip merged MRs - we only want closed but not merged
            if mr.get("mergedAt"):
                logger.debug(
                    f"Skipping merged MR {mr.get('iid')} in app-interface closed query"
                )
                continue

            # Parse datetime strings
            try:
                created_at = datetime.fromisoformat(
                    mr["createdAt"].replace("Z", "+00:00")
                )
                closed_at = None
                if mr.get("closedAt"):
                    closed_at = datetime.fromisoformat(
                        mr["closedAt"].replace("Z", "+00:00")
                    )
            except Exception as e:
                logger.error(
                    f"Error parsing dates for app-interface closed MR {mr.get('iid', 'unknown')}: {e}"
                )
                continue

            # Filter out MRs closed before 2024-01-01 (if they have a closed date)
            if closed_at:
                cutoff_date = datetime(2024, 1, 1, tzinfo=closed_at.tzinfo)
                if closed_at < cutoff_date:
                    logger.debug(
                        f"Skipping app-interface closed MR {mr.get('iid')} closed before 2024-01-01: {closed_at}"
                    )
                    continue

            # Get author username
            author_username = "unknown"
            try:
                if mr.get("author") and mr["author"].get("username"):
                    author_username = mr["author"]["username"]
            except Exception as e:
                logger.debug(
                    f"Error getting author for app-interface closed MR {mr.get('iid', 'unknown')}: {e}"
                )

            # Get diff statistics
            additions = None
            deletions = None
            changed_files = None

            try:
                if mr.get("diffStatsSummary") and isinstance(
                    mr["diffStatsSummary"], dict
                ):
                    diff_stats = mr["diffStatsSummary"]
                    additions = diff_stats.get("additions")
                    deletions = diff_stats.get("deletions")
                    changed_files = diff_stats.get("fileCount")
                    logger.debug(
                        f"App-interface closed MR {mr.get('iid')}: +{additions} -{deletions} ({changed_files} files)"
                    )
            except Exception as e:
                logger.debug(
                    f"Error getting diff stats for app-interface closed MR {mr.get('iid', 'unknown')}: {e}"
                )

            try:
                # Calculate days the MR was open (for closed MRs)
                days_open = calculate_days_open(created_at, closed_at)

                mr_info = PullRequestInfo(
                    number=mr.get("iid", 0),
                    draft=mr.get("draft", False),
                    title=mr.get("title", ""),
                    body=mr.get("description", "") or "",
                    created_at=created_at,
                    merged_at=None,  # Closed MRs are not merged
                    closed_at=closed_at,
                    merge_commit_sha=None,  # No merge commit for closed MRs
                    user_login=author_username,
                    html_url=mr.get("webUrl", ""),
                    branch=mr.get("targetBranch", ""),
                    additions=additions,
                    deletions=deletions,
                    changed_files=changed_files,
                    days_open=days_open,
                )

                result.append(mr_info)
                logger.debug(
                    f"Successfully processed app-interface closed MR {mr.get('iid')}"
                )

            except Exception as e:
                logger.error(
                    f"Error creating PullRequestInfo for app-interface closed MR {mr.get('iid', 'unknown')}: {e}"
                )
                continue

        return result, page_info
