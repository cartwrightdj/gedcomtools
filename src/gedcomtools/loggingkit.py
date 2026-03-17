from __future__ import annotations
"""
======================================================================
 Project: gedcomtools
 File:    loggingkit.py
 Author:  David J. Cartwright
 Purpose: Backward-compatibility re-export stub — use glog instead

 Created: 2025-07-01
 Updated:
   - 2026-03-17: consolidated into glog.py; this file is a re-export stub

======================================================================
"""
# All symbols previously exported from this module now live in glog.
# This stub keeps existing ``from gedcomtools.loggingkit import ...`` imports working.
from .glog import (  # noqa: F401
    hub,
    logging,
    get_logger,
    get_log,
    get_module_log,
    get_manager,
    setup_logging,
    log_failure,
    LoggingManager,
    LoggingConfig,
    LoggerSpec,
    RotationConfig,
    FormatterConfig,
    ChannelConfig,
)
