#!/usr/bin/env python3
"""
Reliable image transfer using periodic scanning instead of file watching.
Much simpler and more robust - like rsync + cron.
"""

import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Set

import yaml


class ReliableTransferDaemon:
    """Simple, reliable transfer daemon that uses periodic scanning."""

    def __init__(self, config_path=None):
        """Initialize the daemon."""
        self.setup_logging()
        self.config = self.load_config(config_path)

        # State file to track transferred files
        self.state_file = (
            Path.home() / ".config" / "image-transfer" / "transferred_files.json"
        )
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.transferred = self.load_state()

        # Setup paths
        self.local_base = Path(self.config["watch_path"]).expanduser().resolve()
        self.remote_host = self.config["remote_host"]
        self.remote_user = self.config["remote_user"]
        self.remote_base = self.config["remote_base_path"]
        self.camera_name = self.config.get("camera_name")

        # Transfer settings
        self.scan_interval = self.config.get("scan_interval", 30)  # seconds
        self.file_patterns = self.config.get("file_patterns", ["*.fits"])
        self.min_file_age = self.config.get("min_file_age_seconds", 5)
        self.max_retries = self.config.get("retry_attempts", 3)

        self.logger.info(f"Starting reliable transfer daemon")
        self.logger.info(f"Local: {self.local_base}")
        self.logger.info(
            f"Remote: {self.remote_user}@{self.remote_host}:{self.remote_base}"
        )
        self.logger.info(f"Scan interval: {self.scan_interval} seconds")

    def setup_logging(self):
        """Set up logging."""
        log_dir = Path.home() / "logs"
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler(log_dir / "image_transfer.log"),
                logging.StreamHandler(),
            ],
        )
        self.logger = logging.getLogger("ReliableTransfer")

    def load_config(self, config_path=None):
        """Load configuration."""
        if config_path:
            path = Path(config_path)
        else:
            path = Path.home() / ".config" / "image-transfer" / "config.yaml"

        if not path.exists():
            self.logger.error(f"Config not found: {path}")
            sys.exit(1)

        with open(path) as f:
            return yaml.safe_load(f)

    def load_state(self) -> Dict:
        """Load the state of transferred files."""
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        return {"files": {}, "last_scan": None}

    def save_state(self):
        """Save the state of transferred files."""
        with open(self.state_file, "w") as f:
            json.dump(self.transferred, f, indent=2)

    def get_file_hash(self, filepath: Path) -> str:
        """Get a hash of file path + size + mtime for tracking."""
        stat = filepath.stat()
        return f"{filepath}|{stat.st_size}|{stat.st_mtime}"

    def find_files_to_transfer(self) -> list:
        """Find all files that need to be transferred."""
        files_to_transfer = []

        if not self.local_base.exists():
            self.logger.warning(f"Watch path does not exist: {self.local_base}")
            return files_to_transfer

        now = datetime.now()

        # Scan for files matching patterns
        for pattern in self.file_patterns:
            for filepath in self.local_base.rglob(pattern):
                # Skip if file is too new (might still be writing)
                file_age = now - datetime.fromtimestamp(filepath.stat().st_mtime)
                if file_age.total_seconds() < self.min_file_age:
                    continue

                # Check if already transferred
                file_hash = self.get_file_hash(filepath)
                if file_hash in self.transferred.get("files", {}):
                    transfer_info = self.transferred["files"][file_hash]
                    if transfer_info.get("status") == "success":
                        continue  # Already successfully transferred
                    if transfer_info.get("retries", 0) >= self.max_retries:
                        continue  # Too many failures, skip

                files_to_transfer.append(filepath)

        return files_to_transfer

    def transfer_file(self, filepath: Path) -> bool:
        """Transfer a single file using scp or rsync."""
        try:
            # Calculate relative path
            relative_path = filepath.relative_to(self.local_base)

            # Add camera name if configured
            if self.camera_name:
                parts = relative_path.parts
                if len(parts) > 1:  # Has date directory
                    remote_relative = (
                        f"{parts[0]}/{self.camera_name}/{'/'.join(parts[1:])}"
                    )
                else:
                    remote_relative = f"{self.camera_name}/{relative_path.as_posix()}"
            else:
                remote_relative = relative_path.as_posix()

            remote_path = f"{self.remote_base}/{remote_relative}"
            remote_dir = str(Path(remote_path).parent.as_posix())

            # Create remote directory
            mkdir_cmd = [
                "ssh",
                "-o",
                "ConnectTimeout=10",
                "-o",
                "BatchMode=yes",
                f"{self.remote_user}@{self.remote_host}",
                f"mkdir -p '{remote_dir}'",
            ]
            result = subprocess.run(
                mkdir_cmd, capture_output=True, text=True, timeout=30
            )

            if result.returncode != 0:
                self.logger.warning(f"Failed to create directory: {result.stderr}")

            # Transfer file
            self.logger.info(f"Transferring: {relative_path}")

            # Try rsync first if available
            if self.try_rsync(filepath, remote_path):
                return True

            # Fall back to scp
            scp_cmd = [
                "scp",
                "-o",
                "ConnectTimeout=30",
                "-o",
                "BatchMode=yes",
                str(filepath).replace("\\", "/"),
                f"{self.remote_user}@{self.remote_host}:{remote_path}",
            ]

            result = subprocess.run(
                scp_cmd, capture_output=True, text=True, timeout=300
            )

            if result.returncode == 0:
                self.logger.info(f"Success: {relative_path}")
                return True
            else:
                self.logger.error(f"Failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.logger.error(f"Timeout transferring {filepath}")
            return False
        except Exception as e:
            self.logger.error(f"Error transferring {filepath}: {e}")
            return False

    def try_rsync(self, local_path: Path, remote_path: str) -> bool:
        """Try to use rsync if available."""
        try:
            rsync_cmd = [
                "rsync",
                "-az",
                "--timeout=30",
                str(local_path).replace("\\", "/"),
                f"{self.remote_user}@{self.remote_host}:{remote_path}",
            ]
            result = subprocess.run(
                rsync_cmd, capture_output=True, text=True, timeout=300
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False  # rsync not available
        except:
            return False

    def run_once(self):
        """Run one transfer cycle."""
        self.logger.debug("Scanning for files...")
        files = self.find_files_to_transfer()

        if files:
            self.logger.info(f"Found {len(files)} files to transfer")

            for filepath in files:
                file_hash = self.get_file_hash(filepath)

                # Initialize tracking if needed
                if file_hash not in self.transferred.get("files", {}):
                    self.transferred.setdefault("files", {})[file_hash] = {
                        "path": str(filepath),
                        "first_seen": datetime.now().isoformat(),
                        "retries": 0,
                    }

                # Try to transfer
                if self.transfer_file(filepath):
                    self.transferred["files"][file_hash]["status"] = "success"
                    self.transferred["files"][file_hash][
                        "transferred_at"
                    ] = datetime.now().isoformat()
                else:
                    self.transferred["files"][file_hash]["status"] = "failed"
                    self.transferred["files"][file_hash]["retries"] += 1
                    self.transferred["files"][file_hash][
                        "last_retry"
                    ] = datetime.now().isoformat()

                # Save state after each file
                self.save_state()

        self.transferred["last_scan"] = datetime.now().isoformat()
        self.save_state()

    def run(self):
        """Run the daemon continuously."""
        self.logger.info("Reliable transfer daemon started")

        while True:
            try:
                self.run_once()
            except KeyboardInterrupt:
                self.logger.info("Daemon stopped by user")
                break
            except Exception as e:
                self.logger.error(f"Error in transfer cycle: {e}")

            # Wait for next scan
            time.sleep(self.scan_interval)

    def cleanup_old_state(self, days=7):
        """Remove old entries from state file."""
        cutoff = datetime.now() - timedelta(days=days)
        cleaned = {"files": {}, "last_scan": self.transferred.get("last_scan")}

        for file_hash, info in self.transferred.get("files", {}).items():
            if info.get("status") != "success":
                cleaned["files"][file_hash] = info
                continue

            transferred_at = info.get("transferred_at")
            if transferred_at:
                transfer_date = datetime.fromisoformat(transferred_at)
                if transfer_date > cutoff:
                    cleaned["files"][file_hash] = info

        self.transferred = cleaned
        self.save_state()


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Reliable Image Transfer Daemon")
    parser.add_argument("-c", "--config", help="Config file path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument(
        "--cleanup", action="store_true", help="Clean old state entries"
    )
    parser.add_argument("--status", action="store_true", help="Show transfer status")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    daemon = ReliableTransferDaemon(args.config)

    if args.cleanup:
        daemon.cleanup_old_state()
        print("Old state entries cleaned")
    elif args.status:
        state = daemon.transferred
        total = len(state.get("files", {}))
        success = sum(
            1 for f in state.get("files", {}).values() if f.get("status") == "success"
        )
        failed = sum(
            1 for f in state.get("files", {}).values() if f.get("status") == "failed"
        )
        print(f"Transfer Status:")
        print(f"  Total tracked: {total}")
        print(f"  Successful: {success}")
        print(f"  Failed: {failed}")
        print(f"  Last scan: {state.get('last_scan', 'Never')}")
    elif args.once:
        daemon.run_once()
    else:
        daemon.run()


if __name__ == "__main__":
    main()
