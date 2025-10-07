# Image Transfer Tool

This is a small module for using rsync to transfer images from one computer to another. It relies on ssh keys allowing access without a password.

## Installing

```python:
pip install -e ".[dev]"
```

## Setup/Use
### Transfer Configuration
The default config is in `config/config.yaml`, which describes which folder to rsync from --> to. It also has entries for describing the details of which files to transfer/ignore, rsync options, and which folders to monitor and transfer from/to.

Example config:
```yaml:
# Image Transfer Daemon - Default Configuration
# Copy this file and modify for your specific setup

# Local directory to watch for new images
# Supports ~ for home directory
watch_path: /mnt/c/Users/oir-user/data/images/NIGHT/spring

# Remote server configuration
remote_host: freya
remote_user: winter
remote_base_path: ~/data/images/NIGHT/spring

# File patterns to watch (glob patterns)
# Case-insensitive on Windows
file_patterns:
  - "*.fits"
  - "*.FITS"


# Logging configuration
log_level: INFO  # DEBUG, INFO, WARNING, ERROR
log_directory: ~/logs
log_file: image_transfer.log


# File handling
min_file_age_seconds: 2  # Wait for file to be stable before transfer
exclude_patterns: []  # Patterns to exclude from transfer
# exclude_patterns:
#   - "*_temp.fits"
#   - "test_*.fits"

rsync_options:
  - -avP
  - --mkpath # Create destination directories as needed
  - --ignore-existing # Skip files that already exist on remote
  # - --remove-source-files # Uncomment to delete local files after transfer
```

### Running the Transfer

Run the image transfer using the default configuration with:
```bash:
image-transfer
```

or, if you want to point to a specific configuration file:

```bash:
image-transfer -c /abs/path/to/config.yaml
```

### Using Overrides
Override options can be passed to image-transfer. Some examples below:

```bash:
# Dry run only
image-transfer -c config/config.yaml --dry-run

# Force a specific night label
image-transfer --night 20251007

# Override remote or watch path without editing YAML
image-transfer --remote-host freya --remote-user winter \
               --remote-base-path '~/data/images/NIGHT/spring' \
               --watch-path '/mnt/c/Users/oir-user/data/images/NIGHT/spring'

# Add extra rsync flags (repeatable)
image-transfer --rsync-option='--partial' --rsync-option='--progress'

```

### Calling the Python Module Directly
Using the command line interface (cli) call (`image-transfer`) relies on having the correct python environment active, eg having the proper conda environment activated. This won't work when trying to call the module from a cron job which won't use the right python by default. The options are to either:
1. Call the correct python using its full path and call:
```bash:
`/abs/path/to/python -m image-transfer.cli
```


2. Activate the conda environment and use the cli in one call:
```bash:
source /mnt/c/Users/oir-user/Desktop/GIT/image-transfer-daemon/.conda/etc/profile.d/conda.sh && conda activate /mnt/c/Users/oir-user/Desktop/GIT/image-transfer-daemon/.conda && image-transfer
```

## Setting up a cron job
Example: run the image transfer every minute:

```bash:
* * * * * /mnt/c/Users/oir-user/Desktop/GIT/image-transfer-daemon/.conda/bin/python -m image_transfer.cli
```

On windows + wsl, to ensure that wsl+cron runs always even on reboot:

You need to have the cron service running:

```bash:
sudo service cron start
```


To have it run automatically after reboot, set up a Windows Task Scheduler entry that runs:
```bash:
wsl.exe -d Ubuntu -u root service cron start
```


