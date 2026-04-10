"""
======================================================================
 Project: gedcomtools
 File:    gedcom.py
 Author:  David J. Cartwright
 Purpose: Top-level Gedcom helper for reading GEDCOM file version info

 Created: 2025-07-01
 Updated:

======================================================================
"""

from .glog import get_logger
# ======================================================================
# Logging
# ======================================================================
log = get_logger(__name__)
serial_log = "gedcomx.serialization"
#=====================================================================

class Gedcom():
    """Provide the high-level facade for loading and working with GEDCOM data."""
    def __init__(self) -> None:
        pass

    @staticmethod
    def read_gedcom_version(filepath: str) -> str | None:
        """
        Reads only the HEAD section of a GEDCOM file and returns the GEDCOM standard version.
        Looks specifically for HEAD → GEDC → VERS.
        
        Returns:
            str: GEDCOM version (e.g., "5.5.1" or "7.0.0"), or None if not found.
        """
        version = None
        inside_head = False
        inside_gedc = False

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(maxsplit=2)
                if not parts:
                    continue

                level = int(parts[0])
                tag = parts[1] if len(parts) > 1 else ""
                value = parts[2] if len(parts) > 2 else None

                # Enter HEAD
                if level == 0 and tag == "HEAD":
                    inside_head = True
                    continue

                # Leave HEAD block
                if inside_head and level == 0:
                    break

                # Inside HEAD, look for GEDC
                if inside_head and level == 1 and tag == "GEDC":
                    inside_gedc = True
                    continue

                # If we drop back to level 1 (but not GEDC), stop looking inside GEDC
                if inside_gedc and level == 1:
                    inside_gedc = False

                # Inside GEDC, look for VERS
                if inside_gedc and tag == "VERS":
                    version = value
                    break

        return version
