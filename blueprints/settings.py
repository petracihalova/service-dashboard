"""
Settings blueprint for application configuration
"""

import os
from flask import Blueprint, jsonify, current_app
import logging

settings_bp = Blueprint("settings", __name__, url_prefix="/settings")
logger = logging.getLogger(__name__)


@settings_bp.route("/favicons", methods=["GET"])
def list_favicons():
    """List all available favicons"""
    try:
        favicons_dir = os.path.join(current_app.static_folder, "favicons")

        if not os.path.exists(favicons_dir):
            return jsonify({"favicons": []})

        # Get all .ico, .png, .svg files
        favicons = []
        for filename in os.listdir(favicons_dir):
            if filename.lower().endswith((".ico", ".png", ".svg", ".jpg", ".jpeg")):
                favicons.append(
                    {
                        "name": os.path.splitext(filename)[0],
                        "filename": filename,
                        "path": f"/static/favicons/{filename}",
                    }
                )

        # Sort by name
        favicons.sort(key=lambda x: x["name"])

        logger.info(f"Found {len(favicons)} favicons")
        return jsonify({"favicons": favicons})

    except Exception as e:
        logger.error(f"Error listing favicons: {e}")
        return jsonify({"error": str(e)}), 500
