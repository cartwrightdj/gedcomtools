"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/converter_base.py
 Purpose: Abstract base class for all GEDCOM → GedcomX converters.

 Created: 2026-03-31
======================================================================
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gedcomx import GedcomX


class GxConverterBase(ABC):
    """Minimal contract shared by all GEDCOM-to-GedcomX converters.

    Concrete implementations:
    * :class:`~gedcomtools.gedcomx.conversion.GedcomConverter` — GEDCOM 5.x → GedcomX
    * :class:`~gedcomtools.gedcom7.g7togx.Gedcom7Converter`    — GEDCOM 7   → GedcomX
    """

    @abstractmethod
    def convert(self, source) -> "GedcomX":
        """Convert *source* and return a populated :class:`GedcomX` object."""
        ...
