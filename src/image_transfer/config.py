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
        "remote_base_path": "~/data/images",
        "transfer_method": "auto",
        "file_patterns": ["*.fits"],
        "compression": False,  # No compression for FITS
        "verify_transfer": True,
        "retry_attempts": 3,
        "retry_delay": 5,
    }

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration."""
        self.config_path = config_path or self._default_config_path()
        self.data = self._load_config()
        self._validate_config()

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
        if self.config_path.exists():
            logger.info(f"Loading configuration from {self.config_path}")

            with open(self.config_path, "r") as f:
                if self.config_path.suffix in [".yaml", ".yml"]:
                    config = yaml.safe_load(f)
                else:
                    config = json.load(f)

            # Merge with defaults
            return {**self.DEFAULT_CONFIG, **config}
        else:
            logger.info("Using default configuration")
            return self.DEFAULT_CONFIG.copy()

    def _validate_config(self):
        """Validate configuration values."""
        # Expand paths
        self.data["watch_path"] = str(Path(self.data["watch_path"]).expanduser())
        if self.data["remote_host"] in ["localhost", "127.0.0.1"]:
            self.data["remote_base_path"] = str(
                Path(self.data["remote_base_path"]).expanduser()
            )

    @classmethod
    def create_default_config(
        cls, path: Optional[Path] = None, format: str = "yaml"
    ) -> Path:
        """Create default configuration file."""
        config_path = path or cls._default_config_path()

        # Use specified format
        if format == "yaml" and config_path.suffix not in [".yaml", ".yml"]:
            config_path = config_path.with_suffix(".yaml")

        config_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "yaml":
            with open(config_path, "w") as f:
                yaml.dump(
                    cls.DEFAULT_CONFIG, f, default_flow_style=False, sort_keys=False
                )
        else:
            with open(config_path, "w") as f:
                json.dump(cls.DEFAULT_CONFIG, f, indent=2)

        return config_path

    def save(self, path: Optional[Path] = None):
        """Save current configuration to file."""
        save_path = path or self.config_path

        with open(save_path, "w") as f:
            if save_path.suffix in [".yaml", ".yml"]:
                yaml.dump(self.data, f, default_flow_style=False, sort_keys=False)
            else:
                json.dump(self.data, f, indent=2)

    def __getitem__(self, key: str) -> Any:
        """Get configuration value."""
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value with default."""
        return self.data.get(key, default)
