"""
BackOffice Proxy Plugin Service

Handles data fetching and processing for the BackOffice Proxy plugin.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests
import yaml

import config

logger = logging.getLogger(__name__)


class BackOfficeProxyService:
    """Service for BackOffice Proxy plugin functionality."""

    def __init__(self):
        """Initialize the service."""
        self.repo_url = config.BACKOFFICE_PROXY_REPO
        self.gitlab_api_base = "https://gitlab.cee.redhat.com/api/v4"
        self.project_path = "insights-platform/backoffice-proxy"

        # OpenShift configuration
        self.openshift_prod_api = (
            "https://api.mpp-w2-prod.0jgd.p1.openshiftapps.com:6443"
        )
        self.openshift_stage_api = (
            "https://api.mpp-w2-preprod.cfln.p1.openshiftapps.com:6443"
        )
        self.openshift_namespace = "insights-services--runtime-ext"
        self.deployment_name = "backoffice-proxy"

        # Cache file path
        self.cache_file = config.DATA_PATH_FOLDER / "backoffice_proxy_data.json"

    def get_service_links(self) -> List[Dict[str, str]]:
        """
        Parse services_links.yml and extract links for backoffice-proxy.

        Returns:
            List of link dictionaries with 'name' and 'url' keys
        """
        try:
            with open(config.SERVICES_LINKS_PATH, "r") as f:
                services_data = yaml.safe_load(f)

            # Find the backoffice-proxy entry by searching through categories
            if not services_data or "categories" not in services_data:
                logger.warning("No categories found in services_links.yml")
                return []

            backoffice_links = []
            categories = services_data.get("categories", [])

            # Iterate through all categories
            for category in categories:
                if not isinstance(category, dict):
                    continue

                category_repos = category.get("category_repos", [])
                for repo in category_repos:
                    if not isinstance(repo, dict):
                        continue

                    # Match by ID
                    if repo.get("id") == "backoffice-proxy":
                        # Found the backoffice-proxy service, get all its links
                        links = repo.get("links", [])
                        for link in links:
                            if not isinstance(link, dict):
                                continue

                            link_name = link.get("link_name", "")
                            link_value = link.get("link_value", "")
                            if link_name and link_value:
                                # Capitalize first letter of link name for display
                                display_name = link_name.title()
                                backoffice_links.append(
                                    {"name": display_name, "url": link_value}
                                )
                        logger.info(
                            f"Found {len(backoffice_links)} links for backoffice-proxy"
                        )
                        return backoffice_links

            logger.warning("backoffice-proxy not found in services_links.yml")
            return []

        except Exception as e:
            logger.error(f"Error parsing services_links.yml: {e}", exc_info=True)
            return []

    def get_default_branch_commit(self) -> Optional[str]:
        """
        Get the latest commit SHA from the default branch via GitLab API.

        Returns:
            Commit SHA or None if failed
        """
        try:
            # Get project info to find default branch
            project_url = f"{self.gitlab_api_base}/projects/{self.project_path.replace('/', '%2F')}"

            headers = {}
            if config.GITLAB_TOKEN:
                headers["PRIVATE-TOKEN"] = config.GITLAB_TOKEN

            response = requests.get(
                project_url, headers=headers, timeout=10, verify=False
            )

            if response.status_code == 200:
                project_data = response.json()
                default_branch = project_data.get("default_branch", "master")

                # Get the latest commit from default branch
                commits_url = f"{self.gitlab_api_base}/projects/{self.project_path.replace('/', '%2F')}/repository/commits/{default_branch}"
                commit_response = requests.get(
                    commits_url, headers=headers, timeout=10, verify=False
                )

                if commit_response.status_code == 200:
                    commit_data = commit_response.json()
                    return commit_data.get("id")

            logger.warning(
                f"Failed to get default branch commit: {response.status_code}"
            )
            return None

        except requests.exceptions.ConnectionError:
            logger.error("VPN connection required for GitLab API access")
            return None
        except Exception as e:
            logger.error(f"Error getting default branch commit: {e}")
            return None

    def get_openshift_deployment_image(
        self, api_url: str, namespace: str, deployment_name: str, token: str
    ) -> Optional[str]:
        """
        Get the image tag from an OpenShift deployment.

        Args:
            api_url: OpenShift API URL
            namespace: OpenShift namespace/project
            deployment_name: Name of the deployment
            token: OpenShift API token

        Returns:
            Image tag or None if failed
        """
        if not token:
            logger.warning("OpenShift token not configured")
            return None

        try:
            deployment_url = f"{api_url}/apis/apps/v1/namespaces/{namespace}/deployments/{deployment_name}"

            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(
                deployment_url, headers=headers, timeout=10, verify=False
            )

            if response.status_code == 200:
                deployment_data = response.json()

                # Extract image from first container
                containers = (
                    deployment_data.get("spec", {})
                    .get("template", {})
                    .get("spec", {})
                    .get("containers", [])
                )

                if containers:
                    image = containers[0].get("image", "")
                    return image

            logger.warning(
                f"Failed to get deployment image: {response.status_code} - {response.text}"
            )
            return None

        except requests.exceptions.ConnectionError:
            logger.error("VPN connection required for OpenShift API access")
            return None
        except Exception as e:
            logger.error(f"Error getting deployment image: {e}")
            return None

    def extract_commit_from_image(self, image: str) -> Optional[str]:
        """
        Extract commit SHA from image tag.

        Args:
            image: Full image path (e.g., images.paas.redhat.com/insights-services/backoffice-proxy:062df42-oeuuqa)

        Returns:
            Commit SHA (first 7 chars) or None
        """
        if not image:
            return None

        try:
            # Extract tag from image
            if ":" in image:
                tag = image.split(":")[-1]

                # Tag format: 062df42-oeuuqa (commit-hash)
                if "-" in tag:
                    commit_short = tag.split("-")[0]
                    return commit_short
                else:
                    # If no dash, assume entire tag is commit
                    return tag[:7]

            return None

        except Exception as e:
            logger.error(f"Error extracting commit from image {image}: {e}")
            return None

    def get_commits_between_refs(
        self, from_commit: str, to_commit: str
    ) -> Optional[List[Dict]]:
        """
        Get all commits between two refs.

        Args:
            from_commit: Starting commit SHA
            to_commit: Ending commit SHA

        Returns:
            List of commit dictionaries or None if failed
        """
        if not config.GITLAB_TOKEN:
            logger.warning("GITLAB_TOKEN not configured")
            return None

        try:
            # Use compare API to get commits between two refs
            compare_url = f"{self.gitlab_api_base}/projects/{self.project_path.replace('/', '%2F')}/repository/compare"
            params = {"from": from_commit, "to": to_commit}

            headers = {"PRIVATE-TOKEN": config.GITLAB_TOKEN}

            response = requests.get(
                compare_url, headers=headers, params=params, timeout=10, verify=False
            )

            if response.status_code == 200:
                compare_data = response.json()
                commits = compare_data.get("commits", [])
                logger.info(
                    f"Found {len(commits)} commits between {from_commit[:7]} and {to_commit[:7]}"
                )
                return commits

            logger.warning(
                f"Failed to get commits between refs: {response.status_code}"
            )
            return None

        except requests.exceptions.ConnectionError:
            logger.error("VPN connection required for GitLab API access")
            return None
        except Exception as e:
            logger.error(f"Error getting commits between refs: {e}")
            return None

    def get_merge_request_details(self, mr_iid: int) -> Optional[Dict]:
        """
        Get details for a specific merge request.

        Args:
            mr_iid: Merge request internal ID

        Returns:
            MR details dictionary or None if failed
        """
        if not config.GITLAB_TOKEN:
            logger.warning("GITLAB_TOKEN not configured")
            return None

        try:
            mr_url = f"{self.gitlab_api_base}/projects/{self.project_path.replace('/', '%2F')}/merge_requests/{mr_iid}"
            headers = {"PRIVATE-TOKEN": config.GITLAB_TOKEN}

            response = requests.get(mr_url, headers=headers, timeout=10, verify=False)

            if response.status_code == 200:
                return response.json()

            logger.warning(f"Failed to get MR details: {response.status_code}")
            return None

        except requests.exceptions.ConnectionError:
            logger.error("VPN connection required for GitLab API access")
            return None
        except Exception as e:
            logger.error(f"Error getting MR details: {e}")
            return None

    def extract_mr_from_commit(self, commit_message: str) -> Optional[int]:
        """
        Extract MR number from commit message.

        GitLab merge commits typically have format:
        "Merge branch 'feature' into 'master'" or
        "See merge request !123" or
        "See merge request project/repo!123"

        Args:
            commit_message: Commit message

        Returns:
            MR number (iid) or None
        """
        import re

        # Pattern 1: "See merge request project/repo!123" or "See merge request !123"
        mr_pattern1 = r"See merge request [^\s]*!(\d+)"
        match = re.search(mr_pattern1, commit_message, re.IGNORECASE)
        if match:
            return int(match.group(1))

        # Pattern 2: "Merge branch 'xyz' into 'master' (!123)" pattern
        mr_pattern2 = r"\(!(\d+)\)"
        match = re.search(mr_pattern2, commit_message)
        if match:
            return int(match.group(1))

        # Pattern 3: Just "!123" anywhere in the message
        mr_pattern3 = r"!(\d+)"
        match = re.search(mr_pattern3, commit_message)
        if match:
            return int(match.group(1))

        return None

    def get_release_scope(self, from_commit: str, to_commit: str) -> Dict:
        """
        Get release scope (commits and MRs) between two commits.

        Args:
            from_commit: Starting commit SHA
            to_commit: Ending commit SHA

        Returns:
            Dict with commits and MR details
        """
        result = {
            "from_commit": from_commit,
            "to_commit": to_commit,
            "from_commit_short": from_commit[:7] if from_commit else "",
            "to_commit_short": to_commit[:7] if to_commit else "",
            "commits": [],
            "merge_requests": [],
            "total_commits": 0,
            "total_mrs": 0,
            "error": None,
        }

        # Get commits
        commits = self.get_commits_between_refs(from_commit, to_commit)
        if commits is None:
            result["error"] = "Failed to fetch commits (VPN/Token required)"
            return result

        result["commits"] = commits
        result["total_commits"] = len(commits)

        # Extract and fetch MR details
        mr_ids = set()
        for commit in commits:
            commit_message = commit.get("message", "")
            commit_title = commit.get("title", "")
            commit_sha = commit.get("short_id", commit.get("id", "")[:7])

            logger.info(f"Commit {commit_sha}: {commit_title}")
            logger.info(f"  Full message: {commit_message[:300]}")

            mr_id = self.extract_mr_from_commit(commit_message)
            if mr_id:
                logger.info(f"  ✓ Found MR !{mr_id}")
                mr_ids.add(mr_id)
            else:
                logger.info("  ✗ No MR found in commit message")

        # Fetch details for each MR
        merge_requests = []
        for mr_id in sorted(mr_ids, reverse=True):
            mr_details = self.get_merge_request_details(mr_id)
            if mr_details:
                merge_requests.append(mr_details)

        result["merge_requests"] = merge_requests
        result["total_mrs"] = len(merge_requests)

        logger.info(
            f"Release scope: {result['total_commits']} commits, {result['total_mrs']} MRs"
        )

        return result

    def load_cached_data(self) -> Optional[Dict]:
        """
        Load cached deployment data from file.

        Returns:
            Cached data dict or None if not available
        """
        try:
            if self.cache_file.exists():
                with open(self.cache_file, "r") as f:
                    data = json.load(f)
                    logger.info(
                        f"Loaded cached data from {self.cache_file} (last updated: {data.get('last_updated', 'unknown')})"
                    )
                    return data
            else:
                logger.info("No cached data found")
                return None
        except Exception as e:
            logger.error(f"Error loading cached data: {e}")
            return None

    def save_cached_data(self, data: Dict) -> bool:
        """
        Save deployment data to cache file.

        Args:
            data: Deployment data to cache

        Returns:
            True if successful, False otherwise
        """
        try:
            # Add timestamp
            data["last_updated"] = datetime.now().isoformat()

            with open(self.cache_file, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved deployment data to cache: {self.cache_file}")
            return True
        except Exception as e:
            logger.error(f"Error saving cached data: {e}")
            return False

    def get_deployment_info(self, fetch_mr_scopes: bool = True) -> Dict:
        """
        Get all deployment information for BackOffice Proxy.

        Args:
            fetch_mr_scopes: Whether to fetch MR scope for prod (stage is automatic, no scope needed)

        Returns:
            Dict with deployment info
        """
        info = {
            "name": "BackOffice Proxy",
            "repo": self.repo_url,
            "repo_name": "insights-platform/backoffice-proxy",
            "links": self.get_service_links(),
            "default_branch_commit": None,
            "stage": {
                "deployment_type": "automatic",
                "commit": None,
                "image": None,
                "console_url": f"https://console-openshift-console.apps.mpp-w2-preprod.cfln.p1.openshiftapps.com/k8s/ns/{self.openshift_namespace}/deployments/{self.deployment_name}",
            },
            "prod": {
                "deployment_type": "manual",
                "commit": None,
                "image": None,
                "console_url": f"https://console-openshift-console.apps.mpp-w2-prod.0jgd.p1.openshiftapps.com/k8s/ns/{self.openshift_namespace}/deployments/{self.deployment_name}",
            },
            "prod_scope": None,
        }

        # Get default branch commit
        info["default_branch_commit"] = self.get_default_branch_commit()

        # Get stage image and commit
        stage_image = self.get_openshift_deployment_image(
            self.openshift_stage_api,
            self.openshift_namespace,
            self.deployment_name,
            config.OPENSHIFT_TOKEN_STAGE,
        )
        if stage_image:
            info["stage"]["image"] = stage_image
            info["stage"]["commit"] = self.extract_commit_from_image(stage_image)

        # Get prod image and commit
        prod_image = self.get_openshift_deployment_image(
            self.openshift_prod_api,
            self.openshift_namespace,
            self.deployment_name,
            config.OPENSHIFT_TOKEN_PROD,
        )
        if prod_image:
            info["prod"]["image"] = prod_image
            info["prod"]["commit"] = self.extract_commit_from_image(prod_image)

        # Fetch MR scope for prod if requested and we have the necessary commits
        if fetch_mr_scopes and info["default_branch_commit"] and info["prod"]["commit"]:
            logger.info(
                f"Fetching prod→default release scope ({info['prod']['commit'][:7]}→{info['default_branch_commit'][:7]})"
            )
            info["prod_scope"] = self.get_release_scope(
                info["prod"]["commit"], info["default_branch_commit"]
            )

        return info


# Singleton instance
backoffice_proxy_service = BackOfficeProxyService()
