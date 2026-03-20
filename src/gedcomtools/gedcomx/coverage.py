from __future__ import annotations
from typing import ClassVar, Optional

from .date import Date
from .gx_base import GedcomXModel
from .place_reference import PlaceReference


class Coverage(GedcomXModel):
    identifier: ClassVar[str] = "http://gedcomx.org/v1/Coverage"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    spatial: Optional[PlaceReference] = None
    temporal: Optional[Date] = None
