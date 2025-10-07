#!/usr/bin/env python3
from __future__ import annotations

import fnmatch
import logging
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, List, Sequence

import pytz
import yaml

# -------------------------- Constants --------------------------

# Non-negotiable rsync flags (pinned in code)
REQUIRED_RSYNC_OPTS: list[str] = [
    "-aP",  # archive + progress (drop 'v' to reduce noise; keep -P so progress goes to stderr)
    "--mkpath",  # create destination dirs (requires newer rsync)
    "--out-format=%i %n",  # machine-parsable itemized output for robust copy/skip detection
]


# -------------------------- Night helper --------------------------


def tonight_local(
    timestamp: str | float = "now", tz: str = "America/Los_Angeles"
) -> str:
    """
    Define the "night" as 08:00 local time to 07:59 next day (local).
    Returns YYYYMMDD string for the "night" date.
    """
    tzinfo = pytz.timezone(tz)
    if timestamp == "now":
        now_local = datetime.now(tzinfo)
    else:
        if isinstance(timestamp, (int, float)):
            now_local = datetime.fromtimestamp(timestamp, tzinfo)
        else:
            try:
                now_local = datetime.fromtimestamp(float(timestamp), tzinfo)
            except Exception:
                now_local = datetime.now(tzinfo)

    if 0 <= now_local.hour < 8:
        now_local = now_local - timedelta(days=1)

    return now_local.strftime("%Y%m%d")


# -------------------------- Config model --------------------------


@dataclass
class Config:
    watch_path: Path
    remote_host: str
    remote_user: str
    remote_base_path: str
    file_patterns: List[str]
    log_level: str
    log_directory: Path
    log_file: str
    min_file_age_seconds: int
    exclude_patterns: List[str]
    log_max_bytes: int = 50 * 1024 * 1024  # 50 MB
    log_backup_count: int = 5

    @staticmethod
    def from_yaml(path: Path) -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # Warn (but ignore) if legacy rsync_options is present
        if "rsync_options" in data:
            logging.warning(
                "Ignoring 'rsync_options' in config; rsync flags are pinned in code."
            )

        file_patterns = data.get("file_patterns") or ["*.fits", "*.FITS"]
        exclude_patterns = data.get("exclude_patterns") or []

        return Config(
            watch_path=Path(os.path.expanduser(data["watch_path"])),
            remote_host=str(data["remote_host"]),
            remote_user=str(data["remote_user"]),
            remote_base_path=str(data["remote_base_path"]),
            file_patterns=[str(p) for p in file_patterns],
            log_level=str(data.get("log_level", "INFO")).upper(),
            log_directory=Path(os.path.expanduser(data.get("log_directory", "~/logs"))),
            log_file=str(data.get("log_file", "image_transfer.log")),
            min_file_age_seconds=int(data.get("min_file_age_seconds", 2)),
            exclude_patterns=[str(p) for p in exclude_patterns],
            log_max_bytes=int(data.get("log_max_bytes", 50 * 1024 * 1024)),
            log_backup_count=int(data.get("log_backup_count", 5)),
        )


# -------------------------- Utilities --------------------------


def default_config_path() -> Path | None:
    """Return default config path inside the installed package's config dir."""
    try:
        from image_transfer.paths import (
            CONFIG_DIR,  # provided elsewhere in your package
        )

        return Path(CONFIG_DIR, "config.yaml")
    except Exception:
        return None


def replace_night_placeholder(p: str | Path, night: str) -> str:
    return str(p).replace("NIGHT", night)


def list_candidate_files(
    root: Path,
    include_patterns: Sequence[str],
    exclude_patterns: Sequence[str],
) -> Iterable[Path]:
    """Yield files under root that match include_patterns and not exclude_patterns (case-insensitive)."""
    inc_lower = [pat.lower() for pat in include_patterns]
    exc_lower = [pat.lower() for pat in exclude_patterns]

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        name_lower = path.name.lower()
        if inc_lower and not any(
            fnmatch.fnmatchcase(name_lower, pat) for pat in inc_lower
        ):
            continue
        if exc_lower and any(fnmatch.fnmatchcase(name_lower, pat) for pat in exc_lower):
            continue
        yield path


