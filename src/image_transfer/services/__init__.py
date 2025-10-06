"""Service installation and management for image transfer daemon."""

import platform
import sys
from pathlib import Path


def install_service(with_password=False):
    """Install the image transfer daemon as a system service."""
    system = platform.system()

    if system == "Windows":
        from .windows_service import install_windows_service, install_with_password

        if with_password:
            install_with_password()
        else:
            install_windows_service()
    elif system == "Linux":
        from .systemd import install_systemd_service

        install_systemd_service()
    elif system == "Darwin":
        from .launchd import install_launchd_service

        install_launchd_service()
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)


def uninstall_service():
    """Uninstall the image transfer daemon service."""
    system = platform.system()

    if system == "Windows":
        from .windows_service import uninstall_windows_service

        uninstall_windows_service()
    elif system == "Linux":
        from .systemd import uninstall_systemd_service

        uninstall_systemd_service()
    elif system == "Darwin":
        from .launchd import uninstall_launchd_service

        uninstall_launchd_service()
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)


def main():
    """Main entry point for service management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Image Transfer Daemon Service Manager"
    )
    parser.add_argument("--install", action="store_true", help="Install the service")
    parser.add_argument(
        "--uninstall", action="store_true", help="Uninstall the service"
    )
    parser.add_argument(
        "--with-password",
        action="store_true",
        help="Install with password (Windows only, for background operation)",
    )
    parser.add_argument(
        "--startup",
        choices=["auto", "manual"],
        default="manual",
        help="Set startup type (not used with Task Scheduler)",
    )

    args = parser.parse_args()

    if args.install:
        install_service(with_password=args.with_password)
    elif args.uninstall:
        uninstall_service()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
