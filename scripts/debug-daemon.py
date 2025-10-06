#!/usr/bin/env python3
"""Debug the running daemon and find/view logs."""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

print("=== Image Transfer Daemon Debugger ===\n")

# 1. Check if daemon is actually running
print("1. Checking for running daemon processes...")
result = subprocess.run(
    'tasklist /FI "IMAGENAME eq python.exe" /FO CSV',
    capture_output=True,
    text=True,
    shell=True,
)
python_processes = [
    line for line in result.stdout.split("\n") if "python.exe" in line.lower()
]

if python_processes:
    print(f"   Found {len(python_processes)} Python process(es)")
    # Try to find which one is the daemon
    wmic_cmd = "wmic process where \"name='python.exe'\" get CommandLine /FORMAT:LIST"
    result = subprocess.run(wmic_cmd, capture_output=True, text=True, shell=True)
    if "image_transfer" in result.stdout:
        print("   ✓ Image transfer daemon appears to be running")
    else:
        print("   ? Python is running but might not be the daemon")
else:
    print("   ✗ No Python processes found - daemon not running")

# 2. Find and create log directory
print("\n2. Checking log locations...")
home = Path.home()
possible_log_locations = [
    home / "logs" / "image_transfer.log",
    home / "image_transfer.log",
    home / ".logs" / "image_transfer.log",
    Path("C:/logs/image_transfer.log"),
    Path.cwd() / "logs" / "image_transfer.log",
]

# Create the expected log directory
log_dir = home / "logs"
if not log_dir.exists():
    print(f"   Creating log directory: {log_dir}")
    log_dir.mkdir(parents=True, exist_ok=True)
    print("   ✓ Log directory created")
else:
    print(f"   ✓ Log directory exists: {log_dir}")

# Look for actual log files
found_logs = []
for log_path in possible_log_locations:
    if log_path.exists():
        found_logs.append(log_path)
        stat = log_path.stat()
        size = stat.st_size
        modified = datetime.fromtimestamp(stat.st_mtime)
        print(f"   Found: {log_path} (Size: {size} bytes, Modified: {modified})")

if not found_logs:
    print("   ✗ No log files found yet")
    print(f"   Expected location: {home / 'logs' / 'image_transfer.log'}")

# 3. Check configuration
print("\n3. Checking configuration...")
config_locations = [
    home / ".config" / "image-transfer" / "config.yaml",
    home / ".config" / "image-transfer" / "config.yml",
    home / ".config" / "image-transfer" / "config.json",
]

config_found = None
for config_path in config_locations:
    if config_path.exists():
        config_found = config_path
        print(f"   ✓ Config found: {config_path}")
        break

if not config_found:
    print("   ✗ No configuration file found!")
    print("   Create one with: image-transfer --create-config")

# 4. Test running the daemon manually to see errors
print("\n4. Testing daemon manually...")
print("   Running: python -m image_transfer --help")
result = subprocess.run(
    [sys.executable, "-m", "image_transfer", "--help"], capture_output=True, text=True
)
if result.returncode == 0:
    print("   ✓ Module is installed correctly")
else:
    print("   ✗ Module error:")
    print(f"   {result.stderr}")

# 5. Try to run daemon in test mode to see output
print("\n5. Starting daemon in debug mode (press Ctrl+C to stop)...")
print("-" * 50)

# Create a test script to run with output
test_script = Path.home() / "test_daemon.py"
with open(test_script, "w") as f:
    f.write(
        """
import sys
import logging
from pathlib import Path

# Set up logging to console AND file
log_dir = Path.home() / "logs"
log_dir.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / "image_transfer.log")
    ]
)

print(f"Starting daemon with config from: {Path.home() / '.config' / 'image-transfer'}")
print(f"Logs will be written to: {log_dir / 'image_transfer.log'}")
print("Press Ctrl+C to stop\\n")

try:
    from image_transfer import ImageTransferDaemon, Config
    config = Config()
    print(f"Loaded config: {config}")
    print(f"Watch path: {config['watch_path']}")
    print(f"Remote: {config['remote_host']}:{config['remote_base_path']}")
    daemon = ImageTransferDaemon(config)
    daemon.run()
except KeyboardInterrupt:
    print("\\nStopped by user")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
"""
    )

print("Running test daemon (this will show all output)...")
print("Press Ctrl+C to stop\n")

try:
    subprocess.run([sys.executable, str(test_script)])
except KeyboardInterrupt:
    print("\nTest stopped")
finally:
    test_script.unlink()  # Clean up test script

print("\n" + "=" * 50)
print("\nSUMMARY:")
if found_logs:
    print(f"✓ View logs: type {found_logs[0]}")
else:
    print(
        f"✗ No logs yet. After running, check: {home / 'logs' / 'image_transfer.log'}"
    )

if config_found:
    print(f"✓ Config: {config_found}")
else:
    print("✗ No config - create with: image-transfer --create-config")

print("\nTo view real-time logs:")
print(f'  powershell Get-Content "{home / "logs" / "image_transfer.log"}" -Wait')
