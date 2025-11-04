import base64
import json
import logging
import re
import requests
import yaml
from datetime import datetime

from flask import Blueprint, redirect, render_template, request, url_for, jsonify
from markupsafe import escape

import blueprints
import config
from services.gitlab_service import GitlabAPI
from services.google_drive_service import GoogleDriveService
from services.release_process_service import release_process_service

logger = logging.getLogger(__name__)

release_notes_bp = Blueprint("release_notes", __name__)

# Initialize Google Drive service
try:
    google_drive_service = GoogleDriveService()
    if google_drive_service.is_available():
        logger.info("Google Drive service initialized successfully")
    else:
        logger.warning("Google Drive service not available - check configuration")
        google_drive_service = None
except Exception as err:
    logger.error(f"Unable to initialize Google Drive service: {err}")
    google_drive_service = None


@release_notes_bp.route("/<depl_name>")
def index(depl_name):
    """Direct route to release notes - redirects to selection page for user choice."""
    return redirect(url_for("release_notes.select_scope", depl_name=depl_name))


@release_notes_bp.route("/<depl_name>/select")
def select_scope(depl_name):
    """Show PR selection page to choose release scope."""
    deployment_data = get_deployment_data(escape(depl_name))
    if not deployment_data:
        return render_template("errors/404.html")

    # Sort PRs by merged_at to ensure chronological order
    prod_stage_pulls = deployment_data.get("prod_stage_pulls", [])
    prod_stage_pulls.sort(key=lambda pr: pr.get("merged_at", ""))

    return render_template(
        "release_notes_select.html",
        deployment_name=depl_name,
        deployment=deployment_data,
        prod_stage_pulls=prod_stage_pulls,
    )


@release_notes_bp.route("/<depl_name>/generate")
def generate(depl_name):
    """Generate release notes with selected scope."""
    up_to_pr = request.args.get("up_to_pr", type=int)

    release_notes = get_release_notes_from_deployment(escape(depl_name), up_to_pr)
    if not release_notes:
        return render_template("errors/404.html")

    today = datetime.now().strftime("%B %d, %Y")
    return render_template("release_notes.html", notes=release_notes, today=today)


@release_notes_bp.route("/<depl_name>/preview_mr")
def preview_deployment_mr(depl_name):
    """Preview deployment MR details before creation."""
    current_commit = request.args.get("current_commit")
    new_commit = request.args.get("new_commit")
    process_id = request.args.get("process_id")  # Optional process_id for JIRA ticket

    if not current_commit or not new_commit:
        return jsonify({"success": False, "error": "Missing commit parameters"}), 400

    # Check GitLab connectivity first (VPN check)
    connectivity_result = check_gitlab_connectivity()
    if not connectivity_result["gitlab_connected"]:
        return jsonify(
            {
                "success": False,
                "error": f"VPN Connection Required: Please connect to company VPN and try again. ({connectivity_result['gitlab_error']})",
                "error_type": "vpn_required",
            }
        )

    deployment_data = get_deployment_data(escape(depl_name))
    if not deployment_data:
        return jsonify({"success": False, "error": "Deployment not found"}), 404

    try:
        # Get JIRA ticket URL if process_id is provided
        jira_ticket_url = None
        if process_id:
            try:
                process = release_process_service.get_process(process_id)
                if process:
                    jira_data = (
                        process.get("steps", {}).get("jira_ticket", {}).get("data", {})
                    )
                    jira_ticket_url = jira_data.get("ticket_url")
            except Exception as e:
                logger.warning(f"Could not fetch JIRA ticket for preview: {e}")

        # Extract deployment information
        mr_preview = extract_deployment_mr_info(
            depl_name, deployment_data, current_commit, new_commit, jira_ticket_url
        )

        # Add GitLab connectivity check
        gitlab_status = check_gitlab_connectivity()
        mr_preview.update(gitlab_status)

        return jsonify({"success": True, "data": mr_preview})

    except Exception:
        logger.exception("Error while previewing deployment MR")
        return jsonify(
            {"success": False, "error": "An internal error has occurred."}
        ), 500


