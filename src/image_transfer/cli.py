from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .transfer import Config, default_config_path, transfer_once


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="image-transfer",
        description="Rsync-based image transfer guided by a YAML config (NIGHT-aware).",
    )
    p.add_argument(
        "-c",
        "--config",
        type=Path,
        default=None,
        help="Path to config.yaml. Defaults to $IMAGE_TRANSFER_CONFIG or PROJECT_ROOT/config/config.yaml.",
    )
    p.add_argument(
        "--tz",
        default="America/Los_Angeles",
        help="Timezone for NIGHT computation (default: America/Los_Angeles).",
    )
    p.add_argument(
        "--night",
        default=None,
        help="Override NIGHT (YYYYMMDD). If omitted, computed from local time & --tz.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not actually transfer; pass --dry-run to rsync.",
    )
    # Optional overrides of config fields (useful for ad-hoc runs)
    p.add_argument(
        "--watch-path", type=Path, default=None, help="Override local watch_path."
    )
    p.add_argument("--remote-host", default=None, help="Override remote_host.")
    p.add_argument("--remote-user", default=None, help="Override remote_user.")
    p.add_argument(
        "--remote-base-path", default=None, help="Override remote_base_path (remote)."
    )

    p.add_argument(
        "--rsync-option",
        action="append",
        default=[],
        help="Extra rsync option(s) to append (can repeat).",
    )
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version and exit.",
    )
    return p


def resolve_config_path(cli_value: Path | None) -> Path:
    if cli_value:
        return cli_value.expanduser().resolve()
    auto = default_config_path()
    if auto:
        return auto
    raise SystemExit(
        "No config provided and could not locate default config.\n"
        "Provide --config /path/to/config.yaml or set IMAGE_TRANSFER_CONFIG."
    )


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    cfg_path = resolve_config_path(args.config)
    cfg = Config.from_yaml(cfg_path)

    return transfer_once(
        cfg=cfg,
        tz=args.tz,
        night_override=args.night,
        dry_run=args.dry_run,
        override_watch=args.watch_path,
        override_remote_host=args.remote_host,
        override_remote_user=args.remote_user,
        override_remote_base=args.remote_base_path,
        add_rsync_options=args.rsync_option,
    )


if __name__ == "__main__":
    sys.exit(main())
