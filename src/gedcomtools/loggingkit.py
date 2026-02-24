#!/usr/bin/env python3
"""
Reusable logging utilities for console + optional per-run file logging.

This module provides a small "logging hub" that is safe to import anywhere:
it does not create directories or attach handlers unless `setup_logging()` is
called.

Style 1 behavior (your choice):
- Call `setup_logging()` once in your entrypoint.
- Everywhere else, call `get_log(__name__)` (or `get_module_log(__name__)`).
- Each logger gets its own console handler (by default) and does NOT propagate,
  so modules are independent and don't require a configured root logger.

File logging is opt-in:
- Enable with `files=True` or `LOG_FILES=1`.
- When enabled, a per-run directory is created and handlers may rotate.

Environment variables (optional overrides):
- LOG_LEVEL: sets common + sub default level (e.g., DEBUG, INFO)
- LOG_CONSOLE_LEVEL: sets console handler level
- LOG_FILES: truthy enables file logging (1/true/yes/on)
- LOG_DIR: base directory for logs (default: ./logs)
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import time
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple



# ---------------------------------------------------------------------
# ANSI color support (console only)
# ---------------------------------------------------------------------

_RESET = "\x1b[0m"
_DIM = "\x1b[2m"

_LEVEL_TO_COLOR = {
    logging.CRITICAL: "\x1b[31;1m",  # bright red
    logging.ERROR: "\x1b[31m",       # red
    logging.WARNING: "\x1b[33m",     # yellow
    logging.INFO: "\x1b[32m",        # green
    logging.DEBUG: "\x1b[34m",       # blue
}

def _supports_color(stream) -> bool:
    # Respect NO_COLOR (https://no-color.org/)
    if os.getenv("NO_COLOR", "").strip():
        return False

    # If not a TTY, don't emit escape sequences
    try:
        if not hasattr(stream, "isatty") or not stream.isatty():
            return False
    except Exception:
        return False

    # Windows: modern terminals support ANSI; if not, colorama can help
    if os.name == "nt":
        # Try enabling colorama if present (safe no-op if absent)
        try:
            import colorama  # type: ignore
            colorama.just_fix_windows_console()
        except Exception:
            # If colorama isn't installed, still attempt ANSI (often works on Win10+)
            pass

    return True


class _AnsiColorFormatter(logging.Formatter):
    """
    Wraps an existing formatter and adds ANSI colors to the level name (and optionally the whole line).
    """
    def __init__(self, base: logging.Formatter, *, stream) -> None:
        # We delegate formatting to `base`
        super().__init__(fmt=base._fmt, datefmt=base.datefmt)
        self.base = base
        self.stream = stream
        self.enable = _supports_color(stream)

    def format(self, record: logging.LogRecord) -> str:
        # Let the base formatter produce the line (with asctime etc.)
        msg = self.base.format(record)

        if not self.enable:
            return msg

        color = _LEVEL_TO_COLOR.get(record.levelno, "")
        if not color:
            return msg

        # Colorize the first occurrence of the level name token in the rendered line.
        # Your format includes "%(levelname)s" early, so this is reliable.
        level = record.levelname
        colored_level = f"{color}{level}{_RESET}"

        return msg.replace(level, colored_level, 1)

# ---------------------------------------------------------------------
# Config models
# ---------------------------------------------------------------------


@dataclass(frozen=True)
class RotationConfig:
    """Rotation settings for file handlers.

    Attributes:
        max_bytes: Maximum size of a log file before rotation occurs.
        backup_count: Number of rotated files to keep.
    """

    max_bytes: int = 10 * 1024 * 1024  # 10 MB
    backup_count: int = 10


@dataclass(frozen=True)
class FormatterConfig:
    """Formatter settings.

    Attributes:
        mode: Formatter mode ("human" or "kv").
        utc: If True, timestamps are emitted in UTC; otherwise local time.
    """

    mode: str = "human"  # "human" or "kv"
    utc: bool = True


@dataclass(frozen=True)
class LoggerSpec:
    """Definition of a sub-logger (a "channel").

    Notes:
        - `filename == ""` means "no file output for this sublog" even if files=True.
        - In Style 1, sublogs do NOT propagate by default.

    Attributes:
        name: Channel name (e.g., "graph", "io", "import").
        filename: File name for this channel when file logging is enabled.
        level: Logger level for this channel.
        mode: Formatter mode ("human" or "kv") for this channel.
        also_to_console: If None, inherit from LoggingConfig.console; otherwise force.
        propagate: Whether this logger propagates to its parent. Default False (Style 1).
    """

    name: str
    filename: str = ""
    level: int = logging.INFO
    mode: str = "human"
    also_to_console: Optional[bool] = None
    propagate: bool = False


@dataclass(frozen=True)
class LoggingConfig:
    """Main logging configuration.

    Defaults:
        - Console-only
        - No log directories created unless `files=True`

    Attributes:
        app_name: Stable prefix for logger names (e.g., "gedcomtools").
        files: Enable per-run file logging.
        base_dir: Base directory for logs (used only when files=True).
        run_dir_prefix: Directory prefix for per-run directory under base_dir.
        common_filename: Filename for the common log when files=True.

        common_level: Level for the common logger.
        console: Enable console output.
        console_level: Level for console handlers.

        rotation: RotationConfig for file handlers.
        formatter: FormatterConfig for formatting.

        include_run_id: Include run_id in formatted output.
        include_host_pid: Include host and PID in formatted output.

        sublogs: Optional logger specs to create at setup time.

        env_level_var: Env var name for common/sub default level.
        env_console_level_var: Env var name for console handler level.
        env_files_var: Env var name to enable file logging.
        env_dir_var: Env var name for base directory override.
    """

    app_name: str = "app"

    # File logging (opt-in)
    files: bool = False
    base_dir: Path = Path("logs")
    run_dir_prefix: str = "run"
    common_filename: str = "common.log"

    # Levels / console
    common_level: int = logging.INFO
    console: bool = True
    console_level: int = logging.INFO

    rotation: RotationConfig = RotationConfig()
    formatter: FormatterConfig = FormatterConfig()

    include_run_id: bool = True
    include_host_pid: bool = True

    sublogs: Sequence[LoggerSpec] = field(default_factory=tuple)

    env_level_var: str = "LOG_LEVEL"
    env_console_level_var: str = "LOG_CONSOLE_LEVEL"
    env_files_var: str = "LOG_FILES"
    env_dir_var: str = "LOG_DIR"


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------


class _ContextFilter(logging.Filter):
    """Injects contextual fields into log records.

    Adds:
        app, run_id, host, pid
    """

    def __init__(
        self,
        app_name: str,
        run_id: str,
        include_run_id: bool,
        include_host_pid: bool,
    ) -> None:
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


def _rotating_file_handler(
    path: Path,
    level: int,
    formatter: logging.Formatter,
    rotation: RotationConfig,
) -> RotatingFileHandler:
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

    # Wrap with color formatter for console only
    h.setFormatter(_AnsiColorFormatter(formatter, stream=h.stream))
    return h



def _new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())


def _logger_full_name(app_name: str, channel: Optional[str]) -> str:
    """Build a stable logger name under the app namespace."""
    ch = (channel or "common").strip(".") or "common"
    return f"{app_name}.{ch}"


# ---------------------------------------------------------------------
# Public API (v2)
# ---------------------------------------------------------------------

_manager: Optional["LoggingManager"] = None


def get_manager() -> Optional["LoggingManager"]:
    """Return the active LoggingManager if setup_logging() has been called.

    Returns:
        LoggingManager | None: The current manager instance, or None if not configured.
    """
    return _manager


def get_log(name: str = "common", *, app_name: Optional[str] = None) -> logging.Logger:
    """
    Always returns a logger safely.

    Style 1:
    - After setup_logging(), this will ensure the logger is configured (console handler
      attached, no propagation by default) the first time it is requested.
    - Before setup_logging(), returns a logger with NullHandler (no output, no warnings).
    """
    global _manager

    # Pre-setup safe logger
    if _manager is None:
        an = app_name or "app"
        logger = logging.getLogger(_logger_full_name(an, name))
        if not any(isinstance(h, logging.NullHandler) for h in logger.handlers):
            logger.addHandler(logging.NullHandler())
        return logger

    # Post-setup: ensure logger is configured and tracked
    an = app_name or _manager.config.app_name
    channel = (name or "common").strip(".") or "common"

    if channel == "common":
        return _manager.get_common()

    # If it already exists in manager, return it
    if channel in _manager._sub_loggers:
        return _manager._sub_loggers[channel]

    # Otherwise, create/register it now (console by default; no per-module file by default)
    spec = LoggerSpec(
        name=channel,
        filename="",  # keep empty unless you want per-module file logs
        level=_manager.config.common_level,
        mode="human",
        also_to_console=None,
        propagate=False,
    )
    return _manager.get_sublogger(spec)



def get_module_log(module_name: str, *, app_name: Optional[str] = None) -> logging.Logger:
    """Convenience wrapper for modules.

    Use this in modules as:
        log = get_module_log(__name__)

    Args:
        module_name: Typically __name__ from the calling module.
        app_name: Optional app namespace override.

    Returns:
        logging.Logger: A logger instance.
    """
    return get_log(module_name, app_name=app_name)


class LoggingManager:
    """Owns configured loggers and optional per-run directory.

    Defaults:
        - Console-only
        - No filesystem writes unless config.files=True
        - Style 1: loggers do not propagate unless explicitly requested

    Args:
        config: LoggingConfig used to build all loggers.

    Attributes:
        config: The effective LoggingConfig.
        run_id: Per-run identifier (only when files=True).
        run_dir: Per-run log directory (only when files=True).
        common_logger: The common logger for the app namespace.
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
        base = self.config.base_dir
        return base / f"{self.config.run_dir_prefix}-{self.run_id}"

    def common_log_path(self) -> Path:
        """Return the common log path (only valid when file logging is enabled).

        Returns:
            Path: Path to the common log file.

        Raises:
            RuntimeError: If file logging is disabled.
        """
        if not self.config.files or self.run_dir is None:
            raise RuntimeError("File logging is disabled; no common log path.")
        return self.run_dir / self.config.common_filename

    def sublog_path(self, filename: str) -> Path:
        """Return the sublog path in the per-run directory.

        Args:
            filename: Sublog file name.

        Returns:
            Path: Path to the sublog file.

        Raises:
            RuntimeError: If file logging is disabled.
        """
        if not self.config.files or self.run_dir is None:
            raise RuntimeError("File logging is disabled; no sublog path.")
        return self.run_dir / filename

    def dump_loggers(self) -> None:
        """Print configured loggers and their handlers/levels to stdout."""
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
        for _, logger in self._sub_loggers.items():
            describe(logger)

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
        logger.propagate = False  # Style 1: independent
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
        """Return the common logger.

        Returns:
            logging.Logger: The configured common logger.
        """
        return self.common_logger

    def log_exists(self, name: str) -> bool:
        """Return True if a logger channel has been configured.

        Args:
            name: Channel name.

        Returns:
            bool: True if known/configured, otherwise False.
        """
        if name in ("common", "", None):
            return True
        return name in self._sub_loggers

    def get_sublogger(self, spec: LoggerSpec) -> logging.Logger:
        """Return (and configure if needed) a sublogger defined by spec.

        Args:
            spec: LoggerSpec describing the channel.

        Returns:
            logging.Logger: The configured sublogger.
        """
        if spec.name in self._sub_loggers:
            return self._sub_loggers[spec.name]

        _, console_level = self._effective_levels()

        logger = logging.getLogger(_logger_full_name(self.config.app_name, spec.name))
        logger.setLevel(spec.level)
        logger.propagate = spec.propagate  # default False for Style 1
        logger.handlers.clear()

        formatter = self._formatters.get(spec.mode, self._formatters["human"])

        # File handler (only if enabled and spec.filename not empty)
        if self.config.files and spec.filename:
            fh = _rotating_file_handler(self.sublog_path(spec.filename), spec.level, formatter, self.config.rotation)
            fh.addFilter(self._context_filter)
            logger.addHandler(fh)

        # Console handler:
        # - inherit config.console by default
        # - spec.also_to_console can force True/False
        wants_console = self.config.console if spec.also_to_console is None else bool(spec.also_to_console)
        if wants_console:
            ch = _console_handler(console_level, self._formatters["human"])
            ch.addFilter(self._context_filter)
            logger.addHandler(ch)

        self._sub_loggers[spec.name] = logger
        return logger

    def child(self, name: str, *, level: int = logging.INFO, mode: str = "human") -> logging.Logger:
        """Convenience method to create/get a sublogger with defaults.

        When file logging is enabled, this creates a per-channel file `{name}.log`.
        When file logging is disabled, the logger is console-only (if enabled).

        Args:
            name: Channel name.
            level: Logger level.
            mode: Formatter mode ("human" or "kv").

        Returns:
            logging.Logger: The configured logger.
        """
        filename = f"{name}.log" if self.config.files else ""
        spec = LoggerSpec(name=name, filename=filename, level=level, mode=mode, also_to_console=None, propagate=False)
        return self.get_sublogger(spec)

    @staticmethod
    def log_error(
        logger: logging.Logger,
        msg: str,
        *args,
        exc: Optional[BaseException] = None,
        stack: bool = False,
    ) -> None:
        # Build a single safe string message, regardless of args
        if args:
            # If someone passed args, stringify them instead of using %-formatting
            msg = f"{msg} | " + " ".join(str(a) for a in args)

        if isinstance(exc, str) and exc:
            msg = f"{msg} | {exc}"
            exc = None

        if exc is None:
            logger.error("%s", msg)
            return

        if stack:
            # works best inside an except block
            logger.exception("%s | %s", msg, exc)
        else:
            logger.error("%s | %s", msg, exc)