@release_notes_bp.route("/<depl_name>/create_mr", methods=["POST"])
def create_deployment_mr(depl_name):
    """Create the actual deployment MR in GitLab."""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    current_commit = data.get("current_commit")
    new_commit = data.get("new_commit")
    process_id = data.get("process_id")  # Get process_id from request

    if not current_commit or not new_commit:
        return jsonify({"success": False, "error": "Missing commit parameters"}), 400

    deployment_data = get_deployment_data(escape(depl_name))
    if not deployment_data:
        return jsonify({"success": False, "error": "Deployment not found"}), 404

    try:
        # Get additional links from process if available
        jira_ticket_url = None
        google_doc_url = None

        if process_id:
            try:
                process = release_process_service.get_process(process_id)
                if process:
                    # Get JIRA ticket URL
                    jira_data = (
                        process.get("steps", {}).get("jira_ticket", {}).get("data", {})
                    )
                    jira_ticket_url = jira_data.get("ticket_url")

                    # Get Google Doc URL
                    google_doc_data = (
                        process.get("steps", {}).get("google_doc", {}).get("data", {})
                    )
                    google_doc_url = google_doc_data.get("doc_url")
            except Exception as e:
                logger.warning(f"Could not fetch process data for links: {e}")

        # Create the MR (returns dict with mr_creation_url, branch_name, branch_url)
        mr_result = create_gitlab_deployment_mr(
            depl_name,
            deployment_data,
            current_commit,
            new_commit,
            jira_ticket_url=jira_ticket_url,
            google_doc_url=google_doc_url,
        )

        mr_url = mr_result.get("mr_creation_url")
        branch_name = mr_result.get("branch_name")
        branch_url = mr_result.get("branch_url")

        # Update release process if process_id is provided
        if process_id:
            try:
                release_process_service.update_step(
                    process_id=process_id,
                    step_name="app_interface_mr",
                    status="in_progress",  # Branch created, MR not yet submitted
                    data={
                        "mr_creation_url": mr_url,
                        "branch_name": branch_name,
                        "branch_url": branch_url,
                        "current_commit": current_commit,
                        "new_commit": new_commit,
                        "status_details": {
                            "branch_created": True,
                            "mr_created": False,
                            "mr_merged": False,
                        },
                    },
                )
                logger.info(
                    f"Updated process {process_id} - app_interface_mr branch created"
                )
            except Exception as e:
                logger.warning(f"Failed to update process {process_id}: {e}")

        return jsonify(
            {
                "success": True,
                "data": {
                    "mr_url": mr_url,
                    "branch_name": branch_name,
                    "branch_url": branch_url,
                    "message": "Deployment branch created successfully! Please create the MR from the link.",
                },
            }
        )

    except Exception:
        logger.exception("Failed to create deployment MR")
        return jsonify(
            {
                "success": False,
                "error": "An internal error occurred creating the deployment merge request.",
            }
        ), 500


@release_notes_bp.route("/<depl_name>/check_mr_status", methods=["POST"])
def check_mr_status(depl_name):
    """Check the status of an app-interface MR."""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    branch_name = data.get("branch_name")

    if not branch_name:
        return jsonify(
            {"success": False, "error": "Missing branch_name parameter"}
        ), 400

    try:
        from services.gitlab_service import GitlabAPI

        gitlab_api = GitlabAPI()
        current_user = gitlab_api.gitlab_api.user
        user_fork_path = f"{current_user.username}/app-interface"
        main_repo_path = "service/app-interface"

        status_details = {
            "branch_created": False,
            "mr_created": False,
            "mr_merged": False,
            "mr_url": None,
            "mr_number": None,
            "mr_state": None,
        }

        # Check if branch exists in user's fork
        try:
            fork_project = gitlab_api.gitlab_api.projects.get(user_fork_path)
            try:
                fork_project.branches.get(branch_name)
                status_details["branch_created"] = True
                logger.info(f"Branch {branch_name} exists in fork")
            except Exception:
                logger.info(f"Branch {branch_name} not found in fork")
                return jsonify({"success": True, "status_details": status_details})
        except Exception as e:
            logger.error(f"Could not access user fork: {e}")
            return jsonify(
                {"success": False, "error": "Could not access your fork"}
            ), 500

        # Check if MR exists for this branch in the main repository
        try:
            main_project = gitlab_api.gitlab_api.projects.get(main_repo_path)

            # Search for MRs with this source branch
            mrs = main_project.mergerequests.list(
                source_branch=branch_name,
                source_project_id=fork_project.id,
                get_all=True,
            )

            if mrs:
                # Take the first (should be only one)
                mr = mrs[0]
                status_details["mr_created"] = True
                status_details["mr_url"] = mr.web_url
                status_details["mr_number"] = mr.iid
                status_details["mr_state"] = mr.state

                # Check if merged
                if mr.state == "merged":
                    status_details["mr_merged"] = True

                logger.info(f"MR !{mr.iid} found with state: {mr.state}")
            else:
                logger.info(f"No MR found for branch {branch_name}")
        except Exception as e:
            logger.error(f"Error checking MR status: {e}")
            # Branch exists but couldn't check MR - still return success with partial data
            return jsonify({"success": True, "status_details": status_details})

        return jsonify({"success": True, "status_details": status_details})

    except Exception:
        logger.exception("Failed to check MR status")
        return jsonify(
            {
                "success": False,
                "error": "An error occurred while checking MR status.",
            }
        ), 500


