#!/usr/bin/env python3
"""
loggingkit.py - reusable logging with:

Goals / behavior (v2):
- SAFE to import anywhere: no directories created, no handlers added unless setup_logging() is called.
- "log object available everywhere": get_log(...) returns a logger even before setup (NullHandler).
- By default: CONSOLE ONLY for common + sub logs.
- File logging is opt-in (files=True or LOG_FILES=1). Per-run directory created only when files enabled.
- Common log + sub-logs can have independent levels/formatters/rotation when files are enabled.
- Exception logging helper defaults to message-only (no stack), with opt-in stack.

Env overrides (optional):
- LOG_LEVEL: sets common + sub default level (e.g., DEBUG, INFO)
- LOG_CONSOLE_LEVEL: sets console handler level
- LOG_FILES: truthy enables file logging (1/true/yes/on)
- LOG_DIR: base directory for logs (default: ./logs)
"""
from __future__ import annotations
"""
======================================================================
 Project: Gedcom-X
 File:    logging_hub.py
 Author:  David J. Cartwright
 Purpose: provide module wide logging at context/channel level

 Created: 2025-08-25
 Updated:
   - 2025-09-09: added global kill
   - 2025-12-07: added ChannelFormatter, removed eval() in size parse,
                 fixed loggingenable alias
======================================================================
"""



import logging
import os
import sys
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from logging.handlers import RotatingFileHandler

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

@dataclass(frozen=True)
class RotationConfig:
    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 10             # keep 10 rotated files


@dataclass(frozen=True)
class FormatterConfig:
    mode: str = "human"  # "human" or "kv"
    utc: bool = True


@dataclass(frozen=True)
class LoggerSpec:
    """
    Defines a logger "channel" (sub-log).

    Notes:
    - filename == "" means "no file output for this sublog" even if files=True.
    - By default, sublogs do NOT propagate.
    """
    name: str
    filename: str = ""              # empty => no file for this sublog
    level: int = logging.INFO
    mode: str = "human"             # formatter mode for this logger
    also_to_console: Optional[bool] = None
    propagate: bool = False


@dataclass(frozen=True)
class LoggingConfig:
    """
    Main logging config.

    Defaults:
    - console only
    - no log directories created unless files=True
    """
    app_name: str = "app"

    # File logging settings (opt-in)
    files: bool = False
    base_dir: Path = Path("logs")
    run_dir_prefix: str = "run"
    common_filename: str = "common.log"

    # Levels
    common_level: int = logging.INFO
    console: bool = True
    console_level: int = logging.INFO

    rotation: RotationConfig = RotationConfig()
    formatter: FormatterConfig = FormatterConfig()

    include_run_id: bool = True
    include_host_pid: bool = True

    # Optional: define sub-logs at setup time
    sublogs: Sequence[LoggerSpec] = field(default_factory=tuple)

    # Env overrides
    env_level_var: str = "LOG_LEVEL"
    env_console_level_var: str = "LOG_CONSOLE_LEVEL"
    env_files_var: str = "LOG_FILES"
    env_dir_var: str = "LOG_DIR"


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

class _ContextFilter(logging.Filter):
    def __init__(self, app_name: str, run_id: str, include_run_id: bool, include_host_pid: bool) -> None:
        super().__init__()
        self.app_name = app_name
        self.run_id = run_id
        self.include_run_id = include_run_id
        self.include_host_pid = include_host_pid
        self.hostname = socket.gethostname()
        self.pid = os.getpid()

    def filter(self, record: logging.LogRecord) -> bool:
        record.app = self.app_name
        record.run_id = self.run_id if self.include_run_id else ""
        record.host = self.hostname if self.include_host_pid else ""
        record.pid = self.pid if self.include_host_pid else 0
        return True


def _utc_timestamp_converter(utc: bool):
    return time.gmtime if utc else time.localtime


def _make_formatter(mode: str, utc: bool) -> logging.Formatter:
    if mode == "kv":
        fmt = (
            "%(asctime)s level=%(levelname)s app=%(app)s "
            "logger=%(name)s run_id=%(run_id)s host=%(host)s pid=%(pid)s "
            "msg=%(message)s"
        )
    else:
        fmt = (
            "%(asctime)s %(levelname)s %(app)s "
            "[%(name)s] run=%(run_id)s %(host)s:%(pid)s - %(message)s"
        )

    formatter = logging.Formatter(fmt=fmt, datefmt="%Y-%m-%dT%H:%M:%SZ")
    formatter.converter = _utc_timestamp_converter(utc)
    return formatter


