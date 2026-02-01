#!/usr/bin/env python3
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
from __future__ import annotations

import logging
import contextvars
import os
from contextlib import contextmanager
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from typing import Dict, Optional

# ──────────────────────────────────────────────────────────────────────────────
# Context: which "channel" (log) is current?
# ──────────────────────────────────────────────────────────────────────────────
_current_channel: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_log_channel", default="default"
)


def get_current_channel() -> str:
    return _current_channel.get()


def set_current_channel(name: str) -> None:
    _current_channel.set(name)


# ──────────────────────────────────────────────────────────────────────────────
# Filters and Formatter
# ──────────────────────────────────────────────────────────────────────────────
class ChannelFilter(logging.Filter):
    """Injects the current channel into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Always ensure log_channel exists
        record.log_channel = getattr(record, "log_channel", get_current_channel())
        return True


class KillSwitchFilter(logging.Filter):
    """Fast global on/off. Returning False drops the record early."""

    def __init__(self) -> None:
        super().__init__()
        self._enabled: bool = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = bool(value)

    def filter(self, record: logging.LogRecord) -> bool:
        return self._enabled


class ChannelFormatter(logging.Formatter):
    """
    Formatter that guarantees `record.log_channel` exists, so that
    format strings using %(log_channel)s never raise KeyError.
    """

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "log_channel"):
            record.log_channel = get_current_channel()
        return super().format(record)


class DispatchingHandler(logging.Handler):
    """
    Routes records to a per-channel handler (file/stream),
    based on LogRecord.log_channel (set by ChannelFilter / ChannelFormatter).
    """

    def __init__(self):
        super().__init__()
        self._channel_handlers: Dict[str, logging.Handler] = {}
        self._enabled: Dict[str, bool] = {}
        self._default_channel = "default"

    def set_default_channel(self, name: str) -> None:
        self._default_channel = name

    def add_channel(
        self, name: str, handler: logging.Handler, enabled: bool = True
    ) -> None:
        self._channel_handlers[name] = handler
        self._enabled[name] = enabled

    def enable(self, name: str) -> None:
        self._enabled[name] = True

    def disable(self, name: str) -> None:
        self._enabled[name] = False

    def remove_channel(self, name: str) -> None:
        h = self._channel_handlers.pop(name, None)
        self._enabled.pop(name, None)
        if h:
            try:
                h.flush()
                h.close()
            except Exception:
                pass

    def has_channel(self, name: str) -> bool:
        return name in self._channel_handlers

    def emit(self, record: logging.LogRecord) -> None:
        channel = getattr(record, "log_channel", None) or self._default_channel
        handler = self._channel_handlers.get(channel) or self._channel_handlers.get(
            self._default_channel
        )
        if not handler:
            return  # nothing to write to
        if not self._enabled.get(channel, True):
            return  # channel muted
        handler.emit(record)


# ──────────────────────────────────────────────────────────────────────────────
# Configuration model
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class ChannelConfig:
    name: str
    path: Optional[str] = None
    level: int = logging.INFO
    fmt: str = (
        "[%(asctime)s] %(levelname)s %(log_channel)s %(name)s: %(message)s"
    )
    datefmt: str = "%Y-%m-%d %H:%M:%S"
    rotation: Optional[str] = None
    # rotation options:
    #   None                     -> plain FileHandler
    #   "size:10MB:3"            -> RotatingFileHandler(maxBytes=10MB, backupCount=3)
    #   "time:midnight:7"        -> TimedRotatingFileHandler(when="midnight", backupCount=7)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _parse_size_to_bytes(size_spec: str) -> int:
    """
    Parse size strings like '10MB', '512KB', '1000' into bytes.
    """
    s = size_spec.strip().upper()
    if s.endswith("MB"):
        return int(s[:-2]) * 1024 * 1024
    if s.endswith("KB"):
        return int(s[:-2]) * 1024
    # plain integer assumed to be bytes
    return int(s)


# ──────────────────────────────────────────────────────────────────────────────
# Hub
# ──────────────────────────────────────────────────────────────────────────────
class LoggingHub:
    """
    Centralized, context-aware logging hub.

    Example:
        hub = LoggingHub()
        hub.init_root()
        hub.start_channel(ChannelConfig(name="default", path="logs/app.log"), make_current=True)

        log = hub.get_logger("gedcomx")
        if hub.logging_enabled:               # cheap guard to avoid formatting
            log.info("hello %s", "world")

        with hub.use("import-job-42"):
            log.info("within job 42")
    """

    def __init__(self, root_logger_name: str = "gedcomx"):
        self.root_name = root_logger_name
        self._root = logging.getLogger(self.root_name)
        self._dispatch = DispatchingHandler()
        self._root.setLevel(logging.DEBUG)  # Handlers/filters determine final behavior

        self._filter = ChannelFilter()
        self._killswitch = KillSwitchFilter()
        self._initialized = False

    # -------- Initialization --------
    def init_root(self) -> None:
        if self._initialized:
            return
        # Clean existing handlers on the root logger (optional safety)
        for h in list(self._root.handlers):
            self._root.removeHandler(h)

        # Order matters: kill-switch first for fastest early exit.
        self._root.addFilter(self._killswitch)
        self._root.addFilter(self._filter)
        self._root.addHandler(self._dispatch)
        self._initialized = True

        # Optional: env bootstrap
        if os.getenv("GEDCOMX_LOG", "1").lower() in {"0", "false", "off"}:
            self.disable_all()
        if os.getenv("GEDCOMX_LOG_HARD", "0") == "1":
            self.hard_disable()

    # -------- Channel Management --------
    def start_channel(
        self, cfg: ChannelConfig, make_current: bool = False, enabled: bool = True
    ) -> None:
        """Create/replace a channel with a file/rotating handler."""
        # Use our ChannelFormatter with a safe default for log_channel
        formatter = ChannelFormatter(
            cfg.fmt,
            datefmt=cfg.datefmt,
            defaults={"log_channel": "default"},
        )

        if cfg.path is None:
            handler: logging.Handler = logging.StreamHandler()
        else:
            # Rotation options
            if cfg.rotation and cfg.rotation.startswith("size:"):
                # "size:10MB:3"
                _, size_str, backups_str = cfg.rotation.split(":")
                max_bytes = _parse_size_to_bytes(size_str)
                backup_count = int(backups_str)
                handler = RotatingFileHandler(
                    cfg.path,
                    maxBytes=max_bytes,
                    backupCount=backup_count,
                    encoding="utf-8",
                )
            elif cfg.rotation and cfg.rotation.startswith("time:"):
                # "time:midnight:7" or "time:H:24"
                parts = cfg.rotation.split(":")
                when = parts[1]
                backup_count = int(parts[2]) if len(parts) > 2 else 7
                handler = TimedRotatingFileHandler(
                    cfg.path,
                    when=when,
                    backupCount=backup_count,
                    encoding="utf-8",
                    utc=False,
                )
            else:
                handler = logging.FileHandler(cfg.path, encoding="utf-8")

        handler.setLevel(cfg.level)
        handler.setFormatter(formatter)

        # Replace if exists
        if self._dispatch.has_channel(cfg.name):
            self._dispatch.remove_channel(cfg.name)
        self._dispatch.add_channel(cfg.name, handler, enabled=enabled)

        if make_current:
            self.set_current(cfg.name)

    def stop_channel(self, name: str) -> None:
        self._dispatch.remove_channel(name)

    def enable(self, name: str) -> None:
        self._dispatch.enable(name)

    def disable(self, name: str) -> None:
        self._dispatch.disable(name)

    def list_channels(self) -> Dict[str, bool]:
        """Return dict of channel -> enabled?"""
        return {name: enabled for name, enabled in self._dispatch._enabled.items()}

    # -------- Current Channel --------
    def set_current(self, name: str) -> None:
        set_current_channel(name)

    @contextmanager
    def use(self, name: str):
        """Temporarily switch to a channel within a with-block."""
        token = _current_channel.set(name)
        try:
            yield
        finally:
            _current_channel.reset(token)

    # -------- Global kill switch (soft) --------
    def enable_all(self) -> None:
        self._killswitch.enabled = True

    def disable_all(self) -> None:
        self._killswitch.enabled = False

    def is_enabled(self) -> bool:
        return self._killswitch.enabled

    @property
    def logging_enabled(self) -> bool:
        """Preferred property name."""
        return self._killswitch.enabled

    @logging_enabled.setter
    def logging_enabled(self, value: bool) -> None:
        self._killswitch.enabled = bool(value)

    # Alias to match your requested spelling: hub.loggingenable
    @property
    def loggingenable(self) -> bool:
        return self.logging_enabled

    @loggingenable.setter
    def loggingenable(self, value: bool) -> None:
        self.logging_enabled = bool(value)

    # Older camelCase alias you used earlier
    @property
    def logEnabled(self) -> bool:
        return self.logging_enabled

    @logEnabled.setter
    def logEnabled(self, value: bool) -> None:
        self.logging_enabled = bool(value)

    @contextmanager
    def muted(self):
        """Temporarily mute all logging in a with-block."""
        prev = self._killswitch.enabled
        try:
            self._killswitch.enabled = False
            yield
        finally:
            self._killswitch.enabled = prev

    # -------- Hard nuke (affects 3rd-party libs too) --------
    def hard_disable(self) -> None:
        # Drop all messages of all loggers by using a level above CRITICAL
        logging.disable(100)

    def hard_enable(self) -> None:
        logging.disable(0)

    # -------- Convenience --------
    def set_default_channel(self, name: str) -> None:
        self._dispatch.set_default_channel(name)

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """Get a named logger under the hub root."""
        if not name:
            return self._root
        return logging.getLogger(f"{self.root_name}.{name}")


# ──────────────────────────────────────────────────────────────────────────────
# Hub instance & sample bootstrap
# ──────────────────────────────────────────────────────────────────────────────
hub = LoggingHub("gedcomx")  # app logger root
hub.init_root()  # do this ONCE at startup

os.makedirs("logs", exist_ok=True)

# 1) Start a default channel (file w/ daily rotation)
hub.start_channel(
    ChannelConfig(
        name="default",
        path="logs/app.log",
        level=logging.INFO,
        fmt="[%(asctime)s] %(levelname)s %(log_channel)s %(name)s: %(message)s",
        rotation="time:midnight:7",
    ),
    make_current=True,
)

serial_log = "gedcomx.serialization"
deserial_log = "gedcomx.deserialization"

hub.start_channel(
    ChannelConfig(
        name=serial_log,
        path=f"logs/{serial_log}.log",
        level=logging.DEBUG,
        fmt="%(asctime)s [%(levelname)s] [%(log_channel)s] %(message)s",
        rotation="size:20MB:100",
    )
)

hub.start_channel(
    ChannelConfig(
        name=deserial_log,
        path=f"logs/{deserial_log}.log",
        level=logging.DEBUG,
        fmt="%(asctime)s [%(levelname)s] [%(log_channel)s] %(message)s",
        rotation="size:10MB:3",
    )
)

# (optional) Also a console channel you can switch to
hub.start_channel(
    ChannelConfig(
        name="console",
        path=None,
        level=logging.DEBUG,
        fmt="[%(asctime)s] %(levelname)s %(log_channel)s %(name)s: %(message)s",
    )
)
