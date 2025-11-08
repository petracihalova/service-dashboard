"""
BackOffice Proxy Plugin Blueprint

Routes and views for the BackOffice Proxy plugin.
"""

import logging
import os

from flask import Blueprint, jsonify, render_template, request

import config
from plugins.backoffice_proxy_service import backoffice_proxy_service

logger = logging.getLogger(__name__)

backoffice_proxy_bp = Blueprint(
    "backoffice_proxy", __name__, url_prefix="/backoffice-proxy"
)


@backoffice_proxy_bp.route("/", methods=["GET"])
def index():
    """Display BackOffice Proxy information page."""
    # Just render the page without fetching data
    # Data will be loaded on demand via the "Update Data" button
    return render_template("plugins/backoffice_proxy.html")


@backoffice_proxy_bp.route("/deployment-info/cached", methods=["GET"])
def get_cached_deployment_info():
    """Get cached deployment information (instant load)."""
    try:
        cached_data = backoffice_proxy_service.load_cached_data()
        if cached_data:
            return jsonify(cached_data)
        else:
            return jsonify({"cached": False}), 404

    except Exception as e:
        logger.error(f"Error getting cached deployment info: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@backoffice_proxy_bp.route("/deployment-info", methods=["GET"])
def get_deployment_info():
    """Get fresh deployment information and update cache."""
    try:
        deployment_info = backoffice_proxy_service.get_deployment_info()

        # Check if we got meaningful data (at least one commit should be present)
        has_useful_data = (
            deployment_info.get("default_branch_commit")
            or deployment_info.get("stage", {}).get("commit")
            or deployment_info.get("prod", {}).get("commit")
        )

        if has_useful_data:
            # We got new data, update the cache
            # Preserve existing document_url and open MRs if commit range hasn't changed
            try:
                cached_data = backoffice_proxy_service.load_cached_data()
                if cached_data and cached_data.get("prod_scope"):
                    old_prod_scope = cached_data["prod_scope"]
                    new_prod_scope = deployment_info.get("prod_scope")

                    # If commit range is the same, preserve document_url
                    if (
                        new_prod_scope
                        and old_prod_scope
                        and old_prod_scope.get("from_commit")
                        == new_prod_scope.get("from_commit")
                        and old_prod_scope.get("to_commit")
                        == new_prod_scope.get("to_commit")
                        and old_prod_scope.get("document_url")
                    ):
                        new_prod_scope["document_url"] = old_prod_scope["document_url"]
                        new_prod_scope["document_created_at"] = old_prod_scope.get(
                            "document_created_at"
                        )
            except Exception as preserve_error:
                logger.warning(f"Failed to preserve document URL: {preserve_error}")

            backoffice_proxy_service.save_cached_data(deployment_info)
            return jsonify(deployment_info)
        else:
            # Failed to fetch new data, return cached data with warning
            logger.warning(
                "Failed to fetch deployment info (VPN required?), returning cached data"
            )
            cached_data = backoffice_proxy_service.load_cached_data()
            if cached_data:
                cached_data["update_error"] = "Failed to fetch new data (VPN required?)"
                return jsonify(
                    cached_data
                ), 206  # 206 Partial Content - using cached data
            else:
                return jsonify(
                    {"error": "Failed to fetch data and no cache available"}
                ), 500

    except Exception as e:
        logger.error(f"Error getting deployment info: {e}", exc_info=True)

        # Try to return cached data on error
        try:
            cached_data = backoffice_proxy_service.load_cached_data()
            if cached_data:
                cached_data["update_error"] = f"Failed to update: {str(e)}"
                logger.info("Returning cached data due to fetch error")
                return jsonify(cached_data), 206  # 206 Partial Content
        except Exception as cache_error:
            logger.warning(f"Could not load cached data: {cache_error}")

        return jsonify({"error": str(e)}), 500


@backoffice_proxy_bp.route("/tokens", methods=["GET"])
def get_tokens():
    """Get current OpenShift token status (masked)."""
    return jsonify(
        {
            "prod_configured": bool(config.OPENSHIFT_TOKEN_PROD),
            "stage_configured": bool(config.OPENSHIFT_TOKEN_STAGE),
            "prod_preview": (
                config.OPENSHIFT_TOKEN_PROD[:20] + "..."
                if config.OPENSHIFT_TOKEN_PROD
                else ""
            ),
            "stage_preview": (
                config.OPENSHIFT_TOKEN_STAGE[:20] + "..."
                if config.OPENSHIFT_TOKEN_STAGE
                else ""
            ),
        }
    )


@backoffice_proxy_bp.route("/tokens", methods=["POST"])
def update_tokens():
    """Update OpenShift tokens in memory and optionally in .env file."""
    try:
        data = request.get_json()
        prod_token = data.get("prod_token", "").strip()
        stage_token = data.get("stage_token", "").strip()
        update_env_file = data.get("update_env_file", False)

        logger.info("Updating OpenShift tokens in memory")

        # Update in-memory config
        if prod_token:
            config.OPENSHIFT_TOKEN_PROD = prod_token
            os.environ["OPENSHIFT_TOKEN_PROD"] = prod_token
            logger.info("Updated OPENSHIFT_TOKEN_PROD in memory")

        if stage_token:
            config.OPENSHIFT_TOKEN_STAGE = stage_token
            os.environ["OPENSHIFT_TOKEN_STAGE"] = stage_token
            logger.info("Updated OPENSHIFT_TOKEN_STAGE in memory")

        # Update .env file if requested
        if update_env_file:
            env_path = config.base_dir / ".env"
            if env_path.exists():
                logger.info(f"Updating .env file at {env_path}")

                # Read existing .env file
                with open(env_path, "r") as f:
                    lines = f.readlines()

                # Update or add token lines
                prod_found = False
                stage_found = False
                new_lines = []

                for line in lines:
                    if line.startswith("OPENSHIFT_TOKEN_PROD="):
                        if prod_token:
                            new_lines.append(f"OPENSHIFT_TOKEN_PROD={prod_token}\n")
                            prod_found = True
                        else:
                            new_lines.append(line)
                    elif line.startswith("OPENSHIFT_TOKEN_STAGE="):
                        if stage_token:
                            new_lines.append(f"OPENSHIFT_TOKEN_STAGE={stage_token}\n")
                            stage_found = True
                        else:
                            new_lines.append(line)
                    else:
                        new_lines.append(line)

                # Add tokens if they weren't found in the file
                if prod_token and not prod_found:
                    new_lines.append(f"\nOPENSHIFT_TOKEN_PROD={prod_token}\n")
                    logger.info("Added OPENSHIFT_TOKEN_PROD to .env file")

                if stage_token and not stage_found:
                    new_lines.append(f"OPENSHIFT_TOKEN_STAGE={stage_token}\n")
                    logger.info("Added OPENSHIFT_TOKEN_STAGE to .env file")

                # Write back to .env file
                with open(env_path, "w") as f:
                    f.writelines(new_lines)

                logger.info(".env file updated successfully")
            else:
                logger.warning(f".env file not found at {env_path}")
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": ".env file not found. Tokens updated in memory only.",
                        }
                    ),
                    404,
                )

        message = "Tokens updated successfully"
        if update_env_file:
            message += " (in memory and .env file)"
        else:
            message += " (in memory only, restart required to persist)"

        return jsonify({"success": True, "message": message})

    except Exception as e:
        logger.error(f"Error updating OpenShift tokens: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@backoffice_proxy_bp.route("/release-scope", methods=["GET"])
def get_release_scope():
    """Get release scope (commits and MRs) between two commits."""
    from_commit = request.args.get("from_commit")
    to_commit = request.args.get("to_commit")

    if not from_commit or not to_commit:
        return jsonify({"error": "Both from_commit and to_commit are required"}), 400

    try:
        scope = backoffice_proxy_service.get_release_scope(from_commit, to_commit)
        return jsonify(scope)

    except Exception as e:
        logger.error(f"Error getting release scope: {e}")
        return jsonify({"error": str(e)}), 500


@backoffice_proxy_bp.route("/open-mrs", methods=["GET"])
def get_open_mrs():
    """Get open MRs from gitlab_pr_list.json for backoffice-proxy."""
    try:
        import json

        pr_list_path = os.path.join(config.data_folder, "gitlab_pr_list.json")

        if not os.path.exists(pr_list_path):
            return jsonify({"error": "gitlab_pr_list.json not found"}), 404

        with open(pr_list_path, "r") as f:
            pr_data = json.load(f)

        # Get backoffice-proxy MRs
        all_mrs = pr_data.get("backoffice-proxy", [])

        # Filter for open MRs (not merged and not closed)
        open_mrs = [
            mr
            for mr in all_mrs
            if mr.get("merged_at") is None and mr.get("closed_at") is None
        ]

        return jsonify({"open_mrs": open_mrs, "total": len(open_mrs)})

    except Exception as e:
        logger.error(f"Error getting open MRs: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@backoffice_proxy_bp.route("/create-release-notes", methods=["POST"])
def create_release_notes():
    """Create a Google Doc with release notes for BackOffice Proxy."""
    try:
        from services.google_drive_service import GoogleDriveService
        from datetime import datetime
        import re

        data = request.get_json()
        deployment_data = data.get("deployment_data", {})
        scope_data = data.get("scope_data", {})

        if not scope_data:
            return jsonify({"error": "No scope data provided"}), 400

        # Initialize Google Drive service
        google_drive_service = GoogleDriveService()
        if not google_drive_service.is_available():
            return jsonify({"error": "Google Drive service is not available"}), 503

        # Build structured release notes data similar to main release notes
        merge_requests = scope_data.get("merge_requests", [])

        # Transform MRs to match expected format (prod_stage_pulls)
        prod_stage_pulls = []
        for mr in merge_requests:
            prod_stage_pulls.append(
                {
                    "number": mr.get("iid", mr.get("number")),
                    "title": mr.get("title", ""),
                    "html_url": mr.get("web_url", ""),
                    "merged_at": mr.get("merged_at", ""),
                    "user_login": mr.get("author", {}).get("username")
                    if isinstance(mr.get("author"), dict)
                    else "Unknown",
                    "user_name": mr.get("author", {}).get("name")
                    if isinstance(mr.get("author"), dict)
                    else "Unknown",
                    "qe_comment": None,  # BackOffice Proxy doesn't have QE comments
                    "bot_pr": "[bot]" in mr.get("title", "").lower(),
                }
            )

        # Get links from deployment data
        links = deployment_data.get("links", [])
        repo_link = ""
        image_link = ""
        release_notes_link = ""

        for link in links:
            link_name = link.get("name", "").lower()
            if link_name == "code":
                repo_link = link.get("url", "")
            elif link_name == "image":
                image_link = link.get("url", "")
            elif link_name == "release notes":
                release_notes_link = link.get("url", "")

        # Build release notes data structure
        release_notes_data = {
            "repo_name": "insights-platform/backoffice-proxy",
            "repo_link": repo_link or config.BACKOFFICE_PROXY_REPO,
            "image_link": image_link,
            "app_interface_link": "",  # Not applicable for BackOffice Proxy
            "release_notes_link": release_notes_link,
            "commit_prod": deployment_data.get("prod", {}).get("commit", ""),
            "commit_stage": deployment_data.get("stage", {}).get("commit", ""),
            "target_prod_commit": deployment_data.get("default_branch_commit", ""),
            "prod_stage_pulls": prod_stage_pulls,
            "last_release_prod_MR": {},  # Not tracked for BackOffice Proxy
        }

        # Extract folder ID from the deployment links (Google Drive release notes link)
        folder_id = None
        logger.info(f"Searching for Google Drive folder in {len(links)} links")

        for link in links:
            if link.get(
                "name", ""
            ).lower() == "release notes" and "drive.google.com" in link.get("url", ""):
                # Extract folder ID from URL like: https://drive.google.com/drive/folders/1dO5SoI1CCpFjdh-ChbQgBnf5_4IVxXZ-
                match = re.search(r"/folders/([a-zA-Z0-9_-]+)", link["url"])
                if match:
                    folder_id = match.group(1)
                    logger.info(f"Found Google Drive folder ID: {folder_id}")
                    break

        if not folder_id:
            logger.error(
                f"Could not find Google Drive folder. Available links: {links}"
            )
            return (
                jsonify(
                    {
                        "error": "Could not find Google Drive folder ID in deployment links"
                    }
                ),
                500,
            )

        # Create the document using the same method as release_notes.py
        result = google_drive_service.create_release_notes_doc(
            "backoffice-proxy", release_notes_data, folder_id
        )

        if result and result.get("document_url"):
            document_url = result["document_url"]
            logger.info(f"Created BackOffice Proxy release notes: {document_url}")

            # Update cached data with document URL
            try:
                cached_data = backoffice_proxy_service.load_cached_data()
                if cached_data and cached_data.get("prod_scope"):
                    # Store document URL with commit range
                    if "prod_scope" not in cached_data:
                        cached_data["prod_scope"] = {}
                    cached_data["prod_scope"]["document_url"] = document_url
                    cached_data["prod_scope"]["document_created_at"] = (
                        datetime.now().isoformat()
                    )

                    # Save updated cache
                    backoffice_proxy_service.save_cached_data(cached_data)
                    logger.info("Updated cached data with document URL")
            except Exception as cache_error:
                logger.warning(
                    f"Failed to update cache with document URL: {cache_error}"
                )

            return jsonify({"success": True, "document_url": document_url})
        else:
            return jsonify({"error": "Failed to create document"}), 500

    except Exception as e:
        logger.error(f"Error creating release notes: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@backoffice_proxy_bp.route("/remove-document-reference", methods=["POST"])
def remove_document_reference():
    """Remove the document reference from cached prod_scope data."""
    try:
        cached_data = backoffice_proxy_service.load_cached_data()

        if not cached_data:
            return jsonify({"error": "No cached data found"}), 404

        if not cached_data.get("prod_scope"):
            return jsonify({"error": "No prod_scope data found"}), 404

        # Remove document reference
        if "document_url" in cached_data["prod_scope"]:
            del cached_data["prod_scope"]["document_url"]
            logger.info("Removed document_url from prod_scope")

        if "document_created_at" in cached_data["prod_scope"]:
            del cached_data["prod_scope"]["document_created_at"]
            logger.info("Removed document_created_at from prod_scope")

        # Save updated cache
        backoffice_proxy_service.save_cached_data(cached_data)

        return jsonify({"success": True, "message": "Document reference removed"})

    except Exception as e:
        logger.error(f"Error removing document reference: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