def setup_logging(
    app_name: str,
    base_dir: Path = Path("logs"),
    *,
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
    """Configure and activate logging for this process.

    This should be called once, typically from your CLI entrypoint or main script.

    Safe import behavior:
        Importing this module does not create directories or attach handlers.
        Only calling this function does.

    Environment overrides (optional):
        - LOG_FILES=1 enables file logging.
        - LOG_DIR overrides base_dir.
        - LOG_LEVEL / LOG_CONSOLE_LEVEL override levels.

    Args:
        app_name: Namespace prefix for all loggers created by this kit.
        base_dir: Base directory for per-run logs (used only when file logging enabled).
        console: If True, enable console handler(s).
        files: If True, enable per-run file logging. Can also be enabled via LOG_FILES.
        common_filename: Common log filename (used only when files enabled).
        common_level: Level for the common logger.
        console_level: Level for console handlers.
        rotation_max_bytes: Rotation threshold for log files.
        rotation_backup_count: Number of rotated files to keep.
        formatter_mode: Formatter mode for file logs ("human" or "kv").
        utc_timestamps: If True, timestamps are UTC (recommended for servers).
        sublogs: Optional LoggerSpec definitions to instantiate at setup time.

    Returns:
        LoggingManager: The active manager instance.
    """
    global _manager

    # Env overrides for files/dir
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

def log_failure(log, message: str, exc=None, details: str | None = None, stack: bool = False):
    """
    Safe logging helper:
    - exc can be an Exception OR a string traceback/message
    - details is optional extra text
    - stack=True logs stack trace if exc is an Exception
    """
    parts = [message]

    if details:
        parts.append(details)

    # If exc is a string, treat it as details (NOT as a formatting arg)
    if isinstance(exc, str) and exc:
        parts.append(exc)
        exc = None

    final = " | ".join(parts)

    if exc is not None and stack:
        log.exception(final)  # includes stack trace from the active exception context
    elif exc is not None:
        log.error("%s: %s", final, exc)  # safe placeholder formatting
    else:
        log.error(final)