# image-transfer-daemon

Cross-platform watchdog daemon which watches a specific folder and transfers data from that folder to another computer using scp/rsync.

## Features

- Monitors directories for new FITS files
- Automatically transfers files to remote systems
- Maintains directory structure (YYYYMMDD format)
- Cross-platform: Windows, Linux, macOS
- Multiple transfer methods (scp, rsync, local)
- Automatic retry on failure
- Service/daemon installation for all platforms

## Quick Start

```bash
# Install
pip install .

# Create config
image-transfer --create-config

# Edit config
# Windows: notepad %USERPROFILE%\.config\image-transfer\config.yaml
# Linux/Mac: nano ~/.config/image-transfer/config.yaml

# Test run
image-transfer -v

# Install as service (no password needed on Windows!)
# Windows (as admin): image-transfer-service --install
# Linux: sudo image-transfer-service --install
# macOS: image-transfer-service --install
```

## Installation

### Install from source (development)

```bash
git clone <repo>
cd image-transfer-daemon

# Create conda environment (recommended for development)
conda create --prefix .conda python=3.11
conda activate ./.conda

# Install in development mode with all dependencies
pip install -e ".[dev]"
```

### Install from source (production)

```bash
git clone <repo>
cd image-transfer-daemon
pip install .

# No extra dependencies needed for any platform!
```

### Platform-specific installations

#### Windows development setup

```powershell
# Clone repository
git clone <repo>
cd image-transfer-daemon

# Create conda environment
conda create --prefix .conda python=3.11
conda activate .\.conda

# Install with development dependencies
pip install -e ".[dev]"
```

#### Linux/macOS development setup

```bash
# Clone repository
git clone <repo>
cd image-transfer-daemon

# Create virtual environment (alternative to conda)
python3 -m venv venv
source venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"
```

## Configuration

After installation, create your configuration file:

```bash
# Create default YAML configuration
image-transfer --create-config

# The config will be created at:
# Windows: %USERPROFILE%\.config\image-transfer\config.yaml
# Linux/macOS: ~/.config/image-transfer/config.yaml
```

Edit the configuration file for your setup. Example for Windows to Linux transfer:

```yaml
# ~/.config/image-transfer/config.yaml
watch_path: C:/Users/Observer/data/images  # Windows path
remote_host: freya
remote_user: observer
remote_base_path: /home/observer/data/images
transfer_method: scp
compression: false  # No compression for FITS files
file_patterns:
  - "*.fits"
  - "*.FIT"
verify_transfer: true
retry_attempts: 3
retry_delay: 5
```

## Running the Daemon

### Test mode (manual run)

```bash
# Run with default config
image-transfer

# Run with specific config
image-transfer -c /path/to/config.yaml

# Run with verbose logging
image-transfer -v
```

## Service Installation & Management

### Windows Service (Task Scheduler)

Windows uses Task Scheduler for user-level execution (no password required).

#### Install service

```powershell
# Run PowerShell as Administrator
image-transfer-service --install

# The service will:
# - Run as your current user
# - Start automatically when you log in
# - Have access to your SSH keys and config files
# - No password required!
```

#### Start/Stop service

```powershell
# Using PowerShell commands
Start-ScheduledTask -TaskName ImageTransferDaemon  # Start
Stop-ScheduledTask -TaskName ImageTransferDaemon   # Stop
Get-ScheduledTask -TaskName ImageTransferDaemon    # Status

# Or use the management script
.\scripts\manage-daemon.ps1 start
.\scripts\manage-daemon.ps1 stop
.\scripts\manage-daemon.ps1 status
.\scripts\manage-daemon.ps1 logs
```

#### Uninstall service

```powershell
# Uninstall the service
image-transfer-service --uninstall

# Or manually with PowerShell
Unregister-ScheduledTask -TaskName ImageTransferDaemon -Confirm:$false
```

### Linux Service (systemd)

