"""Command-line interface for image transfer."""

import argparse
import sys
from pathlib import Path

from .config import Config
from .transfer import ImageTransfer


def main():
    """Main entry point for image-transfer command."""
    parser = argparse.ArgumentParser(
        description="Transfer images to remote server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  image-transfer                    # Run with default config
  image-transfer -c myconfig.yaml   # Use specific config
  image-transfer --dry-run          # Test without transferring
        """,
    )

    parser.add_argument(
        "-c", "--config", help="Configuration file path", type=Path, default=None
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be transferred without actually transferring",
    )
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    args = parser.parse_args()

    try:
        # Load configuration
        config = Config(args.config)

        # Create and run transfer
        transfer = ImageTransfer(config)
        transfer.run()

    except KeyboardInterrupt:
        print("\nTransfer interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
