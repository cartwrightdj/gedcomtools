"""
======================================================================
 Project: Gedcom-X
 File:    gedcomx/coverage.py
 Author:  David J. Cartwright
 Purpose: GedcomX Coverage model: temporal and spatial scope of a source description

 Created: 2025-08-25
 Updated:
======================================================================
"""
from __future__ import annotations
from typing import ClassVar, Optional

from .date import Date
from .gx_base import GedcomXModel
from .place_reference import PlaceReference


class Coverage(GedcomXModel):
    """Describes the temporal and spatial scope of a source description."""

    identifier: ClassVar[str] = "http://gedcomx.org/v1/Coverage"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    spatial: Optional[PlaceReference] = None
    temporal: Optional[Date] = None

    def _validate_self(self, result) -> None:
        super()._validate_self(result)
        from .validation import check_instance
        if self.spatial is None and self.temporal is None:
            result.warn("", "Coverage has neither spatial nor temporal component")
        check_instance(result, "spatial", self.spatial, PlaceReference)
        check_instance(result, "temporal", self.temporal, Date)
