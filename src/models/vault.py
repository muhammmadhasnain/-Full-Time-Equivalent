"""
Vault model for AI Employee Foundation
Implements the vault structure and operations with local-first architecture
"""
import os
import shutil
import tempfile
import sys
import threading
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from functools import lru_cache
import asyncio
import portalocker  # For file locking

# Add the src directory to the path so we can import modules
current_dir = Path(__file__).parent
src_dir = current_dir.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from lib.constants import VAULT_FOLDERS
from lib.exceptions import VaultError
from lib.utils import ensure_directory_exists


class Vault:
    """
    Represents the Obsidian vault structure for the AI Employee Foundation.
    Manages the folder structure and basic operations for the automation system.
    """

    def __init__(self, vault_path: str):
        """
        Initialize the vault with the given path.

        Args:
            vault_path: Path to the vault directory
        """
        self.vault_path = Path(vault_path)
        self.logger = logging.getLogger(__name__)
        self._folder_paths_cache = {}  # Cache for folder paths
        self._lock = threading.Lock()  # Thread lock for critical operations

        # Validate vault path
        if not self.vault_path.is_absolute():
            raise VaultError(f"Vault path must be absolute: {vault_path}")

    def initialize(self) -> bool:
        """
        Initialize the vault structure by creating all required directories.

        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Create the main vault directory if it doesn't exist
            ensure_directory_exists(str(self.vault_path))

            # Create all required subdirectories
            # Using a single loop to reduce function calls
            folder_paths = [self.vault_path / folder_name for folder_name in VAULT_FOLDERS]
            for folder_path in folder_paths:
                ensure_directory_exists(str(folder_path))
                # Pre-populate cache
                self._folder_paths_cache[folder_path.name] = folder_path

            # Create the dashboard file
            dashboard_path = self.vault_path / "Dashboard.md"
            if not dashboard_path.exists():
                self._create_dashboard_file(dashboard_path)

            self.logger.info(f"Vault initialized successfully at {self.vault_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize vault: {str(e)}")
            raise VaultError(f"Failed to initialize vault: {str(e)}")

    def _create_dashboard_file(self, dashboard_path: Path) -> None:
        """
        Create the initial Dashboard.md file with basic content.

        Args:
            dashboard_path: Path where the dashboard file should be created
        """
        # Since get_current_iso_timestamp is already imported at the top of the file,
        # we can use it directly without importing again
        from lib.utils import get_current_iso_timestamp

        dashboard_content = f"""# AI Employee Dashboard

## System Status
- **Active**: Active
- **Last Updated**: {get_current_iso_timestamp()}

## Metrics
- **Total Actions**: 0
- **Pending Approvals**: 0
- **Processed Today**: 0

## Recent Activity
- Vault initialized on {get_current_iso_timestamp()}

## System Health
- Vault: Operational
- Storage: Available

## Watchers
- **Gmail Watcher**: Not Started
- **File System Watcher**: Not Started

