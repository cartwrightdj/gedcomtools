from __future__ import annotations
"""
======================================================================
 Project: gedcomtools
 File:    loggingkit.py
 Author:  David J. Cartwright
 Purpose: Reusable logging utilities backed by loguru with setup and channel management

 Created: 2025-07-01
 Updated:

======================================================================
"""
"""
Reusable logging utilities backed by loguru.

Safe to import anywhere: no directories created or handlers attached unless
setup_logging() is called.

Usage:
    # Once at your CLI entrypoint:
    setup_logging("myapp", files=True, base_dir=Path("logs"))

    # In any module:
    log = get_log(__name__)
    log.info("started processing {}", name)

Environment variable overrides (optional):
    LOG_LEVEL           common + file handler level  (e.g. DEBUG, INFO)
    LOG_CONSOLE_LEVEL   console handler level
    LOG_FILES           truthy (1/true/yes/on) enables file logging
    LOG_DIR             overrides base_dir
"""

import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence, Union

from loguru import logger as _logger
from loguru import _Logger as Logger

# Set safe defaults so format strings with {extra[module]} / {extra[channel]}
# never raise KeyError even on loggers that skip bind().
_logger.configure(extra={"module": "", "channel": ""})


# ─────────────────────────────────────────────────────────────────────────────
# Config dataclasses  (API-compatible with the old loggingkit)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RotationConfig:
    """Rotation settings for file sinks."""
    max_bytes: int = 10 * 1024 * 1024   # 10 MB
    backup_count: int = 10


@dataclass(frozen=True)
class FormatterConfig:
    """Formatter settings (kept for API compatibility)."""
    mode: str = "human"   # "human" | "kv"
    utc: bool = True


@dataclass(frozen=True)
class LoggerSpec:
    """Definition of a sub-logger (channel).

    Attributes:
        name:           Channel name (e.g. "graph", "io").
        filename:       File name for this channel when file logging is on.
                        Empty string disables file output for this channel.
        level:          Logger level (int or levelname string).
        mode:           Formatter mode ("human" | "kv").
        also_to_console: None = inherit config.console; True/False = force.
        propagate:      Kept for API compat; loguru does not use this.
    """
    name: str
    filename: str = ""
    level: Union[int, str] = 20   # logging.INFO
    mode: str = "human"
    also_to_console: Optional[bool] = None
    propagate: bool = False


@dataclass(frozen=True)
class LoggingConfig:
    """Full logging configuration (mirrors old API)."""
    app_name: str = "app"
    files: bool = False
    base_dir: Path = Path("logs")
    run_dir_prefix: str = "run"
    common_filename: str = "common.log"
    common_level: Union[int, str] = 20   # logging.INFO
    console: bool = True
    console_level: Union[int, str] = 20
    rotation: RotationConfig = field(default_factory=RotationConfig)
    formatter: FormatterConfig = field(default_factory=FormatterConfig)
    include_run_id: bool = True
    include_host_pid: bool = True
    sublogs: Sequence[LoggerSpec] = field(default_factory=tuple)
    env_level_var: str = "LOG_LEVEL"
    env_console_level_var: str = "LOG_CONSOLE_LEVEL"
    env_files_var: str = "LOG_FILES"
    env_dir_var: str = "LOG_DIR"


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

_LEVEL_MAP: dict = {
    10: "DEBUG", 20: "INFO", 30: "WARNING", 40: "ERROR", 50: "CRITICAL",
    "DEBUG": "DEBUG", "INFO": "INFO",
    "WARNING": "WARNING", "WARN": "WARNING",
    "ERROR": "ERROR", "CRITICAL": "CRITICAL",
    "NOTSET": "TRACE",
}


def _to_level(level: Union[int, str]) -> str:
    if isinstance(level, str):
        return _LEVEL_MAP.get(level.strip().upper(), "INFO")
    return _LEVEL_MAP.get(level, "INFO")


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())


