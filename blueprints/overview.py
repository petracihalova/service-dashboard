import os
import re
import shutil

import yaml
from flask import Blueprint, jsonify, render_template, request

import config
from utils import logger

overview_bp = Blueprint("overview", __name__)


@overview_bp.route("/")
def index():
    """Overview page."""
    services_links = get_services_links()
    if not services_links:
        return render_template("errors/404.html")
    return render_template("overview.html", services=services_links)


def get_services_links():
    """Get services links from a file."""
    if not config.SERVICES_LINKS_PATH.is_file():
        try:
            source = config.DATA_PATH_FOLDER / "test_data"
            dest = config.DATA_PATH_FOLDER
            for filename in ["services_links.yml"]:
                source_file = os.path.join(source, filename)
                dest_file = os.path.join(dest, filename)
                if os.path.isfile(source_file):
                    shutil.copy2(source_file, dest_file)

        except (FileNotFoundError, PermissionError) as e:
            logger.error(f"Error copying directory: {e}")

    return yaml.safe_load(config.SERVICES_LINKS_PATH.read_text())


def ensure_protocol(url):
    """Ensure URL has a protocol, add https:// if missing."""
    if not url:
        return url

    # Check if URL already has a protocol
    if not re.match(r"^https?://", url, re.IGNORECASE):
        return f"https://{url}"

    return url


def fix_links_protocols(links):
    """Fix all links in a list to ensure they have proper protocols."""
    if not links:
        return links

    for link in links:
        if "link_value" in link and link["link_value"]:
            link["link_value"] = ensure_protocol(link["link_value"])

    return links


@overview_bp.route("/update-service-links", methods=["POST"])
def update_service_links():
    """Update service name and links for a specific service."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"})

        service_id = data.get("service_id")
        service_name = data.get("service_name")
        original_service_name = data.get("original_service_name")
        category_name = data.get("category_name")
        links = data.get("links", [])
        color = data.get("color", "none")
        # Convert legacy "default" value to "none"
        if color == "default":
            color = "none"

        # Fix URL protocols in links
        links = fix_links_protocols(links)

        if not service_id or not category_name:
            return jsonify(
                {"success": False, "error": "Missing service_id or category_name"}
            )

        if service_name is not None:
            if not service_name or not service_name.strip():
                return jsonify(
                    {"success": False, "error": "Service name cannot be empty"}
                )
            service_name = service_name.strip()

        # Load current services data
        services_data = get_services_links()
        if not services_data:
            return jsonify({"success": False, "error": "Failed to load services data"})

        # Check if service name is changing and if new name already exists
        if (
            service_name
            and original_service_name
            and original_service_name != service_name
        ):
            for category in services_data.get("categories", []):
                for repo in category.get("category_repos", []):
                    if (
                        repo.get("name", "").lower() == service_name.lower()
                        and repo.get("id") != service_id
                    ):
                        return jsonify(
                            {
                                "success": False,
                                "error": f"Service name '{service_name}' already exists",
                            }
                        )

        # Find and update the service
        service_updated = False
        for category in services_data.get("categories", []):
            if category.get("category_name") == category_name:
                for repo in category.get("category_repos", []):
                    if repo.get("id") == service_id:
                        # Update the links
                        repo["links"] = links
                        # Update the name if provided
                        if service_name:
                            repo["name"] = service_name
                        # Update the color
                        repo["color"] = color
                        service_updated = True
                        logger.info(
                            f"Updated links for service {service_id} in category {category_name}"
                        )
                        break
                if service_updated:
                    break

        if not service_updated:
            return jsonify(
                {
                    "success": False,
                    "error": f"Service {service_id} not found in category {category_name}",
                }
            )

        # Save the updated data back to the file
        try:
            with open(config.SERVICES_LINKS_PATH, "w", encoding="utf-8") as file:
                yaml.dump(
                    services_data,
                    file,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            logger.info(
                f"Successfully saved updated services data to {config.SERVICES_LINKS_PATH}"
            )
            if service_name and original_service_name != service_name:
                return jsonify(
                    {
                        "success": True,
                        "message": f"Service '{service_name}' updated successfully",
                    }
                )
            else:
                return jsonify(
                    {"success": True, "message": "Service links updated successfully"}
                )

        except Exception as e:
            logger.error(f"Error saving services data: {e}")
            return jsonify(
                {"success": False, "error": f"Failed to save data: {str(e)}"}
            )

    except Exception as e:
        logger.error(f"Error in update_service_links: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"})


@overview_bp.route("/add-service", methods=["POST"])
def add_service():
    """Add a new service to a category."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"})

        service_id = data.get("service_id")
        service_name = data.get("service_name")
        category_name = data.get("category_name")
        links = data.get("links", [])
        color = data.get("color", "none")
        # Convert legacy "default" value to "none"
        if color == "default":
            color = "none"

        # Fix URL protocols in links
        links = fix_links_protocols(links)

        if not service_id or not service_name or not category_name:
            return jsonify(
                {
                    "success": False,
                    "error": "Missing required fields: service_id, service_name, or category_name",
                }
            )

        # Load current services data
        services_data = get_services_links()
        if not services_data:
            return jsonify({"success": False, "error": "Failed to load services data"})

        # Check if service ID already exists
        for category in services_data.get("categories", []):
            for repo in category.get("category_repos", []):
                if repo.get("id") == service_id:
                    return jsonify(
                        {
                            "success": False,
                            "error": f"Service with ID '{service_id}' already exists",
                        }
                    )

        # Find the category and add the new service
        category_found = False
        for category in services_data.get("categories", []):
            if category.get("category_name") == category_name:
                new_service = {
                    "id": service_id,
                    "name": service_name,
                    "links": links,
                    "color": color,
                }

                if "category_repos" not in category:
                    category["category_repos"] = []

                category["category_repos"].append(new_service)
                category_found = True
                logger.info(
                    f"Added new service '{service_name}' (ID: {service_id}) to category '{category_name}'"
                )
                break

        if not category_found:
            return jsonify(
                {"success": False, "error": f"Category '{category_name}' not found"}
            )

        # Save the updated data back to the file
        try:
            with open(config.SERVICES_LINKS_PATH, "w", encoding="utf-8") as file:
                yaml.dump(
                    services_data,
                    file,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            logger.info(
                f"Successfully saved updated services data with new service {service_id}"
            )
            return jsonify({"success": True, "message": "Service added successfully"})

        except Exception as e:
            logger.error(f"Error saving services data: {e}")
            return jsonify(
                {"success": False, "error": f"Failed to save data: {str(e)}"}
            )

    except Exception as e:
        logger.error(f"Error in add_service: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"})


