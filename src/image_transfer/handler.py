"""File system event handler for image transfers."""

import logging
import queue
import threading
import time
from pathlib import Path
from typing import Set

from watchdog.events import FileSystemEventHandler

from .config import Config
from .platforms import get_platform_handler

logger = logging.getLogger(__name__)


class ImageTransferHandler(FileSystemEventHandler):
    """Handler for file system events that triggers transfers."""

    def __init__(self, config: Config):
        """Initialize the handler."""
        self.config = config
        self.platform_handler = get_platform_handler(config)

        # Queue for handling transfers
        self.transfer_queue: queue.Queue = queue.Queue()
        self.transfer_thread = threading.Thread(
            target=self._transfer_worker, daemon=True
        )
        self.transfer_thread.start()

        # Track processed files
        self.processed_files: Set[str] = set()
        self.lock = threading.Lock()

        # Test connection on startup
        self.platform_handler.test_connection()

    def on_created(self, event):
        """Handle file creation events."""
        if not event.is_directory and self._should_transfer(event.src_path):
            self._queue_transfer(event.src_path)

    def on_modified(self, event):
        """Handle file modification events."""
        if not event.is_directory and self._should_transfer(event.src_path):
            with self.lock:
                if event.src_path not in self.processed_files:
                    self._queue_transfer(event.src_path)

    def _should_transfer(self, path: str) -> bool:
        """Check if file should be transferred."""
        file_path = Path(path)
        patterns = self.config.get("file_patterns", ["*.fits"])

        return any(file_path.match(pattern) for pattern in patterns)

    def _queue_transfer(self, filepath: str):
        """Add file to transfer queue."""
        # Wait to ensure file is completely written
        time.sleep(1.0)

        if Path(filepath).exists():
            self.transfer_queue.put(filepath)
            with self.lock:
                self.processed_files.add(filepath)
            logger.info(f"Queued for transfer: {filepath}")

    def _transfer_worker(self):
        """Worker thread for processing transfers."""
        while True:
            try:
                filepath = self.transfer_queue.get(timeout=1)
                success = self.platform_handler.transfer_file(filepath)

                if not success:
                    # Remove from processed files for retry
                    with self.lock:
                        self.processed_files.discard(filepath)

                self.transfer_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Transfer worker error: {e}")
