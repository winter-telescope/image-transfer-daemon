"""Configuration management for image transfer daemon."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the image transfer daemon."""

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration."""
        # Load default config first
        self.data = self._load_default_config()

        # Then overlay user config if provided
        if config_path:
            config_path = self._resolve_config_path(config_path)
            if config_path:
                self._load_user_config(config_path)
                self.config_path = config_path
            else:
                self.config_path = self._get_default_config_path()
        else:
            # Look for user config in default location
            user_config_path = self._get_user_config_path()
            if user_config_path and user_config_path.exists():
                self._load_user_config(user_config_path)
                self.config_path = user_config_path
            else:
                self.config_path = self._get_default_config_path()
                logger.info("No user config found, using defaults")

        self._validate_config()

    def _load_default_config(self) -> Dict[str, Any]:
        """Load the default configuration from default_config.yaml."""
        # Look for default_config.yaml in various locations
        search_paths = [
            # In config directory relative to this file
            Path(__file__).parent.parent.parent / "config" / "default_config.yaml",
            # In current working directory
            Path.cwd() / "config" / "default_config.yaml",
            # Installed location
            Path(sys.prefix) / "config" / "default_config.yaml",
        ]

        for path in search_paths:
            if path.exists():
                logger.debug(f"Loading default config from: {path}")
                with open(path, "r") as f:
                    return yaml.safe_load(f)

        # Fallback to hardcoded defaults if file not found
        logger.warning("default_config.yaml not found, using hardcoded defaults")
        return {
            "watch_path": "~/data/images",
            "remote_host": "localhost",
            "remote_user": "user",
            "remote_base_path": "/data/images",
            "transfer_method": "auto",
            "file_patterns": ["*.fits"],
            "compression": False,
            "verify_transfer": True,
            "retry_attempts": 3,
            "retry_delay": 5,
            "log_level": "INFO",
        }

    def _get_default_config_path(self) -> Path:
        """Get the path to the default config file."""
        # Look for default_config.yaml
        search_paths = [
            Path(__file__).parent.parent.parent / "config" / "default_config.yaml",
            Path.cwd() / "config" / "default_config.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        # Return first option as fallback
        return search_paths[0]

    def _get_user_config_path(self) -> Optional[Path]:
        """Get the user's config path if it exists."""
        config_dir = Path.home() / ".config" / "image-transfer"

        # Check for YAML first, then JSON
        yaml_path = config_dir / "config.yaml"
        yml_path = config_dir / "config.yml"
        json_path = config_dir / "config.json"

        for path in [yaml_path, yml_path, json_path]:
            if path.exists():
                return path

        return None

    def _resolve_config_path(self, config_path) -> Optional[Path]:
        """Resolve config path, checking multiple locations."""
        # Convert string to Path if needed
        if isinstance(config_path, str):
            config_path = Path(config_path)

        # If absolute path and exists, use it
        if config_path.is_absolute() and config_path.exists():
            return config_path

        # List of locations to check for the config file
        search_locations = []

        # 1. Check as-is (relative to current directory)
        search_locations.append(Path.cwd() / config_path)

        # 2. Check in project's config folder (when running from repo)
        # Find project root by looking for pyproject.toml
        current = Path.cwd()
        while current != current.parent:
            if (current / "pyproject.toml").exists():
                search_locations.append(current / "config" / config_path.name)
                break
            current = current.parent

        # 3. Check in config subfolder relative to current directory
        search_locations.append(Path.cwd() / "config" / config_path.name)

        # 4. Check in user's config directory
        user_config_dir = Path.home() / ".config" / "image-transfer"
        search_locations.append(user_config_dir / config_path.name)

        # Try each location
        for location in search_locations:
            if location.exists():
                logger.info(f"Found config file at: {location}")
                return location

        # Config not found
        tried_locations = "\n  - ".join(str(loc) for loc in search_locations)
        logger.warning(
            f"Config file '{config_path}' not found in any of these locations:"
        )
        logger.warning(f"  - {tried_locations}")
        return None

    def _load_user_config(self, config_path: Path):
        """Load user configuration and merge with defaults."""
        logger.info(f"Loading user configuration from {config_path}")

        with open(config_path, "r") as f:
            if config_path.suffix in [".yaml", ".yml"]:
                user_config = yaml.safe_load(f)
            else:
                user_config = json.load(f)

        # Merge with defaults (user config overrides defaults)
        self.data.update(user_config)

        # Log which settings are from user config
        logger.debug("Configuration settings:")
        for key, value in self.data.items():
            if key in user_config:
                logger.debug(f"  {key}: {value} (from user config)")
            else:
                logger.debug(f"  {key}: {value} (from defaults)")

    def _validate_config(self):
        """Validate configuration values."""
        # Expand paths
        self.data["watch_path"] = str(
            Path(self.data["watch_path"]).expanduser().resolve()
        )

        # For local transfers, expand the remote path too
        if self.data["remote_host"] in ["localhost", "127.0.0.1", "::1"]:
            self.data["remote_base_path"] = str(
                Path(self.data["remote_base_path"]).expanduser().resolve()
            )

        # Validate transfer method
        valid_methods = ["auto", "scp", "rsync", "local"]
        if self.data.get("transfer_method") not in valid_methods:
            logger.warning(
                f"Invalid transfer_method '{self.data.get('transfer_method')}', using 'auto'"
            )
            self.data["transfer_method"] = "auto"

        # Set up logging level
        log_level = self.data.get("log_level", "INFO")
        logging.getLogger("image_transfer").setLevel(getattr(logging, log_level))

        # Log final configuration
        logger.info(f"Watching: {self.data['watch_path']}")
        logger.info(
            f"Destination: {self.data['remote_host']}:{self.data['remote_base_path']}"
        )
        logger.info(f"Transfer method: {self.data['transfer_method']}")
        if self.data.get("camera_name"):
            logger.info(f"Camera name: {self.data['camera_name']}")

    @classmethod
    def create_default_config(
        cls, path: Optional[Path] = None, format: str = "yaml"
    ) -> Path:
        """Create default configuration file in user directory."""
        if not path:
            config_dir = Path.home() / ".config" / "image-transfer"
            config_dir.mkdir(parents=True, exist_ok=True)
            path = config_dir / f"config.{format}"

        # Copy default_config.yaml to user location
        default_config_path = cls()._get_default_config_path()

        if default_config_path.exists():
            # Copy the default config file
            import shutil

            shutil.copy2(default_config_path, path)
            logger.info(f"Copied default configuration to: {path}")
        else:
            # Create from hardcoded defaults
            cls()._save_config(cls()._load_default_config(), path, format)
            logger.info(f"Created default configuration at: {path}")

        return path

    def _save_config(self, data: Dict[str, Any], path: Path, format: str = "yaml"):
        """Save configuration to file."""
        with open(path, "w") as f:
            if format == "yaml":
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(data, f, indent=2)

    def save(self, path: Optional[Path] = None):
        """Save current configuration to file."""
        save_path = path or self.config_path

        format = "yaml" if save_path.suffix in [".yaml", ".yml"] else "json"
        self._save_config(self.data, save_path, format)
        logger.info(f"Saved configuration to: {save_path}")

    def __getitem__(self, key: str) -> Any:
        """Get configuration value."""
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default."""
        return self.data.get(key, default)

    def __repr__(self) -> str:
        """String representation of config."""
        return f"Config(path={self.config_path}, transfer_method={self.data.get('transfer_method')})"
