from __future__ import annotations

from typing import Any, ClassVar, List, Optional, Union

from .date import Date
from .evidence_reference import EvidenceReference
from .identifier import IdentifierList
from .note import Note
from .resource import Resource
from .source_reference import SourceReference
from .subject import Subject
from .textvalue import TextValue
from .uri import URI


class PlaceDescription(Subject):
    """PlaceDescription describes the details of a place in terms of its name
    and possibly its type, time period, and/or a geospatial description.
    """

    identifier: ClassVar[str] = "http://gedcomx.org/v1/PlaceDescription"
    version: ClassVar[str] = "http://gedcomx.org/conceptual-model/v1"

    names: Optional[List[TextValue]] = None
    type: Optional[str] = None  # TODO: replace with enumeration
    place: Optional[URI] = None
    jurisdiction: Optional[Any] = None  # Resource | PlaceDescription
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    temporalDescription: Optional[Date] = None
    spatialDescription: Optional[Any] = None  # PlaceReference
