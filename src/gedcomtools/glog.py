from __future__ import annotations
# ======================================================================
#  Project: gedcomtools
#  File:    glog.py
#  Author:  David J. Cartwright
#  Purpose: Unified loguru-based logging for all gedcomtools modules
#  Created: 2026-03-17
# ======================================================================
# Unified logging module backed by loguru.
#
# All modules obtain a logger with:
#     from gedcomtools.glog import get_logger
#     log = get_logger(__name__)
#
# Entrypoint setup (call once from CLI / main):
#     from gedcomtools.glog import setup_logging
#     setup_logging("gedcomtools", console=True, files=False)
#
# Channel context (route records to a named sink):
#     with hub.use("serialization"):
#         log.debug("goes to the serialization sink")
#
# Environment variables (set in .env or shell — take effect on import):
#     LOG_LEVEL           level for all sinks (e.g. DEBUG, INFO, WARNING, ERROR)
#     LOG_CONSOLE_LEVEL   overrides LOG_LEVEL for the console sink only
#     LOG_CONSOLE         truthy (1/true/yes/on) = enable console; falsy = disable
#     LOG_FILES           truthy (1/true/yes/on) enables per-run file logging
#     LOG_FILE            path to a single log file (alternative to LOG_FILES/LOG_DIR)
#     LOG_DIR             base directory for per-run file logging
#     GEDCOMTOOLS_DEBUG   shortcut: sets level=DEBUG, enables console + file

import logging as _stdlib_logging
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Generator, Optional, Sequence, Union

from dotenv import load_dotenv
from loguru import logger as _logger
from loguru import _Logger as Logger

# Load .env from the project root (or CWD) so env vars are available before
# any module-level code reads them.  override=False means real env vars win.
load_dotenv(override=False)

# Ensure format-string extras never raise KeyError on unbound loggers.
_logger.configure(extra={"module": "", "channel": ""})

# Re-exported so legacy call-sites (`from .glog import logging`) keep working.
logging = _stdlib_logging


# ─────────────────────────────────────────────────────────────────────────────
# Format strings
# ─────────────────────────────────────────────────────────────────────────────

_CONSOLE_FMT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level:<8}</level> | "
    "<cyan>{extra[module]}</cyan> - <level>{message}</level>"
)

_FILE_FMT = (
    "{time:YYYY-MM-DDTHH:mm:ssZ} | {level:<8} | "
    "{extra[module]} | {extra[channel]} | {message}"
)

_SINK_FMT = (
    "{time:YYYY-MM-DDTHH:mm:ss} | {level:<8} | "
    "{extra[channel]} | {extra[module]} | {message}"
)


# ─────────────────────────────────────────────────────────────────────────────
# Config dataclasses
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class RotationConfig:
    """File-sink rotation settings."""
    max_bytes: int = 10 * 1024 * 1024   # 10 MB
    backup_count: int = 10


@dataclass(frozen=True)
class FormatterConfig:
    """Formatter settings (kept for API compatibility)."""
    mode: str = "human"   # "human" | "kv"
    utc: bool = True


@dataclass(frozen=True)
class LoggerSpec:
    """Definition of a named sub-logger / channel.

    Attributes:
        name:            Channel name (e.g. "graph", "io").
        filename:        File name for this channel when file logging is on.
                         Empty string disables file output for this channel.
        level:           Logger level (int or level-name string).
        mode:            Formatter mode ("human" | "kv").
        also_to_console: None = inherit config.console; True/False = force.
        propagate:       Kept for API compat; loguru does not use this field.
    """
    name: str
    filename: str = ""
    level: Union[int, str] = 20   # INFO
    mode: str = "human"
    also_to_console: Optional[bool] = None
    propagate: bool = False


@dataclass(frozen=True)
class LoggingConfig:
    """Full logging configuration snapshot stored on the active manager."""
    app_name: str = "app"
    files: bool = False
    base_dir: Path = Path("logs")
    run_dir_prefix: str = "run"
    common_filename: str = "common.log"
    common_level: Union[int, str] = 20
    console: bool = True
    console_level: Union[int, str] = 20
    rotation: RotationConfig = field(default_factory=RotationConfig)
    formatter: FormatterConfig = field(default_factory=FormatterConfig)
    sublogs: Sequence[LoggerSpec] = field(default_factory=tuple)