def _parse_level(s: str) -> Optional[int]:
    s2 = (s or "").strip().upper()
    if not s2:
        return None
    mapping = {
        "CRITICAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    return mapping.get(s2)


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _rotating_file_handler(path: Path, level: int, formatter: logging.Formatter, rotation: RotationConfig) -> RotatingFileHandler:
    _ensure_dir(path.parent)
    h = RotatingFileHandler(
        filename=str(path),
        maxBytes=rotation.max_bytes,
        backupCount=rotation.backup_count,
        encoding="utf-8",
        delay=True,
    )
    h.setLevel(level)
    h.setFormatter(formatter)
    return h


def _console_handler(level: int, formatter: logging.Formatter) -> logging.Handler:
    h = logging.StreamHandler(stream=sys.stdout)
    h.setLevel(level)
    h.setFormatter(formatter)
    return h


def _new_run_id() -> str:
    # Example: 20260201-133012
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())


def _logger_full_name(app_name: str, channel: str) -> str:
    # stable naming convention
    channel = channel.strip(".") or "common"
    return f"{app_name}.{channel}"


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

_manager: Optional["LoggingManager"] = None


def get_manager() -> Optional["LoggingManager"]:
    """Return the active LoggingManager if setup_logging() has been called."""
    return _manager


def get_log(name: str = "common", *, app_name: Optional[str] = None) -> logging.Logger:
    """
    Always returns a logger safely.
    - If setup_logging() has been called, you'll get the configured logger.
    - If not, you get a logger with a NullHandler to avoid warnings.
    """
    global _manager

    if _manager is not None:
        # If app_name not provided, use manager's.
        an = app_name or _manager.config.app_name
        return logging.getLogger(_logger_full_name(an, name))

    # Pre-setup safe logger: no output unless user configures logging elsewhere.
    an = app_name or "app"
    logger = logging.getLogger(_logger_full_name(an, name))
    # Ensure no "No handler could be found" warnings.
    if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
        logger.addHandler(logging.NullHandler())
    return logger


class LoggingManager:
    """
    Owns (optional) per-run directory, a common logger, and any number of sub-loggers.

    Defaults:
    - console only
    - subloggers also log to console by default (inherits config.console)
    - no filesystem writes unless config.files=True
    """

    def __init__(self, config: LoggingConfig) -> None:
        self.config = config

        # Only allocate run_dir/run_id if file logging is enabled.
        self.run_id = _new_run_id() if self.config.files else ""
        self.run_dir = self._compute_run_dir() if self.config.files else None
        if self.config.files and self.run_dir is not None:
            _ensure_dir(self.run_dir)

        self._context_filter = _ContextFilter(
            app_name=self.config.app_name,
            run_id=self.run_id,
            include_run_id=self.config.include_run_id,
            include_host_pid=self.config.include_host_pid,
        )

        self._formatters: Dict[str, logging.Formatter] = {
            "human": _make_formatter("human", self.config.formatter.utc),
            "kv": _make_formatter("kv", self.config.formatter.utc),
        }

        self.common_logger = self._build_common_logger()
        self._sub_loggers: Dict[str, logging.Logger] = {}

        for spec in self.config.sublogs:
            self.get_sublogger(spec)

    def _compute_run_dir(self) -> Path:
        # logs/run-20260130-205512/
        base = self.config.base_dir
        return base / f"{self.config.run_dir_prefix}-{self.run_id}"

    def common_log_path(self) -> Path:
        if not self.config.files or self.run_dir is None:
            raise RuntimeError("File logging is disabled; no common log path.")
        return self.run_dir / self.config.common_filename

    def dump_loggers(self) -> None:
        """
        Print all configured loggers and their handlers/levels.
        """
        print("=== Configured Loggers ===")

        def describe(logger: logging.Logger):
            print(f"Logger: {logger.name}")
            print(f"  level: {logging.getLevelName(logger.level)}")
            print(f"  propagate: {logger.propagate}")
            for h in logger.handlers:
                print(f"  handler: {type(h).__name__}")
                print(f"    level: {logging.getLevelName(h.level)}")
                print(f"    formatter: {h.formatter._fmt if h.formatter else None}")

        describe(self.common_logger)

        for name, logger in self._sub_loggers.items():
            describe(logger)

    def sublog_path(self, filename: str) -> Path:
        if not self.config.files or self.run_dir is None:
            raise RuntimeError("File logging is disabled; no sublog path.")
        return self.run_dir / filename

    def _effective_levels(self) -> Tuple[int, int]:
        common_level = self.config.common_level
        console_level = self.config.console_level

        env_common = _parse_level(os.getenv(self.config.env_level_var, ""))
        env_console = _parse_level(os.getenv(self.config.env_console_level_var, ""))

        if env_common is not None:
            common_level = env_common
        if env_console is not None:
            console_level = env_console

        return common_level, console_level

    def _build_common_logger(self) -> logging.Logger:
        common_level, console_level = self._effective_levels()

        logger = logging.getLogger(_logger_full_name(self.config.app_name, "common"))
        logger.setLevel(common_level)
        logger.propagate = False
        logger.handlers.clear()

        # File handler (opt-in)
        if self.config.files:
            file_formatter = self._formatters.get(self.config.formatter.mode, self._formatters["human"])
            fh = _rotating_file_handler(self.common_log_path(), common_level, file_formatter, self.config.rotation)
            fh.addFilter(self._context_filter)
            logger.addHandler(fh)

        # Console handler (default True)
        if self.config.console:
            ch = _console_handler(console_level, self._formatters["human"])
            ch.addFilter(self._context_filter)
            logger.addHandler(ch)

        return logger

    def get_common(self) -> logging.Logger:
        return self.common_logger

    def get_sublogger(self, spec: LoggerSpec) -> logging.Logger:
        if spec.name in self._sub_loggers:
            return self._sub_loggers[spec.name]

        common_level, console_level = self._effective_levels()

        logger = logging.getLogger(_logger_full_name(self.config.app_name, spec.name))
        logger.setLevel(spec.level)
        logger.propagate = spec.propagate
        logger.handlers.clear()

        formatter = self._formatters.get(spec.mode, self._formatters["human"])

        # File handler (only if enabled and spec.filename not empty)
        if self.config.files and spec.filename:
            fh = _rotating_file_handler(self.sublog_path(spec.filename), spec.level, formatter, self.config.rotation)
            fh.addFilter(self._context_filter)
            logger.addHandler(fh)

        # Console handler:
        # - default is inherit config.console (so YES by default)
        # - spec.also_to_console can force True/False
        if spec.also_to_console is None:
            wants_console = self.config.console
        else:
            wants_console = bool(spec.also_to_console)

        if wants_console:
            # Console level: use console_level; if you want sublogs noisier than common, set env LOG_CONSOLE_LEVEL or config.
            ch = _console_handler(console_level, self._formatters["human"])
            ch.addFilter(self._context_filter)
            logger.addHandler(ch)

        self._sub_loggers[spec.name] = logger
        return logger

    def child(self, name: str, *, level: int = logging.INFO, mode: str = "human") -> logging.Logger:
        """
        Convenience: create a sublogger with defaults.
        - When files=True: writes to {name}.log in the per-run directory.
        - When files=False: console-only.
        """
        filename = f"{name}.log" if self.config.files else ""
        spec = LoggerSpec(name=name, filename=filename, level=level, mode=mode, also_to_console=None, propagate=False)
        return self.get_sublogger(spec)

    # ---------------------------
    # Exception helpers
    # ---------------------------

    @staticmethod
    def log_error(
        logger: logging.Logger,
        msg: str,
        *args,
        exc: Optional[BaseException] = None,
        stack: bool = False,
    ) -> None:
        """
        Default: message-only for errors. If `stack=True`, include full traceback.
        - stack=False: "ERROR ... msg: <exc>"
        - stack=True: logs traceback too
        """
        if exc is None:
            logger.error(msg, *args)
            return

        if stack:
            logger.error("%s: %s", msg, str(exc), exc_info=exc)
        else:
            logger.error("%s: %s", msg, str(exc))


