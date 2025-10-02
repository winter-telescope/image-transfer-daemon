"""Windows-specific transfer handler."""

from .base import BaseTransferHandler


class WindowsTransferHandler(BaseTransferHandler):
    """Transfer handler for Windows systems."""

    def setup_platform_specifics(self):
        """Set up Windows-specific configurations."""
        # Windows uses the ssh/scp commands from OpenSSH client
        # No special setup needed as base class handles it
        pass
