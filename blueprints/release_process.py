"""
Blueprint for release process management.

Handles routes for:
- Viewing all release processes
- Creating new processes
- Viewing individual process details
- Updating process steps
- Deleting processes
"""

import logging
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash

from services.release_process_service import release_process_service

logger = logging.getLogger(__name__)

release_process_bp = Blueprint(
    "release_process", __name__, url_prefix="/release_processes"
)


@release_process_bp.route("/", methods=["GET"])
def list_processes():
    """Display all release processes."""
    try:
        all_processes = release_process_service.get_all_processes()
        active_processes = [p for p in all_processes if p.get("status") == "active"]
        stale_processes = [p for p in all_processes if p.get("status") == "stale"]

        # Add progress info to each process
        for process in all_processes:
            process["progress"] = release_process_service.get_process_progress(
                process["process_id"]
            )

        return render_template(
            "release_processes.html",
            active_processes=active_processes,
            stale_processes=stale_processes,
        )
    except Exception as e:
        logger.error(f"Error listing processes: {e}")
        flash("Error loading processes.", "danger")
        return render_template(
            "release_processes.html", active_processes=[], stale_processes=[]
        )


@release_process_bp.route("/<process_id>", methods=["GET"])
def view_process(process_id):
    """Display individual release process details."""
    try:
        from blueprints.release_notes import get_deployment_data

        process = release_process_service.get_process(process_id)
        if not process:
            flash(f"Process {process_id} not found", "danger")
            return redirect(url_for("release_process.list_processes"))

        # Add progress info
        process["progress"] = release_process_service.get_process_progress(process_id)

        # Get deployment data for repo name and commit info
        deployment_data = get_deployment_data(process["deployment_name"])
        repo_url = deployment_data.get("repo", "") if deployment_data else ""

        # Extract repo name from URL (e.g., "https://github.com/redhatinsights/hermod" -> "redhatinsights/hermod")
        # Or use deployment name as fallback
        if repo_url and "/" in repo_url:
            # Extract org/repo from URL
            repo_name = "/".join(repo_url.rstrip("/").split("/")[-2:])
        else:
            # Fallback to deployment name
            repo_name = process["deployment_name"]

        return render_template(
            "release_process_detail.html",
            process=process,
            repo_name=repo_name,
            deployment_data=deployment_data,
        )
    except Exception as e:
        logger.error(f"Error loading process {process_id}: {e}")
        flash(f"Error loading process: {e}", "danger")
        return redirect(url_for("release_process.list_processes"))


