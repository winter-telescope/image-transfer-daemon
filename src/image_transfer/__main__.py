#!/usr/bin/env python3
"""Main entry point for the image transfer daemon."""

import argparse
import logging
import sys
from pathlib import Path

from .config import Config
from .daemon import ImageTransferDaemon


def setup_logging(verbose=False):
    """Set up basic logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Image Transfer Daemon - Automatically transfer FITS images"
    )
    parser.add_argument("-c", "--config", type=Path, help="Path to configuration file")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--create-config",
        action="store_true",
        help="Create default configuration file and exit",
    )

    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.create_config:
        config_path = Config.create_default_config()
        print(f"Created default configuration at: {config_path}")
        return 0

    try:
        config = Config(args.config)
        daemon = ImageTransferDaemon(config)
        daemon.run()
    except KeyboardInterrupt:
        print("\nShutdown requested...")
        return 0
    except Exception as e:
        logging.error(f"Failed to start daemon: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