@dataclass
class ChannelConfig:
    """Configuration for a named log channel / file sink.

    Attributes:
        name:     Channel name — used as ``hub.use(name)`` context key.
        path:     File path for the sink; None → console (stdout).
        level:    Minimum level for this sink (stdlib int constant).
        fmt:      Kept for API compat; loguru uses its own format string.
        datefmt:  Kept for API compat.
        rotation: Rotation spec:
                    None                  — plain file, no rotation
                    "size:10MB:3"         — rotate at 10 MB, keep 3
                    "time:midnight:7"     — daily at midnight, keep 7
    """
    name: str
    path: Optional[str] = None
    level: int = _stdlib_logging.INFO
    fmt: str = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"
    rotation: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

_LEVEL_MAP: Dict[Union[int, str], str] = {
    10: "DEBUG", 20: "INFO", 30: "WARNING", 40: "ERROR", 50: "CRITICAL",
    "DEBUG": "DEBUG", "INFO": "INFO",
    "WARNING": "WARNING", "WARN": "WARNING",
    "ERROR": "ERROR", "CRITICAL": "CRITICAL",
    "NOTSET": "TRACE",
}


def _to_level(level: Union[int, str]) -> str:
    """Normalise a stdlib int level or string to a loguru level name."""
    if isinstance(level, str):
        return _LEVEL_MAP.get(level.strip().upper(), "INFO")
    return _LEVEL_MAP.get(level, "INFO")


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S", time.localtime())


def _parse_size(s: str) -> int:
    s = s.strip().upper()
    if s.endswith("MB"):
        return int(s[:-2]) * 1024 * 1024
    if s.endswith("KB"):
        return int(s[:-2]) * 1024
    return int(s)


# ─────────────────────────────────────────────────────────────────────────────
# LoggingManager
# ─────────────────────────────────────────────────────────────────────────────

class LoggingManager:
    """Owns the active loguru sink IDs and run directory for this process.

    Returned by ``setup_logging()``.  Also accessible via ``get_manager()``.
    """

    def __init__(
        self,
        config: LoggingConfig,
        run_dir: Optional[Path],
        sink_ids: list[int],
    ) -> None:
        self.config = config
        self.run_dir = run_dir
        self.run_id = run_dir.name.split("-", 1)[-1] if run_dir else ""
        self._sink_ids = sink_ids

    def get_common(self) -> Logger:
        """Return a logger bound to the common app channel."""
        return _logger.bind(module=f"{self.config.app_name}.common")

    def child(self, name: str, **_) -> Logger:
        """Return a logger bound to ``app_name.name``."""
        return _logger.bind(module=f"{self.config.app_name}.{name}")

    def common_log_path(self) -> Path:
        """Return the path of the catch-all log file (file logging only)."""
        if not self.run_dir:
            raise RuntimeError("File logging is disabled; no common log path.")
        return self.run_dir / self.config.common_filename

    def sublog_path(self, filename: str) -> Path:
        """Return the path of a named sublog file (file logging only)."""
        if not self.run_dir:
            raise RuntimeError("File logging is disabled; no sublog path.")
        return self.run_dir / filename

    def dump_sinks(self) -> None:
        """Print a summary of active loguru sinks to stdout."""
        print(f"=== glog (loguru) — {len(self._sink_ids)} active sink(s) ===")
        for i, sid in enumerate(self._sink_ids):
            print(f"  sink[{i}] id={sid}")


# ─────────────────────────────────────────────────────────────────────────────
# LoggingHub — channel context manager and sink registry
# ─────────────────────────────────────────────────────────────────────────────

