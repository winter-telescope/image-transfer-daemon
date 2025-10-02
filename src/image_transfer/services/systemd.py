"""Linux systemd service installation."""

import os
import subprocess
import sys
from pathlib import Path

SYSTEMD_SERVICE_TEMPLATE = """[Unit]
Description=Image Transfer Daemon
After=network.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={python_path} -m image_transfer
Restart=on-failure
RestartSec=10
StandardOutput=append:{log_path}
StandardError=append:{log_path}

[Install]
WantedBy=multi-user.target
"""


def install_systemd_service():
    """Install systemd service on Linux."""
    service_name = "image-transfer.service"
    service_path = Path(f"/etc/systemd/system/{service_name}")

    # Check if running as root
    if os.geteuid() != 0:
        print("Error: Must run as root (use sudo)")
        sys.exit(1)

    # Get user who will run the service
    user = os.environ.get("SUDO_USER", os.environ.get("USER", "nobody"))
    home_dir = Path.home() if user == os.environ.get("USER") else Path(f"/home/{user}")

    log_dir = home_dir / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)

    service_content = SYSTEMD_SERVICE_TEMPLATE.format(
        user=user,
        working_dir=home_dir,
        python_path=sys.executable,
        log_path=log_dir / "image_transfer.log",
    )

    # Write service file
    print(f"Installing systemd service to {service_path}")
    with open(service_path, "w") as f:
        f.write(service_content)

    # Reload systemd
    subprocess.run(["systemctl", "daemon-reload"], check=True)

    print("Service installed successfully!")
    print(f"\nCommands:")
    print(f"  Start:   sudo systemctl start {service_name}")
    print(f"  Stop:    sudo systemctl stop {service_name}")
    print(f"  Enable:  sudo systemctl enable {service_name}")
    print(f"  Status:  sudo systemctl status {service_name}")
    print(f"  Logs:    journalctl -u {service_name} -f")


def uninstall_systemd_service():
    """Uninstall systemd service."""
    service_name = "image-transfer.service"

    if os.geteuid() != 0:
        print("Error: Must run as root (use sudo)")
        sys.exit(1)

    print("Stopping service...")
    subprocess.run(["systemctl", "stop", service_name], capture_output=True)

    print("Disabling service...")
    subprocess.run(["systemctl", "disable", service_name], capture_output=True)

    print("Removing service file...")
    service_path = Path(f"/etc/systemd/system/{service_name}")
    if service_path.exists():
        service_path.unlink()

    subprocess.run(["systemctl", "daemon-reload"], check=True)

    print("Service uninstalled successfully!")
