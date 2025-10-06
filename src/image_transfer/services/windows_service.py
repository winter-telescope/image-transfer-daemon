"""Windows service implementation using user-level Task Scheduler (no admin needed)."""

import os
import subprocess
import sys
from pathlib import Path


def install_windows_service():
    """Install as user-level scheduled task (no admin or password needed)."""
    task_name = "ImageTransferDaemon"

    print("Installing Image Transfer Daemon (User Level)...")
    print(f"Will run as: {os.environ.get('USERNAME')}")
    print("No Administrator privileges required!\n")

    # Get Python executable path
    python_exe = sys.executable

    # Create a simple batch file to run the daemon
    batch_file = Path.home() / ".config" / "image-transfer" / "run_daemon.bat"
    batch_file.parent.mkdir(parents=True, exist_ok=True)

    with open(batch_file, "w") as f:
        f.write(f"@echo off\n")
        f.write(f'cd /d "{Path.home()}"\n')
        f.write(f'"{python_exe}" -m image_transfer\n')

    # Use schtasks.exe which works without admin for user tasks
    # This creates a task that starts at logon for the current user
    cmd = [
        "schtasks",
        "/create",
        "/tn",
        task_name,
        "/tr",
        f'"{batch_file}"',
        "/sc",
        "onlogon",  # Start at logon
        "/rl",
        "limited",  # Run with limited privileges (no admin needed)
        "/f",  # Force overwrite if exists
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print("✓ Task created successfully!")

        # Start the task immediately
        start_cmd = ["schtasks", "/run", "/tn", task_name]
        start_result = subprocess.run(start_cmd, capture_output=True, text=True)

        if start_result.returncode == 0:
            print("✓ Daemon started!\n")
        else:
            print(f"Note: Could not start immediately: {start_result.stderr}\n")

        print("The daemon will:")
        print("  - Start automatically when you log in")
        print("  - Run with your user account")
        print("  - Have access to your SSH keys and config")
        print("  - NO Administrator privileges needed!\n")

        print("Commands (no admin needed):")
        print(f"  Start:   schtasks /run /tn {task_name}")
        print(f"  Stop:    schtasks /end /tn {task_name}")
        print(f"  Status:  schtasks /query /tn {task_name}")
        print(f"  Remove:  schtasks /delete /tn {task_name} /f")
        print("\nView logs at: ~/logs/image_transfer.log")
        print("\nTo see the task in Task Scheduler GUI:")
        print("  1. Open Task Scheduler (taskschd.msc)")
        print("  2. Look in 'Task Scheduler Library' (not under Microsoft)")

    else:
        if "access is denied" in result.stderr.lower():
            print("Failed: Access denied.")
            print("Trying alternative method with password...\n")
            install_with_password()
        else:
            print("Installation failed!")
            print(f"Error: {result.stderr}")
            print("\nTry the password method:")
            print("  image-transfer-service --install --with-password")


def install_with_password():
    """Install with password prompt for more reliable scheduling."""
    import getpass

    task_name = "ImageTransferDaemon"
    username = os.environ.get("USERNAME")

    print("Installing with password authentication...")
    print(
        "This creates a more reliable scheduled task that can run in the background.\n"
    )

    password = getpass.getpass(f"Enter password for {username}: ")

    # Get Python executable path
    python_exe = sys.executable

    # Create XML for more control over the task
    xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Automatically transfers FITS images to remote processing server</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>Password</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
    <RestartOnFailure>
      <Interval>PT1M</Interval>
      <Count>3</Count>
    </RestartOnFailure>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>-m image_transfer</Arguments>
      <WorkingDirectory>{Path.home()}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    # Save XML to temp file
    xml_file = Path.home() / ".config" / "image-transfer" / "task.xml"
    xml_file.parent.mkdir(parents=True, exist_ok=True)
    with open(xml_file, "w", encoding="utf-16") as f:
        f.write(xml_content)

    # Create task with password
    cmd = [
        "schtasks",
        "/create",
        "/tn",
        task_name,
        "/xml",
        str(xml_file),
        "/ru",
        username,
        "/rp",
        password,
        "/f",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Clean up XML file
    try:
        xml_file.unlink()
    except:
        pass

    if result.returncode == 0:
        print("✓ Service installed successfully with password!\n")

        # Start the task
        start_cmd = ["schtasks", "/run", "/tn", task_name]
        subprocess.run(start_cmd, capture_output=True)

        print("The daemon is now running and will:")
        print("  - Start automatically when you log in")
        print("  - Run in the background even when logged out")
        print("  - Have access to your SSH keys and config")
        print("  - Restart automatically if it crashes\n")

        print("Commands:")
        print(f"  Start:   schtasks /run /tn {task_name}")
        print(f"  Stop:    schtasks /end /tn {task_name}")
        print(f"  Status:  schtasks /query /tn {task_name}")
        print(f"  Remove:  schtasks /delete /tn {task_name} /f")

    else:
        print("Installation failed!")
        if "incorrect" in result.stderr.lower() or "0x80070569" in result.stderr:
            print("Incorrect password. Please try again.")
        else:
            print(f"Error: {result.stderr}")


def uninstall_windows_service():
    """Uninstall scheduled task (no admin needed)."""
    task_name = "ImageTransferDaemon"

    print(f"Uninstalling {task_name}...")

    # First try to stop it
    stop_cmd = ["schtasks", "/end", "/tn", task_name]
    subprocess.run(stop_cmd, capture_output=True, text=True)

    # Delete the task
    delete_cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
    result = subprocess.run(delete_cmd, capture_output=True, text=True)

    if (
        "cannot find the file" in result.stderr.lower()
        or "system cannot find" in result.stderr.lower()
    ):
        print("Service was not installed")
    elif result.returncode == 0:
        print("Service uninstalled successfully!")
    else:
        print(f"Error: {result.stderr}")