class LoggingHub:
    """Context-aware logging hub backed by loguru.

    Provides channel context switching (``hub.use("channel")``), a global
    enable/disable toggle, and named file-sink management.

    Typical usage::

        log = get_logger(__name__)

        with hub.use("serialization"):
            log.debug("routed to the serialization sink")

        hub.start_channel(ChannelConfig(name="job", path="logs/job.log"))

    No I/O occurs at construction time.
    """

    def __init__(self, root_name: str = "gedcomtools") -> None:
        self.root_name = root_name
        self._sink_ids: Dict[str, int] = {}
        self._enabled: bool = True

    # ── logger acquisition ────────────────────────────────────────────────────

    def get_logger(self, name: Optional[str] = None) -> Logger:
        """Return a loguru logger bound to *name* (defaults to root_name)."""
        return _logger.bind(module=name or self.root_name)

    # ── enable / disable ──────────────────────────────────────────────────────

    @property
    def log_enabled(self) -> bool:
        """Whether logging is currently enabled."""
        return self._enabled

    @log_enabled.setter
    def log_enabled(self, value: bool) -> None:
        self._enabled = bool(value)
        if self._enabled:
            _logger.enable("")
        else:
            _logger.disable("")

    def enable_all(self) -> None:
        """Re-enable all logging."""
        self.log_enabled = True

    def disable_all(self) -> None:
        """Disable all logging."""
        self.log_enabled = False

    def is_enabled(self) -> bool:
        """Return True if logging is currently enabled."""
        return self._enabled

    # ── context managers ──────────────────────────────────────────────────────

    @contextmanager
    def use(self, channel: str) -> Generator[None, None, None]:
        """Route log records to *channel* for the duration of this block."""
        with _logger.contextualize(channel=channel):
            yield

    @contextmanager
    def muted(self) -> Generator[None, None, None]:
        """Temporarily suppress all logging within this block."""
        prev = self._enabled
        try:
            self.log_enabled = False
            yield
        finally:
            self.log_enabled = prev

    # ── sink management ───────────────────────────────────────────────────────

    def start_channel(
        self,
        cfg: ChannelConfig,
        enabled: bool = True,
    ) -> None:
        """Add (or replace) a loguru sink described by *cfg*.

        File records reach this sink only when inside ``hub.use(cfg.name)``.

        Args:
            cfg:     Channel configuration.
            enabled: If False the channel is removed but no new sink is added.
        """
        self.stop_channel(cfg.name)
        if not enabled:
            return

        rotation = None
        retention = None
        if cfg.rotation and cfg.rotation.startswith("size:"):
            _, size_str, count_str = cfg.rotation.split(":")
            rotation = _parse_size(size_str)
            retention = int(count_str)
        elif cfg.rotation and cfg.rotation.startswith("time:"):
            parts = cfg.rotation.split(":")
            rotation = parts[1]
            retention = int(parts[2]) if len(parts) > 2 else 7

        channel_name = cfg.name
        lvl = _stdlib_logging.getLevelName(cfg.level)

        kwargs: dict = {
            "format": _SINK_FMT,
            "level": lvl,
            "encoding": "utf-8",
            "filter": lambda r, ch=channel_name: r["extra"].get("channel") == ch,
        }
        if rotation is not None:
            kwargs["rotation"] = rotation
        if retention is not None:
            kwargs["retention"] = retention

        if cfg.path:
            Path(cfg.path).resolve().parent.mkdir(parents=True, exist_ok=True)
            sid = _logger.add(cfg.path, **kwargs)
        else:
            del kwargs["filter"]
            sid = _logger.add(sys.stderr, **kwargs)

        self._sink_ids[cfg.name] = sid

    def stop_channel(self, name: str) -> None:
        """Remove the sink for *name* if it exists."""
        if name in self._sink_ids:
            try:
                _logger.remove(self._sink_ids.pop(name))
            except ValueError:
                pass

    def has_channel(self, name: str) -> bool:
        """Return True if a sink named *name* is active."""
        return name in self._sink_ids

    def list_channels(self) -> Dict[str, bool]:
        """Return a mapping of channel name → enabled (always True if present)."""
        return {name: True for name in self._sink_ids}


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton  — no I/O at import time
# ─────────────────────────────────────────────────────────────────────────────

hub = LoggingHub("gedcomtools")

_manager: Optional[LoggingManager] = None


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def get_logger(name: str = "gedcomtools") -> Logger:
    """Return a loguru logger bound to *name*.

    Safe to call at module level before ``setup_logging()``::

        log = get_logger(__name__)

    Args:
        name: Logger name, typically ``__name__``.

    Returns:
        Logger: loguru logger with ``extra["module"]`` bound to *name*.
    """
    return _logger.bind(module=name)


# Aliases kept for backward compatibility with loggingkit import sites.
get_log = get_logger
get_module_log = get_logger