@release_process_bp.route("/create", methods=["POST"])
def create_process():
    """Create a new release process."""
    try:
        data = request.get_json()
        deployment_name = data.get("deployment_name")
        from_commit = data.get("from_commit")
        to_commit = data.get("to_commit")
        enable_jira = data.get("enable_jira", True)
        release_notes_data = data.get("release_notes_data")

        if not all([deployment_name, from_commit, to_commit]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        # If release_notes_data is missing or has 0 PRs, try to calculate it server-side
        if not release_notes_data or not release_notes_data.get("pr_count"):
            logger.info(f"Calculating PR count server-side for {deployment_name}")
            try:
                from blueprints.release_notes import get_deployment_data

                deployment = get_deployment_data(deployment_name)
                if deployment:
                    # Count PRs between from_commit and to_commit
                    prod_stage_pulls = deployment.get("prod_stage_pulls", [])

                    # Filter PRs up to the to_commit
                    prs_in_scope = []
                    for pr in prod_stage_pulls:
                        prs_in_scope.append(pr)
                        if pr.get("merge_commit_sha") == to_commit:
                            break

                    pr_count = len(prs_in_scope)
                    logger.info(
                        f"Calculated {pr_count} PRs in scope for {deployment_name}"
                    )

                    if not release_notes_data:
                        release_notes_data = {}
                    release_notes_data["pr_count"] = pr_count
                    release_notes_data["url"] = url_for(
                        "release_notes.generate",
                        depl_name=deployment_name,
                        up_to_pr=to_commit,
                        _external=True,
                    )
            except Exception as e:
                logger.warning(f"Could not calculate PR count server-side: {e}")

        # Create process
        process = release_process_service.create_process(
            deployment_name=deployment_name,
            from_commit=from_commit,
            to_commit=to_commit,
            enable_jira=enable_jira,
            release_notes_data=release_notes_data,
        )

        return jsonify(
            {
                "success": True,
                "process_id": process["process_id"],
                "redirect_url": url_for(
                    "release_process.view_process", process_id=process["process_id"]
                ),
            }
        )

    except ValueError as e:
        logger.error(f"Invalid input while creating process: {e}")
        return jsonify({"success": False, "error": "Invalid input."}), 400
    except Exception as e:
        logger.error(f"Error creating process: {e}")
        return jsonify({"success": False, "error": "An internal error occurred."}), 500


@release_process_bp.route("/<process_id>/update_step", methods=["POST"])
def update_step(process_id):
    """Update a process step."""
    try:
        data = request.get_json()
        step_name = data.get("step_name")
        status = data.get("status")
        step_data = data.get("data", {})

        if not all([step_name, status]):
            return jsonify({"success": False, "error": "Missing required fields"}), 400

        success = release_process_service.update_step(
            process_id=process_id, step_name=step_name, status=status, data=step_data
        )

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Failed to update step"}), 500

    except Exception as e:
        logger.error(f"Error updating step for process {process_id}: {e}")
        return jsonify({"success": False, "error": "An internal error occurred."}), 500


@release_process_bp.route("/<process_id>/check_mr_status", methods=["POST"])
def check_process_mr_status(process_id):
    """Check and update the MR status for a process."""
    try:
        # Get the process
        process = release_process_service.get_process(process_id)
        if not process:
            return jsonify({"success": False, "error": "Process not found"}), 404

        # Get the branch name and current status from app_interface_mr step data
        mr_step_data = (
            process.get("steps", {}).get("app_interface_mr", {}).get("data", {})
        )
        branch_name = mr_step_data.get("branch_name")
        existing_mr_number = mr_step_data.get("mr_number")
        current_status = (
            process.get("steps", {}).get("app_interface_mr", {}).get("status")
        )

        # If step is already completed, don't reset it
        if current_status == "completed":
            logger.info(
                f"Step already completed for process {process_id}, no check needed"
            )
            return jsonify(
                {
                    "success": True,
                    "status_details": mr_step_data.get("status_details", {}),
                    "step_status": "completed",
                    "message": "MR already merged",
                }
            )

        if not branch_name:
            return jsonify(
                {"success": False, "error": "No branch information found"}
            ), 400

        # Call the check_mr_status endpoint
        deployment_name = process.get("deployment_name")

        # Make internal request to check MR status
        from flask import current_app

        with current_app.test_client() as client:
            request_data = {"branch_name": branch_name}
            if existing_mr_number:
                request_data["mr_number"] = existing_mr_number

            response = client.post(
                f"/release_notes/{deployment_name}/check_mr_status",
                json=request_data,
                headers={"Content-Type": "application/json"},
            )

            result = response.get_json()

            if not result.get("success"):
                return jsonify(result), response.status_code

            status_details = result.get("status_details", {})

            # Update the process with new status details
            updated_data = mr_step_data.copy()
            updated_data["status_details"] = status_details

            # If MR is found, add/update the MR URL and number
            if status_details.get("mr_url"):
                updated_data["mr_url"] = status_details["mr_url"]
                updated_data["mr_number"] = status_details["mr_number"]

            # Update step status based on progress
            if status_details.get("mr_merged"):
                new_status = "completed"
            elif status_details.get("mr_created"):
                new_status = "in_progress"
            elif status_details.get("branch_created"):
                new_status = "in_progress"
            else:
                # Branch no longer exists
                # If we have an MR number stored, the MR was created but we can't find it now
                # This likely means it was merged and the branch was deleted
                # In this case, preserve the MR data and keep status as in_progress
                if existing_mr_number:
                    logger.info(
                        f"Branch not found but MR {existing_mr_number} was previously created - preserving MR data"
                    )
                    new_status = "in_progress"
                    # Keep the existing MR data
                else:
                    # No MR was ever created - reset to pending and clear branch data
                    new_status = "pending"
                    # Explicitly clear branch-related data so UI shows "Create MR" button again
                    updated_data = {
                        "status_details": status_details,
                        # Keep current_commit and new_commit for reference
                        "current_commit": updated_data.get("current_commit"),
                        "new_commit": updated_data.get("new_commit"),
                        # Explicitly set these to None to clear them (update() merges, doesn't replace)
                        "branch_name": None,
                        "branch_url": None,
                        "mr_creation_url": None,
                        "mr_url": None,
                        "mr_number": None,
                    }

            # Update the step
            release_process_service.update_step(
                process_id=process_id,
                step_name="app_interface_mr",
                status=new_status,
                data=updated_data,
            )

            return jsonify(
                {
                    "success": True,
                    "status_details": status_details,
                    "step_status": new_status,
                }
            )

    except Exception as e:
        logger.error(
            f"Error checking MR status for process {process_id}: {e}", exc_info=True
        )
        return jsonify({"success": False, "error": "Internal server error"}), 500


@release_process_bp.route("/<process_id>/delete", methods=["POST"])
def delete_process(process_id):
    """Delete a release process."""
    try:
        success = release_process_service.delete_process(process_id)

        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Process not found"}), 404

    except Exception as e:
        logger.error(f"Error deleting process {process_id}: {e}")
        return jsonify(
            {"success": False, "error": "An internal error has occurred."}
        ), 500


@release_process_bp.route("/delete_all_active", methods=["POST"])
def delete_all_active():
    """Delete all active release processes."""
    try:
        active_processes = release_process_service.get_active_processes()
        deleted_count = 0
        failed_count = 0

        for process in active_processes:
            process_id = process.get("process_id")
            if process_id:
                success = release_process_service.delete_process(process_id)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1

        logger.info(f"Deleted {deleted_count} active processes, {failed_count} failed")

        if failed_count > 0:
            return jsonify(
                {
                    "success": False,
                    "error": f"Deleted {deleted_count} processes, but {failed_count} failed",
                }
            ), 500

        return jsonify({"success": True, "deleted_count": deleted_count})

    except Exception as e:
        logger.error(f"Error deleting all active processes: {e}")
        return jsonify({"success": False, "error": "An internal error occurred."}), 500


@release_process_bp.route("/<process_id>/slack_message", methods=["GET"])
def get_slack_message(process_id):
    """Generate Slack message for a process."""
    try:
        message = release_process_service.generate_slack_message(process_id)

        if message:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"success": False, "error": "Process not found"}), 404

    except Exception as e:
        logger.error(f"Error generating Slack message for {process_id}: {e}")
        return jsonify(
            {"success": False, "error": "An internal error has occurred."}
        ), 500