#### Install service

```bash
# Install systemd service
sudo image-transfer-service --install

# Enable auto-start on boot
sudo systemctl enable image-transfer.service
```

#### Start/Stop service

```bash
# Start service
sudo systemctl start image-transfer.service

# Stop service
sudo systemctl stop image-transfer.service

# Restart service
sudo systemctl restart image-transfer.service

# Check service status
sudo systemctl status image-transfer.service

# Enable auto-start on boot
sudo systemctl enable image-transfer.service

# Disable auto-start
sudo systemctl disable image-transfer.service
```

#### Uninstall service

```bash
# Stop and disable service
sudo systemctl stop image-transfer.service
sudo systemctl disable image-transfer.service

# Uninstall the service
sudo image-transfer-service --uninstall
```

### macOS Service (launchd)

#### Install service

```bash
# Install launchd service
image-transfer-service --install
```

#### Start/Stop service

```bash
# Load/Start service
launchctl load ~/Library/LaunchAgents/com.observatory.imagetransfer.plist

# Unload/Stop service
launchctl unload ~/Library/LaunchAgents/com.observatory.imagetransfer.plist

# Check if service is running
launchctl list | grep imagetransfer

# Start service manually (if already loaded)
launchctl start com.observatory.imagetransfer

# Stop service manually
launchctl stop com.observatory.imagetransfer
```

#### Uninstall service

```bash
# Uninstall the service
image-transfer-service --uninstall
```

## Monitoring & Logs

### Check transfer logs

The daemon logs all transfers to `~/logs/image_transfer.log` with automatic rotation (10MB max, 5 backup files).

#### Windows

```powershell
# View latest log entries
Get-Content $env:USERPROFILE\logs\image_transfer.log -Tail 50

# Monitor log in real-time
Get-Content $env:USERPROFILE\logs\image_transfer.log -Wait

# Search for successful transfers
Select-String -Path $env:USERPROFILE\logs\image_transfer.log -Pattern "Successfully transferred"

# Search for failures
Select-String -Path $env:USERPROFILE\logs\image_transfer.log -Pattern "Failed to transfer"

# Count total transfers today
(Select-String -Path $env:USERPROFILE\logs\image_transfer.log -Pattern "Successfully transferred" | Where-Object {$_.Line -like "*$(Get-Date -Format yyyy-MM-dd)*"}).Count
```

#### Linux/macOS

```bash
# View latest log entries
tail -n 50 ~/logs/image_transfer.log

# Monitor log in real-time
tail -f ~/logs/image_transfer.log

# Search for successful transfers
grep "Successfully transferred" ~/logs/image_transfer.log

# Search for failures
grep "Failed to transfer" ~/logs/image_transfer.log

# Count total transfers today
grep "Successfully transferred" ~/logs/image_transfer.log | grep "$(date +%Y-%m-%d)" | wc -l

# Show transfer statistics
echo "=== Transfer Statistics ==="
echo "Total transfers: $(grep -c "Successfully transferred" ~/logs/image_transfer.log)"
echo "Failed transfers: $(grep -c "Failed to transfer" ~/logs/image_transfer.log)"
echo "Today's transfers: $(grep "Successfully transferred" ~/logs/image_transfer.log | grep "$(date +%Y-%m-%d)" | wc -l)"

# List all transferred files from today
grep "Successfully transferred" ~/logs/image_transfer.log | grep "$(date +%Y-%m-%d)" | awk '{print $NF}'
```

### Service-specific logs

#### Windows Task Scheduler logs

```powershell
# Check task status and last run time
Get-ScheduledTask -TaskName ImageTransferDaemon | Get-ScheduledTaskInfo

# View application logs
Get-Content $env:USERPROFILE\logs\image_transfer.log -Tail 50

# Or use the management script
.\scripts\manage-daemon.ps1 logs
```

#### Linux systemd logs