@release_notes_bp.route("/<depl_name>/create_google_doc", methods=["POST"])
def create_google_doc(depl_name):
    """Create a Google Doc with release notes in the configured folder."""
    data = request.get_json()

    if not data:
        return jsonify({"success": False, "error": "No data provided"}), 400

    # Check if Google Drive service is available
    if not google_drive_service or not google_drive_service.is_available():
        return jsonify(
            {
                "success": False,
                "error": "Google Drive integration is not configured. See OAUTH_SETUP.md for setup instructions.",
            }
        ), 503

    # Get up_to_pr and process_id parameters if provided
    up_to_pr = data.get("up_to_pr")
    process_id = data.get("process_id")

    # Get release notes data
    deployment_data = get_deployment_data(escape(depl_name))
    if not deployment_data:
        return jsonify({"success": False, "error": "Deployment not found"}), 404

    # Get release notes with proper scope
    release_notes = get_release_notes_from_deployment(escape(depl_name), up_to_pr)
    if not release_notes:
        return jsonify(
            {"success": False, "error": "Failed to generate release notes"}
        ), 500

    try:
        # Get folder ID from deployment-specific configuration (services_links.yml)
        # or from explicit request override (advanced use)
        folder_id = data.get("folder_id") or release_notes.get("google_drive_folder_id")

        if not folder_id:
            return jsonify(
                {
                    "success": False,
                    "error": "No Google Drive folder configured for this deployment. Please add a 'release notes' link with a Google Drive folder URL in services_links.yml",
                }
            ), 400

        logger.info(
            f"Creating Google Doc for {depl_name} in folder: {folder_id[:10]}..."
        )

        # Create the Google Doc
        result = google_drive_service.create_release_notes_doc(
            depl_name, release_notes, folder_id
        )

        # Update release process if process_id is provided
        if process_id:
            try:
                release_process_service.update_step(
                    process_id=process_id,
                    step_name="google_doc",
                    status="completed",
                    data={
                        "doc_url": result["document_url"],
                        "doc_id": result.get("document_id"),
                        "doc_title": result["document_title"],
                    },
                )
                logger.info(f"Updated process {process_id} - google_doc step completed")
            except Exception as e:
                logger.warning(f"Failed to update process {process_id}: {e}")

        return jsonify(
            {
                "success": True,
                "data": {
                    "document_url": result["document_url"],
                    "document_title": result["document_title"],
                    "message": "Release notes Google Doc created successfully!",
                    "folder_id": folder_id,
                },
            }
        )

    except Exception as e:
        logger.exception("Failed to create Google Doc")
        error_message = str(e)
        return jsonify({"success": False, "error": error_message}), 500


@release_notes_bp.route("/<depl_name>/check_google_drive")
def check_google_drive(depl_name):
    """Check if Google Drive integration is available and configured."""
    is_available = google_drive_service and google_drive_service.is_available()

    response = {
        "success": True,
        "google_drive_available": is_available,
    }

    if is_available:
        # Get release notes to check for deployment-specific folder
        release_notes = get_release_notes_from_deployment(escape(depl_name))

        # Only use deployment-specific folder from services_links.yml
        folder_id = (
            release_notes.get("google_drive_folder_id") if release_notes else None
        )

        if folder_id:
            try:
                folder_info = google_drive_service.get_folder_info(folder_id)
                response["folder_configured"] = True
                response["folder_name"] = folder_info.get("folder_name")
                response["folder_url"] = folder_info.get("folder_url")
                response["folder_id"] = folder_id
                response["folder_source"] = (
                    "deployment-specific (from services_links.yml)"
                )

                logger.info(
                    f"Found deployment-specific folder for {depl_name}: {folder_id}"
                )

            except Exception as e:
                logger.error(f"Failed to access folder for {depl_name}: {e}")
                response["folder_configured"] = False
                response["error"] = (
                    f"Folder not accessible: {str(e)}. Check service account permissions."
                )
        else:
            response["folder_configured"] = False
            response["error"] = (
                "No Google Drive folder configured for this deployment. Add a 'release notes' link with a Google Drive folder URL in services_links.yml"
            )
            logger.info(
                f"No Google Drive folder found for {depl_name} in services_links.yml"
            )
    else:
        response["error"] = (
            "Google Drive integration not configured. See OAUTH_SETUP.md for setup instructions."
        )

    return jsonify(response)


def get_deployment_data(depl_name):
    """Get raw deployment data from JSON file."""
    with open(config.DEPLOYMENTS_FILE, mode="r", encoding="utf-8") as file:
        return json.load(file).get(depl_name)


