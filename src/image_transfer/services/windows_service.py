"""Windows service implementation for image transfer daemon."""

import os
import sys
from pathlib import Path


def install_windows_service():
    """Install Windows service using pywin32."""
    try:
        # Check if pywin32 is installed
        try:
            import win32service
            import win32serviceutil
        except ImportError:
            print("Error: pywin32 is required for Windows service.")
            print("Install it with: pip install pywin32")
            print("Or reinstall with: pip install .[windows]")
            sys.exit(1)

        print("Installing Image Transfer Daemon service...")

        # Find the wrapper script
        wrapper_path = Path(__file__).parent / "windows_service_wrapper.py"

        if not wrapper_path.exists():
            print(f"Error: Service wrapper not found at {wrapper_path}")
            sys.exit(1)

        # The key is to change to the directory containing the wrapper
        # and run it directly with HandleCommandLine
        original_dir = os.getcwd()

        try:
            # Change to the services directory
            os.chdir(wrapper_path.parent)

            # Import the wrapper module and install the service
            import windows_service_wrapper

            # Save original argv and replace with install command
            original_argv = sys.argv
            sys.argv = [sys.argv[0], "install"]

            # Install the service using HandleCommandLine
            win32serviceutil.HandleCommandLine(
                windows_service_wrapper.ImageTransferService
            )

            # Restore argv
            sys.argv = original_argv

            print("\nService installed successfully!")
            print("\nTo start the service:")
            print("  net start ImageTransferDaemon")
            print("\nTo stop the service:")
            print("  net stop ImageTransferDaemon")
            print("\nTo set auto-start on boot:")
            print("  sc config ImageTransferDaemon start=auto")

        finally:
            # Change back to original directory
            os.chdir(original_dir)

    except Exception as e:
        print(f"Error installing service: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def uninstall_windows_service():
    """Uninstall Windows service."""
    try:
        import win32serviceutil

        print("Uninstalling Image Transfer Daemon service...")

        # Find the wrapper script
        wrapper_path = Path(__file__).parent / "windows_service_wrapper.py"

        if wrapper_path.exists():
            # Change to the services directory
            original_dir = os.getcwd()

            try:
                os.chdir(wrapper_path.parent)

                # Import the wrapper module
                import windows_service_wrapper

                # Save original argv and replace with remove command
                original_argv = sys.argv
                sys.argv = [sys.argv[0], "remove"]

                # Remove the service using HandleCommandLine
                win32serviceutil.HandleCommandLine(
                    windows_service_wrapper.ImageTransferService
                )

                # Restore argv
                sys.argv = original_argv

                print("\nService uninstalled successfully!")

            finally:
                os.chdir(original_dir)
        else:
            # Fallback to sc command
            import subprocess

            print("Using sc command to remove service...")
            subprocess.run(["sc", "stop", "ImageTransferDaemon"], capture_output=True)
            subprocess.run(["sc", "delete", "ImageTransferDaemon"], capture_output=True)
            print("Service removed")

    except Exception as e:
        print(f"Error uninstalling service: {e}")
        sys.exit(1)