def is_stable_file(path: Path, min_age_seconds: int) -> bool:
    """Return True if file mtime is at least min_age_seconds in the past."""
    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError:
        return False
    age = datetime.now().timestamp() - mtime
    return age >= min_age_seconds


def ensure_logging(
    log_dir: Path,
    log_file: str,
    level: str = "INFO",
    max_bytes: int = 50 * 1024 * 1024,
    backup_count: int = 5,
) -> None:
    """Set up rotating logging to file + stream."""
    from logging.handlers import RotatingFileHandler

    log_dir.mkdir(parents=True, exist_ok=True)
    logfile = log_dir / log_file

    logger = logging.getLogger()  # root logger
    logger.setLevel(getattr(logging, level, logging.INFO))

    # Make idempotent: clear existing handlers so we don’t double-log
    if logger.handlers:
        logger.handlers.clear()

    file_handler = RotatingFileHandler(
        logfile, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    stream_handler = logging.StreamHandler(sys.stdout)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)


def check_rsync_available() -> None:
    from shutil import which

    if which("rsync") is None:
        raise RuntimeError(
            "rsync not found in PATH. Install it (e.g., `sudo apt install rsync`)."
        )


def build_rsync_cmd(
    src_file: Path,
    remote_user: str,
    remote_host: str,
    remote_dir: str,
    rsync_options: Sequence[str],
) -> list[str]:
    remote_spec = f"{remote_user}@{remote_host}:{remote_dir}"
    return ["rsync", *rsync_options, str(src_file), remote_spec]


def sanitize_rsync_options(opts: list[str]) -> list[str]:
    """
    Glue split --out-format arguments and return a sanitized list.
    e.g. ["--out-format", "%i %n"] -> ["--out-format=%i %n"]
         ["--out-format=%i", "%n"] -> ["--out-format=%i %n"]
    """
    out: list[str] = []
    i = 0
    while i < len(opts):
        o = opts[i]
        if o == "--out-format" and i + 1 < len(opts):
            out.append(f"--out-format={opts[i+1]}")
            i += 2
            continue
        if o.startswith("--out-format="):
            if i + 1 < len(opts) and opts[i + 1].startswith("%") and " " in opts[i + 1]:
                # unlikely, but join if someone split the format string oddly
                out.append(f"{o} {opts[i+1]}")
                i += 2
                continue
            out.append(o)
            i += 1
            continue
        if o.startswith("--out-format=%") and i + 1 < len(opts) and "%n" in opts[i + 1]:
            out.append(f"{o} {opts[i+1]}")
            i += 2
            continue
        out.append(o)
        i += 1
    return out


def _dedupe(seq: list[str]) -> list[str]:
    seen = set()
    out: list[str] = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


# -------------------------- rsync execution & parsing --------------------------

ITEMIZED_RE = re.compile(r"^(?P<icode>[<>ch\.][^\s]*)\s+(?P<name>.+)$")


def run_rsync_cmd(cmd: list[str]) -> tuple[int, bool, list[str]]:
    """
    Run rsync and detect whether at least one file was actually transferred.

    Returns (rc, copied_any, itemized_lines)
    """
    proc = subprocess.run(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )

    stdout = proc.stdout or ""
    stderr = proc.stderr or ""

    lines = [ln.strip() for ln in stdout.splitlines() if ln.strip()]
    if stderr.strip():
        logging.debug("rsync stderr:\n%s", stderr.strip())

    copied_any = False
    itemized: list[str] = []
    for ln in lines:
        m = ITEMIZED_RE.match(ln)
        if not m:
            continue
        itemized.append(ln)
        code = m.group("icode")
        # '<f' = sender wrote/sent a regular file, '>f' = receiver wrote a regular file
        if code.startswith(("<f", ">f")):
            copied_any = True

    if proc.returncode != 0:
        logging.error(
            "rsync failed (%d)\nSTDOUT:\n%s\nSTDERR:\n%s",
            proc.returncode,
            stdout.strip(),
            stderr.strip(),
        )
    else:
        if itemized:
            logging.debug("rsync itemized:\n%s", "\n".join(itemized))

    return proc.returncode, copied_any, itemized


