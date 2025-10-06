"""Main transfer module for image synchronization."""

import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


class ImageTransfer:
    """Handle image file transfers based on configuration."""

    def __init__(self, config):
        """Initialize transfer handler."""
        self.config = config
        self.transferred_files: Set[Path] = set()
        self._setup_logging()
        self._detect_platform()

    def _detect_platform(self):
        """Detect platform and available transfer tools."""
        self.is_windows = sys.platform.startswith("win")
        self.has_rsync = self._check_command("rsync")
        self.has_ssh = self._check_command("ssh")

        if self.is_windows and not self.has_ssh:
            logger.warning("SSH not found. Please install OpenSSH Client or Git Bash")

    def _check_command(self, cmd: str) -> bool:
        """Check if a command is available."""
        try:
            result = subprocess.run(
                ["where" if sys.platform.startswith("win") else "which", cmd],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except:
            return False

    def _setup_logging(self):
        """Configure logging based on config."""
        # Always use ~/logs, not a path in the repo
        log_dir = Path.home() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)

        # Use a single log file with rotation
        log_file = log_dir / "image_transfer.log"

        # Configure rotating file handler
        handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config.get("log_rotation_size_mb", 10) * 1024 * 1024,
            backupCount=self.config.get("log_backup_count", 5),
        )

        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)

        # Clear any existing handlers and add our handler
        logger.handlers.clear()
        logger.addHandler(handler)

        # Also log to console when running interactively
        if sys.stdout.isatty():
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        logger.setLevel(getattr(logging, self.config.get("log_level", "INFO")))

        # Log startup
        logger.info("=" * 60)
        logger.info(f"Image Transfer starting - {datetime.now()}")
        logger.info(f"Watch path: {self.config['watch_path']}")
        logger.info(
            f"Remote: {self.config['remote_user']}@{self.config['remote_host']}:{self.config['remote_base_path']}"
        )

    def find_new_files(self) -> List[Path]:
        """Find new files matching configured patterns."""
        watch_path = Path(self.config["watch_path"])

        if not watch_path.exists():
            logger.error(f"Watch path does not exist: {watch_path}")
            return []

        new_files = []
        patterns = self.config.get("file_patterns", ["*.fits"])
        exclude_patterns = self.config.get("exclude_patterns", [])
        min_age = self.config.get("min_file_age_seconds", 2)
        cutoff_time = datetime.now() - timedelta(seconds=min_age)

        for pattern in patterns:
            for file_path in watch_path.rglob(pattern):
                # Skip if already transferred
                if file_path in self.transferred_files:
                    continue

                # Skip excluded patterns
                if any(file_path.match(exc) for exc in exclude_patterns):
                    continue

                # Check file age (ensure write is complete)
                try:
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime > cutoff_time:
                        continue
                except (OSError, IOError):
                    continue

                new_files.append(file_path)

        return new_files

    def build_remote_path(self, local_file: Path) -> str:
        """Build the remote destination path."""
        watch_path = Path(self.config["watch_path"])
        relative_path = local_file.relative_to(watch_path)

        # Extract date folder if present (e.g., 20251006)
        parts = relative_path.parts
        remote_base = self.config["remote_base_path"]

        # Add camera name if configured
        camera_name = self.config.get("camera_name")

        if camera_name and parts:
            # Check if first part looks like a date folder
            if len(parts[0]) == 8 and parts[0].isdigit():
                # Insert camera name after date folder
                remote_parts = [remote_base, parts[0], camera_name] + list(parts[1:])
            else:
                # Add camera name at beginning
                remote_parts = [remote_base, camera_name] + list(parts)
        else:
            remote_parts = [remote_base] + list(parts)

        # Use forward slashes for remote path (even from Windows)
        return "/".join(str(p) for p in remote_parts)

    def transfer_file(self, local_file: Path) -> bool:
        """Transfer a single file to remote destination."""
        remote_path = self.build_remote_path(local_file)
        remote_host = self.config["remote_host"]
        remote_user = self.config["remote_user"]

        # Handle local transfers
        if remote_host in ["localhost", "127.0.0.1", "::1"]:
            return self._local_transfer(local_file, remote_path)

        # Determine transfer method
        method = self.config.get("transfer_method", "auto")

        if method == "auto":
            if self.has_rsync:
                method = "rsync"
            elif self.has_ssh:
                method = "scp"
            else:
                logger.error("No suitable transfer method available")
                return False

        # Create remote directory
        remote_dir = "/".join(remote_path.split("/")[:-1])
        if not self._create_remote_directory(remote_user, remote_host, remote_dir):
            return False

        # Transfer file
        success = False
        attempts = self.config.get("retry_attempts", 3)
        delay = self.config.get("retry_delay", 5)

        for attempt in range(attempts):
            if attempt > 0:
                logger.info(f"Retry attempt {attempt + 1}/{attempts}")
                time.sleep(delay)

            if method == "rsync":
                success = self._rsync_transfer(
                    local_file, remote_user, remote_host, remote_path
                )
            elif method == "scp":
                success = self._scp_transfer(
                    local_file, remote_user, remote_host, remote_path
                )

            if success:
                break

        if success and self.config.get("verify_transfer", True):
            success = self._verify_transfer(
                local_file, remote_user, remote_host, remote_path
            )

        if success:
            self.transferred_files.add(local_file)
            logger.info(
                f"Successfully transferred: {local_file} -> {remote_host}:{remote_path}"
            )
        else:
            logger.error(f"Failed to transfer: {local_file}")

        return success

    def _local_transfer(self, local_file: Path, remote_path: str) -> bool:
        """Handle local file transfers."""
        dest_path = Path(remote_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            shutil.copy2(local_file, dest_path)
            return True
        except Exception as e:
            logger.error(f"Local transfer failed: {e}")
            return False

    def _create_remote_directory(self, user: str, host: str, directory: str) -> bool:
        """Create directory on remote host."""
        cmd = ["ssh", f"{user}@{host}", f"mkdir -p {directory}"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("transfer_timeout_seconds", 300),
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Failed to create remote directory: {e}")
            return False

    def _rsync_transfer(
        self, local_file: Path, user: str, host: str, remote_path: str
    ) -> bool:
        """Transfer file using rsync."""
        cmd = ["rsync", "-av"]

        if self.config.get("compression", False):
            cmd.append("-z")

        # Add Windows-specific options
        if self.is_windows:
            cmd.extend(["--no-perms", "--no-owner", "--no-group"])

        cmd.extend([str(local_file), f"{user}@{host}:{remote_path}"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("transfer_timeout_seconds", 300),
            )
            if result.returncode != 0:
                logger.debug(f"Rsync stderr: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Rsync transfer failed: {e}")
            return False

    def _scp_transfer(
        self, local_file: Path, user: str, host: str, remote_path: str
    ) -> bool:
        """Transfer file using scp."""
        cmd = ["scp"]

        if self.config.get("compression", False):
            cmd.append("-C")

        cmd.extend([str(local_file), f"{user}@{host}:{remote_path}"])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get("transfer_timeout_seconds", 300),
            )
            if result.returncode != 0:
                logger.debug(f"SCP stderr: {result.stderr}")
            return result.returncode == 0
        except Exception as e:
            logger.error(f"SCP transfer failed: {e}")
            return False

    def _verify_transfer(
        self, local_file: Path, user: str, host: str, remote_path: str
    ) -> bool:
        """Verify file was transferred correctly."""
        local_size = local_file.stat().st_size

        cmd = [
            "ssh",
            f"{user}@{host}",
            f"stat -c %s {remote_path} 2>/dev/null || stat -f %z {remote_path} 2>/dev/null",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            if result.returncode == 0:
                remote_size = int(result.stdout.strip())
                if local_size == remote_size:
                    return True
                else:
                    logger.error(
                        f"Size mismatch: local={local_size}, remote={remote_size}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Verification failed: {e}")

        return False

    def run(self):
        """Run a single transfer cycle."""
        logger.info("Starting transfer cycle")

        new_files = self.find_new_files()

        if not new_files:
            logger.debug("No new files to transfer")
            return

        logger.info(f"Found {len(new_files)} new files to transfer")

        # Transfer files (respecting parallel transfer limit)
        # For simplicity, we'll do sequential transfers in this version
        # For parallel transfers, you'd use concurrent.futures or asyncio

        success_count = 0
        for file_path in new_files:
            if self.transfer_file(file_path):
                success_count += 1

        logger.info(
            f"Transfer cycle complete: {success_count}/{len(new_files)} successful"
        )
