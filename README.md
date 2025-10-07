# Image Transfer Tool

This is a small module for using rsync to transfer images from one computer to another. It relies on ssh keys allowing access without a password.

## Installing
Set up a dedicated python environment. Eg, if you use conda, make a conda environment in the top level repository, here called ".conda":

```bash:
conda create --prefix .conda python=3.11
```

Then activate that environment:

```bash:
conda activate ./.conda
```

Now install the module and dependencies:

```python:
pip install -e .
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
log_level: INFO  # DEBUG, INFO, WARNING, ERROR to see other levels of entries in the log
log_directory: ~/logs
log_file: image_transfer.log


# File handling
min_file_age_seconds: 2  # Wait for file to be stable before transfer
exclude_patterns: []  # Patterns to exclude from transfer
# exclude_patterns:
#   - "*_temp.fits"
#   - "test_*.fits"
```

You can then tail the log (eg the last 200 lines) with:

```bash:
tail -fn 200 ~/logs/image_transfer.log
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

**Option A: Call the Python binary directly (recommended)**

Find the full path to the environment’s Python and call the CLI as a module:

```bash:
/home/oir-user/GIT/image-transfer-daemon/.conda/bin/python -m image_transfer.cli -c /home/oir-user/GIT/image-transfer-daemon/config/config.yaml
```

This guarantees you’re using the Python from your .conda env, without needing to activate anything.

**Option B: Activate the conda env inside bash**

If you want to activate the environment first (useful if your CLI relies on conda activate to set variables):
```bash:
source /home/oir-user/GIT/image-transfer-daemon/.conda/etc/profile.d/conda.sh && conda activate /home/oir-user/GIT/image-transfer-daemon/.conda && image-transfer -c /home/oir-user/GIT/image-transfer-daemon/config/config.yaml
```

This runs a login shell, sources conda’s activation script, activates your .conda environment, and then calls the image-transfer CLI entrypoint.

## Setting up a cron job
Example: run the image transfer every minute:

```bash:
* * * * * /home/oir-user/GIT/image-transfer-daemon/.conda/bin/python -m image_transfer.cli
```

### Windows + Cron Job Execution in WSL
On windows + wsl, to ensure that wsl+cron runs always even on reboot:

You need to have the cron service running:

```bash:
sudo service cron start
```


To have it run automatically after reboot, set up a Windows Task Scheduler entry that runs:
```bash:
wsl.exe -d Ubuntu -u root service cron start
```

Steps for setting up the task:
1. open **Task Scheduler** in windows
2. Create a new **Task** (not a basic task)
3. **General Tab:**
  - Name: `WSL Cron Startup`
  - Description: Start up an ubuntu terminal with WSL running in the background always to ensure that cronjobs defined in linux run all the time whether the user is logged in or not.
  - Select "Run whether user is logged on or not"
  - Select "Run with highest privileges"
4. **Triggers tab:**
  - New trigger --> "At startup"
5. **Actions tab:**
  - New action --> "Start a program"
  - Program/script: `wsl.exe`
  - Add arguments: `-d Ubuntu -u root service cron start`
6. **Conditions tab:**
  - Uncheck “Start the task only if the computer is on AC power” if you want it even on battery.
7. **Settings tab:**
  - Enable “If the task fails, restart every …” for robustness, and select 5 minutes
  - Uncheck "Stop the task if it runs longer than..." box


**Note:**
WSL will terminate when idle unless something is running. The cron daemon counts as “something running,” so as long as you start it this way, WSL will stay up.

If you ever want to ensure WSL never shuts down, you can run:
```bash:
wsl --set-default-version 2
wsl --install -d Ubuntu
```
and then start a lightweight background process like tail -f /dev/null via Task Scheduler. But usually service cron start is enough.


** Test the setup **

Reboot Windows.

After logging in, check from Windows PowerShell:
```bash:
wsl -d Ubuntu -u root pgrep cron
```

You should see cron’s PID.

Check your cron log (e.g., /var/log/syslog in Ubuntu) to confirm it’s running jobs.