def get_release_notes_from_deployment(depl_name, up_to_pr=None):
    """Get release notes data, optionally filtered to a specific PR cutoff point."""
    notes = get_deployment_data(depl_name)
    if not notes:
        return None

    # If up_to_pr is specified, filter the prod_stage_pulls to only include PRs up to that point
    if up_to_pr is not None:
        prod_stage_pulls = notes.get("prod_stage_pulls", [])
        prod_stage_pulls.sort(key=lambda pr: pr.get("merged_at", ""))

        # Find the cutoff point and slice the array
        cutoff_index = None
        for i, pr in enumerate(prod_stage_pulls):
            if pr.get("number") == up_to_pr:
                cutoff_index = i
                break

        if cutoff_index is not None:
            notes["prod_stage_pulls"] = prod_stage_pulls[: cutoff_index + 1]
            # Update the target commit to the last selected PR's merge commit
            if notes["prod_stage_pulls"]:
                last_pr = notes["prod_stage_pulls"][-1]
                notes["target_prod_commit"] = last_pr.get(
                    "merge_commit_sha", notes.get("commit_stage")
                )
            else:
                notes["target_prod_commit"] = notes.get("commit_prod")  # No change
        else:
            # PR not found, use current stage as fallback
            notes["target_prod_commit"] = notes.get("commit_stage")
    else:
        # No filtering, use current stage commit
        notes["target_prod_commit"] = notes.get("commit_stage")

    add_release_notes_google_link(notes)
    return notes


def add_release_notes_google_link(notes):
    """
    Add release notes link and extract Google Drive folder ID if present.

    This function looks for a link named "release notes" in the services_links.yml
    for the repository. If found and it's a Google Drive folder URL, it extracts
    the folder ID and adds it to the notes.
    """
    links = blueprints.get_services_links()
    repo_link = notes.get("repo_link").lower()

    for category in links.get("categories", ()):
        for repo in category["category_repos"]:
            for link in repo["links"]:
                if link.get("link_value").lower() == repo_link:
                    for link in repo["links"]:
                        if link.get("link_name") == "release notes":
                            release_notes_url = link.get("link_value")
                            notes["release_notes_link"] = release_notes_url

                            # Extract Google Drive folder ID if it's a Drive URL
                            folder_id = extract_google_drive_folder_id(
                                release_notes_url
                            )
                            if folder_id:
                                notes["google_drive_folder_id"] = folder_id
                                logger.info(
                                    f"Found Google Drive folder ID for {repo_link}: {folder_id}"
                                )

                            return notes


def extract_google_drive_folder_id(url):
    """
    Extract folder ID from a Google Drive folder URL.

    Supports formats:
    - https://drive.google.com/drive/folders/FOLDER_ID
    - https://drive.google.com/drive/folders/FOLDER_ID?usp=sharing

    Args:
        url: Google Drive folder URL

    Returns:
        Folder ID if found, None otherwise
    """
    if not url:
        return None

    # Pattern to match Google Drive folder URLs
    pattern = r"drive\.google\.com/drive/folders/([a-zA-Z0-9_-]+)"
    match = re.search(pattern, url)

    if match:
        return match.group(1)

    return None


