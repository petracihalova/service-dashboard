"""
Backup Service for managing data folder backups.

Handles creating, listing, deleting, and switching between backups.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import config

logger = logging.getLogger(__name__)

BACKUPS_DIR = config.base_dir / "backups"
BACKUP_METADATA_FILE = "backup_metadata.json"
MAX_BACKUPS = 10


class BackupService:
    """Service for managing data folder backups."""

    def __init__(self):
        """Initialize the backup service."""
        # Ensure backups directory exists
        BACKUPS_DIR.mkdir(exist_ok=True)

        # Restore backup state if exists
        self._restore_backup_state_on_startup()

    def create_backup(self, description: Optional[str] = None) -> Dict:
        """
        Create a backup of the current data folder.

        Args:
            description: Optional custom description for the backup

        Returns:
            Dict with backup info (id, timestamp, description, path)
        """
        # Check if we're already at max backups
        backups = self.list_backups()
        if len(backups) >= MAX_BACKUPS:
            raise ValueError(
                f"Maximum number of backups ({MAX_BACKUPS}) reached. "
                "Please delete old backups before creating new ones."
            )

        # Generate backup ID and path
        timestamp = datetime.now()
        backup_id = timestamp.strftime("%Y%m%d_%H%M%S")
        backup_path = BACKUPS_DIR / f"backup_{backup_id}"

        # Check if already exists (shouldn't happen but just in case)
        if backup_path.exists():
            raise ValueError(f"Backup with ID {backup_id} already exists")

        try:
            # Copy the entire data folder
            shutil.copytree(config.DATA_PATH_FOLDER, backup_path)

            # Copy the .env file if it exists
            env_file = config.base_dir / ".env"
            env_backed_up = False
            if env_file.exists():
                try:
                    shutil.copy2(env_file, backup_path / ".env")
                    env_backed_up = True
                    logger.info(f"Backed up .env file for backup {backup_id}")
                except Exception as e:
                    logger.warning(f"Failed to backup .env file: {e}")

            # Create metadata
            metadata = {
                "id": backup_id,
                "timestamp": timestamp.isoformat(),
                "description": description
                or f"Backup {timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
                "path": str(backup_path),
                "size_mb": self._get_folder_size(backup_path),
                "env_backed_up": env_backed_up,
            }

            # Save metadata file
            metadata_file = backup_path / BACKUP_METADATA_FILE
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)

            logger.info(
                f"Created backup: {backup_id} - {metadata['description']} "
                f"(env: {env_backed_up})"
            )
            return metadata

        except Exception as e:
            # Clean up partial backup if something went wrong
            if backup_path.exists():
                shutil.rmtree(backup_path)
            logger.error(f"Failed to create backup: {e}")
            raise

    def list_backups(self) -> List[Dict]:
        """
        List all available backups.

        Returns:
            List of backup metadata dicts, sorted by timestamp (newest first)
        """
        backups = []

        if not BACKUPS_DIR.exists():
            return backups

        for backup_dir in BACKUPS_DIR.iterdir():
            if backup_dir.is_dir() and backup_dir.name.startswith("backup_"):
                metadata_file = backup_dir / BACKUP_METADATA_FILE
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                            backups.append(metadata)
                    except Exception as e:
                        logger.error(f"Failed to load metadata for {backup_dir}: {e}")

        # Sort by timestamp, newest first
        backups.sort(key=lambda x: x["timestamp"], reverse=True)
        return backups

    def get_backup(self, backup_id: str) -> Optional[Dict]:
        """
        Get metadata for a specific backup.

        Args:
            backup_id: The backup ID

        Returns:
            Backup metadata dict or None if not found
        """
        backup_path = BACKUPS_DIR / f"backup_{backup_id}"
        metadata_file = backup_path / BACKUP_METADATA_FILE

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load backup metadata: {e}")
            return None

    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a backup.

        Args:
            backup_id: The backup ID to delete

        Returns:
            True if deleted successfully, False otherwise
        """
        backup_path = BACKUPS_DIR / f"backup_{backup_id}"

        if not backup_path.exists():
            logger.warning(f"Backup {backup_id} not found")
            return False

        # Check if this backup is currently active
        current_backup = self.get_current_backup()
        if current_backup and current_backup == backup_id:
            raise ValueError("Cannot delete the currently active backup")

        try:
            shutil.rmtree(backup_path)
            logger.info(f"Deleted backup: {backup_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False

    def switch_to_backup(self, backup_id: str) -> bool:
        """
        Switch to viewing a backup (read-only mode).

        Args:
            backup_id: The backup ID to switch to

        Returns:
            True if switched successfully
        """
        backup_path = BACKUPS_DIR / f"backup_{backup_id}"

        if not backup_path.exists():
            raise ValueError(f"Backup {backup_id} not found")

        # Update the DATA_PATH_FOLDER and all derived paths
        self._update_config_paths(backup_path)

        # Store current backup info in a temp file
        state_file = config.base_dir / ".backup_state"
        state = {"current_backup": backup_id, "mode": "backup"}

        with open(state_file, "w") as f:
            json.dump(state, f)

        logger.info(f"Switched to backup mode: {backup_id}")
        return True

    def restore_to_live(self) -> bool:
        """
        Restore to live data mode (exit backup mode).

        Returns:
            True if restored successfully
        """
        # Restore original data path and all derived paths
        live_data_path = config.base_dir / "data"
        self._update_config_paths(live_data_path)

        # Remove backup state file
        state_file = config.base_dir / ".backup_state"
        if state_file.exists():
            state_file.unlink()

        logger.info("Restored to live data mode")
        return True

    def get_current_backup(self) -> Optional[str]:
        """
        Get the currently active backup ID, if any.

        Returns:
            Backup ID if in backup mode, None if in live mode
        """
        state_file = config.base_dir / ".backup_state"
        if not state_file.exists():
            return None

        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                return state.get("current_backup")
        except Exception as e:
            logger.error(f"Failed to read backup state: {e}")
            return None

    def is_backup_mode(self) -> bool:
        """
        Check if currently in backup mode.

        Returns:
            True if viewing a backup, False if in live mode
        """
        return self.get_current_backup() is not None

    def restore_backup(self, backup_id: str) -> Dict:
        """
        Restore a backup to live mode.

        This will:
        1. Create an automatic backup of current live data
        2. Clear the data folder (except excluded files)
        3. Copy files from the selected backup to data folder
        4. Restore the .env file from the backup

        Args:
            backup_id: The backup ID to restore

        Returns:
            Dict with info about the automatic backup created

        Raises:
            ValueError: If backup not found or in backup mode
        """
        # Check if we're in backup mode
        if self.is_backup_mode():
            raise ValueError(
                "Cannot restore backup while in backup viewing mode. "
                "Please restore to live mode first."
            )

        # Check if backup exists
        backup_path = BACKUPS_DIR / f"backup_{backup_id}"
        if not backup_path.exists():
            raise ValueError(f"Backup {backup_id} not found")

        # Files and folders to exclude from deletion
        EXCLUDE_FILES = {"oauth_credentials.json", "token.json"}
        EXCLUDE_FOLDERS = {"test_data"}

        try:
            # Step 1: Create automatic backup of current live data
            timestamp = datetime.now()
            auto_description = f"Auto backup before restore - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
            auto_backup = self.create_backup(description=auto_description)
            logger.info(f"Created automatic backup: {auto_backup['id']}")

            # Step 2: Clear data folder (except excluded files/folders)
            data_path = Path(config.DATA_PATH_FOLDER)
            for item in data_path.iterdir():
                # Skip excluded folders
                if item.is_dir() and item.name in EXCLUDE_FOLDERS:
                    logger.info(f"Skipping excluded folder: {item.name}")
                    continue

                # Skip excluded files
                if item.is_file() and item.name in EXCLUDE_FILES:
                    logger.info(f"Skipping excluded file: {item.name}")
                    continue

                # Remove the item
                if item.is_dir():
                    shutil.rmtree(item)
                    logger.info(f"Removed folder: {item.name}")
                else:
                    item.unlink()
                    logger.info(f"Removed file: {item.name}")

            # Step 3: Copy files from backup to data folder
            for item in backup_path.iterdir():
                # Skip metadata file, .env file (handle separately), and excluded items
                if item.name == BACKUP_METADATA_FILE:
                    continue
                if item.name == ".env":
                    continue
                if item.is_dir() and item.name in EXCLUDE_FOLDERS:
                    continue
                if item.is_file() and item.name in EXCLUDE_FILES:
                    continue

                dest = data_path / item.name

                if item.is_dir():
                    shutil.copytree(item, dest)
                    logger.info(f"Restored folder: {item.name}")
                else:
                    shutil.copy2(item, dest)
                    logger.info(f"Restored file: {item.name}")

            # Step 4: Restore .env file if it exists in the backup
            env_backup = backup_path / ".env"
            if env_backup.exists():
                env_dest = config.base_dir / ".env"
                shutil.copy2(env_backup, env_dest)
                logger.info("Restored .env file")

            logger.info(f"Successfully restored backup {backup_id} to live mode")

            return {"success": True, "backup_id": backup_id, "auto_backup": auto_backup}

        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            raise

    def _restore_backup_state_on_startup(self):
        """
        Check for backup state on startup and restore config paths if needed.
        """
        state_file = config.base_dir / ".backup_state"
        if not state_file.exists():
            return

        try:
            with open(state_file, "r") as f:
                state = json.load(f)
                backup_id = state.get("current_backup")

                if backup_id:
                    backup_path = BACKUPS_DIR / f"backup_{backup_id}"
                    if backup_path.exists():
                        self._update_config_paths(backup_path)
                        logger.info(f"Restored backup state on startup: {backup_id}")
                    else:
                        logger.warning(
                            f"Backup {backup_id} from state file not found, removing state file"
                        )
                        state_file.unlink()
        except Exception as e:
            logger.error(f"Failed to restore backup state on startup: {e}")
            # Remove corrupted state file
            if state_file.exists():
                state_file.unlink()

    def _update_config_paths(self, data_path: Path):
        """
        Update all config paths to point to the specified data directory.

        Args:
            data_path: Path to the data directory (live or backup)
        """
        config.DATA_PATH_FOLDER = data_path

        # Update all derived file paths
        config.SERVICES_LINKS_PATH = data_path / "services_links.yml"

        config.GH_OPEN_PR_FILE = data_path / "github_pr_list.json"
        config.GH_MERGED_PR_FILE = data_path / "github_merged_pr_list.json"
        config.GH_CLOSED_PR_FILE = data_path / "github_closed_pr_list.json"

        config.GL_OPEN_PR_FILE = data_path / "gitlab_pr_list.json"
        config.GL_MERGED_PR_FILE = data_path / "gitlab_merged_pr_list.json"
        config.GL_CLOSED_PR_FILE = data_path / "gitlab_closed_pr_list.json"

        config.DEPLOYMENTS_FILE = data_path / "deployments_list.json"

        config.APP_INTERFACE_OPEN_MR_FILE = (
            data_path / "app_interface_open_mr_list.json"
        )
        config.APP_INTERFACE_MERGED_MR_FILE = (
            data_path / "app_interface_merged_mr_list.json"
        )
        config.APP_INTERFACE_CLOSED_MR_FILE = (
            data_path / "app_interface_closed_mr_list.json"
        )

        config.JIRA_OPEN_TICKETS_FILE = data_path / "jira_open_tickets.json"
        config.JIRA_REPORTED_TICKETS_FILE = data_path / "jira_reported_tickets.json"
        config.JIRA_CLOSED_TICKETS_FILE = data_path / "jira_closed_tickets.json"

        logger.info(f"Updated config paths to: {data_path}")

    def _get_folder_size(self, folder_path: Path) -> float:
        """
        Calculate folder size in MB.

        Args:
            folder_path: Path to the folder

        Returns:
            Size in MB
        """
        total_size = 0
        for file in folder_path.rglob("*"):
            if file.is_file():
                total_size += file.stat().st_size
        return round(total_size / (1024 * 1024), 2)


# Singleton instance
backup_service = BackupService()
