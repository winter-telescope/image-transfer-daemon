"""macOS launchd service installation."""

import os
import subprocess
import sys
from pathlib import Path

LAUNCHD_PLIST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.observatory.imagetransfer</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>image_transfer</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{working_dir}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{log_path}</string>
    <key>StandardErrorPath</key>
    <string>{error_log_path}</string>
</dict>
</plist>
"""


def install_launchd_service():
    """Install launchd service on macOS."""
    plist_name = "com.observatory.imagetransfer.plist"
    plist_path = Path.home() / "Library" / "LaunchAgents" / plist_name

    # Create logs directory
    log_dir = Path.home() / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)

    plist_content = LAUNCHD_PLIST_TEMPLATE.format(
        python_path=sys.executable,
        working_dir=str(Path.home()),
        log_path=str(log_dir / "image_transfer.log"),
        error_log_path=str(log_dir / "image_transfer_error.log"),
    )

    # Create LaunchAgents directory if needed
    plist_path.parent.mkdir(parents=True, exist_ok=True)

    # Write plist file
    print(f"Installing launchd service to {plist_path}")
    with open(plist_path, "w") as f:
        f.write(plist_content)

    # Load the service
    try:
        subprocess.run(["launchctl", "load", str(plist_path)], check=True)
        print("Service installed and started successfully!")
    except subprocess.CalledProcessError:
        print("Service installed but could not be started automatically.")

    print(f"\nCommands:")
    print(f"  Start:   launchctl load {plist_path}")
    print(f"  Stop:    launchctl unload {plist_path}")
    print(f"  Status:  launchctl list | grep imagetransfer")


def uninstall_launchd_service():
    """Uninstall launchd service."""
    plist_name = "com.observatory.imagetransfer.plist"
    plist_path = Path.home() / "Library" / "LaunchAgents" / plist_name

    if plist_path.exists():
        print("Unloading service...")
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)

        print("Removing plist file...")
        plist_path.unlink()

        print("Service uninstalled successfully!")
    else:
        print("Service not found")