# ─────────────────────────────────────────────────────────────────────────────
# LoggingManager
# ─────────────────────────────────────────────────────────────────────────────

class LoggingManager:
    """Owns the loguru sink IDs and run directory for this process.

    Returned by setup_logging(); also accessible via get_manager().
    """

    def __init__(self, config: LoggingConfig, run_dir: Optional[Path], sink_ids: list[int]) -> None:
        self.config = config
        self.run_dir = run_dir
        self.run_id = run_dir.name.split("-", 1)[-1] if run_dir else ""
        self._sink_ids = sink_ids

    def get_common(self) -> Logger:
        return _logger.bind(module=f"{self.config.app_name}.common")

    def get_sublogger(self, spec: LoggerSpec) -> Logger:
        return _logger.bind(module=f"{self.config.app_name}.{spec.name}")

    def child(self, name: str, **_) -> Logger:
        return _logger.bind(module=f"{self.config.app_name}.{name}")

    def log_exists(self, name: str) -> bool:
        return True

    def common_log_path(self) -> Path:
        if not self.run_dir:
            raise RuntimeError("File logging is disabled; no common log path.")
        return self.run_dir / self.config.common_filename

    def sublog_path(self, filename: str) -> Path:
        if not self.run_dir:
            raise RuntimeError("File logging is disabled; no sublog path.")
        return self.run_dir / filename

    def dump_loggers(self) -> None:
        print(f"=== loggingkit (loguru) — {len(self._sink_ids)} active sink(s) ===")
        for i, sid in enumerate(self._sink_ids):
            print(f"  sink[{i}] id={sid}")

    @staticmethod
    def log_error(
        log: Logger,
        msg: str,
        *args,
        exc: Optional[BaseException] = None,
        stack: bool = False,
    ) -> None:
        if args:
            msg = f"{msg} | " + " ".join(str(a) for a in args)
        if isinstance(exc, str) and exc:
            msg = f"{msg} | {exc}"
            exc = None
        if exc is None:
            log.error(msg)
        elif stack:
            log.opt(exception=exc).error(msg)
        else:
            log.error(f"{msg} | {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# Module-level state
# ─────────────────────────────────────────────────────────────────────────────

_manager: Optional[LoggingManager] = None

_CONSOLE_FMT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{extra[module]}</cyan> - <level>{message}</level>"
)

_FILE_FMT = "{time:YYYY-MM-DDTHH:mm:ssZ} | {level:<8} | {extra[module]} | {extra[channel]} | {message}"


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_manager() -> Optional[LoggingManager]:
    """Return the active LoggingManager, or None if setup_logging() not called."""
    return _manager


def get_log(name: str = "common", *, app_name: Optional[str] = None) -> Logger:
    """Return a loguru logger bound to *name*. Safe before setup_logging()."""
    return _logger.bind(module=name)


def get_module_log(module_name: str, *, app_name: Optional[str] = None) -> Logger:
    """Convenience alias: use as ``log = get_module_log(__name__)``."""
    return get_log(module_name, app_name=app_name)


