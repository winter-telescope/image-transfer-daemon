#!/usr/bin/env python3
"""Debug a running Windows service that isn't transferring files."""

import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

print("=== Image Transfer Service Debugger ===\n")

# 1. Check service status
print("1. Service Status:")
result = subprocess.run(
    ["sc", "query", "ImageTransferDaemon"], capture_output=True, text=True
)
if "RUNNING" in result.stdout:
    print("   ✓ Service is RUNNING")
else:
    print("   ✗ Service is NOT running")
    print(result.stdout)

# 2. Check service configuration
print("\n2. Service Configuration:")
result = subprocess.run(
    ["sc", "qc", "ImageTransferDaemon"], capture_output=True, text=True
)
print(result.stdout)

# Check what user the service runs as
if "LocalSystem" in result.stdout:
    print("   ! Service runs as SYSTEM (this can cause SSH key issues)")
    service_home = Path("C:/Windows/System32/config/systemprofile")
elif "SERVICE_START_NAME" in result.stdout:
    for line in result.stdout.split("\n"):
        if "SERVICE_START_NAME" in line:
            print(f"   Service runs as: {line.strip()}")
            service_home = Path.home()

# 3. Check for log files
print("\n3. Looking for log files:")

log_locations = [
    Path.home() / "logs",
    Path("C:/Windows/System32/config/systemprofile/logs"),
    Path("C:/Windows/SysWOW64/config/systemprofile/logs"),
    Path("C:/ProgramData/ImageTransfer/logs"),
]

found_logs = []
for log_dir in log_locations:
    if log_dir.exists():
        logs = list(log_dir.glob("*.log"))
        if logs:
            print(f"   Found logs in: {log_dir}")
            for log in logs:
                found_logs.append(log)
                # Check if recently modified
                mtime = datetime.fromtimestamp(log.stat().st_mtime)
                age = datetime.now() - mtime
                if age < timedelta(minutes=10):
                    print(
                        f"     - {log.name} (ACTIVE - modified {age.seconds//60} min ago)"
                    )
                else:
                    print(f"     - {log.name} (modified {age.days} days ago)")

# 4. Check debug log if it exists
debug_log_paths = [
    Path.home() / "logs" / "service_debug.log",
    Path("C:/Windows/System32/config/systemprofile/logs/service_debug.log"),
]

print("\n4. Service Debug Log:")
for debug_log in debug_log_paths:
    if debug_log.exists():
        print(f"   Found debug log at: {debug_log}")
        print("   Last 20 lines:")
        print("   " + "-" * 50)
        with open(debug_log, "r") as f:
            lines = f.readlines()
            for line in lines[-20:]:
                print(f"   {line.rstrip()}")
        break
else:
    print("   No debug log found")

# 5. Check SSH configuration
print("\n5. SSH Key Configuration:")
ssh_locations = [
    Path.home() / ".ssh",
    service_home / ".ssh" if "service_home" in locals() else None,
]

for ssh_dir in ssh_locations:
    if ssh_dir and ssh_dir.exists():
        print(f"   SSH directory found: {ssh_dir}")
        keys = list(ssh_dir.glob("id_*"))
        if keys:
            for key in keys:
                print(f"     - {key.name}")
        else:
            print("     ! No SSH keys found")
    elif ssh_dir:
        print(f"   ! SSH directory missing: {ssh_dir}")

# 6. Check config file
print("\n6. Configuration File:")
config_paths = [
    Path.home() / ".config" / "image-transfer" / "config.yaml",
    Path.home() / ".config" / "image-transfer" / "config.yml",
    Path("C:/ProgramData/image-transfer/config.yaml"),
]

for config_path in config_paths:
    if config_path.exists():
        print(f"   Found config at: {config_path}")
        with open(config_path, "r") as f:
            print("   First 10 lines:")
            for i, line in enumerate(f):
                if i >= 10:
                    break
                print(f"     {line.rstrip()}")
        break
else:
    print("   ! No config file found")

# 7. Test folder creation
print("\n7. Testing file operations:")
test_path = Path.home() / "data" / "images" / "test_service"
try:
    test_path.mkdir(parents=True, exist_ok=True)
    test_file = test_path / f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    test_file.write_text("Service debug test")
    print(f"   ✓ Created test file: {test_file}")

    # Wait and check if anything happens
    print("   Waiting 5 seconds to see if service detects the file...")
    import time

    time.sleep(5)

    if test_file.exists():
        print("   File still exists (not transferred)")
        test_file.unlink()
    else:
        print("   File was processed!")

except Exception as e:
    print(f"   ✗ Error creating test file: {e}")

print("\n" + "=" * 50)
print("\nCommon Issues:")
print("1. Service runs as SYSTEM - SSH keys in wrong location")
print("   Fix: Run service as your user account or copy SSH keys to SYSTEM profile")
print("2. Config file not found by service")
print("   Fix: Copy config to C:/ProgramData/image-transfer/")
print("3. Watch path doesn't exist")
print("   Fix: Create the watch directory")
print("\nTo change service to run as your user:")
print("  sc config ImageTransferDaemon obj= .\\YourUsername password= YourPassword")