@release_process_bp.route("/<process_id>/update_reviewer", methods=["POST"])
def update_reviewer(process_id):
    """Update the reviewer for a process."""
    try:
        data = request.get_json()
        reviewer = data.get("reviewer", "").strip()

        if not reviewer:
            return jsonify({"success": False, "error": "Reviewer cannot be empty"}), 400

        process = release_process_service.get_process(process_id)
        if not process:
            return jsonify({"success": False, "error": "Process not found"}), 404

        # Update reviewer in metadata
        if "metadata" not in process:
            process["metadata"] = {}
        process["metadata"]["reviewer"] = reviewer

        # Save the process
        release_process_service._save_process(process)

        return jsonify({"success": True, "reviewer": reviewer})

    except Exception as e:
        logger.error(f"Error updating reviewer for process {process_id}: {e}")
        return jsonify(
            {"success": False, "error": "An internal error has occurred."}
        ), 500


@release_process_bp.route("/<process_id>/validate", methods=["POST"])
def validate_process(process_id):
    """Validate a process's commit range."""
    try:
        data = request.get_json()
        commit_list = data.get("commit_list", [])

        is_valid = release_process_service.validate_process(process_id, commit_list)

        return jsonify({"success": True, "is_valid": is_valid})

    except Exception as e:
        logger.error(f"Error validating process {process_id}: {e}")
        return jsonify(
            {"success": False, "error": "An internal error has occurred."}
        ), 500


@release_process_bp.route("/check_existing", methods=["GET"])
def check_existing_process():
    """Check if an active process exists for a deployment and commit range."""
    try:
        deployment_name = request.args.get("deployment")
        from_commit = request.args.get("from_commit")
        to_commit = request.args.get("to_commit")

        if not all([deployment_name, from_commit, to_commit]):
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        # Get all active processes for this deployment
        processes = release_process_service.get_active_processes(deployment_name)

        # Find matching process
        matching_process = None
        for process in processes:
            if (
                process["commit_range"]["from_commit"] == from_commit
                and process["commit_range"]["to_commit"] == to_commit
            ):
                matching_process = process
                break

        if matching_process:
            return jsonify(
                {
                    "success": True,
                    "exists": True,
                    "process_id": matching_process["process_id"],
                    "process_url": url_for(
                        "release_process.view_process",
                        process_id=matching_process["process_id"],
                    ),
                }
            )
        else:
            return jsonify({"success": True, "exists": False})

    except Exception as e:
        logger.error(f"Error checking for existing process: {e}")
        return jsonify(
            {"success": False, "error": "An internal error has occurred."}
        ), 500