@overview_bp.route("/delete-service", methods=["POST"])
def delete_service():
    """Delete a service from a category."""
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No data provided"})

        service_id = data.get("service_id")
        category_name = data.get("category_name")

        if not service_id or not category_name:
            return jsonify(
                {
                    "success": False,
                    "error": "Missing required fields: service_id or category_name",
                }
            )

        # Load current services data
        services_data = get_services_links()
        if not services_data:
            return jsonify({"success": False, "error": "Failed to load services data"})

        # Find and remove the service
        service_found = False
        for category in services_data.get("categories", []):
            if category.get("category_name") == category_name:
                category_repos = category.get("category_repos", [])
                for i, repo in enumerate(category_repos):
                    if repo.get("id") == service_id:
                        # Remove the service
                        removed_service = category_repos.pop(i)
                        service_found = True
                        logger.info(
                            f"Deleted service '{removed_service.get('name')}' (ID: {service_id}) from category '{category_name}'"
                        )
                        break
                if service_found:
                    break

        if not service_found:
            return jsonify(
                {
                    "success": False,
                    "error": f"Service with ID '{service_id}' not found in category '{category_name}'",
                }
            )

        # Save the updated data back to the file
        try:
            with open(config.SERVICES_LINKS_PATH, "w", encoding="utf-8") as file:
                yaml.dump(
                    services_data,
                    file,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )

            logger.info(
                f"Successfully saved updated services data after deleting service {service_id}"
            )
            return jsonify({"success": True, "message": "Service deleted successfully"})

        except Exception as e:
            logger.error(f"Error saving services data: {e}")
            return jsonify(
                {"success": False, "error": f"Failed to save data: {str(e)}"}
            )

    except Exception as e:
        logger.error(f"Error in delete_service: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"})


@overview_bp.route("/update-category-name", methods=["POST"])
def update_category_name():
    """Update a category name."""
    try:
        data = request.get_json()
        original_name = data.get("original_name")
        new_name = data.get("new_name", "").strip()

        if not original_name or not new_name:
            return jsonify({"success": False, "error": "Missing required fields"})

        # Load current data
        services_file_path = os.path.join(
            os.path.dirname(__file__), "../data/services_links.yml"
        )

        with open(services_file_path, "r", encoding="utf-8") as file:
            services_data = yaml.safe_load(file)

        # Check if new name already exists (case insensitive)
        existing_names = [
            cat.get("category_name", "").lower()
            for cat in services_data.get("categories", [])
        ]
        if (
            new_name.lower() in existing_names
            and new_name.lower() != original_name.lower()
        ):
            return jsonify(
                {"success": False, "error": f"Category '{new_name}' already exists"}
            )

        # Find and update the category
        category_found = False
        for category in services_data.get("categories", []):
            if category.get("category_name") == original_name:
                category["category_name"] = new_name
                category_found = True
                break

        if not category_found:
            return jsonify(
                {"success": False, "error": f"Category '{original_name}' not found"}
            )

        # Save the updated data
        with open(services_file_path, "w", encoding="utf-8") as file:
            yaml.dump(services_data, file, default_flow_style=False, allow_unicode=True)

        logger.info(
            f"Successfully updated category name from '{original_name}' to '{new_name}'"
        )
        return jsonify(
            {"success": True, "message": f"Category renamed to '{new_name}'"}
        )

    except Exception as e:
        logger.error(f"Error in update_category_name: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"})


