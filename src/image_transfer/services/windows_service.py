"""Windows service implementation for image transfer daemon."""

import subprocess
import sys
from pathlib import Path


def install_windows_service():
    """Install Windows service using pywin32."""
    try:
        # Check if pywin32 is installed
        try:
            import win32serviceutil
        except ImportError:
            print("Error: pywin32 is required for Windows service.")
            print("Install it with: pip install pywin32")
            print("Or reinstall with: pip install .[windows]")
            sys.exit(1)

        print("Installing Image Transfer Daemon service...")

        # Use the entry point to install the service
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "image_transfer.services.windows_service_wrapper",
                "install",
            ],
            capture_output=True,
            text=True,
        )

        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        # Check if installation was successful
        if result.returncode == 0 or "successfully installed" in result.stdout.lower():
            print("\nService installed successfully!")
            print("\nTo start the service:")
            print("  net start ImageTransferDaemon")
            print("\nTo stop the service:")
            print("  net stop ImageTransferDaemon")
            print("\nTo set auto-start on boot:")
            print("  sc config ImageTransferDaemon start=auto")
        else:
            print("\nIf installation failed, try running as Administrator")
            sys.exit(1)

    except Exception as e:
        print(f"Error installing service: {e}")
        sys.exit(1)


def uninstall_windows_service():
    """Uninstall Windows service."""
    try:
        print("Uninstalling Image Transfer Daemon service...")

        # Use the entry point to remove the service
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "image_transfer.services.windows_service_wrapper",
                "remove",
            ],
            capture_output=True,
            text=True,
        )

        # Print the output
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0 or "successfully removed" in result.stdout.lower():
            print("\nService uninstalled successfully!")
        else:
            print("\nService may not have been installed")

    except Exception as e:
        print(f"Error uninstalling service: {e}")
        sys.exit(1)
