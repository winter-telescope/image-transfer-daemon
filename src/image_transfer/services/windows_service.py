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

        # Install the service
        print("Installing Image Transfer Daemon service...")

        # Run the service installation
        result = subprocess.run(
            [sys.executable, str(service_script), "install"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            print("Service installed successfully!")
            print("\nTo start the service:")
            print("  net start ImageTransferDaemon")
            print("\nTo stop the service:")
            print("  net stop ImageTransferDaemon")
            print("\nTo set auto-start:")
            print("  sc config ImageTransferDaemon start=auto")
        else:
            print(f"Failed to install service: {result.stderr}")
            sys.exit(1)

    except Exception as e:
        print(f"Error installing service: {e}")
        sys.exit(1)


def uninstall_windows_service():
    """Uninstall Windows service."""
    try:
        print("Stopping service...")
        subprocess.run(["net", "stop", "ImageTransferDaemon"], capture_output=True)

        print("Removing service...")
        subprocess.run(["sc", "delete", "ImageTransferDaemon"], capture_output=True)

        print("Service uninstalled successfully!")

    except Exception as e:
        print(f"Error uninstalling service: {e}")
        sys.exit(1)


# Windows Service Wrapper (embedded in the same file for simplicity)
WINDOWS_SERVICE_WRAPPER = '''
"""Windows Service wrapper for Image Transfer Daemon."""

import win32serviceutil
import win32service
import win32event
import servicemanager
import sys
import os
from pathlib import Path

# Add the src directory to path so we can import image_transfer
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from image_transfer import ImageTransferDaemon, Config


class ImageTransferService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ImageTransferDaemon"
    _svc_display_name_ = "Image Transfer Daemon"
    _svc_description_ = "Automatically transfers FITS images to remote processing server"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.daemon = None
        self.running = True
        
    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)
        if self.daemon:
            self.daemon.stop()
        
    def SvcDoRun(self):
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        try:
            # Load configuration
            config = Config()
            
            # Create and run daemon
            self.daemon = ImageTransferDaemon(config)
            
            # Run in a way that can be stopped
            watch_path = Path(config["watch_path"])
            self.daemon.observer.schedule(
                self.daemon.handler,
                str(watch_path),
                recursive=True
            )
            self.daemon.observer.start()
            
            # Wait for stop signal
            while self.running:
                win32event.WaitForSingleObject(self.hWaitStop, 1000)
            
            self.daemon.observer.stop()
            self.daemon.observer.join()
            
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {str(e)}")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ImageTransferService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ImageTransferService)
'''
