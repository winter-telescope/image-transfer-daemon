"""Scheduler setup for periodic execution."""

import os
import subprocess
import sys
from pathlib import Path


def setup_windows_task():
    """Setup Windows Task Scheduler task."""
    print("Setting up Windows Task Scheduler...")

    task_name = "ImageTransferTask"
    interval = input("Enter interval in minutes (default 5): ").strip() or "5"

    # Use the installed command
    command = "image-transfer"

    # Build PowerShell command to create scheduled task
    ps_script = f"""
$action = New-ScheduledTaskAction -Execute "python" -Argument "-m image_transfer.cli"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes {interval})
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "{task_name}" -Action $action -Trigger $trigger -Settings $settings -Force
"""

    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_script], capture_output=True, text=True
        )

        if result.returncode == 0:
            print(f"✓ Task '{task_name}' created successfully")
            print(f"  Runs every {interval} minutes")
            print("\nTo manage the task:")
            print(f"  View: Get-ScheduledTask -TaskName {task_name}")
            print(f"  Run now: Start-ScheduledTask -TaskName {task_name}")
            print(f"  Delete: Unregister-ScheduledTask -TaskName {task_name}")
        else:
            raise Exception(result.stderr)

    except Exception as e:
        print(f"Failed to create task: {e}")
        print("\nManual setup instructions:")
        print("1. Open Task Scheduler")
        print("2. Create Basic Task")
        print(f"3. Set program: python -m image_transfer.cli")
        print(f"4. Set interval: {interval} minutes")


def setup_linux_cron():
    """Setup Linux cron job."""
    print("Setting up cron job...")

    interval = input("Enter interval in minutes (default 5): ").strip() or "5"

    # Build cron entry using the installed command
    cron_entry = (
        f"*/{interval} * * * * image-transfer >> ~/logs/image_transfer_cron.log 2>&1\n"
    )

    # Get current crontab
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
        current_cron = result.stdout if result.returncode == 0 else ""
    except:
        current_cron = ""

    # Check if already exists
    if "image-transfer" in current_cron:
        print("⚠ A cron job for image transfer already exists")
        if input("Replace it? (y/n): ").lower() != "y":
            return
        # Remove old entry
        lines = current_cron.split("\n")
        current_cron = "\n".join(l for l in lines if "image-transfer" not in l)

    # Add new entry
    new_cron = current_cron.rstrip("\n") + "\n" + cron_entry

    # Install new crontab
    try:
        proc = subprocess.Popen(["crontab", "-"], stdin=subprocess.PIPE, text=True)
        proc.communicate(new_cron)

        print(f"✓ Cron job created successfully")
        print(f"  Runs every {interval} minutes")
        print("\nTo manage the cron job:")
        print("  View: crontab -l")
        print("  Edit: crontab -e")
        print("  Remove: crontab -r")

    except Exception as e:
        print(f"Failed to setup cron: {e}")
        print(f"\nManual setup - add this to crontab:")
        print(f"  {cron_entry}")


def setup():
    """Main entry point for scheduler setup."""
    print("Image Transfer Scheduler Setup")
    print("=" * 40)

    # Ensure log directory exists
    log_dir = Path.home() / "logs"
    log_dir.mkdir(exist_ok=True)

    if sys.platform.startswith("win"):
        setup_windows_task()
    else:
        setup_linux_cron()

    print("\n✓ Setup complete!")
    print("\nNote: Make sure to:")
    print("1. Configure SSH keys for passwordless authentication")
    print("2. Test the transfer manually first: image-transfer")
    print(f"3. Check logs regularly in {log_dir}/")


if __name__ == "__main__":
    setup()