@overview_bp.route("/add-category", methods=["POST"])
def add_category():
    """Add a new category."""
    try:
        data = request.get_json()
        category_name = data.get("category_name", "").strip()

        if not category_name:
            return jsonify({"success": False, "error": "Category name cannot be empty"})

        # Load current data
        services_file_path = os.path.join(
            os.path.dirname(__file__), "../data/services_links.yml"
        )

        with open(services_file_path, "r", encoding="utf-8") as file:
            services_data = yaml.safe_load(file)

        # Check if category already exists (case insensitive)
        existing_names = [
            cat.get("category_name", "").lower()
            for cat in services_data.get("categories", [])
        ]
        if category_name.lower() in existing_names:
            return jsonify(
                {
                    "success": False,
                    "error": f"Category '{category_name}' already exists",
                }
            )

        # Add new category
        new_category = {"category_name": category_name, "category_repos": []}

        if "categories" not in services_data:
            services_data["categories"] = []

        services_data["categories"].append(new_category)

        # Save the updated data
        with open(services_file_path, "w", encoding="utf-8") as file:
            yaml.dump(services_data, file, default_flow_style=False, allow_unicode=True)

        logger.info(f"Successfully added new category: '{category_name}'")
        return jsonify(
            {
                "success": True,
                "message": f"Category '{category_name}' created successfully",
            }
        )

    except Exception as e:
        logger.error(f"Error in add_category: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"})


@overview_bp.route("/delete-category", methods=["POST"])
def delete_category():
    """Delete a category (only if it's empty)."""
    try:
        data = request.get_json()
        category_name = data.get("category_name")

        if not category_name:
            return jsonify({"success": False, "error": "Category name is required"})

        # Load current data
        services_file_path = os.path.join(
            os.path.dirname(__file__), "../data/services_links.yml"
        )

        with open(services_file_path, "r", encoding="utf-8") as file:
            services_data = yaml.safe_load(file)

        # Find the category and check if it's empty
        category_found = False
        category_to_remove = None

        for category in services_data.get("categories", []):
            if category.get("category_name") == category_name:
                category_found = True
                category_to_remove = category

                # Check if category has services
                service_count = len(category.get("category_repos", []))
                if service_count > 0:
                    return jsonify(
                        {
                            "success": False,
                            "error": f"Cannot delete category '{category_name}' because it contains {service_count} services",
                        }
                    )
                break

        if not category_found:
            return jsonify(
                {"success": False, "error": f"Category '{category_name}' not found"}
            )

        # Remove the category
        services_data["categories"].remove(category_to_remove)

        # Save the updated data
        with open(services_file_path, "w", encoding="utf-8") as file:
            yaml.dump(services_data, file, default_flow_style=False, allow_unicode=True)

        logger.info(f"Successfully deleted category: '{category_name}'")
        return jsonify(
            {
                "success": True,
                "message": f"Category '{category_name}' deleted successfully",
            }
        )

    except Exception as e:
        logger.error(f"Error in delete_category: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"})


@overview_bp.route("/move-category", methods=["POST"])
def move_category():
    """Move a category to a different position."""
    try:
        data = request.get_json()
        category_name = data.get("category_name")
        from_index = data.get("from_index")
        to_index = data.get("to_index")

        if category_name is None or from_index is None or to_index is None:
            return jsonify({"success": False, "error": "Missing required fields"})

        # Load current data
        services_file_path = os.path.join(
            os.path.dirname(__file__), "../data/services_links.yml"
        )

        with open(services_file_path, "r", encoding="utf-8") as file:
            services_data = yaml.safe_load(file)

        categories = services_data.get("categories", [])

        # Validate indices
        if from_index < 0 or from_index >= len(categories):
            return jsonify({"success": False, "error": "Invalid source position"})

        if to_index < 0 or to_index >= len(categories):
            return jsonify({"success": False, "error": "Invalid destination position"})

        # Validate category name matches
        if categories[from_index].get("category_name") != category_name:
            return jsonify({"success": False, "error": "Category name mismatch"})

        # Perform the move
        category_to_move = categories.pop(from_index)
        categories.insert(to_index, category_to_move)

        # Update the data
        services_data["categories"] = categories

        # Save the updated data
        with open(services_file_path, "w", encoding="utf-8") as file:
            yaml.dump(services_data, file, default_flow_style=False, allow_unicode=True)

        direction = "up" if to_index < from_index else "down"
        logger.info(
            f"Successfully moved category '{category_name}' {direction} from position {from_index} to {to_index}"
        )
        return jsonify(
            {
                "success": True,
                "message": f"Category '{category_name}' moved {direction} successfully",
            }
        )

    except Exception as e:
        logger.error(f"Error in move_category: {e}")
        return jsonify({"success": False, "error": f"Internal server error: {str(e)}"})
