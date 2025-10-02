"""Configuration management for image transfer daemon."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager for the image transfer daemon."""

    DEFAULT_CONFIG = {
        "watch_path": "~/data/images",
        "remote_host": "localhost",
        "remote_user": "user",
        "remote_base_path": "/data/images",
        "transfer_method": "auto",
        "file_patterns": ["*.fits"],
        "compression": False,  # No compression for FITS
        "verify_transfer": True,
        "retry_attempts": 3,
        "retry_delay": 5,
    }

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration."""
        if config_path:
            config_path = self._resolve_config_path(config_path)

        self.config_path = config_path or self._default_config_path()
        self.data = self._load_config()
        self._validate_config()

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
        logger.info("Using default configuration instead")
        return None

    @classmethod
    def _default_config_path(cls) -> Path:
        """Get default configuration path."""
        config_dir = Path.home() / ".config" / "image-transfer"
        # Check for YAML first, then JSON
        yaml_path = config_dir / "config.yaml"
        json_path = config_dir / "config.json"

        if yaml_path.exists():
            return yaml_path
        return json_path

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML or JSON file."""
        if self.config_path and self.config_path.exists():
            logger.info(f"Loading configuration from {self.config_path}")

            with open(self.config_path, "r") as f:
                if self.config_path.suffix in [".yaml", ".yml"]:
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)

            # Merge with defaults
            merged_config = {**self.DEFAULT_CONFIG, **config}

            # Log which settings are being used
            logger.debug("Configuration settings:")
            for key, value in merged_config.items():
                if key in config:
                    logger.debug(f"  {key}: {value} (from config file)")
                else:
                    logger.debug(f"  {key}: {value} (default)")

            return merged_config
        else:
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()

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

        # Log final configuration
        logger.info(f"Watching: {self.data['watch_path']}")
        logger.info(
            f"Destination: {self.data['remote_host']}:{self.data['remote_base_path']}"
        )
        logger.info(f"Transfer method: {self.data['transfer_method']}")

    @classmethod
    def create_default_config(
        cls, path: Optional[Path] = None, format: str = "yaml"
    ) -> Path:
        """Create default configuration file."""
        if not path:
            config_dir = Path.home() / ".config" / "image-transfer"
            path = config_dir / f"config.{format}"

        path.parent.mkdir(parents=True, exist_ok=True)

        if format == "yaml":
            with open(path, "w") as f:
                # Add helpful comments to the YAML
                f.write("# Image Transfer Daemon Configuration\n")
                f.write("# Edit this file to match your setup\n\n")
                yaml.dump(
                    cls.DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False
                )
        else:
            with open(path, "w") as f:
                json.dump(cls.DEFAULT_CONFIG, f, indent=2)

        logger.info(f"Created default configuration at: {path}")
        return path

    def save(self, path: Optional[Path] = None):
        """Save current configuration to file."""
        save_path = path or self.config_path

        with open(save_path, "w") as f:
            if save_path.suffix in [".yaml", ".yml"]:
                yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(self.data, f, indent=2)

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
