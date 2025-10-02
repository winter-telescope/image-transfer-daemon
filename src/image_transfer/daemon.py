"""Main daemon implementation."""

import logging
import time
from pathlib import Path

from watchdog.observers import Observer

from .config import Config
from .handler import ImageTransferHandler

logger = logging.getLogger(__name__)


class ImageTransferDaemon:
    """Main daemon for watching and transferring images."""

    def __init__(self, config: Config):
        """Initialize the daemon."""
        self.config = config
        self.handler = ImageTransferHandler(config)
        self.observer = Observer()
        self._setup_watch_directory()

    def _setup_watch_directory(self):
        """Ensure watch directory exists."""
        watch_path = Path(self.config["watch_path"])
        if not watch_path.exists():
            watch_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created watch directory: {watch_path}")

    def run(self):
        """Run the daemon."""
        watch_path = Path(self.config["watch_path"])

        self.observer.schedule(self.handler, str(watch_path), recursive=True)

        self.observer.start()
        logger.info(f"Started watching {watch_path}")
        logger.info(
            f"Transferring to {self.config['remote_host']}:"
            f"{self.config['remote_base_path']}"
        )

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Stopping daemon...")
            self.observer.stop()

        self.observer.join()

    def stop(self):
        """Stop the daemon."""
        self.observer.stop()
