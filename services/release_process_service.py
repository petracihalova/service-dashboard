"""
Service for managing production release processes.

This service handles the lifecycle of release processes, including:
- Creating new processes
- Tracking process steps
- Validating commit ranges
- Managing process state (active, stale, completed)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ReleaseProcessService:
    """Service for managing release processes."""

    def __init__(self, data_dir: str = "data/release_processes"):
        """
        Initialize the release process service.

        Args:
            data_dir: Directory to store process JSON files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def create_process(
        self,
        deployment_name: str,
        from_commit: str,
        to_commit: str,
        enable_jira: bool = True,
        release_notes_data: Dict = None,
    ) -> Dict:
        """
        Create a new release process.

        Args:
            deployment_name: Name of the deployment
            from_commit: Starting commit (full SHA)
            to_commit: Target commit (full SHA)
            enable_jira: Whether to include JIRA ticket step
            release_notes_data: Release notes data if already generated

        Returns:
            Process dictionary

        Raises:
            ValueError: If a process with this commit range already exists
        """
        # Check for existing process with same commit range
        if not self.check_unique_range(deployment_name, from_commit, to_commit):
            raise ValueError(
                f"A process already exists for {deployment_name} "
                f"with commits {from_commit[:7]}...{to_commit[:7]}"
            )

        # Generate process ID
        process_id = self._generate_process_id(deployment_name, from_commit, to_commit)

        # Determine if release notes step should be auto-completed
        release_notes_status = "pending"
        release_notes_timestamp = None
        release_notes_step_data = {}
        pr_count = 0

        if release_notes_data:
            # Auto-complete Step 1 if release notes are already generated
            release_notes_status = "completed"
            release_notes_timestamp = datetime.now().isoformat()
            release_notes_step_data = {
                "commit": to_commit,
                "pr_count": release_notes_data.get("pr_count", 0),
                "release_notes_url": release_notes_data.get("url"),
            }
            pr_count = release_notes_data.get("pr_count", 0)

        # Create process structure
        process = {
            "process_id": process_id,
            "deployment_name": deployment_name,
            "created_at": datetime.now().isoformat(),
            "status": "active",
            "commit_range": {
                "from_commit": from_commit,
                "to_commit": to_commit,
                "is_valid": True,
            },
            "steps": {
                "release_notes": {
                    "status": release_notes_status,
                    "timestamp": release_notes_timestamp,
                    "data": release_notes_step_data,
                },
                "jira_ticket": {
                    "status": "pending",
                    "optional": True,
                    "enabled": enable_jira,
                    "timestamp": None,
                    "data": {},
                },
                "google_doc": {"status": "pending", "timestamp": None, "data": {}},
                "app_interface_mr": {
                    "status": "pending",
                    "timestamp": None,
                    "data": {},
                },
            },
            "metadata": {
                "pr_count": pr_count,
                "last_validated": datetime.now().isoformat(),
                "reviewer": "reviewer",
            },
        }

        # Save to file
        self._save_process(process)
        logger.info(f"Created release process: {process_id}")

        return process

    def get_process(self, process_id: str) -> Optional[Dict]:
        """
        Get a process by ID.

        Args:
            process_id: Process ID

        Returns:
            Process dictionary or None if not found
        """
        file_path = self.data_dir / f"{process_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading process {process_id}: {e}")
            return None

    def get_all_processes(self) -> List[Dict]:
        """
        Get all processes.

        Returns:
            List of process dictionaries
        """
        processes = []
        for file_path in self.data_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    process = json.load(f)
                    processes.append(process)
            except Exception as e:
                logger.error(f"Error loading process from {file_path}: {e}")

        # Sort by created_at descending
        processes.sort(key=lambda p: p.get("created_at", ""), reverse=True)
        return processes

    def get_active_processes(self, deployment_name: Optional[str] = None) -> List[Dict]:
        """
        Get all active processes.

        Args:
            deployment_name: Filter by deployment name (optional)

        Returns:
            List of active process dictionaries
        """
        processes = self.get_all_processes()
        active = [p for p in processes if p.get("status") == "active"]

        if deployment_name:
            active = [p for p in active if p.get("deployment_name") == deployment_name]

        return active

    def get_stale_processes(self) -> List[Dict]:
        """
        Get all stale processes.

        Returns:
            List of stale process dictionaries
        """
        processes = self.get_all_processes()
        return [p for p in processes if p.get("status") == "stale"]

    def update_step(
        self, process_id: str, step_name: str, status: str, data: Dict = None
    ) -> bool:
        """
        Update a process step.

        Args:
            process_id: Process ID
            step_name: Step name (release_notes, jira_ticket, google_doc, app_interface_mr)
            status: Step status (pending, completed, failed)
            data: Step data to merge

        Returns:
            True if successful, False otherwise
        """
        process = self.get_process(process_id)
        if not process:
            logger.error(f"Process {process_id} not found")
            return False

        if step_name not in process["steps"]:
            logger.error(f"Invalid step name: {step_name}")
            return False

        # Update step
        process["steps"][step_name]["status"] = status
        if status == "completed":
            process["steps"][step_name]["timestamp"] = datetime.now().isoformat()

        if data:
            process["steps"][step_name]["data"].update(data)

        # Save
        self._save_process(process)
        logger.info(f"Updated step {step_name} for process {process_id}")

        return True

    def delete_process(self, process_id: str) -> bool:
        """
        Delete a process.

        Args:
            process_id: Process ID

        Returns:
            True if successful, False otherwise
        """
        file_path = self.data_dir / f"{process_id}.json"
        if not file_path.exists():
            return False

        try:
            file_path.unlink()
            logger.info(f"Deleted process: {process_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting process {process_id}: {e}")
            return False

    def validate_process(self, process_id: str, commit_list: List[str]) -> bool:
        """
        Validate that a process's commit range is still valid.

        Args:
            process_id: Process ID
            commit_list: List of current commit SHAs for the deployment

        Returns:
            True if valid, False if stale
        """
        process = self.get_process(process_id)
        if not process:
            return False

        from_commit = process["commit_range"]["from_commit"]
        to_commit = process["commit_range"]["to_commit"]

        # Check if both commits exist
        if from_commit not in commit_list or to_commit not in commit_list:
            process["status"] = "stale"
            process["commit_range"]["is_valid"] = False
            process["metadata"]["stale_reason"] = "Commit(s) no longer in history"
            process["metadata"]["last_validated"] = datetime.now().isoformat()
            self._save_process(process)
            logger.warning(f"Process {process_id} marked as stale")
            return False

        # Update validation timestamp
        process["metadata"]["last_validated"] = datetime.now().isoformat()
        self._save_process(process)

        return True

    def check_unique_range(
        self, deployment_name: str, from_commit: str, to_commit: str
    ) -> bool:
        """
        Check if a commit range is unique (no active process exists for it).

        Args:
            deployment_name: Deployment name
            from_commit: Starting commit
            to_commit: Target commit

        Returns:
            True if unique, False if exists
        """
        processes = self.get_active_processes(deployment_name)
        for p in processes:
            if (
                p["commit_range"]["from_commit"] == from_commit
                and p["commit_range"]["to_commit"] == to_commit
            ):
                return False
        return True

    def get_process_progress(self, process_id: str) -> Dict:
        """
        Get process progress summary.

        Args:
            process_id: Process ID

        Returns:
            Dictionary with progress info (completed, total, percentage)
        """
        process = self.get_process(process_id)
        if not process:
            return {"completed": 0, "total": 0, "percentage": 0}

        steps = process["steps"]
        total = len(steps)
        completed = sum(
            1
            for step in steps.values()
            if step["status"] == "completed"
            or (step.get("optional") and not step.get("enabled"))
        )

        return {
            "completed": completed,
            "total": total,
            "percentage": int((completed / total) * 100) if total > 0 else 0,
        }

    def generate_slack_message(self, process_id: str) -> str:
        """
        Generate a Slack message for the release process.

        Args:
            process_id: Process ID

        Returns:
            Formatted Slack message
        """
        process = self.get_process(process_id)
        if not process:
            return ""

        deployment = process["deployment_name"].upper()
        reviewer = process.get("metadata", {}).get("reviewer", "reviewer")

        message = f":alert-siren: {deployment} prod release\n"

        # Add Google Doc link with HTML-style clickable text
        google_doc = process["steps"]["google_doc"]
        if google_doc["status"] == "completed" and google_doc["data"].get("doc_url"):
            doc_url = google_doc["data"]["doc_url"]
            message += f'• <a href="{doc_url}">release notes</a>\n'

        message += f"• please @{reviewer} can you take a look? :heart: :hero:"

        return message

    def _generate_process_id(
        self, deployment_name: str, from_commit: str, to_commit: str
    ) -> str:
        """
        Generate a unique process ID.

        Args:
            deployment_name: Deployment name
            from_commit: Starting commit
            to_commit: Target commit

        Returns:
            Process ID
        """
        return f"{deployment_name}-{from_commit[:7]}-{to_commit[:7]}"

    def _save_process(self, process: Dict) -> None:
        """
        Save a process to disk.

        Args:
            process: Process dictionary
        """
        process_id = process["process_id"]
        file_path = self.data_dir / f"{process_id}.json"

        try:
            with open(file_path, "w") as f:
                json.dump(process, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving process {process_id}: {e}")
            raise


# Global instance
release_process_service = ReleaseProcessService()