def setup_logging(
    app_name: str,
    base_dir: Path = Path("logs"),
    *,
    # defaults = console-only
    console: bool = True,
    files: bool = False,

    common_filename: str = "common.log",
    common_level: int = logging.INFO,
    console_level: int = logging.INFO,

    rotation_max_bytes: int = 10 * 1024 * 1024,
    rotation_backup_count: int = 10,

    formatter_mode: str = "human",
    utc_timestamps: bool = True,

    sublogs: Sequence[LoggerSpec] = (),
) -> LoggingManager:
    """
    One-call setup for scripts.

    Defaults:
    - console=True
    - files=False  (no log dirs/files created)

    Env can override:
    - LOG_FILES=1 enables file logging
    - LOG_DIR=/path/to/logs overrides base_dir
    - LOG_LEVEL / LOG_CONSOLE_LEVEL override levels
    """
    global _manager

    # Env overrides for files/dir (but explicit args still win unless you want env to override hard)
    env_files = _env_truthy("LOG_FILES")
    env_dir = os.getenv("LOG_DIR", "").strip()

    effective_files = files or env_files
    effective_base_dir = Path(env_dir) if env_dir else base_dir

    cfg = LoggingConfig(
        app_name=app_name,
        files=effective_files,
        base_dir=effective_base_dir,
        common_filename=common_filename,
        common_level=common_level,
        console=console,
        console_level=console_level,
        rotation=RotationConfig(max_bytes=rotation_max_bytes, backup_count=rotation_backup_count),
        formatter=FormatterConfig(mode=formatter_mode, utc=utc_timestamps),
        sublogs=sublogs,
    )

    _manager = LoggingManager(cfg)
    return _manager


def log_exists(self, name: str) -> bool:
    """
    Return True if a logger with this channel name has been configured
    (either common or a sublogger).
    """
    if name in ("common", "", None):
        return True

    return name in self._sub_loggers
