"""Base platform handler class."""

import logging
import shutil
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class BaseTransferHandler(ABC):
    """Base class for platform-specific transfer handlers."""

    def __init__(self, config):
        """Initialize the transfer handler."""
        self.config = config
        self.local_base_path = Path(config["watch_path"]).expanduser().resolve()
        self.remote_host = config["remote_host"]
        self.remote_user = config["remote_user"]

        # Handle tilde in remote path - expand it to absolute path
        remote_path = config["remote_base_path"]
        if remote_path.startswith("~"):
            # Replace ~ with /home/username for remote systems
            self.remote_base_path = remote_path.replace(
                "~", f"/home/{self.remote_user}"
            )
        else:
            self.remote_base_path = remote_path

        # Camera name for subdirectory (optional)
        self.camera_name = config.get("camera_name", None)

        self.transfer_method = config.get("transfer_method", "auto")
        self.verify_transfer = config.get("verify_transfer", True)
        self.setup_platform_specifics()

    @abstractmethod
    def setup_platform_specifics(self):
        """Set up platform-specific configurations."""
        pass

    def test_connection(self):
        """Test connection to remote host."""
        if self.transfer_method == "local" or self.remote_host in [
            "localhost",
            "127.0.0.1",
        ]:
            # Local transfer
            dest_path = Path(self.remote_base_path).expanduser()
            dest_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local transfer mode - destination: {dest_path}")
            if self.camera_name:
                logger.info(f"Camera subfolder: {self.camera_name}")
            return True

        try:
            # Test SSH connection and create base directory
            # First, get the actual home directory on the remote system
            cmd = [
                "ssh",
                "-o",
                "ConnectTimeout=10",
                f"{self.remote_user}@{self.remote_host}",
                "echo $HOME",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)

            if result.returncode == 0:
                remote_home = result.stdout.strip()
                logger.debug(f"Remote home directory: {remote_home}")

                # Update remote_base_path if it uses ~
                if self.config["remote_base_path"].startswith("~"):
                    self.remote_base_path = self.config["remote_base_path"].replace(
                        "~", remote_home
                    )
                    logger.info(f"Expanded remote path to: {self.remote_base_path}")

                if self.camera_name:
                    logger.info(f"Camera subfolder: {self.camera_name}")

                # Now create the base directory
                mkdir_cmd = [
                    "ssh",
                    "-o",
                    "ConnectTimeout=10",
                    f"{self.remote_user}@{self.remote_host}",
                    f"mkdir -p {self.remote_base_path}",
                ]

                result = subprocess.run(
                    mkdir_cmd, capture_output=True, text=True, timeout=15
                )

                if result.returncode == 0:
                    logger.info(f"Successfully connected to {self.remote_host}")
                    return True
                else:
                    logger.warning(f"Failed to create base directory: {result.stderr}")
                    return True  # Connection works, just directory creation failed
            else:
                logger.error(f"SSH connection failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"SSH connection to {self.remote_host} timed out")
            logger.info("Hint: Make sure SSH key authentication is set up:")
            logger.info(f"  ssh-keygen -t rsa -b 4096")
            logger.info(f"  ssh-copy-id {self.remote_user}@{self.remote_host}")
            return False
        except Exception as e:
            logger.error(f"Failed to test connection: {e}")
            return False

    def _build_remote_path(self, relative_path: Path) -> str:
        """Build the remote path, inserting camera name if configured."""
        # Convert to POSIX path
        relative_posix = relative_path.as_posix()

        if self.camera_name:
            # Insert camera name into the path
            # For a file like 20251002/image.fits, we want 20251002/spring/image.fits
            path_parts = relative_posix.split("/")

            if len(path_parts) > 1:
                # Has subdirectory (like YYYYMMDD)
                # Insert camera name after the date directory
                date_dir = path_parts[0]
                remaining = "/".join(path_parts[1:])
                remote_relative = f"{date_dir}/{self.camera_name}/{remaining}"
            else:
                # No subdirectory, just add camera name
                remote_relative = f"{self.camera_name}/{relative_posix}"
        else:
            remote_relative = relative_posix

        return f"{self.remote_base_path}/{remote_relative}"

    def transfer_file(self, local_path: str) -> bool:
        """Transfer a file to the remote location."""
        try:
            # Calculate relative path
            local_path_obj = Path(local_path).resolve()
            relative_path = local_path_obj.relative_to(self.local_base_path)

            # Determine transfer method
            if self.transfer_method == "local" or self.remote_host in [
                "localhost",
                "127.0.0.1",
            ]:
                return self.transfer_local(local_path_obj, relative_path)
            else:
                return self.transfer_remote(local_path_obj, relative_path)

        except Exception as e:
            logger.error(f"Transfer failed for {local_path}: {e}")
            return False

    def transfer_local(self, local_path: Path, relative_path: Path) -> bool:
        """Transfer file locally."""
        try:
            # Build destination path with camera subfolder if configured
            if self.camera_name:
                # Insert camera name into the path
                path_parts = relative_path.parts
                if len(path_parts) > 1:
                    # Has subdirectory (like YYYYMMDD)
                    dest_path = (
                        Path(self.remote_base_path).expanduser()
                        / path_parts[0]
                        / self.camera_name
                        / Path(*path_parts[1:])
                    )
                else:
                    # No subdirectory
                    dest_path = (
                        Path(self.remote_base_path).expanduser()
                        / self.camera_name
                        / relative_path
                    )
            else:
                dest_path = Path(self.remote_base_path).expanduser() / relative_path

            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(str(local_path), str(dest_path))

            if self.verify_transfer:
                source_size = local_path.stat().st_size
                dest_size = dest_path.stat().st_size
                if source_size != dest_size:
                    raise ValueError(f"Size mismatch: {source_size} != {dest_size}")

            logger.info(
                f"Successfully transferred {relative_path} → {dest_path.relative_to(Path(self.remote_base_path).expanduser())}"
            )
            return True

        except Exception as e:
            logger.error(f"Local transfer failed: {e}")
            return False

    def transfer_remote(self, local_path: Path, relative_path: Path) -> bool:
        """Transfer file to remote host."""
        import time

        try:
            # Build remote path with camera subfolder
            remote_path = self._build_remote_path(relative_path)
            remote_dir = str(Path(remote_path).parent.as_posix())

            logger.info(f"Transferring {relative_path} → {remote_path}")

            # Check if rsync is available (won't be on Windows usually)
            use_rsync = False
            if self.transfer_method in ["auto", "rsync"]:
                try:
                    # Check if rsync exists
                    check_rsync = subprocess.run(
                        ["where" if sys.platform == "win32" else "which", "rsync"],
                        capture_output=True,
                        timeout=2,
                    )
                    use_rsync = check_rsync.returncode == 0
                    if not use_rsync and self.transfer_method == "rsync":
                        logger.warning(
                            "rsync requested but not available, falling back to scp"
                        )
                except:
                    use_rsync = False

            # Try rsync if available
            if use_rsync:
                rsync_cmd = [
                    "rsync",
                    "-avz",
                    "--mkpath",  # --mkpath creates the path
                    str(local_path),
                    f"{self.remote_user}@{self.remote_host}:{remote_path}",
                ]

                result = subprocess.run(
                    rsync_cmd, capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    logger.info(
                        f"Successfully transferred via rsync to {self.remote_host}:{remote_path}"
                    )
                    return True
                # If rsync fails, fall back to scp
                logger.debug("rsync failed, falling back to scp")

            # Use SCP (default for Windows)
            # First, create directory via SSH
            setup_cmd = [
                "ssh",
                "-o",
                "ConnectTimeout=10",
                f"{self.remote_user}@{self.remote_host}",
                f"mkdir -p {remote_dir}",
            ]

            logger.debug(f"Creating remote directory: {remote_dir}")
            result = subprocess.run(
                setup_cmd, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                logger.warning(f"Failed to create remote directory: {result.stderr}")

            # Small delay to ensure SSH connection is closed
            time.sleep(0.5)

            # Now transfer the file
            # Convert Windows path to forward slashes
            local_path_str = str(local_path).replace("\\", "/")

            scp_cmd = [
                "scp",
                "-o",
                "ConnectTimeout=60",
                local_path_str,
                f"{self.remote_user}@{self.remote_host}:{remote_path}",
            ]

            logger.debug(f"Running SCP: {' '.join(scp_cmd)}")
            result = subprocess.run(
                scp_cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                logger.error(f"SCP failed: {result.stderr}")
                return False

            logger.info(f"Successfully transferred to {self.remote_host}:{remote_path}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Transfer timed out for {local_path}")
            return False
        except Exception as e:
            logger.error(f"Remote transfer failed: {e}")
            return False
