"""
Logging hub — backward-compatible wrapper backed by loguru.

Exports:
    hub          LoggingHub instance (no side effects at import time)
    ChannelConfig
    logging      stdlib logging module (re-exported for call-site compat)

Previously this module ran four blocks of initialization at import time
(os.makedirs, hub.init_root(), hub.start_channel() × 3).  That is now fixed:
importing this module is safe and has no I/O side effects.

Configure logging from your entrypoint:
    from gedcomtools.loggingkit import setup_logging
    setup_logging("gedcomtools", files=True)

Or add channels directly wherever you need them:
    from gedcomtools.logging_hub import hub, ChannelConfig
    hub.start_channel(ChannelConfig(name="myjob", path="logs/myjob.log"))
"""
from __future__ import annotations

import logging          # re-exported for call-site backward compat
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Dict, Optional

from loguru import logger as _logger


# ─────────────────────────────────────────────────────────────────────────────
# ChannelConfig  (kept for import compat)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ChannelConfig:
    """Configuration for a named log channel / sink.

    Attributes:
        name:     Channel name used to route records via hub.use(name).
        path:     File path for the sink; None => StreamHandler (console).
        level:    Minimum level for this sink (stdlib int constant).
        fmt:      Kept for API compat; loguru uses its own format string.
        datefmt:  Kept for API compat.
        rotation: Rotation spec string:
                    None                  — plain FileHandler
                    "size:10MB:3"         — RotatingFileHandler
                    "time:midnight:7"     — TimedRotatingFileHandler
    """
    name: str
    path: Optional[str] = None
    level: int = logging.INFO
    fmt: str = "[%(asctime)s] %(levelname)s %(log_channel)s %(name)s: %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"
    rotation: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _parse_size(s: str) -> int:
    s = s.strip().upper()
    if s.endswith("MB"):
        return int(s[:-2]) * 1024 * 1024
    if s.endswith("KB"):
        return int(s[:-2]) * 1024
    return int(s)


_SINK_FMT = (
    "{time:YYYY-MM-DDTHH:mm:ss} | {level:<8} | "
    "{extra[channel]} | {extra[module]} | {message}"
)


class _HubLogger:
    """Thin wrapper exposing the stdlib Logger interface via loguru.

    Handles both %-style args (``log.debug("msg %s", val)``) and plain
    f-strings (``log.debug(f"msg {val}")``) transparently.
    """

    __slots__ = ("_bound",)

    def __init__(self, name: str) -> None:
        self._bound = _logger.bind(module=name)

    # format %-style args the same way stdlib logging does
    @staticmethod
    def _fmt(msg: str, args: tuple) -> str:
        if args:
            try:
                return msg % args
            except Exception:
                return f"{msg} {args}"
        return msg

    def debug(self, msg: str, *args, **_) -> None:
        self._bound.opt(depth=1).debug(self._fmt(msg, args))

    def info(self, msg: str, *args, **_) -> None:
        self._bound.opt(depth=1).info(self._fmt(msg, args))

    def warning(self, msg: str, *args, **_) -> None:
        self._bound.opt(depth=1).warning(self._fmt(msg, args))

    # keep warn() as an alias (stdlib has it)
    warn = warning

    def error(self, msg: str, *args, **_) -> None:
        self._bound.opt(depth=1).error(self._fmt(msg, args))

    def exception(self, msg: str, *args, **_) -> None:
        self._bound.opt(depth=1, exception=True).error(self._fmt(msg, args))

    def critical(self, msg: str, *args, **_) -> None:
        self._bound.opt(depth=1).critical(self._fmt(msg, args))

    def log(self, level, msg: str, *args, **_) -> None:
        name = logging.getLevelName(level) if isinstance(level, int) else str(level)
        self._bound.opt(depth=1).log(name, self._fmt(msg, args))


# ─────────────────────────────────────────────────────────────────────────────
# LoggingHub
# ─────────────────────────────────────────────────────────────────────────────