## Claude Integration
- **Connected**: Not Connected
"""
        with open(dashboard_path, 'w', encoding='utf-8') as f:
            f.write(dashboard_content)

    def exists(self) -> bool:
        """
        Check if the vault exists (directory exists and contains required folders).

        Returns:
            True if vault exists and is properly structured, False otherwise
        """
        if not self.vault_path.exists():
            return False

        # Use all() to short-circuit if any folder doesn't exist
        return all(
            (self.vault_path / folder_name).exists() and (self.vault_path / folder_name).is_dir()
            for folder_name in VAULT_FOLDERS
        ) and (self.vault_path / "Dashboard.md").exists()

    @lru_cache(maxsize=16)  # Cache frequently accessed folder paths
    def get_folder_path(self, folder_name: str) -> Optional[Path]:
        """
        Get the full path for a specific vault folder.

        Args:
            folder_name: Name of the folder to get path for

        Returns:
            Path object for the folder, or None if folder doesn't exist
        """
        if folder_name not in VAULT_FOLDERS:
            self.logger.warning(f"Folder '{folder_name}' is not a standard vault folder")

        folder_path = self.vault_path / folder_name
        return folder_path if folder_path.exists() else None

    def get_all_files_in_folder(self, folder_name: str) -> List[Path]:
        """
        Get all files in a specific vault folder.

        Args:
            folder_name: Name of the folder to list files from

        Returns:
            List of Path objects representing files in the folder
        """
        folder_path = self.get_folder_path(folder_name)
        if not folder_path:
            raise VaultError(f"Folder '{folder_name}' does not exist in vault")

        # Use list comprehension with generator for better performance
        return [f for f in folder_path.iterdir() if f.is_file()]

    def move_file(self, source_folder: str, dest_folder: str, filename: str) -> bool:
        """
        Move a file from one vault folder to another using atomic operations.

        Args:
            source_folder: Source folder name
            dest_folder: Destination folder name
            filename: Name of the file to move

        Returns:
            True if move was successful, False otherwise
        """
        source_path = self.get_folder_path(source_folder)
        dest_path = self.get_folder_path(dest_folder)

        if not source_path:
            raise VaultError(f"Source folder '{source_folder}' does not exist")
        if not dest_path:
            raise VaultError(f"Destination folder '{dest_folder}' does not exist")

        source_file = source_path / filename
        dest_file = dest_path / filename

        if not source_file.exists():
            raise VaultError(f"Source file '{filename}' does not exist in '{source_folder}'")

        try:
            # Acquire thread lock for critical section
            with self._lock:
                # Perform atomic move operation using temporary file
                temp_dest = dest_file.with_suffix(dest_file.suffix + '.tmp')
                
                # Copy the file to a temporary location in the destination
                shutil.copy2(str(source_file), str(temp_dest))
                
                # Rename the temporary file to the final destination (atomic on most systems)
                temp_dest.rename(dest_file)
                
                # Remove the source file
                source_file.unlink()
                
                # Invalidate cache for the affected folders
                self.get_folder_path.cache_clear()
                
                self.logger.info(f"Moved file '{filename}' from '{source_folder}' to '{dest_folder}'")
                return True
        except Exception as e:
            self.logger.error(f"Failed to move file '{filename}': {str(e)}")
            return False

    def copy_file(self, source_folder: str, dest_folder: str, filename: str) -> bool:
        """
        Copy a file from one vault folder to another using atomic operations.

        Args:
            source_folder: Source folder name
            dest_folder: Destination folder name
            filename: Name of the file to copy

        Returns:
            True if copy was successful, False otherwise
        """
        source_path = self.get_folder_path(source_folder)
        dest_path = self.get_folder_path(dest_folder)

        if not source_path:
            raise VaultError(f"Source folder '{source_folder}' does not exist")
        if not dest_path:
            raise VaultError(f"Destination folder '{dest_folder}' does not exist")

        source_file = source_path / filename
        dest_file = dest_path / filename

        if not source_file.exists():
            raise VaultError(f"Source file '{filename}' does not exist in '{source_folder}'")

        try:
            # Acquire thread lock for critical section
            with self._lock:
                # Perform atomic copy operation using temporary file
                temp_dest = dest_file.with_suffix(dest_file.suffix + '.tmp')
                
                # Copy the file to a temporary location in the destination
                shutil.copy2(str(source_file), str(temp_dest))
                
                # Rename the temporary file to the final destination (atomic on most systems)
                temp_dest.rename(dest_file)
                
                self.logger.info(f"Copied file '{filename}' from '{source_folder}' to '{dest_folder}'")
                return True
        except Exception as e:
            self.logger.error(f"Failed to copy file '{filename}': {str(e)}")
            return False

    def write_file_atomic(self, folder_name: str, filename: str, content: str) -> bool:
        """
        Write content to a file atomically using a temporary file and rename operation.

        Args:
            folder_name: Name of the folder to write the file to
            filename: Name of the file to write
            content: Content to write to the file

        Returns:
            True if write was successful, False otherwise
        """
        folder_path = self.get_folder_path(folder_name)
        if not folder_path:
            raise VaultError(f"Folder '{folder_name}' does not exist in vault")

        target_file = folder_path / filename
        
        try:
            # Acquire thread lock for critical section
            with self._lock:
                # Write to a temporary file first
                temp_file = target_file.with_suffix(target_file.suffix + '.tmp')
                
                # Write content to temporary file
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                # Atomically rename the temporary file to the target file
                temp_file.rename(target_file)
                
                self.logger.info(f"Atomically wrote file '{filename}' to '{folder_name}'")
                return True
        except Exception as e:
            self.logger.error(f"Failed to atomically write file '{filename}': {str(e)}")
            # Clean up temporary file if it exists
            temp_file = target_file.with_suffix(target_file.suffix + '.tmp')
            if temp_file.exists():
                temp_file.unlink()
            return False

    def read_file_with_lock(self, folder_name: str, filename: str) -> Optional[str]:
        """
        Read a file with file-level locking to prevent corruption during concurrent access.

        Args:
            folder_name: Name of the folder containing the file
            filename: Name of the file to read

        Returns:
            Content of the file as a string, or None if file doesn't exist
        """
        folder_path = self.get_folder_path(folder_name)
        if not folder_path:
            raise VaultError(f"Folder '{folder_name}' does not exist in vault")

        file_path = folder_path / filename
        if not file_path.exists():
            return None

        try:
            # Use portalocker to acquire a shared lock while reading
            with open(file_path, 'r', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.SHARED)
                content = f.read()
                portalocker.unlock(f)
                return content
        except Exception as e:
            self.logger.error(f"Failed to read file '{filename}' with lock: {str(e)}")
            return None

    def write_file_with_lock(self, folder_name: str, filename: str, content: str) -> bool:
        """
        Write to a file with file-level locking to prevent corruption during concurrent access.

        Args:
            folder_name: Name of the folder containing the file
            filename: Name of the file to write to
            content: Content to write to the file

        Returns:
            True if write was successful, False otherwise
        """
        folder_path = self.get_folder_path(folder_name)
        if not folder_path:
            raise VaultError(f"Folder '{folder_name}' does not exist in vault")

        file_path = folder_path / filename
        
        try:
            # Use portalocker to acquire an exclusive lock while writing
            with open(file_path, 'w', encoding='utf-8') as f:
                portalocker.lock(f, portalocker.EXCLUSIVE)
                f.write(content)
                portalocker.unlock(f)
                
            self.logger.info(f"Wrote file '{filename}' to '{folder_name}' with lock")
            return True
        except Exception as e:
            self.logger.error(f"Failed to write file '{filename}' with lock: {str(e)}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vault contents.

        Returns:
            Dictionary containing vault statistics
        """
        stats = {}

        # Count files in each folder using optimized approach
        for folder_name in VAULT_FOLDERS:
            folder_path = self.get_folder_path(folder_name)
            if folder_path:
                # Use generator expression for memory efficiency
                file_count = sum(1 for f in folder_path.iterdir() if f.is_file())
                stats[f"{folder_name.lower()}_count"] = file_count
            else:
                stats[f"{folder_name.lower()}_count"] = 0

        # Total actions would be the sum of certain folders
        stats['total_actions'] = (
            stats.get('inbox_count', 0) +
            stats.get('needs_action_count', 0) +
            stats.get('done_count', 0)
        )

        # Pending approvals
        stats['pending_approvals'] = stats.get('pending_approval_count', 0)

        return stats

    async def get_stats_async(self) -> Dict[str, Any]:
        """
        Asynchronously get statistics about the vault contents.

        Returns:
            Dictionary containing vault statistics
        """
        stats = {}

        # Count files in each folder asynchronously
        tasks = []
        for folder_name in VAULT_FOLDERS:
            folder_path = self.get_folder_path(folder_name)
            if folder_path:
                task = asyncio.create_task(self._count_files_async(folder_path))
                tasks.append((f"{folder_name.lower()}_count", task))
            else:
                stats[f"{folder_name.lower()}_count"] = 0

        # Gather results
        results = await asyncio.gather(*[task for _, task in tasks])
        
        # Assign results to stats
        for i, (key, _) in enumerate(tasks):
            stats[key] = results[i]

        # Total actions would be the sum of certain folders
        stats['total_actions'] = (
            stats.get('inbox_count', 0) +
            stats.get('needs_action_count', 0) +
            stats.get('done_count', 0)
        )

        # Pending approvals
        stats['pending_approvals'] = stats.get('pending_approval_count', 0)

        return stats

    async def _count_files_async(self, folder_path: Path) -> int:
        """
        Asynchronously count files in a folder.

        Args:
            folder_path: Path to the folder to count files in

        Returns:
            Number of files in the folder
        """
        return sum(1 for f in folder_path.iterdir() if f.is_file())

    def get_file_info(self, folder_name: str, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get information about a specific file in a vault folder.

        Args:
            folder_name: Name of the folder containing the file
            filename: Name of the file to get info for

        Returns:
            Dictionary with file information or None if file doesn't exist
        """
        folder_path = self.get_folder_path(folder_name)
        if not folder_path:
            return None

        file_path = folder_path / filename
        if not file_path.exists():
            return None

        try:
            stat = file_path.stat()
            return {
                'name': file_path.name,
                'size': stat.st_size,
                'created': stat.st_ctime,
                'modified': stat.st_mtime,
                'is_file': file_path.is_file(),
                'extension': file_path.suffix
            }
        except OSError:
            return None