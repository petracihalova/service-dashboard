"""
Blueprint for enhancing existing data with additional fields like close_actor.
"""

import logging
from flask import Blueprint, jsonify, request
from services.close_actor_enhancer import enhancer

logger = logging.getLogger(__name__)

enhance_data_bp = Blueprint("enhance_data", __name__)


@enhance_data_bp.route("/api/enhance/close-actor/start", methods=["POST"])
def start_close_actor_enhancement():
    """Start the close_actor enhancement process."""
    try:
        result = enhancer.start_enhancement()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error starting enhancement: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/stop", methods=["POST"])
def stop_close_actor_enhancement():
    """Gracefully stop the close_actor enhancement process."""
    try:
        result = enhancer.stop_enhancement()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error stopping enhancement: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/progress", methods=["GET"])
def get_close_actor_progress():
    """Get the current progress of close_actor enhancement."""
    try:
        progress = enhancer.get_progress()
        return jsonify(progress)
    except Exception as e:
        logger.error(f"Error getting progress: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/status", methods=["GET"])
def get_enhancement_status():
    """Get overall enhancement status and statistics."""
    try:
        progress = enhancer.get_progress()

        # For stopped processes, add small delay to ensure files are fully written
        if progress.get("status") == "stopped":
            import time

            time.sleep(0.2)  # 200ms delay to ensure file system sync

        # Force fresh calculation of existing_data_status after enhancement stops
        # This ensures coverage reflects newly enhanced PRs
        existing_data_status = enhancer.check_existing_data_status()

        # Coverage data refreshed for stopped processes

        # Determine availability based on existing data OR completed process
        is_process_complete = progress["status"] == "completed"
        is_data_enhanced = existing_data_status["is_enhanced"]

        # Calculate some additional stats
        status = {
            "is_available": is_data_enhanced or is_process_complete,
            "is_running": progress["status"] == "running",
            "is_stopping": progress["status"] == "stopping",
            "is_stopped": progress["status"] == "stopped",
            "has_error": progress["status"] == "error",
            "progress": progress,
            "existing_data": existing_data_status,
        }

        # Status object ready for return

        if progress["total"] > 0:
            status["completion_percentage"] = (
                progress["processed"] / progress["total"]
            ) * 100
        else:
            status["completion_percentage"] = existing_data_status.get(
                "coverage_percentage", 0
            )

        return jsonify(status)

    except Exception as e:
        logger.error(f"Error getting enhancement status: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/is-running", methods=["GET"])
def is_enhancement_running():
    """Simple endpoint to check if enhancement is currently running."""
    try:
        progress = enhancer.get_progress()
        is_running = progress.get("status") in ["running", "stopping"]
        return jsonify(
            {"is_running": is_running, "status": progress.get("status", "idle")}
        )
    except Exception as e:
        logger.error(f"Error checking if enhancement is running: {e}")
        return jsonify({"is_running": False, "status": "error", "error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/retry-failed", methods=["POST"])
def retry_failed_enhancements():
    """Reset failed PRs so they can be retried with improved logic."""
    try:
        result = enhancer.retry_failed_prs()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error retrying failed enhancements: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/test-hybrid", methods=["POST"])
def test_hybrid_approach():
    """Test the hybrid GraphQL + REST approach on a single repository."""
    try:
        data = request.get_json() or {}
        repo_owner = data.get("repo_owner", "redhatinsights")
        repo_name = data.get("repo_name", "insights-rbac")
        pr_type = data.get("pr_type", "merged")

        result = enhancer.test_hybrid_approach(repo_owner, repo_name, pr_type)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error testing hybrid approach: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/missing-prs", methods=["GET"])
def get_missing_close_actor_prs():
    """Get list of PRs that are missing close_actor data for manual update."""
    try:
        result = enhancer.get_missing_close_actor_prs()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting missing PRs: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/manual-update", methods=["POST"])
def manual_update_close_actor():
    """Manually update close_actor for specific PRs."""
    try:
        data = request.get_json() or {}
        updates = data.get("updates", [])

        if not updates:
            return jsonify({"error": "No updates provided"}), 400

        result = enhancer.manual_update_close_actor(updates)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error with manual update: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/personal-stats", methods=["GET"])
def get_personal_close_actor_stats():
    """Get personal close_actor statistics for the current user."""
    try:
        # Get date range parameters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        result = enhancer.get_personal_close_actor_stats(
            date_from=date_from, date_to=date_to
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting personal close_actor stats: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route(
    "/api/enhance/close-actor/personal-konflux-stats", methods=["GET"]
)
def get_personal_konflux_close_actor_stats():
    """Get personal close_actor statistics filtered for PRs authored by Konflux bots."""
    try:
        # Get date range parameters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        result = enhancer.get_personal_konflux_close_actor_stats(
            date_from=date_from, date_to=date_to
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting personal Konflux close_actor stats: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/team-stats", methods=["GET"])
def get_team_close_actor_stats():
    """Get team-wide close_actor statistics."""
    try:
        # Get date range parameters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        result = enhancer.get_team_close_actor_stats(
            date_from=date_from, date_to=date_to
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting team close_actor stats: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/team-konflux-stats", methods=["GET"])
def get_team_konflux_close_actor_stats():
    """Get team-wide Konflux close_actor statistics."""
    try:
        # Get date range parameters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        result = enhancer.get_team_konflux_close_actor_stats(
            date_from=date_from, date_to=date_to
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting team Konflux close_actor stats: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/close-actor/organization-stats", methods=["GET"])
def get_repository_breakdown():
    """Get repository closure activity breakdown for organization statistics."""
    try:
        # Get date range parameters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        result = enhancer.get_repository_breakdown(date_from=date_from, date_to=date_to)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting repository breakdown: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route(
    "/api/enhance/close-actor/konflux-repository-stats", methods=["GET"]
)
def get_konflux_repository_breakdown():
    """Get Konflux repository closure activity breakdown for organization statistics."""
    try:
        # Get date range parameters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")

        result = enhancer.get_konflux_repository_breakdown(
            date_from=date_from, date_to=date_to
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting Konflux repository breakdown: {e}")
        return jsonify({"error": str(e)}), 500