def extract_deployment_mr_info(
    depl_name, deployment_data, current_commit, new_commit, jira_ticket_url=None
):
    """Extract and validate deployment MR information."""

    # Step 1: Handle deployment renaming
    original_depl_name = depl_name
    for key, value in config.DEPLOYMENT_RENAME_LIST.items():
        if value == depl_name:
            original_depl_name = key
            break

    # Step 2: Generate branch name and MR info
    import time
    import re

    timestamp = int(time.time())
    branch_name = f"{depl_name}-prod-{new_commit[:7]}-{timestamp}"

    # Extract JIRA ticket ID from URL if available
    jira_ticket_id = None
    if jira_ticket_url:
        # Extract ticket ID from URL like https://issues.redhat.com/browse/RHCLOUD-43067
        match = re.search(r"/([A-Z]+-\d+)", jira_ticket_url)
        if match:
            jira_ticket_id = match.group(1)

    # Build MR title with optional JIRA ticket ID
    if jira_ticket_id:
        mr_title = f"[{jira_ticket_id}] Deploy {depl_name.upper()} to production - {new_commit[:7]}"
    else:
        mr_title = f"Deploy {depl_name.upper()} to production - {new_commit[:7]}"

    # Step 3: Get deployment file paths
    app_interface_link = deployment_data.get("app_interface_link", "")
    deploy_file = deployment_data.get("app_interface_deploy_file", "deploy.yml")
    prod_target_name = deployment_data.get("prod_target_name", "")

    # Step 4: Access deploy.yml via GitLab API
    try:
        gitlab_api = GitlabAPI()
        project = gitlab_api.gitlab_api.projects.get("service/app-interface")

        # Extract the file path from the app_interface_link URL
        # Example URL: "https://gitlab.cee.redhat.com/service/app-interface/-/tree/master/data/services/insights/rbac/"
        # We need to get the path after "/data/" in the URL
        url_parts = app_interface_link.rstrip("/").split("/")
        logger.info(f"Processing deployment {depl_name}: URL parts = {url_parts}")

        # Find the index of 'data' in the URL parts
        try:
            data_index = url_parts.index("data")
            # Get everything after 'data/' to build the path
            service_path_parts = url_parts[data_index + 1 :]
            service_path = "/".join(service_path_parts)
            deploy_file_path = f"data/{service_path}/{deploy_file}"
            logger.info(f"Constructed deploy file path: {deploy_file_path}")
        except ValueError:
            # Fallback if 'data' is not found in URL
            deploy_file_path = f"data/services/{depl_name}/{deploy_file}"
            logger.warning(
                f"Could not find 'data' in URL, using fallback path: {deploy_file_path}"
            )

        # Get the deploy file content
        try:
            file_content = project.files.get(file_path=deploy_file_path, ref="master")
            deploy_yaml = yaml.safe_load(file_content.decode())
            logger.info(f"Successfully loaded deploy file: {deploy_file_path}")
        except Exception as file_error:
            logger.error(f"Failed to access file {deploy_file_path}: {file_error}")
            raise Exception(
                f"Failed to access deploy file '{deploy_file}' at path: {deploy_file_path}. Error: {file_error}"
            )

        # Step 5: Find the right template and extract current commit
        found_template = None
        current_ref_in_file = None

        logger.info(
            f"Looking for template '{original_depl_name}' (original from '{depl_name}')"
        )
        logger.info(f"Target prod ref: {prod_target_name}")

        if "resourceTemplates" in deploy_yaml:
            logger.info(
                f"Found {len(deploy_yaml['resourceTemplates'])} resourceTemplates"
            )
            for template in deploy_yaml["resourceTemplates"]:
                template_name = template.get("name", "unnamed")
                logger.info(f"Checking template: {template_name}")

                if template.get("name") == original_depl_name:
                    found_template = template
                    logger.info(f"Found matching template: {original_depl_name}")

                    # Look for the reference field - it can be in various nested structures
                    current_ref_in_file = find_ref_for_prod_target(
                        template, prod_target_name
                    )
                    if current_ref_in_file:
                        logger.info(
                            f"Found matching prod target! Current ref: {current_ref_in_file}"
                        )
                    else:
                        logger.warning(
                            f"Could not find ref field for prod target: {prod_target_name}"
                        )
                    break
        else:
            logger.warning("No resourceTemplates found in deploy YAML")

        # Step 6: Validation
        validation_success = True
        validation_message = "All checks passed!"

        if not found_template:
            validation_success = False
            validation_message = (
                f"Template '{original_depl_name}' not found in deploy.yml"
            )
        elif not current_ref_in_file:
            validation_success = False
            validation_message = (
                f"Reference field not found for prod target: {prod_target_name}"
            )
        elif current_ref_in_file != current_commit:
            validation_success = False
            validation_message = f"Commit mismatch! Expected {current_commit[:7]}, found {current_ref_in_file[:7]}"

        return {
            "branch_name": branch_name,
            "mr_title": mr_title,
            "deploy_file_path": deploy_file_path,
            "current_commit": current_commit[:7],
            "new_commit": new_commit[:7],
            "found_template": original_depl_name,
            "current_ref_in_file": current_ref_in_file[:7]
            if current_ref_in_file
            else "Not found",
            "validation_success": validation_success,
            "validation_message": validation_message,
        }

    except Exception as e:
        raise Exception(f"Failed to access deploy.yml: {str(e)}")


def find_ref_for_prod_target(obj, target_ref):
    """
    Recursively search for a ref field that corresponds to the target $ref.

    Handles structures like:
    - namespace:
        $ref: /services/insights/rbac/namespaces/rbac-prod.yml
      ref: 84a20fd2c50a884c177e3a38330a3e64acc1f26b
    """
    if isinstance(obj, dict):
        # Check if this dict has both a nested object with matching $ref and a ref field
        ref_value = obj.get("ref")

        # Look for nested objects with $ref
        for key, value in obj.items():
            if isinstance(value, dict) and value.get("$ref") == target_ref:
                # Found matching $ref, check if ref is at the same level
                if ref_value:
                    logger.info(
                        f"Found matching structure: {key} -> $ref: {target_ref}, ref: {ref_value}"
                    )
                    return ref_value

        # Recursively search nested objects and lists
        for key, value in obj.items():
            if key != "ref":  # Don't recurse into the ref field itself
                result = find_ref_for_prod_target(value, target_ref)
                if result:
                    return result

    elif isinstance(obj, list):
        # Search each item in the list
        for item in obj:
            result = find_ref_for_prod_target(item, target_ref)
            if result:
                return result

    return None