def setup_logging(
    app_name: str,
    base_dir: Path = Path("logs"),
    *,
    console: bool = True,
    files: bool = False,
    common_filename: str = "common.log",
    common_level: Union[int, str] = 20,
    console_level: Union[int, str] = 20,
    rotation_max_bytes: int = 10 * 1024 * 1024,
    rotation_backup_count: int = 10,
    formatter_mode: str = "human",
    utc_timestamps: bool = True,
    sublogs: Sequence[LoggerSpec] = (),
) -> LoggingManager:
    """Configure loguru for this process.  Call once from your entrypoint.

    Safe import: importing this module does NOT create directories or attach
    handlers.  Only calling this function does.

    Args:
        app_name:              Namespace prefix for all loggers.
        base_dir:              Base directory for per-run logs (files=True only).
        console:               Enable console output.
        files:                 Enable per-run file logging.
        common_filename:       Filename for the catch-all log (files=True only).
        common_level:          Level for file sinks.
        console_level:         Level for the console sink.
        rotation_max_bytes:    Rotate file after this many bytes.
        rotation_backup_count: Rotated files to keep.
        formatter_mode:        "human" or "kv" (future use; loguru handles fmt).
        utc_timestamps:        UTC timestamps in file sinks.
        sublogs:               Per-channel LoggerSpec list created at setup time.

    Returns:
        LoggingManager: the active manager.
    """
    global _manager

    # ── env overrides ──────────────────────────────────────────────────────────
    env_level         = os.getenv("LOG_LEVEL", "").strip().upper()
    env_console_level = os.getenv("LOG_CONSOLE_LEVEL", "").strip().upper()
    env_files         = _env_truthy("LOG_FILES")
    env_dir           = os.getenv("LOG_DIR", "").strip()

    eff_level         = _to_level(env_level or common_level)
    eff_console_level = _to_level(env_console_level or console_level)
    eff_files         = files or env_files
    eff_base_dir      = Path(env_dir) if env_dir else base_dir

    # ── tear down previous configuration ──────────────────────────────────────
    if _manager is not None:
        for sid in _manager._sink_ids:
            try:
                _logger.remove(sid)
            except Exception:
                pass

    # Remove loguru's default stderr sink (id=0) on first call
    try:
        _logger.remove(0)
    except Exception:
        pass

    sink_ids: list[int] = []

    # ── console sink ──────────────────────────────────────────────────────────
    if console:
        sid = _logger.add(
            sys.stdout,
            format=_CONSOLE_FMT,
            level=eff_console_level,
            colorize=True,
        )
        sink_ids.append(sid)

    # ── file sinks (opt-in) ───────────────────────────────────────────────────
    run_dir: Optional[Path] = None
    if eff_files:
        run_dir = eff_base_dir / f"run-{_new_run_id()}"
        run_dir.mkdir(parents=True, exist_ok=True)

        # catch-all common log
        sid = _logger.add(
            str(run_dir / common_filename),
            format=_FILE_FMT,
            level=eff_level,
            rotation=rotation_max_bytes,
            retention=rotation_backup_count,
            encoding="utf-8",
        )
        sink_ids.append(sid)

        # per-channel sublogs
        for spec in sublogs:
            if spec.filename:
                channel = spec.name
                sid = _logger.add(
                    str(run_dir / spec.filename),
                    format=_FILE_FMT,
                    level=_to_level(spec.level),
                    filter=lambda r, ch=channel: r["extra"].get("channel") == ch,
                    rotation=rotation_max_bytes,
                    retention=rotation_backup_count,
                    encoding="utf-8",
                )
                sink_ids.append(sid)

    _manager = LoggingManager(
        config=LoggingConfig(
            app_name=app_name,
            files=eff_files,
            base_dir=eff_base_dir,
            common_filename=common_filename,
            common_level=common_level,
            console=console,
            console_level=console_level,
            rotation=RotationConfig(max_bytes=rotation_max_bytes, backup_count=rotation_backup_count),
            formatter=FormatterConfig(mode=formatter_mode, utc=utc_timestamps),
            sublogs=sublogs,
        ),
        run_dir=run_dir,
        sink_ids=sink_ids,
    )
    return _manager


def log_failure(
    log: Logger,
    message: str,
    exc=None,
    details: Optional[str] = None,
    stack: bool = False,
) -> None:
    """Safe logging helper compatible with the old API."""
    parts = [message]
    if details:
        parts.append(details)
    if isinstance(exc, str) and exc:
        parts.append(exc)
        exc = None
    final = " | ".join(parts)
    if exc is not None and stack:
        log.opt(exception=exc).error(final)
    elif exc is not None:
        log.error(f"{final}: {exc}")
    else:
        log.error(final)
