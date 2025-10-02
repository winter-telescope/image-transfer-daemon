"""Unix/Linux-specific transfer handler."""

import logging
import subprocess
from pathlib import Path

from .base import BaseTransferHandler

logger = logging.getLogger(__name__)


class UnixTransferHandler(BaseTransferHandler):
    """Transfer handler for Unix/Linux systems."""

    def setup_platform_specifics(self):
        """Set up Unix-specific configurations."""
        # Check if rsync is available
        if self.transfer_method == "auto":
            try:
                result = subprocess.run(
                    ["which", "rsync"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    self.transfer_method = "rsync"
                    logger.info("Using rsync for transfers")
                else:
                    self.transfer_method = "scp"
                    logger.info("Using scp for transfers")
            except:
                self.transfer_method = "scp"

    def transfer_remote(self, local_path: Path, relative_path: Path) -> bool:
        """Transfer file to remote host with rsync support."""
        if self.transfer_method == "rsync":
            return self.transfer_rsync(local_path, relative_path)
        else:
            return super().transfer_remote(local_path, relative_path)

    def transfer_rsync(self, local_path: Path, relative_path: Path) -> bool:
        """Transfer file using rsync."""
        try:
            remote_relative = relative_path.as_posix()
            remote_path = f"{self.remote_base_path}/{remote_relative}"

            # Create remote directory structure
            remote_dir = str(Path(remote_path).parent.as_posix())
            mkdir_cmd = [
                "ssh",
                f"{self.remote_user}@{self.remote_host}",
                f"mkdir -p '{remote_dir}'",
            ]
            subprocess.run(mkdir_cmd, capture_output=True, timeout=30)

            # Transfer with rsync
            rsync_cmd = [
                "rsync",
                "-av",
                "--progress",
                str(local_path),
                f"{self.remote_user}@{self.remote_host}:{remote_path}",
            ]

            result = subprocess.run(
                rsync_cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode != 0:
                raise Exception(f"Rsync failed: {result.stderr}")

            logger.info(f"Successfully transferred {relative_path} via rsync")
            return True

        except Exception as e:
            logger.error(f"Rsync transfer failed: {e}")
            # Fall back to scp
            return super().transfer_remote(local_path, relative_path)
