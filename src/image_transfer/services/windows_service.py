"""Windows service implementation using Startup folder (no permissions needed)."""

import os
import subprocess
import sys
from pathlib import Path


def install_windows_service():
    """Install daemon using Windows Startup folder (no admin or special permissions needed)."""

    print("Installing Image Transfer Daemon...")
    print(f"Will run as: {os.environ.get('USERNAME')}")
    print("Using Windows Startup folder - no special permissions needed!\n")

    # Get the CURRENT Python executable path (from conda environment)
    python_exe = sys.executable
    print(f"Python environment: {python_exe}")

    # Detect if we're in a conda environment
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        print(f"Conda environment detected: {conda_prefix}\n")

    # Get the Startup folder path
    startup_folder = (
        Path(os.environ["APPDATA"])
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )

    # Create a batch file to run the daemon WITH the correct Python
    batch_file = startup_folder / "ImageTransferDaemon.bat"

    # Create VBS script for hidden operation (no console window)
    vbs_file = startup_folder / "ImageTransferDaemon.vbs"

    # Write the batch file with FULL PATH to the correct Python
    with open(batch_file, "w") as f:
        f.write("@echo off\n")
        f.write(f'cd /d "{Path.home()}"\n')

        # If in conda, activate it first
        if conda_prefix:
            # Find conda activation script
            conda_bat = Path(conda_prefix).parent.parent / "condabin" / "conda.bat"
            if not conda_bat.exists():
                # Try alternative location
                conda_bat = Path(conda_prefix) / "condabin" / "conda.bat"

            if conda_bat.exists():
                f.write(f'call "{conda_bat}" activate "{conda_prefix}"\n')
            else:
                # Just use the full Python path directly
                print("Warning: Could not find conda.bat, using Python directly")

        # Use the FULL PATH to Python from current environment
        f.write(f'"{python_exe}" -m image_transfer\n')

    # Write the VBS file that runs the batch file hidden
    with open(vbs_file, "w") as f:
        f.write('Set WshShell = CreateObject("WScript.Shell")\n')
        f.write(f'WshShell.Run """{batch_file}""", 0\n')
        f.write("Set WshShell = Nothing\n")

    print("✓ Startup files created with correct Python environment!")

    # Test that the module can be imported with this Python
    test_cmd = [python_exe, "-c", 'import image_transfer; print("Module found")']
    result = subprocess.run(test_cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print("✓ Verified image_transfer module is accessible\n")
    else:
        print(
            "Warning: Could not verify module access. Make sure package is installed in this environment!"
        )
        print(f"Error: {result.stderr}\n")

    # Start the daemon immediately WITH THE CORRECT PYTHON
    print("Starting the daemon now...")
    subprocess.Popen(
        [python_exe, "-m", "image_transfer"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    print("✓ Daemon started!\n")

    # Also try to create a scheduled task as backup (but don't fail if it doesn't work)
    try:
        create_simple_task()
    except:
        pass  # Ignore if task creation fails

    # Start the daemon immediately
    print("\nStarting the daemon now...")
    subprocess.Popen(
        [python_exe, "-m", "image_transfer"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )

    print("✓ Daemon started!\n")

    print("The daemon will:")
    print("  - Start automatically when Windows starts")
    print("  - Run with your user account")
    print("  - Have access to your SSH keys and config")
    print("  - Run silently in the background\n")

    print("Installation complete! The daemon is now running.")
    print(f"\nStartup files location: {startup_folder}")
    print("\nTo verify it's running:")
    print("  tasklist | findstr python")
    print("\nTo stop the daemon:")
    print('  taskkill /F /IM python.exe /FI "WINDOWTITLE eq image_transfer"')
    print("\nView logs at: ~/logs/image_transfer.log")


def create_simple_task():
    """Try to create a basic scheduled task (optional, may fail due to permissions)."""
    # Very simple task creation without special flags
    cmd = f'schtasks /create /tn ImageTransferDaemon /tr "pythonw -m image_transfer" /sc onstart /f'
    subprocess.run(cmd, shell=True, capture_output=True)


def uninstall_windows_service():
    """Uninstall daemon by removing startup files."""

    print("Uninstalling Image Transfer Daemon...")

    # Remove from Startup folder
    startup_folder = (
        Path(os.environ["APPDATA"])
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup"
    )

    removed = False

    # Remove batch file
    batch_file = startup_folder / "ImageTransferDaemon.bat"
    if batch_file.exists():
        batch_file.unlink()
        removed = True

    # Remove VBS file
    vbs_file = startup_folder / "ImageTransferDaemon.vbs"
    if vbs_file.exists():
        vbs_file.unlink()
        removed = True

    # Try to remove scheduled task if it exists
    try:
        subprocess.run(
            "schtasks /delete /tn ImageTransferDaemon /f",
            shell=True,
            capture_output=True,
        )
    except:
        pass

    # Try to stop running instances
    try:
        subprocess.run(
            'taskkill /F /IM python.exe /FI "COMMANDLINE like *image_transfer*"',
            shell=True,
            capture_output=True,
        )
        print("Stopped running daemon instances")
    except:
        pass

    if removed:
        print("✓ Service uninstalled successfully!")
    else:
        print("Service was not installed")


def install_with_password():
    """Fallback method - just use the startup folder."""
    print("Note: Password method not needed with Startup folder approach.")
    print("Using standard installation instead...\n")
    install_windows_service()