# -------------------------- Main transfer --------------------------


def transfer_once(
    cfg: Config,
    tz: str = "America/Los_Angeles",
    night_override: str | None = None,
    dry_run: bool = False,
    override_watch: Path | None = None,
    override_remote_host: str | None = None,
    override_remote_user: str | None = None,
    override_remote_base: str | None = None,
    add_rsync_options: Sequence[str] | None = None,
) -> int:
    night = night_override or tonight_local("now", tz=tz)

    watch_path_str = replace_night_placeholder(override_watch or cfg.watch_path, night)
    remote_base_str = replace_night_placeholder(
        override_remote_base or cfg.remote_base_path, night
    )
    watch_root = Path(os.path.expanduser(str(watch_path_str)))

    ensure_logging(
        cfg.log_directory,
        cfg.log_file,
        cfg.log_level,
        max_bytes=cfg.log_max_bytes,
        backup_count=cfg.log_backup_count,
    )

    try:
        check_rsync_available()
    except RuntimeError as e:
        logging.critical(str(e))
        return 2

    logging.info("Night = %s", night)
    logging.info("Local watch path: %s", watch_root)
    logging.info("Remote base path: %s", remote_base_str)

    remote_host = override_remote_host or cfg.remote_host
    remote_user = override_remote_user or cfg.remote_user
    logging.info("Remote: %s@%s", remote_user, remote_host)

    if not watch_root.exists():
        logging.error("Watch path does not exist: %s", watch_root)
        return 1

    candidates = list(
        list_candidate_files(watch_root, cfg.file_patterns, cfg.exclude_patterns)
    )
    if not candidates:
        logging.info("No files found matching patterns.")
        return 0

    stable_files = [
        p for p in candidates if is_stable_file(p, cfg.min_file_age_seconds)
    ]
    skipped = len(candidates) - len(stable_files)
    if skipped:
        logging.info("Skipped %d file(s) not yet stable.", skipped)

    if not stable_files:
        logging.info("No stable files to transfer.")
        return 0

    # Build effective rsync options ONCE
    rsync_opts = list(REQUIRED_RSYNC_OPTS)
    if dry_run and "--dry-run" not in rsync_opts and "-n" not in rsync_opts:
        rsync_opts.append("--dry-run")
    if add_rsync_options:
        rsync_opts.extend(add_rsync_options)
    rsync_opts = sanitize_rsync_options(_dedupe(rsync_opts))

    failures = 0
    for src in sorted(stable_files):
        rel = src.relative_to(watch_root)
        remote_dir = (
            f"{remote_base_str}/{rel.parent.as_posix()}"
            if rel.parent.as_posix() != "."
            else remote_base_str
        )

        cmd = build_rsync_cmd(
            src_file=src,
            remote_user=remote_user,
            remote_host=remote_host,
            remote_dir=remote_dir,
            rsync_options=rsync_opts,
        )

        logging.debug("Executing: %s", " ".join(shlex.quote(c) for c in cmd))
        rc, copied, lines = run_rsync_cmd(cmd)
        logging.debug("rsync returned rc=%s, copied=%s", rc, copied)
        logging.debug("itemized lines: %r", lines)
        if rc != 0:
            failures += 1
        elif copied:
            logging.info("Copied: %s", src)
        else:
            logging.info("Skipped (exists/up-to-date): %s", src)

    if failures:
        logging.error(
            "Completed with %d failure(s) out of %d files.", failures, len(stable_files)
        )
        return 3

    logging.info("Transfer complete. %d file(s) transferred.", len(stable_files))
    return 0
