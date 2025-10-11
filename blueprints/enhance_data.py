"""
Blueprint for enhancing existing data with additional fields like close_actor and reviewers.
Note: Both close_actor and reviewers are fetched together by the close_actor_enhancer service.
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
        return jsonify({"error": "An internal error has occurred."}), 500


@enhance_data_bp.route("/api/enhance/close-actor/stop", methods=["POST"])
def stop_close_actor_enhancement():
    """Gracefully stop the close_actor enhancement process."""
    try:
        result = enhancer.stop_enhancement()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error stopping enhancement: {e}")
        return jsonify({"error": "An internal error has occurred."}), 500


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
        return jsonify({"error": "An internal error has occurred."}), 500


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
        return jsonify({"error": "An internal error has occurred."}), 500


# ============================================================================
# PR Review Enhancement Endpoints
# Note: Reviews are now fetched together with close_actor in the same process
# These endpoints delegate to the close_actor enhancer for compatibility
# ============================================================================


@enhance_data_bp.route("/api/enhance/reviews/start", methods=["POST"])
def start_review_enhancement():
    """Start the PR review enhancement process (delegates to close_actor enhancer)."""
    try:
        # Reviews are fetched together with close_actor, so just start that process
        result = enhancer.start_enhancement()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error starting review enhancement: {e}")
        return jsonify({"error": "An internal error has occurred."}), 500


@enhance_data_bp.route("/api/enhance/reviews/progress", methods=["GET"])
def get_review_progress():
    """Get the current progress of review enhancement (delegates to close_actor enhancer)."""
    try:
        # Reviews are fetched together with close_actor
        progress = enhancer.get_progress()
        return jsonify(progress)
    except Exception as e:
        logger.error(f"Error getting review progress: {e}")
        return jsonify({"error": "An internal error has occurred."}), 500


@enhance_data_bp.route("/api/enhance/reviews/status", methods=["GET"])
def get_review_enhancement_status():
    """Get overall review enhancement status (delegates to close_actor enhancer)."""
    try:
        # Reviews are fetched together with close_actor
        progress = enhancer.get_progress()

        # For completed processes, add small delay to ensure files are fully written
        if progress.get("status") in ["completed", "stopped"]:
            import time

            time.sleep(0.2)  # 200ms delay to ensure file system sync

        # Check existing data for reviewers field
        existing_data_status = _check_reviewers_data_status()

        # Determine availability
        is_process_complete = progress["status"] in ["completed", "stopped"]
        is_data_enhanced = existing_data_status["is_enhanced"]

        # Calculate status
        status = {
            "is_available": is_data_enhanced or is_process_complete,
            "is_running": progress["status"] == "running",
            "has_error": progress["status"] == "error",
            "progress": progress,
            "existing_data": existing_data_status,
        }

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
        logger.error(f"Error getting review enhancement status: {e}")
        return jsonify({"error": "An internal error has occurred."}), 500


def _check_reviewers_data_status():
    """Check if existing data has reviewers information."""
    from pathlib import Path
    from utils import load_json_data

    try:
        merged_file = Path("data/github_merged_pr_list.json")
        closed_file = Path("data/github_closed_pr_list.json")

        if not merged_file.exists() or not closed_file.exists():
            return {
                "is_enhanced": False,
                "coverage_percentage": 0,
                "total_prs": 0,
                "enhanced_prs": 0,
                "needs_enhancement": 0,
                "files_missing": True,
            }

        merged_data = load_json_data(merged_file)
        closed_data = load_json_data(closed_file)

        total_prs = 0
        enhanced_prs = 0

        # Check merged PRs for reviewers field
        # Field exists = enhanced (even if it's an empty list [])
        for repo_prs in merged_data.get("data", {}).values():
            for pr in repo_prs:
                total_prs += 1
                if "reviewers" in pr:
                    enhanced_prs += 1

        # Check closed PRs for reviewers field
        # Field exists = enhanced (even if it's an empty list [])
        for repo_prs in closed_data.get("data", {}).values():
            for pr in repo_prs:
                total_prs += 1
                if "reviewers" in pr:
                    enhanced_prs += 1

        needs_enhancement = total_prs - enhanced_prs
        coverage_percentage = (enhanced_prs / total_prs * 100) if total_prs > 0 else 0

        return {
            "is_enhanced": coverage_percentage > 90,
            "coverage_percentage": round(coverage_percentage, 1),
            "total_prs": total_prs,
            "enhanced_prs": enhanced_prs,
            "needs_enhancement": needs_enhancement,
            "files_missing": False,
        }

    except Exception as e:
        logger.error(f"Error checking reviewers data status: {e}")
        return {
            "is_enhanced": False,
            "coverage_percentage": 0,
            "total_prs": 0,
            "enhanced_prs": 0,
            "needs_enhancement": 0,
            "error": "An internal error has occurred.",
        }


@enhance_data_bp.route("/api/enhance/reviews/personal-stats", methods=["GET"])
def get_personal_review_stats():
    """Get personal PR review statistics for the current user."""
    try:
        from config import GITHUB_USERNAME

        # Get date range parameters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        # Get Konflux filter parameter
        konflux_filter = request.args.get(
            "konflux_filter"
        )  # "konflux", "non-konflux", or None for all

        # Get current user
        username = GITHUB_USERNAME
        if not username:
            return jsonify({"error": "No GitHub user configured"}), 400

        result = _calculate_personal_review_stats(
            username, date_from, date_to, konflux_filter
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting personal review stats: {e}")
        return jsonify({"error": str(e)}), 500


@enhance_data_bp.route("/api/enhance/reviews/team-stats", methods=["GET"])
def get_team_review_stats():
    """Get team-wide PR review statistics."""
    try:
        # Get date range parameters
        date_from = request.args.get("date_from")
        date_to = request.args.get("date_to")
        # Get Konflux filter parameter
        konflux_filter = request.args.get(
            "konflux_filter"
        )  # "konflux", "non-konflux", or None for all

        result = _calculate_team_review_stats(date_from, date_to, konflux_filter)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting team review stats: {e}")
        return jsonify({"error": str(e)}), 500


def _is_personal_repo_review(html_url, username):
    """Check if a PR is from a personal repository for review statistics.

    Args:
        html_url: The HTML URL of the PR
        username: The GitHub username to check against

    Returns:
        bool: True if this is a personal repository
    """
    if not html_url or not username:
        return False

    try:
        # Parse GitHub URL: https://github.com/{owner}/{repo}/pull/{number}
        if "github.com" in html_url:
            url_parts = html_url.split("/")
            if len(url_parts) >= 5:
                owner = url_parts[3]
                return owner.lower() == username.lower()
    except Exception:
        pass

    return False


def _calculate_personal_review_stats(
    username, date_from=None, date_to=None, konflux_filter=None
):
    """Calculate personal review statistics from PR data.

    Args:
        username: GitHub username to calculate stats for
        date_from: Start date filter
        date_to: End date filter
        konflux_filter: "konflux" for only Konflux PRs, "non-konflux" for non-Konflux PRs, None for all
    """
    from pathlib import Path
    from utils import load_json_data
    from datetime import datetime

    try:
        merged_file = Path("data/github_merged_pr_list.json")
        closed_file = Path("data/github_closed_pr_list.json")

        if not merged_file.exists() or not closed_file.exists():
            return {
                "total_reviews": 0,
                "merged_reviews": 0,
                "closed_reviews": 0,
                "by_repository": {},
                "error": "PR data files not found",
            }

        merged_data = load_json_data(merged_file)
        closed_data = load_json_data(closed_file)

        # Parse date filters (use date objects for comparison, not datetime)
        date_from_obj = None
        date_to_obj = None
        if date_from:
            try:
                parsed = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                date_from_obj = parsed.date()  # Convert to date only
            except ValueError:
                pass
        if date_to:
            try:
                parsed = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                date_to_obj = parsed.date()  # Convert to date only
            except ValueError:
                pass

        merged_reviews = 0
        closed_reviews = 0
        by_repository = {}

        # Process merged PRs
        for repo_name, prs in merged_data.get("data", {}).items():
            for pr in prs:
                # Apply date filter
                if date_from_obj or date_to_obj:
                    pr_date_str = pr.get("merged_at") or pr.get("closed_at")
                    if pr_date_str:
                        try:
                            pr_date = datetime.fromisoformat(
                                pr_date_str.replace("Z", "+00:00")
                            ).date()  # Convert to date only
                            if date_from_obj and pr_date < date_from_obj:
                                continue
                            if date_to_obj and pr_date > date_to_obj:
                                continue
                        except ValueError:
                            continue

                # Skip personal repositories
                html_url = pr.get("html_url", "")
                if _is_personal_repo_review(html_url, username):
                    continue

                # Apply Konflux filter
                if konflux_filter:
                    user_login = pr.get("user_login", "").lower()
                    is_konflux_pr = "konflux" in user_login

                    if konflux_filter == "konflux" and not is_konflux_pr:
                        continue  # Skip non-Konflux PRs
                    elif konflux_filter == "non-konflux" and is_konflux_pr:
                        continue  # Skip Konflux PRs

                reviewers = pr.get("reviewers", [])
                if username in reviewers:
                    merged_reviews += 1
                    if repo_name not in by_repository:
                        by_repository[repo_name] = {
                            "merged": 0,
                            "closed": 0,
                            "total": 0,
                        }
                    by_repository[repo_name]["merged"] += 1
                    by_repository[repo_name]["total"] += 1

        # Process closed PRs
        for repo_name, prs in closed_data.get("data", {}).items():
            for pr in prs:
                # Apply date filter
                if date_from_obj or date_to_obj:
                    pr_date_str = pr.get("closed_at")
                    if pr_date_str:
                        try:
                            pr_date = datetime.fromisoformat(
                                pr_date_str.replace("Z", "+00:00")
                            ).date()  # Convert to date only
                            if date_from_obj and pr_date < date_from_obj:
                                continue
                            if date_to_obj and pr_date > date_to_obj:
                                continue
                        except ValueError:
                            continue

                # Skip personal repositories
                html_url = pr.get("html_url", "")
                if _is_personal_repo_review(html_url, username):
                    continue

                # Apply Konflux filter
                if konflux_filter:
                    user_login = pr.get("user_login", "").lower()
                    is_konflux_pr = "konflux" in user_login

                    if konflux_filter == "konflux" and not is_konflux_pr:
                        continue  # Skip non-Konflux PRs
                    elif konflux_filter == "non-konflux" and is_konflux_pr:
                        continue  # Skip Konflux PRs

                reviewers = pr.get("reviewers", [])
                if username in reviewers:
                    closed_reviews += 1
                    if repo_name not in by_repository:
                        by_repository[repo_name] = {
                            "merged": 0,
                            "closed": 0,
                            "total": 0,
                        }
                    by_repository[repo_name]["closed"] += 1
                    by_repository[repo_name]["total"] += 1

        return {
            "total_reviews": merged_reviews + closed_reviews,
            "merged_reviews": merged_reviews,
            "closed_reviews": closed_reviews,
            "by_repository": by_repository,
        }

    except Exception as e:
        logger.error(f"Error calculating personal review stats: {e}")
        return {
            "total_reviews": 0,
            "merged_reviews": 0,
            "closed_reviews": 0,
            "by_repository": {},
            "error": str(e),
        }


def _calculate_team_review_stats(date_from=None, date_to=None, konflux_filter=None):
    """Calculate team-wide review statistics from PR data.

    Args:
        date_from: Start date filter
        date_to: End date filter
        konflux_filter: "konflux" for only Konflux PRs, "non-konflux" for non-Konflux PRs, None for all
    """
    from pathlib import Path
    from utils import load_json_data
    from datetime import datetime
    from config import GITHUB_USERNAME

    try:
        merged_file = Path("data/github_merged_pr_list.json")
        closed_file = Path("data/github_closed_pr_list.json")

        if not merged_file.exists() or not closed_file.exists():
            return {
                "by_user": {},
                "total_prs": 0,
                "prs_with_reviews": 0,
                "prs_without_reviews": 0,
                "prs_with_one_review": 0,
                "prs_with_multiple_reviews": 0,
                "prs_without_reviews_list": [],
                "error": "PR data files not found",
            }

        merged_data = load_json_data(merged_file)
        closed_data = load_json_data(closed_file)

        # Parse date filters (use date objects for comparison, not datetime)
        date_from_obj = None
        date_to_obj = None
        if date_from:
            try:
                parsed = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
                date_from_obj = parsed.date()  # Convert to date only
            except ValueError:
                pass
        if date_to:
            try:
                parsed = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
                date_to_obj = parsed.date()  # Convert to date only
            except ValueError:
                pass

        by_user = {}
        total_prs_analyzed = 0
        prs_with_reviews = 0
        prs_without_reviews = 0
        prs_with_one_review = 0  # PRs with exactly 1 reviewer
        prs_with_multiple_reviews = 0  # PRs with 2+ reviewers
        prs_without_reviews_list = []  # List of PRs without reviews

        # Process merged PRs
        for repo_name, prs in merged_data.get("data", {}).items():
            for pr in prs:
                # Apply date filter
                if date_from_obj or date_to_obj:
                    pr_date_str = pr.get("merged_at") or pr.get("closed_at")
                    if pr_date_str:
                        try:
                            pr_date = datetime.fromisoformat(
                                pr_date_str.replace("Z", "+00:00")
                            ).date()  # Convert to date only
                            if date_from_obj and pr_date < date_from_obj:
                                continue
                            if date_to_obj and pr_date > date_to_obj:
                                continue
                        except ValueError:
                            continue

                # Skip personal repositories
                html_url = pr.get("html_url", "")
                if GITHUB_USERNAME and _is_personal_repo_review(
                    html_url, GITHUB_USERNAME
                ):
                    continue

                # Apply Konflux filter
                if konflux_filter:
                    user_login = pr.get("user_login", "").lower()
                    is_konflux_pr = "konflux" in user_login

                    if konflux_filter == "konflux" and not is_konflux_pr:
                        continue  # Skip non-Konflux PRs
                    elif konflux_filter == "non-konflux" and is_konflux_pr:
                        continue  # Skip Konflux PRs

                total_prs_analyzed += 1
                reviewers = pr.get("reviewers", [])

                if reviewers:
                    prs_with_reviews += 1
                    # Count PRs by number of unique reviewers
                    if len(reviewers) == 1:
                        prs_with_one_review += 1
                    elif len(reviewers) > 1:
                        prs_with_multiple_reviews += 1

                    for reviewer in reviewers:
                        if reviewer not in by_user:
                            by_user[reviewer] = {
                                "merged": 0,
                                "closed": 0,
                                "total": 0,
                            }
                        by_user[reviewer]["merged"] += 1
                        by_user[reviewer]["total"] += 1
                else:
                    prs_without_reviews += 1
                    # Add PR details to the list
                    prs_without_reviews_list.append(
                        {
                            "title": pr.get("title", ""),
                            "number": pr.get("number"),
                            "url": pr.get("html_url", ""),
                            "repo": repo_name,
                            "author": pr.get("user_login", ""),
                            "state": "merged",
                            "date": pr.get("merged_at") or pr.get("closed_at"),
                            "close_actor": pr.get("close_actor", ""),
                        }
                    )

        # Process closed PRs
        for repo_name, prs in closed_data.get("data", {}).items():
            for pr in prs:
                # Apply date filter
                if date_from_obj or date_to_obj:
                    pr_date_str = pr.get("closed_at")
                    if pr_date_str:
                        try:
                            pr_date = datetime.fromisoformat(
                                pr_date_str.replace("Z", "+00:00")
                            ).date()  # Convert to date only
                            if date_from_obj and pr_date < date_from_obj:
                                continue
                            if date_to_obj and pr_date > date_to_obj:
                                continue
                        except ValueError:
                            continue

                # Skip personal repositories
                html_url = pr.get("html_url", "")
                if GITHUB_USERNAME and _is_personal_repo_review(
                    html_url, GITHUB_USERNAME
                ):
                    continue

                # Apply Konflux filter
                if konflux_filter:
                    user_login = pr.get("user_login", "").lower()
                    is_konflux_pr = "konflux" in user_login

                    if konflux_filter == "konflux" and not is_konflux_pr:
                        continue  # Skip non-Konflux PRs
                    elif konflux_filter == "non-konflux" and is_konflux_pr:
                        continue  # Skip Konflux PRs

                total_prs_analyzed += 1
                reviewers = pr.get("reviewers", [])

                if reviewers:
                    prs_with_reviews += 1
                    # Count PRs by number of unique reviewers
                    if len(reviewers) == 1:
                        prs_with_one_review += 1
                    elif len(reviewers) > 1:
                        prs_with_multiple_reviews += 1

                    for reviewer in reviewers:
                        if reviewer not in by_user:
                            by_user[reviewer] = {
                                "merged": 0,
                                "closed": 0,
                                "total": 0,
                            }
                        by_user[reviewer]["closed"] += 1
                        by_user[reviewer]["total"] += 1
                else:
                    prs_without_reviews += 1
                    # Add PR details to the list
                    prs_without_reviews_list.append(
                        {
                            "title": pr.get("title", ""),
                            "number": pr.get("number"),
                            "url": pr.get("html_url", ""),
                            "repo": repo_name,
                            "author": pr.get("user_login", ""),
                            "state": "closed",
                            "date": pr.get("closed_at"),
                            "close_actor": pr.get("close_actor", ""),
                        }
                    )

        return {
            "by_user": by_user,
            "total_prs": total_prs_analyzed,
            "prs_with_reviews": prs_with_reviews,
            "prs_without_reviews": prs_without_reviews,
            "prs_with_one_review": prs_with_one_review,
            "prs_with_multiple_reviews": prs_with_multiple_reviews,
            "prs_without_reviews_list": prs_without_reviews_list,
        }

    except Exception as e:
        logger.error(f"Error calculating team review stats: {e}")
        return {
            "by_user": {},
            "total_prs": 0,
            "prs_with_reviews": 0,
            "prs_without_reviews": 0,
            "prs_with_one_review": 0,
            "prs_with_multiple_reviews": 0,
            "prs_without_reviews_list": [],
            "error": str(e),
        }
