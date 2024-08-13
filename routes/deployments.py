import json

import requests
from flask import flash

import config
import routes
from github_api import get_default_branch, get_last_commit_sha
from gitlab_api import (
    get_app_interface_deploy_config_files,
    get_app_interface_file_content,
)
from utils import get_app_interface_folders, save_json_data_and_return

IGNORE_LIST = (
    "floorist",
    "-ui",
    "access-permissions",
    "frontend",
    "routes",
    "-dev",
    "ephemeral",
)


def get_deployments(reload_data=None):
    """
    Get deployments data from the file or download them.
    """
    if config.GITLAB_TOKEN and config.GITHUB_TOKEN:
        if not config.DEPLOYMENTS_LIST.is_file() or reload_data:
            get_app_interface_deployments()
    else:
        if not config.DEPLOYMENTS_LIST.is_file():
            return {}

    with open(config.DEPLOYMENTS_LIST, mode="r", encoding="utf-8") as file:
        return json.load(file)


def get_app_interface_deployments():
    """
    Download deployments data from app-interface repository
    (https://gitlab.cee.redhat.com/service/app-interface)
    based on links from the Overview page.
    """
    services_links = routes.overview_page.get_services_links()
    app_interface_folders = get_app_interface_folders(
        services_links, config.APP_INTERFACE_PATTERN
    )
    deployments = {}

    for folder, app_interface_link in app_interface_folders:
        try:
            for file in get_app_interface_deploy_config_files(folder):
                print(f"Processing {file.name} from {folder}")

                file_content = get_app_interface_file_content(id=file.id)

                for template in file_content["resourceTemplates"]:
                    if any(item in template["name"] for item in IGNORE_LIST):
                        continue

                    deployment_name = customize_deployment_name(template["name"])
                    deployment_data = deployments.get(deployment_name, {})

                    save_deployment_commit_refs(template, deployment_data)

                    deployment_data["app_interface_link"] = app_interface_link

                    deployment_data["repo_link"] = template["url"]

                    save_quay_image_link(deployment_name, deployment_data)

                    deployment_data["default_branch"] = get_default_branch(
                        deployment_data["repo_link"]
                    )

                    get_last_commit_sha(deployment_data)

                    deployments[deployment_name] = deployment_data

        except requests.exceptions.ConnectionError:
            flash(
                "Connection Error when downloading the GitLab data: Check your connection to the Red Hat VPN",
                category="danger",
            )
            break

        except requests.exceptions.HTTPError as err:
            if "401" in err.args[0]:
                flash("401 Unauthorized: GitLab data not updated.", category="danger")
                break
            raise Exception()

        except Exception as err:
            flash(f"Unexpected error occured: {err}", category="danger")
            break

    return save_json_data_and_return(deployments, config.DEPLOYMENTS_LIST)


def customize_deployment_name(name):
    """
    Rename deployments by specific
    """
    if "entitlements-api-go" in name:
        return "entitlements-api-go"
    elif "entitlements-bundle-config" in name:
        return "entitlements-config"
    elif "rbac-config-yml" in name:
        return "rbac-config"
    elif name in ["web", "nginx", "nginx-prometheus"]:
        return f"turnpike-{name}"
    return name


def get_image_repo(template_name):
    services_links = routes.overview_page.get_services_links()

    for category in services_links.get("categories", ()):
        for repo in category["category_repos"]:
            if repo["id"] == template_name:
                for link in repo["links"]:
                    if "quay.io" in link["link_value"]:
                        return link["link_value"]
            if repo["id"] == "turnpike" and "turnpike" in template_name:
                for link in repo["links"]:
                    if template_name in link["link_value"]:
                        return link["link_value"]


def save_deployment_commit_refs(deployment, deployment_data):
    for target in deployment["targets"]:
        if "stage" in target["namespace"]["$ref"]:
            if target["ref"] in ("main", "master"):
                deployment_data["stage_deployment_type"] = "auto"
            else:
                deployment_data["stage_deployment_type"] = "manual"
                deployment_data["commit_stage"] = target["ref"]

        elif "prod" in target["namespace"]["$ref"]:
            if target["ref"] in ("main", "master"):
                deployment_data["prod_deployment_type"] = "auto"
            else:
                deployment_data["prod_deployment_type"] = "manual"
                deployment_data["commit_prod"] = target["ref"]


def save_quay_image_link(deployment_name, deployment_data):
    if deployment_name == "insights-gateway":
        image_repo = "insights-3scale"
    elif deployment_name == "sources-api":
        image_repo = "sources-api-go"
    else:
        image_repo = deployment_name

    if deployment_name in ["entitlements-config", "rbac-config"]:
        deployment_data["image_link"] = None
    else:
        deployment_data["image_link"] = (
            f"https://quay.io/repository/cloudservices/{image_repo}?tab=tags"
        )
