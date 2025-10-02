"""macOS-specific transfer handler."""

from .unix import UnixTransferHandler


class DarwinTransferHandler(UnixTransferHandler):
    """Transfer handler for macOS systems."""

    def setup_platform_specifics(self):
        """Set up macOS-specific configurations."""
        # macOS is Unix-like, so we can reuse Unix handler
        super().setup_platform_specifics()