def get_manager() -> Optional[LoggingManager]:
    """Return the active ``LoggingManager``, or ``None`` if not yet configured."""
    return _manager


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

    Importing this module is safe and has no I/O side-effects.  Only calling
    this function creates directories or attaches handlers.

    Args:
        app_name:              Namespace prefix for all loggers.
        base_dir:              Base directory for per-run log files.
        console:               Enable console (stdout) output.
        files:                 Enable per-run file logging.
        common_filename:       Filename for the catch-all log (files only).
        common_level:          Level for file sinks.
        console_level:         Level for the console sink.
        rotation_max_bytes:    Rotate file after this many bytes.
        rotation_backup_count: Number of rotated files to keep.
        formatter_mode:        "human" or "kv" (reserved for future use).
        utc_timestamps:        Use UTC timestamps in file sinks.
        sublogs:               Per-channel ``LoggerSpec`` list.

    Returns:
        LoggingManager: the newly activated manager.
    """
    global _manager  # pylint: disable=global-statement

    # env overrides
    env_debug         = _env_truthy("GEDCOMTOOLS_DEBUG")
    env_level         = os.getenv("LOG_LEVEL", "").strip().upper()
    env_console_level = os.getenv("LOG_CONSOLE_LEVEL", "").strip().upper()
    env_console_raw   = os.getenv("LOG_CONSOLE", "").strip().lower()
    env_files         = _env_truthy("LOG_FILES")
    env_file          = os.getenv("LOG_FILE", "").strip()
    env_dir           = os.getenv("LOG_DIR", "").strip()

    if env_debug:
        env_level = env_level or "DEBUG"
        env_console_level = env_console_level or "DEBUG"
        env_files = env_files or True

    eff_level         = _to_level(env_level or common_level)
    eff_console_level = _to_level(env_console_level or console_level)
    eff_files         = files or env_files or bool(env_file)
    eff_base_dir      = Path(env_dir) if env_dir else base_dir

    # LOG_CONSOLE explicitly set overrides the caller's console arg
    if env_console_raw in {"1", "true", "yes", "y", "on"}:
        console = True
    elif env_console_raw in {"0", "false", "no", "n", "off"}:
        console = False

    # tear down previous configuration
    if _manager is not None:
        for sid in _manager._sink_ids:
            try:
                _logger.remove(sid)
            except ValueError:
                pass

    # remove loguru's default stderr sink on first call
    try:
        _logger.remove(0)
    except ValueError:
        pass

    sink_ids: list[int] = []

    if console:
        sid = _logger.add(
            sys.stderr,
            format=_CONSOLE_FMT,
            level=eff_console_level,
            colorize=True,
        )
        sink_ids.append(sid)

    run_dir: Optional[Path] = None
    if eff_files:
        if env_file:
            # LOG_FILE: single named file, no run-subdirectory
            log_path = Path(env_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            sid = _logger.add(
                str(log_path),
                format=_FILE_FMT,
                level=eff_level,
                rotation=rotation_max_bytes,
                retention=rotation_backup_count,
                encoding="utf-8",
            )
            sink_ids.append(sid)
        else:
            run_dir = eff_base_dir / f"run-{_new_run_id()}"
            run_dir.mkdir(parents=True, exist_ok=True)

            sid = _logger.add(
                str(run_dir / common_filename),
                format=_FILE_FMT,
                level=eff_level,
                rotation=rotation_max_bytes,
                retention=rotation_backup_count,
                encoding="utf-8",
            )
            sink_ids.append(sid)

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
            rotation=RotationConfig(
                max_bytes=rotation_max_bytes,
                backup_count=rotation_backup_count,
            ),
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
    exc: Optional[BaseException] = None,
    details: Optional[str] = None,
    stack: bool = False,
) -> None:
    """Log an error, optionally attaching exception info and a detail string.

    Args:
        log:     Logger to emit on.
        message: Primary error message.
        exc:     Exception instance (optional).
        details: Extra detail string appended after a pipe separator.
        stack:   If True and *exc* is set, include a full stack trace.
    """
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


# ─────────────────────────────────────────────────────────────────────────────
# Auto-configure on import
# ─────────────────────────────────────────────────────────────────────────────
# Apply env-var configuration as soon as this module is imported so that
# LOG_LEVEL / LOG_CONSOLE / LOG_FILE etc. take effect without the caller
# needing to explicitly invoke setup_logging().
#
# Only runs when no manager has been set up yet (i.e. the CLI hasn't already
# called setup_logging() before import).  The default is INFO on console only
# — set LOG_LEVEL=WARNING to silence routine conversion chatter.

def _auto_configure() -> None:
    global _manager  # pylint: disable=global-statement
    if _manager is not None:
        return  # already configured by an explicit setup_logging() call

    has_any_env = any([
        os.getenv("LOG_LEVEL"),
        os.getenv("LOG_CONSOLE_LEVEL"),
        os.getenv("LOG_CONSOLE"),
        os.getenv("LOG_FILES"),
        os.getenv("LOG_FILE"),
        os.getenv("LOG_DIR"),
        os.getenv("GEDCOMTOOLS_DEBUG"),
    ])

    if not has_any_env:
        # Nothing set — leave loguru's default stderr handler alone so we
        # don't produce unexpected output in libraries and test runs.
        return

    setup_logging(
        app_name="gedcomtools",
        console=True,
        files=False,
        common_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
        console_level=os.getenv("LOG_LEVEL", "INFO").strip().upper(),
    )


_auto_configure()
