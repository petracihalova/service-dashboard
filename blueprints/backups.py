"""
Blueprint for backup management.

Handles routes for creating, listing, deleting, and switching backups.
"""

import logging
from flask import Blueprint, jsonify, request

from services.backup_service import backup_service

logger = logging.getLogger(__name__)

backups_bp = Blueprint("backups", __name__, url_prefix="/backups")


@backups_bp.route("/", methods=["GET"])
def list_backups():
    """List all available backups."""
    try:
        backups = backup_service.list_backups()
        current_backup = backup_service.get_current_backup()

        return jsonify(
            {
                "success": True,
                "backups": backups,
                "current_backup": current_backup,
                "is_backup_mode": backup_service.is_backup_mode(),
            }
        )
    except Exception as e:
        logger.error(f"Error listing backups: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@backups_bp.route("/create", methods=["POST"])
def create_backup():
    """Create a new backup."""
    try:
        data = request.get_json() or {}
        description = data.get("description")

        # Check if in backup mode
        if backup_service.is_backup_mode():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Cannot create backup while in backup mode. Please restore to live mode first.",
                    }
                ),
                400,
            )

        backup = backup_service.create_backup(description)
        return jsonify({"success": True, "backup": backup})

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error creating backup: {e}", exc_info=True)
        return jsonify({"success": False, "error": "Failed to create backup"}), 500


@backups_bp.route("/<backup_id>", methods=["DELETE"])
def delete_backup(backup_id):
    """Delete a backup."""
    try:
        success = backup_service.delete_backup(backup_id)
        if success:
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": "Backup not found"}), 404

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error deleting backup: {e}")
        return jsonify({"success": False, "error": "Failed to delete backup"}), 500


@backups_bp.route("/switch/<backup_id>", methods=["POST"])
def switch_to_backup(backup_id):
    """Switch to viewing a backup (read-only mode)."""
    try:
        success = backup_service.switch_to_backup(backup_id)
        if success:
            backup = backup_service.get_backup(backup_id)
            return jsonify(
                {
                    "success": True,
                    "message": "Switched to backup mode",
                    "backup": backup,
                }
            )
        else:
            return (
                jsonify({"success": False, "error": "Failed to switch to backup"}),
                500,
            )

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        logger.error(f"Error switching to backup: {e}")
        return jsonify({"success": False, "error": "Failed to switch to backup"}), 500


@backups_bp.route("/restore", methods=["POST"])
def restore_to_live():
    """Restore to live data mode."""
    try:
        success = backup_service.restore_to_live()
        if success:
            return jsonify({"success": True, "message": "Restored to live mode"})
        else:
            return (
                jsonify({"success": False, "error": "Failed to restore to live mode"}),
                500,
            )

    except Exception as e:
        logger.error(f"Error restoring to live mode: {e}")
        return (
            jsonify({"success": False, "error": "Failed to restore to live mode"}),
            500,
        )


@backups_bp.route("/restore/<backup_id>", methods=["POST"])
def restore_backup_to_live(backup_id):
    """
    Restore a backup to live mode.

    This will:
    1. Create an automatic backup of current live data
    2. Clear the data folder (except excluded files)
    3. Copy files from the selected backup to data folder
    4. Restore the .env file from the backup
    """
    try:
        result = backup_service.restore_backup(backup_id)
        return jsonify(
            {
                "success": True,
                "message": f"Successfully restored backup {backup_id} to live mode",
                "backup_id": result["backup_id"],
                "auto_backup": result["auto_backup"],
            }
        )

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"Error restoring backup to live: {e}", exc_info=True)
        return jsonify(
            {"success": False, "error": f"Failed to restore backup: {str(e)}"}
        ), 500


@backups_bp.route("/status", methods=["GET"])
def get_backup_status():
    """Get current backup status."""
    try:
        current_backup = backup_service.get_current_backup()
        is_backup_mode = backup_service.is_backup_mode()

        result = {"success": True, "is_backup_mode": is_backup_mode}

        if is_backup_mode and current_backup:
            backup = backup_service.get_backup(current_backup)
            result["current_backup"] = backup

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting backup status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
