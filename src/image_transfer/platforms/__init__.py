"""Platform-specific handlers for image transfers."""

import platform
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import Config


def get_platform_handler(config: "Config"):
    """Get the appropriate platform handler for the current system."""
    system = platform.system()

    if system == "Windows":
        from .windows import WindowsTransferHandler

        return WindowsTransferHandler(config)
    elif system == "Darwin":
        from .darwin import DarwinTransferHandler

        return DarwinTransferHandler(config)
    else:  # Linux and other Unix-like systems
        from .unix import UnixTransferHandler

        return UnixTransferHandler(config)
