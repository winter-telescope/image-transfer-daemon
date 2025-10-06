#!/usr/bin/env python3
"""Check which Python environment will be used by the daemon."""

import os
import sys
from pathlib import Path

print("=== Python Environment Check ===\n")

# Current Python info
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python prefix: {sys.prefix}")

# Check if in conda
conda_prefix = os.environ.get("CONDA_PREFIX")
conda_default = os.environ.get("CONDA_DEFAULT_ENV")

if conda_prefix:
    print(f"\n✓ Conda environment detected!")
    print(f"  CONDA_PREFIX: {conda_prefix}")
    print(f"  CONDA_DEFAULT_ENV: {conda_default}")
else:
    print("\n✗ Not in a conda environment")

# Check if image_transfer is installed
print("\nChecking if image_transfer module is installed...")
try:
    import image_transfer

    print(f"✓ image_transfer found at: {image_transfer.__file__}")
    print(f"  Version: {getattr(image_transfer, '__version__', 'unknown')}")
except ImportError as e:
    print(f"✗ image_transfer NOT found: {e}")
    print("\nMake sure to install it in this environment:")
    print("  pip install -e .")

# Check what the startup script will use
startup_folder = (
    Path(os.environ["APPDATA"])
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Startup"
)
batch_file = startup_folder / "ImageTransferDaemon.bat"

if batch_file.exists():
    print(f"\nStartup script found at: {batch_file}")
    print("Contents:")
    print("-" * 50)
    with open(batch_file, "r") as f:
        print(f.read())
    print("-" * 50)
else:
    print(f"\nNo startup script found at: {batch_file}")
    print("Run 'image-transfer-service --install' to create it")

print("\n" + "=" * 50)
print("\nRECOMMENDATION:")
if conda_prefix:
    print(f"Always activate your conda environment before installing:")
    print(f"  conda activate {conda_default or conda_prefix}")
    print(f"  pip install -e .")
    print(f"  image-transfer-service --install")
else:
    print("Consider using a conda environment for isolation:")
    print("  conda create --prefix .conda python=3.11")
    print("  conda activate ./.conda")
    print("  pip install -e .")
    print("  image-transfer-service --install")