def check_gitlab_connectivity():
    """Check GitLab API connectivity and VPN status."""
    try:
        if not config.GITLAB_TOKEN:
            return {
                "gitlab_connected": False,
                "gitlab_error": "GitLab token not configured",
                "can_create_mr": False,
            }

        # Test GitLab connection and check token scopes
        gitlab_api = GitlabAPI()
        gitlab_api.gitlab_api.auth()

        # Try to get current user info to verify token scopes
        try:
            current_user = gitlab_api.gitlab_api.user
            logger.info(
                f"GitLab connectivity check: SUCCESS - User: {current_user.username}"
            )
            logger.info(
                f"GitLab token scopes: {getattr(current_user, 'token_scopes', 'Unknown')}"
            )
        except Exception as e:
            logger.warning(f"Could not verify token scopes: {e}")

        logger.info("GitLab connectivity check: SUCCESS")
        return {"gitlab_connected": True, "gitlab_error": None, "can_create_mr": True}

    except requests.exceptions.ConnectionError:
        error_msg = "GitLab connection failed - check VPN connection"
        logger.error(f"GitLab connectivity check: {error_msg}")
        return {
            "gitlab_connected": False,
            "gitlab_error": error_msg,
            "can_create_mr": False,
        }
    except Exception:
        logger.error(
            "GitLab connectivity check: Unexpected exception during connectivity check",
            exc_info=True,
        )
        # Return a generic error message to the user
        return {
            "gitlab_connected": False,
            "gitlab_error": "GitLab token invalid or unexpected error occurred.",
            "can_create_mr": False,
        }


