"""Windows service implementation for image transfer daemon."""

import os
import subprocess
import sys
from pathlib import Path


def install_windows_service():
    """Install Windows service using pywin32."""
    try:
        # Check if pywin32 is installed
        try:
            import pythoncom
            import win32serviceutil
        except ImportError:
            print("Error: pywin32 is required for Windows service.")
            print("Install it with: pip install pywin32")
            sys.exit(1)

        # Find the service wrapper script
        service_script = Path(__file__).parent / "windows_service_wrapper.py"

        if not service_script.exists():
            print(f"Error: Service wrapper not found at {service_script}")
            sys.exit(1)

        print("Installing Image Transfer Daemon service...")

        # Run the service wrapper directly to install
        # This needs to be run with pythonservice.exe from pywin32
        result = subprocess.run(
            [sys.executable, str(service_script), "install"],
            capture_output=True,
            text=True,
        )

        print(result.stdout)
        if result.stderr:
            print(result.stderr)

        if result.returncode == 0 or "Service installed" in result.stdout:
            print("\nService installed successfully!")
            print("\nTo start the service:")
            print("  net start ImageTransferDaemon")
            print("\nTo stop the service:")
            print("  net stop ImageTransferDaemon")
            print("\nTo set auto-start:")
            print("  sc config ImageTransferDaemon start=auto")

            # Try to update the service to ensure it's properly configured
            subprocess.run(
                [sys.executable, str(service_script), "update"], capture_output=True
            )
        else:
            print(f"Installation may have failed. Try running directly:")
            print(f"  python {service_script} install")

    except Exception as e:
        print(f"Error installing service: {e}")
        sys.exit(1)


def uninstall_windows_service():
    """Uninstall Windows service."""
    try:
        # Find the service wrapper script
        service_script = Path(__file__).parent / "windows_service_wrapper.py"

        if service_script.exists():
            print("Removing service...")
            result = subprocess.run(
                [sys.executable, str(service_script), "remove"],
                capture_output=True,
                text=True,
            )
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
        else:
            # Try using sc command as fallback
            print("Stopping service...")
            subprocess.run(["net", "stop", "ImageTransferDaemon"], capture_output=True)

            print("Removing service...")
            result = subprocess.run(
                ["sc", "delete", "ImageTransferDaemon"], capture_output=True
            )

        print("Service uninstalled successfully!")

    except Exception as e:
        print(f"Error uninstalling service: {e}")
        sys.exit(1)
