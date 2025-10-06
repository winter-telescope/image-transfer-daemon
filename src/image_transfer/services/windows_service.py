"""Windows service implementation using Task Scheduler for user-level execution."""

import os
import subprocess
import sys
from pathlib import Path


def install_windows_service():
    """Install as scheduled task (runs as current user, no password needed)."""
    task_name = "ImageTransferDaemon"

    print("Installing Image Transfer Daemon...")
    print(f"Will run as: {os.environ.get('USERNAME')}")
    print("Using Task Scheduler (no password required)\n")

    # Get Python executable path
    python_exe = sys.executable

    # Build PowerShell command to create scheduled task
    ps_script = f"""
    $TaskName = "{task_name}"
    $Description = "Automatically transfers FITS images to remote processing server"

    # Create the action
    $Action = New-ScheduledTaskAction -Execute "{python_exe}" -Argument "-m image_transfer" -WorkingDirectory "$HOME"

    # Create trigger to start at logon and keep running
    $Trigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERNAME"

    # Create principal (current user with highest privileges)
    $Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest

    # Create settings
    $Settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Days 365)

    # Register the task
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $Description `
        -Action $Action `
        -Trigger $Trigger `
        -Principal $Principal `
        -Settings $Settings `
        -Force

    # Start the task
    Start-ScheduledTask -TaskName $TaskName
    """

    # Run PowerShell command
    result = subprocess.run(
        ["powershell", "-Command", ps_script], capture_output=True, text=True
    )

    if result.returncode == 0:
        print("✓ Service installed successfully!\n")
        print("The daemon is now running and will:")
        print("  - Start automatically when you log in")
        print("  - Run with your user account")
        print("  - Have access to your SSH keys and config")
        print("  - Restart automatically if it crashes\n")
        print("Commands:")
        print(f"  Start:   Start-ScheduledTask -TaskName {task_name}")
        print(f"  Stop:    Stop-ScheduledTask -TaskName {task_name}")
        print(f"  Status:  Get-ScheduledTask -TaskName {task_name}")
        print(
            f"  Remove:  Unregister-ScheduledTask -TaskName {task_name} -Confirm:$false"
        )
        print("\nView logs at: ~/logs/image_transfer.log")
    else:
        print("Installation failed!")
        print(result.stderr)
        print("\nTry running as Administrator")
        sys.exit(1)


def uninstall_windows_service():
    """Uninstall scheduled task."""
    task_name = "ImageTransferDaemon"

    print(f"Uninstalling {task_name}...")

    # PowerShell command to remove task
    ps_script = f"""
    Stop-ScheduledTask -TaskName "{task_name}" -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName "{task_name}" -Confirm:$false
    """

    result = subprocess.run(
        ["powershell", "-Command", ps_script], capture_output=True, text=True
    )

    if "cannot find the file specified" in result.stderr.lower():
        print("Service was not installed")
    else:
        print("Service uninstalled successfully!")