def create_gitlab_deployment_mr(
    depl_name,
    deployment_data,
    current_commit,
    new_commit,
    jira_ticket_url=None,
    google_doc_url=None,
):
    """Create deployment MR in GitLab app-interface repository."""

    # Step 1: Handle deployment renaming
    original_depl_name = depl_name
    for key, value in config.DEPLOYMENT_RENAME_LIST.items():
        if value == depl_name:
            original_depl_name = key
            break

    # Step 2: Generate branch name and MR info (with timestamp to avoid conflicts)
    import time
    import re

    timestamp = int(time.time())
    branch_name = f"{depl_name}-prod-{new_commit[:7]}-{timestamp}"

    # Extract JIRA ticket ID from URL if available
    jira_ticket_id = None
    if jira_ticket_url:
        # Extract ticket ID from URL like https://issues.redhat.com/browse/RHCLOUD-43067
        match = re.search(r"/([A-Z]+-\d+)", jira_ticket_url)
        if match:
            jira_ticket_id = match.group(1)

    # Build MR title with optional JIRA ticket ID
    if jira_ticket_id:
        mr_title = f"[{jira_ticket_id}] Deploy {depl_name.upper()} to production - {new_commit[:7]}"
    else:
        mr_title = f"Deploy {depl_name.upper()} to production - {new_commit[:7]}"

    # Build commit message with optional links
    commit_message = mr_title  # Use the same title for commit message

    if jira_ticket_url or google_doc_url:
        commit_message += "\n\n"
        if jira_ticket_url:
            commit_message += f"JIRA Ticket: {jira_ticket_url}\n"
        if google_doc_url:
            commit_message += f"Release Notes: {google_doc_url}\n"

    # Step 3: Get deployment file paths
    app_interface_link = deployment_data.get("app_interface_link", "")
    deploy_file = deployment_data.get("app_interface_deploy_file", "deploy.yml")
    prod_target_name = deployment_data.get("prod_target_name", "")

    logger.info(f"Creating deployment MR: {mr_title}")
    logger.info(f"Branch: {branch_name}")

    try:
        gitlab_api = GitlabAPI()

        # Log current user for MR creation
        current_user = gitlab_api.gitlab_api.user
        logger.info(
            f"Creating MR as user: {current_user.username} (ID: {current_user.id})"
        )

        # Get both user's fork and main repository for fork-to-upstream MR
        user_fork_path = f"{current_user.username}/app-interface"
        main_repo_path = "service/app-interface"

        # Get user's fork (where we'll create the branch)
        try:
            logger.info(f"Attempting to access user fork: {user_fork_path}")
            fork_project = gitlab_api.gitlab_api.projects.get(user_fork_path)
            logger.info(f"Successfully accessed user fork: {fork_project.name}")
        except Exception as fork_error:
            logger.error(f"Could not access user fork: {fork_error}")
            raise Exception(
                f"Please create a fork of 'service/app-interface' repository first. User '{current_user.username}' needs a fork to create deployment MRs."
            )

        # Get main repository (where we'll target the MR)
        try:
            logger.info(f"Attempting to access main repository: {main_repo_path}")
            main_project = gitlab_api.gitlab_api.projects.get(main_repo_path)
            logger.info(f"Successfully accessed main repository: {main_project.name}")
        except Exception as main_error:
            logger.error(f"Could not access main repository: {main_error}")
            raise Exception(
                "Cannot access main 'service/app-interface' repository. Please check access permissions."
            )

        logger.info(f"Will create branch in fork: {fork_project.path_with_namespace}")
        logger.info(f"Will create MR from fork to: {main_project.path_with_namespace}")

        try:
            # Step 4: Get deploy file path
            logger.info("Step 4: Building deploy file path...")
            url_parts = app_interface_link.rstrip("/").split("/")
            logger.info(f"URL parts: {url_parts}")
            try:
                data_index = url_parts.index("data")
                service_path_parts = url_parts[data_index + 1 :]
                service_path = "/".join(service_path_parts)
                deploy_file_path = f"data/{service_path}/{deploy_file}"
            except ValueError:
                deploy_file_path = f"data/services/{depl_name}/{deploy_file}"
            logger.info(f"Deploy file path: {deploy_file_path}")

            # Step 5: Get current file content from fork
            logger.info("Step 5: Getting file content from fork...")
            file_obj = fork_project.files.get(file_path=deploy_file_path, ref="master")
            logger.info(f"File object type: {type(file_obj)}")

            logger.info("Step 5b: Decoding file content...")
            raw_content = file_obj.decode()
            logger.info(f"Raw decoded type: {type(raw_content)}")

            # Ensure we have a string, not bytes
            if isinstance(raw_content, bytes):
                current_yaml_content = raw_content.decode("utf-8")
                logger.info("Converted bytes to string")
            else:
                current_yaml_content = raw_content
                logger.info("Already a string")

            logger.info(f"Final content type: {type(current_yaml_content)}")
            logger.info(f"Content length: {len(current_yaml_content)} chars")

            # Step 6: Update the YAML with new commit reference (minimal change)
            logger.info("Step 6: Updating YAML content...")
            updated_yaml_content = update_commit_ref_in_yaml(
                current_yaml_content,
                original_depl_name,
                prod_target_name,
                current_commit,
                new_commit,
            )
            logger.info(f"Updated content type: {type(updated_yaml_content)}")
            logger.info(f"Updated content length: {len(updated_yaml_content)} chars")

            # Step 7: Create new branch in fork
            logger.info("Step 7: Creating new branch...")
            master_branch = fork_project.branches.get("master")
            logger.info(f"Master branch commit: {master_branch.commit['id'][:8]}")

            try:
                fork_project.branches.create(
                    {
                        "branch": branch_name,
                        "ref": "master",  # Use branch name instead of commit ID
                    }
                )
                logger.info(f"Created new branch in fork: {branch_name}")
            except Exception as branch_error:
                if "already exists" in str(branch_error).lower():
                    logger.warning(
                        f"Branch {branch_name} already exists, using existing branch"
                    )
                    # Check if existing branch is at the right commit
                    existing_branch = fork_project.branches.get(branch_name)
                    logger.info(
                        f"Existing branch commit: {existing_branch.commit['id'][:8]}"
                    )

                    # If branch exists, check if file already has the correct commit reference
                    try:
                        existing_file = fork_project.files.get(
                            file_path=deploy_file_path, ref=branch_name
                        )
                        existing_content = existing_file.decode()
                        if isinstance(existing_content, bytes):
                            existing_content = existing_content.decode("utf-8")

                        # Check if the file already has the target commit
                        if new_commit in existing_content:
                            logger.info(
                                f"File already contains target commit {new_commit[:7]}, skipping update"
                            )
                            # Branch and file are already ready, create MR link directly
                            fork_url = fork_project.web_url
                            from urllib.parse import quote

                            encoded_title = quote(mr_title)
                            mr_creation_url = f"{fork_url}/-/merge_requests/new?merge_request[source_branch]={branch_name}&merge_request[target_branch]=master&merge_request[title]={encoded_title}"
                            logger.info(
                                f"Using existing branch and file, MR link: {mr_creation_url}"
                            )
                            return mr_creation_url
                    except Exception as file_check_error:
                        logger.info(
                            f"Could not check existing file, proceeding with update: {file_check_error}"
                        )
                else:
                    logger.error(f"Failed to create branch: {branch_error}")
                    raise Exception(f"Branch creation failed: {branch_error}")

        except Exception as early_step_error:
            logger.error(
                f"Error in steps 4-7: {type(early_step_error).__name__}: {early_step_error}"
            )
            raise Exception(f"Early step failed: {early_step_error}")

        # Step 8: Update file in the new branch - with detailed error tracking
        try:
            logger.info("Step 8: Starting file update process...")

            # GitLab API often expects base64 encoded content
            logger.info(
                f"File content type before encoding: {type(updated_yaml_content)}"
            )
            content_bytes = updated_yaml_content.encode("utf-8")
            logger.info(f"Content bytes type: {type(content_bytes)}")
            content_b64 = base64.b64encode(content_bytes).decode("utf-8")
            logger.info(f"Content b64 type: {type(content_b64)}")

            file_data = {
                "file_path": deploy_file_path,
                "branch": branch_name,
                "content": content_b64,
                "commit_message": commit_message,
                "encoding": "base64",
            }

            logger.info(f"File data prepared with keys: {list(file_data.keys())}")
            logger.info(
                f"Data types: {[(k, type(v).__name__) for k, v in file_data.items()]}"
            )

            # For existing files in branches, we must use update, not create
            try:
                logger.info("Attempting file update (files exist in new branch)...")

                # Get the existing file in the new branch first
                existing_file = fork_project.files.get(
                    file_path=deploy_file_path, ref=branch_name
                )
                logger.info(
                    f"Found existing file in branch, SHA: {existing_file.last_commit_id[:8]}"
                )

                # Update the existing file
                existing_file.content = file_data["content"]
                existing_file.encoding = file_data["encoding"]
                existing_file.save(
                    branch=branch_name, commit_message=file_data["commit_message"]
                )

                logger.info(f"Successfully updated file in branch: {deploy_file_path}")

            except Exception as update_error:
                logger.error(
                    f"File update failed: {type(update_error).__name__}: {update_error}"
                )
                logger.error(f"Update error details: {str(update_error)}")
                raise Exception(f"Could not update file in branch: {update_error}")

            logger.info("File update completed successfully!")

        except Exception as file_step_error:
            logger.error(
                f"Step 8 (file update) failed: {type(file_step_error).__name__}: {file_step_error}"
            )
            raise Exception(f"File update step failed: {file_step_error}")

        logger.info("File update successful! Creating manual MR link...")

        # Create MR from fork - GitLab will automatically detect upstream target
        fork_url = fork_project.web_url

        # Create the GitLab MR creation URL from the fork (proper workflow)
        from urllib.parse import quote

        encoded_title = quote(mr_title)

        # Build MR description with only JIRA ticket and Release Notes links
        mr_description = ""
        if jira_ticket_url:
            mr_description += f"JIRA Ticket: {jira_ticket_url}\n"
        if google_doc_url:
            # Add empty line before Release Notes if JIRA ticket exists
            if jira_ticket_url:
                mr_description += "\n"
            mr_description += f"Release Notes: {google_doc_url}\n"

        # Encode description for URL
        encoded_description = quote(mr_description.strip())

        mr_creation_url = f"{fork_url}/-/merge_requests/new?merge_request[source_branch]={branch_name}&merge_request[target_branch]=master&merge_request[title]={encoded_title}&merge_request[description]={encoded_description}"

        logger.info(f"Branch created successfully: {fork_url}/-/tree/{branch_name}")
        logger.info(f"MR creation link (from fork): {mr_creation_url}")

        return {
            "mr_creation_url": mr_creation_url,
            "branch_name": branch_name,
            "branch_url": f"{fork_url}/-/tree/{branch_name}",
        }

    except Exception as e:
        logger.error(f"Failed to create GitLab MR: {e}")

        # Provide more specific error messages for common issues
        error_str = str(e).lower()
        if "403" in error_str and "insufficient_scope" in error_str:
            raise Exception(
                "GitLab token has insufficient permissions. Please create a new token with 'api' scope."
            )
        elif "404" in error_str:
            raise Exception(
                "Repository or file not found. Please ensure you have a fork of 'service/app-interface'."
            )
        elif "409" in error_str and "branch" in error_str:
            raise Exception(
                f"Branch '{branch_name}' already exists. Please delete it manually from your fork or try again."
            )
        elif "fork" in error_str.lower():
            raise Exception(
                "Please create a fork of 'service/app-interface' repository first."
            )
        else:
            raise Exception(f"Failed to create deployment MR: {str(e)}")


def update_commit_ref_in_yaml(
    yaml_content, template_name, prod_target_name, old_commit, new_commit
):
    """Update commit reference in YAML content with minimal changes."""

    # Simple string replacement approach - only changes the commit line
    lines = yaml_content.split("\n")
    updated_lines = []

    for line in lines:
        # Look for the old commit reference and replace it
        if old_commit in line and "ref:" in line:
            # Only replace if this looks like a commit reference line
            if len(old_commit) >= 8 and old_commit.lower() in line.lower():
                updated_line = line.replace(old_commit, new_commit)
                logger.info(
                    f"Updated YAML line: '{line.strip()}' → '{updated_line.strip()}'"
                )
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)

    updated_content = "\n".join(updated_lines)

    # Verify the change was made
    if old_commit in updated_content:
        logger.warning(f"Old commit {old_commit[:7]} still found in YAML after update")
    if new_commit not in updated_content:
        logger.warning(f"New commit {new_commit[:7]} not found in YAML after update")

    return updated_content


# Removed update_ref_in_template function - using simple string replacement now
