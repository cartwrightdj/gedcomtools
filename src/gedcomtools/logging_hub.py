from __future__ import annotations
"""
======================================================================
 Project: gedcomtools
 File:    logging_hub.py
 Author:  David J. Cartwright
 Purpose: Backward-compatibility re-export stub — use glog instead

 Created: 2025-07-01
 Updated:
   - 2026-03-17: consolidated into glog.py; this file is a re-export stub

======================================================================
"""
# All symbols previously exported from this module now live in glog.
# This stub keeps existing ``from .logging_hub import ...`` imports working.
from .glog import (  # noqa: F401
    hub,
    logging,
    ChannelConfig,
    get_logger,
    get_log,
    LoggingHub,
    LoggingManager,
    setup_logging,
)