```bash
# View service logs
sudo journalctl -u image-transfer.service

# Follow service logs in real-time
sudo journalctl -u image-transfer.service -f

# View logs from today
sudo journalctl -u image-transfer.service --since today

# View logs from last hour
sudo journalctl -u image-transfer.service --since "1 hour ago"
```

#### macOS Console logs

```bash
# View service logs
log show --predicate 'process == "image-transfer"' --last 1h

# Or use Console.app GUI
# Open Console.app → Search for "image-transfer"
```

## Available Commands

After installation, these commands are available:

```bash
# Show help
image-transfer --help

# Create default configuration
image-transfer --create-config

# Run with specific config
image-transfer -c /path/to/config.yaml

# Run with verbose output
image-transfer -v

# Install as system service
image-transfer-service --install

# Dry run (show what would be transferred without actually transferring)
image-transfer --dry-run
```

## SSH Key Setup

For remote transfers, set up SSH key authentication:

### Windows

```powershell
# Generate SSH key
ssh-keygen -t rsa -b 4096 -f $env:USERPROFILE\.ssh\id_rsa

# Copy public key to remote server
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh user@remote-host "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Test connection
ssh user@remote-host "echo 'Connection successful'"
```

### Linux/macOS

```bash
# Generate SSH key
ssh-keygen -t rsa -b 4096

# Copy public key to remote server
ssh-copy-id user@remote-host

# Test connection
ssh user@remote-host "echo 'Connection successful'"
```

## Troubleshooting

### Check if daemon is running

```bash
# Windows
tasklist | findstr python

# Linux
ps aux | grep image-transfer

# macOS
ps aux | grep image-transfer
```

### Test SSH connection

```bash
# Windows PowerShell
ssh user@remote-host "echo 'Connection successful'"

# Linux/macOS
ssh user@remote-host "echo 'Connection successful'"
```

### Common issues

1. **SSH authentication fails**: Set up SSH key authentication (see SSH Key Setup section)

2. **Permission denied on remote**: Check remote directory permissions
   ```bash
   ssh user@remote-host "ls -la /path/to/remote/directory"
   ```

3. **Service won't start**: Check logs for errors
   - Windows: Check Task Scheduler or `Get-ScheduledTask -TaskName ImageTransferDaemon`
   - Linux: `sudo journalctl -u image-transfer.service`
   - macOS: Console.app

4. **Files not transferring**: Verify file patterns in config match your files
   ```yaml
   file_patterns:
     - "*.fits"
     - "*.FIT"
     - "*.fit"
   ```

5. **Network timeouts**: Increase timeout in configuration
   ```yaml
   transfer_timeout_seconds: 300
   ```

## Development

### Running tests

```bash
# Install dev dependencies first
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=image_transfer

# Run specific test
pytest tests/test_daemon.py
```

### Code formatting

```bash
# Format code with black
black src/

# Check code with ruff
ruff check src/
```

### Building for distribution

```bash
# Install build tools
pip install build

# Build distribution packages
python -m build

# This creates wheels and source distributions in dist/
```

## Example Configurations

### Basic Windows to Linux

```yaml
watch_path: C:/Users/Observer/data/images
remote_host: freya
remote_user: observer
remote_base_path: /home/observer/data/images
transfer_method: scp
compression: false
file_patterns:
  - "*.fits"
```

### Linux to Linux with rsync

```yaml
watch_path: ~/telescope/images
remote_host: processing-server.local
remote_user: pipeline
remote_base_path: /data/incoming/images
transfer_method: rsync
compression: false
rsync_options:
  - --archive
  - --partial
  - --progress
file_patterns:
  - "*.fits"
  - "*.fit"
```

### Local transfer (same machine)

```yaml
watch_path: ~/camera/raw
remote_host: localhost
remote_user: ignored
remote_base_path: ~/processing/inbox
transfer_method: local
file_patterns:
  - "*.fits"
```

## License

MIT