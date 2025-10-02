"""Base platform handler class."""

import logging
import shutil
import subprocess
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
            dest_path = Path(self.remote_base_path).expanduser() / relative_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            shutil.copy2(str(local_path), str(dest_path))

            if self.verify_transfer:
                source_size = local_path.stat().st_size
                dest_size = dest_path.stat().st_size
                if source_size != dest_size:
                    raise ValueError(f"Size mismatch: {source_size} != {dest_size}")

            logger.info(f"Successfully transferred {relative_path} (local)")
            return True

        except Exception as e:
            logger.error(f"Local transfer failed: {e}")
            return False

    def transfer_remote(self, local_path: Path, relative_path: Path) -> bool:
        """Transfer file to remote host."""
        try:
            # Convert path for remote system (use absolute path, not ~)
            remote_relative = relative_path.as_posix()
            remote_path = f"{self.remote_base_path}/{remote_relative}"
            remote_dir = str(Path(remote_path).parent.as_posix())

            # Create remote directory (without quotes around path)
            mkdir_cmd = [
                "ssh",
                "-o",
                "ConnectTimeout=30",
                f"{self.remote_user}@{self.remote_host}",
                f"mkdir -p {remote_dir}",
            ]

            logger.debug(f"Creating remote directory: {remote_dir}")
            result = subprocess.run(
                mkdir_cmd, capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                logger.warning(f"Failed to create remote directory: {result.stderr}")
                # Try alternative method using shell expansion
                mkdir_cmd = [
                    "ssh",
                    "-o",
                    "ConnectTimeout=30",
                    f"{self.remote_user}@{self.remote_host}",
                    "sh",
                    "-c",
                    f"'mkdir -p {remote_dir}'",
                ]
                result = subprocess.run(
                    mkdir_cmd, capture_output=True, text=True, timeout=30
                )
                if result.returncode != 0:
                    logger.error(
                        f"Second attempt to create directory failed: {result.stderr}"
                    )

            # Transfer file using scp
            logger.info(
                f"Transferring {relative_path} to {self.remote_host}:{remote_path}"
            )
            scp_cmd = [
                "scp",
                "-q",
                "-o",
                "ConnectTimeout=30",
                str(local_path),
                f"{self.remote_user}@{self.remote_host}:{remote_path}",
            ]

            result = subprocess.run(
                scp_cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                raise Exception(f"SCP failed: {result.stderr}")

            # Optionally verify the transfer
            if self.verify_transfer:
                stat_cmd = [
                    "ssh",
                    "-o",
                    "ConnectTimeout=10",
                    f"{self.remote_user}@{self.remote_host}",
                    f"stat -c %s {remote_path} 2>/dev/null || stat -f %z {remote_path} 2>/dev/null",
                ]

                result = subprocess.run(
                    stat_cmd, capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.strip():
                    remote_size = int(result.stdout.strip())
                    local_size = local_path.stat().st_size
                    if remote_size != local_size:
                        logger.warning(
                            f"Size mismatch: local={local_size}, remote={remote_size}"
                        )
                    else:
                        logger.debug(f"Transfer verified: {local_size} bytes")

            logger.info(f"Successfully transferred {relative_path}")
            return True

        except subprocess.TimeoutExpired:
            logger.error(f"Transfer timed out for {local_path}")
            logger.info("This might be due to SSH key authentication not being set up")
            return False
        except Exception as e:
            logger.error(f"Remote transfer failed: {e}")
            return False
