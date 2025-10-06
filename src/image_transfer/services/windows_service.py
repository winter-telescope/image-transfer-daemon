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

        # Add the services directory to Python path so we can import the wrapper
        services_dir = wrapper_path.parent
        if str(services_dir) not in sys.path:
            sys.path.insert(0, str(services_dir))

        try:
            # Import the wrapper module
            from windows_service_wrapper import ImageTransferService

            # Save original argv and replace with install command
            original_argv = sys.argv
            sys.argv = [str(wrapper_path), "install"]

            # Install the service using HandleCommandLine
            win32serviceutil.HandleCommandLine(ImageTransferService)

            # Restore argv
            sys.argv = original_argv

            print("\nService installed successfully!")
            print("\nTo start the service:")
            print("  net start ImageTransferDaemon")
            print("\nTo stop the service:")
            print("  net stop ImageTransferDaemon")
            print("\nTo set auto-start on boot:")
            print("  sc config ImageTransferDaemon start=auto")

        except ImportError as e:
            print(f"Failed to import service wrapper: {e}")
            print(f"Wrapper should be at: {wrapper_path}")
            sys.exit(1)

    except Exception as e:
        print(f"Error installing service: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

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
            # Add the services directory to Python path
            services_dir = wrapper_path.parent
            if str(services_dir) not in sys.path:
                sys.path.insert(0, str(services_dir))

            try:
                # Import the wrapper module
                from windows_service_wrapper import ImageTransferService

                # Save original argv and replace with remove command
                original_argv = sys.argv
                sys.argv = [str(wrapper_path), "remove"]

                # Remove the service using HandleCommandLine
                win32serviceutil.HandleCommandLine(ImageTransferService)

                # Restore argv
                sys.argv = original_argv

                print("\nService uninstalled successfully!")

            except ImportError as e:
                print(f"Failed to import service wrapper: {e}")
                # Fallback to sc command
                import subprocess

                print("Using sc command to remove service...")
                subprocess.run(
                    ["sc", "stop", "ImageTransferDaemon"], capture_output=True
                )
                subprocess.run(
                    ["sc", "delete", "ImageTransferDaemon"], capture_output=True
                )
                print("Service removed")
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
