"""Windows Service wrapper for Image Transfer Daemon."""

import os
import sys
from pathlib import Path

import servicemanager
import win32event
import win32service
import win32serviceutil

# Add the src directory to path so we can import image_transfer
src_path = Path(__file__).parent.parent.parent
if src_path.exists():
    sys.path.insert(0, str(src_path))

try:
    from image_transfer import Config, ImageTransferDaemon
except ImportError:
    # If installed as package, import directly
    try:
        from image_transfer import Config, ImageTransferDaemon
    except ImportError as e:
        print(f"Failed to import image_transfer: {e}")
        sys.exit(1)


class ImageTransferService(win32serviceutil.ServiceFramework):
    _svc_name_ = "ImageTransferDaemon"
    _svc_display_name_ = "Image Transfer Daemon"
    _svc_description_ = (
        "Automatically transfers FITS images to remote processing server"
    )

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.daemon = None
        self.running = True

    def SvcStop(self):
        """Stop the service."""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self.running = False
        win32event.SetEvent(self.hWaitStop)
        if self.daemon:
            self.daemon.stop()

    def SvcDoRun(self):
        """Run the service."""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )

        try:
            # Load configuration
            config = Config()

            # Create and run daemon
            self.daemon = ImageTransferDaemon(config)

            # Run in a way that can be stopped
            watch_path = Path(config["watch_path"])
            self.daemon.observer.schedule(
                self.daemon.handler, str(watch_path), recursive=True
            )
            self.daemon.observer.start()

            # Wait for stop signal
            while self.running:
                win32event.WaitForSingleObject(self.hWaitStop, 1000)

            self.daemon.observer.stop()
            self.daemon.observer.join()

        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {str(e)}")
            raise


def main():
    """Entry point for the service wrapper - handles install/remove/start commands."""
    if len(sys.argv) == 1:
        # Service is being started by Windows Service Manager
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ImageTransferService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        # Command line - install/remove/start/stop/etc
        win32serviceutil.HandleCommandLine(ImageTransferService)


if __name__ == "__main__":
    main()
