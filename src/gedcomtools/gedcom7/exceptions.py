"""
======================================================================
 Project: gedcomtools
 File:    gedcom7/Exceptions.py
 Author:  David J. Cartwright
 Purpose: Exception hierarchy for the GEDCOM 7 parser and validator.

 Created: 2026-03-01
 Updated:
   - 2026-03-16: added GedcomParseError; wired into loadfile(); added header
   - 2026-03-16: removed unused GedcomInvalidSubStructure (dead code)
======================================================================

Exception classes for gedcom7.
"""

from __future__ import annotations


class GedcomError(Exception):
    """Base class for all GEDCOM 7 errors."""


class GedcomParseError(GedcomError):
    """Raised when a GEDCOM file cannot be opened or is structurally invalid."""