class LoggingHub:
    """Context-aware logging hub backed by loguru.

    Preserves the existing call-site API:

        log = hub.get_logger("mymodule")
        log.info("processing %s", name)

        if hub.log_enabled:            # kill-switch guard (optional with loguru)
            log.debug("verbose %s", detail)

        with hub.use("serialization"):
            log.debug("goes to serialization sink")

        hub.start_channel(ChannelConfig(name="job", path="logs/job.log"))

    No I/O happens at construction time; only start_channel() writes files.
    """

    def __init__(self, root_name: str = "gedcomx") -> None:
        self.root_name = root_name
        self._sink_ids: Dict[str, int] = {}
        self._enabled: bool = True

    def init_root(self) -> None:
        """No-op: loguru does not need explicit root initialisation."""

    # ── Logger acquisition ────────────────────────────────────────────────────

    def get_logger(self, name: Optional[str] = None) -> _HubLogger:
        """Return a logger bound to *name* (defaults to the hub root name)."""
        return _HubLogger(name or self.root_name)

    # ── Kill switch ───────────────────────────────────────────────────────────

    @property
    def log_enabled(self) -> bool:
        return self._enabled

    @log_enabled.setter
    def log_enabled(self, value: bool) -> None:
        self._enabled = bool(value)
        if self._enabled:
            _logger.enable("")
        else:
            _logger.disable("")

    # deprecated aliases — kept for backward compatibility
    @property
    def logEnabled(self) -> bool:
        return self.log_enabled

    @logEnabled.setter
    def logEnabled(self, value: bool) -> None:
        self.log_enabled = value

    @property
    def logging_enabled(self) -> bool:
        return self.log_enabled

    @logging_enabled.setter
    def logging_enabled(self, value: bool) -> None:
        self.log_enabled = value

    @property
    def loggingenable(self) -> bool:
        return self.log_enabled

    @loggingenable.setter
    def loggingenable(self, value: bool) -> None:
        self.log_enabled = value

    def enable_all(self) -> None:
        self.log_enabled = True

    def disable_all(self) -> None:
        self.log_enabled = False

    def is_enabled(self) -> bool:
        return self._enabled

    def hard_disable(self) -> None:
        """Suppress all Python logging (including third-party libs)."""
        logging.disable(logging.CRITICAL + 1)

    def hard_enable(self) -> None:
        logging.disable(logging.NOTSET)

    # ── Channel context ───────────────────────────────────────────────────────

    @contextmanager
    def use(self, channel: str):
        """Route log records to *channel* within this with-block."""
        with _logger.contextualize(channel=channel):
            yield

    @contextmanager
    def muted(self):
        """Temporarily suppress all logging within this with-block."""
        prev = self._enabled
        try:
            self.log_enabled = False
            yield
        finally:
            self.log_enabled = prev

    def set_current(self, name: str) -> None:
        """No-op: use hub.use() for channel context switching."""

    def set_default_channel(self, name: str) -> None:
        """No-op: loguru routes records by context extra."""

    # ── Channel / sink management ─────────────────────────────────────────────

    def start_channel(
        self,
        cfg: ChannelConfig,
        make_current: bool = False,
        enabled: bool = True,
    ) -> None:
        """Add (or replace) a loguru sink for *cfg.name*.

        Records reach this sink only when inside ``hub.use(cfg.name)``.
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
            rotation = parts[1]          # e.g. "midnight"
            retention = int(parts[2]) if len(parts) > 2 else 7

        channel_name = cfg.name
        lvl = logging.getLevelName(cfg.level)

        kwargs: dict = dict(
            format=_SINK_FMT,
            level=lvl,
            encoding="utf-8",
            filter=lambda r, ch=channel_name: r["extra"].get("channel") == ch,
        )
        if rotation is not None:
            kwargs["rotation"] = rotation
        if retention is not None:
            kwargs["retention"] = retention

        if cfg.path:
            os.makedirs(os.path.dirname(os.path.abspath(cfg.path)), exist_ok=True)
            sid = _logger.add(cfg.path, **kwargs)
        else:
            # console sink — no channel filter so it catches everything
            del kwargs["filter"]
            sid = _logger.add(sys.stdout, **kwargs)

        self._sink_ids[cfg.name] = sid

    def stop_channel(self, name: str) -> None:
        if name in self._sink_ids:
            try:
                _logger.remove(self._sink_ids.pop(name))
            except Exception:
                pass

    def enable(self, name: str) -> None:
        """Per-channel enable (no-op; use stop_channel / start_channel)."""

    def disable(self, name: str) -> None:
        """Per-channel disable (no-op; use stop_channel)."""

    def list_channels(self) -> Dict[str, bool]:
        return {name: True for name in self._sink_ids}

    def has_channel(self, name: str) -> bool:
        return name in self._sink_ids


# ─────────────────────────────────────────────────────────────────────────────
# Module-level hub instance  — NO side effects beyond object creation
# ─────────────────────────────────────────────────────────────────────────────

hub = LoggingHub("gedcomx")


# ─────────────────────────────────────────────────────────────────────────────
# Keep contextvars helpers for any code that imported them directly
# ─────────────────────────────────────────────────────────────────────────────

import contextvars as _cv

_current_channel: _cv.ContextVar[str] = _cv.ContextVar(
    "current_log_channel", default="default"
)


def get_current_channel() -> str:
    return _current_channel.get()


def set_current_channel(name: str) -> None:
    _current_channel.set(name)
