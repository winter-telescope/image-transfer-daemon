#!/usr/bin/env python3
"""Debug script to check Windows service installation issues."""

import subprocess
import sys
from pathlib import Path

print("=== Image Transfer Daemon Service Debugger ===\n")

# Check if running as admin
try:
    import ctypes

    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    print(f"Running as Administrator: {bool(is_admin)}")
    if not is_admin:
        print("  WARNING: Service installation requires Administrator privileges!")
except:
    print("Could not check admin status (not Windows?)")

# Check Python installation
print(f"\nPython executable: {sys.executable}")
print(f"Python version: {sys.version}")

# Check pywin32
try:
    import win32service
    import win32serviceutil

    print("\npywin32 is installed ✓")
except ImportError:
    print("\npywin32 is NOT installed ✗")
    print("Install with: pip install pywin32")
    sys.exit(1)

# Check if service exists
print("\nChecking for existing service...")
result = subprocess.run(
    ["sc", "query", "ImageTransferDaemon"], capture_output=True, text=True
)

if result.returncode == 0:
    print("Service EXISTS in Windows registry")
    print(result.stdout)
else:
    print("Service NOT FOUND in Windows registry")

# Check for the wrapper script
print("\nLooking for service wrapper...")
possible_paths = [
    Path(__file__).parent.parent
    / "src"
    / "image_transfer"
    / "services"
    / "windows_service_wrapper.py",
    Path(sys.prefix)
    / "Lib"
    / "site-packages"
    / "image_transfer"
    / "services"
    / "windows_service_wrapper.py",
    Path.cwd() / "src" / "image_transfer" / "services" / "windows_service_wrapper.py",
]

wrapper_found = False
for path in possible_paths:
    if path.exists():
        print(f"Found wrapper at: {path}")
        wrapper_found = True
        wrapper_path = path
        break

if not wrapper_found:
    print("Wrapper script NOT FOUND")
    print("Searched in:")
    for path in possible_paths:
        print(f"  - {path}")
else:
    print("\nTrying direct installation...")
    print(f"Running: python {wrapper_path} install")

    result = subprocess.run(
        [sys.executable, str(wrapper_path), "install"], capture_output=True, text=True
    )

    print("\nOutput:")
    print(result.stdout)
    if result.stderr:
        print("Errors:")
        print(result.stderr)

    # Check again if service exists
    result = subprocess.run(
        ["sc", "query", "ImageTransferDaemon"], capture_output=True, text=True
    )

    if result.returncode == 0:
        print("\n✓ Service successfully registered!")
        print("You can now use: net start ImageTransferDaemon")
    else:
        print("\n✗ Service still not registered")
        print("Try running the wrapper directly as Administrator:")
        print(f"  python {wrapper_path} install")

print("\n" + "=" * 50)
